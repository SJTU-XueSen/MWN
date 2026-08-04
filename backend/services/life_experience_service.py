"""人生拟真体验服务 — 用户选择未来人格后进入的逐年叙事模拟

场景与选择全部由当前人格状态 + ChromaDB 真实记忆驱动。
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import LLM_ENABLED
from backend.database.models import FutureSelf, SimulationSession
from backend.services.llm_service import _call_deepseek

logger = logging.getLogger(__name__)

STABLE_TRAITS = ["专注度", "独立性", "探索欲", "社交需求", "抗挫力"]
GROWING_TRAITS = ["技术能力", "表达能力", "管理能力", "行动力"]

_DEFAULT_TRAITS = {"专注度": 50, "独立性": 50, "探索欲": 50, "社交需求": 50, "抗挫力": 50,
                   "技术能力": 30, "表达能力": 30, "管理能力": 30, "行动力": 40}


def _init_traits(future: FutureSelf) -> dict:
    """从未来人格 profile 初始化人格权重"""
    traits = dict(_DEFAULT_TRAITS)
    profile = future.profile or {}
    shift = profile.get("persona_shift", {}) or {}
    for key, arrow in shift.items():
        if key in traits:
            delta = 8 if "↑" in str(arrow) else (-8 if "↓" in str(arrow) else 0)
            traits[key] = min(95, max(5, traits[key] + delta))
    return traits


async def start_experience(db: AsyncSession, user_id: int, future_self_id: int):
    """开始一次拟真体验"""
    future = await db.get(FutureSelf, future_self_id)
    if not future or future.user_id != user_id:
        raise ValueError("future_self_not_found")

    now_year = datetime.utcnow().year
    session = SimulationSession(
        user_id=user_id,
        future_self_id=future.id,
        simulation_id=future.simulation_id,
        random_seed=42,
        start_year=now_year,
        current_year=now_year,
        current_age=22,
        persona_snapshot=_init_traits(future),
        current_state=_init_traits(future),
        event_log=[],
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: int):
    return await db.get(SimulationSession, session_id)


async def _llm_scene(session: SimulationSession, memories: list[str]):
    """LLM 生成场景（失败返回 None → 规则回退）"""
    if not LLM_ENABLED:
        return None
    traits_text = json.dumps(session.current_state or {}, ensure_ascii=False)
    memories_text = "\n".join(f"- {m[:120]}" for m in memories[:6]) or "(无)"
    prompt = f"""你在为一个用户生成"人生拟真体验"的年度场景。

当前年份：{session.current_year}
当前人格状态：{traits_text}

用户的真实记忆（场景必须与这些记忆中的兴趣与经历方向一致，不要编造用户从未接触的领域）：
{memories_text}

请生成 3 个选择，格式 JSON：
{{"narrative": "一年一景的叙事描述（120字以内，中文）", "choices": [{{"text": "选项A（20字内）", "gain": "可能获得什么", "cost": "可能需要放下什么"}}, ...]}}

约束：选项要能体现不同人格倾向的代价权衡，不设置好坏选项。
只返回 JSON。"""
    raw = await _call_deepseek("你是人生叙事引擎。", prompt, temperature=0.7, max_tokens=600)
    if raw:
        try:
            import json as _json

            data = _json.loads(raw.strip().strip("`").lstrip("json\n"))
            if data.get("narrative") and data.get("choices"):
                return data
        except Exception:
            pass
    return None


def _rule_scene(session: SimulationSession):
    """规则引擎场景（基于当前人格状态动态生成）"""
    traits = session.current_state or {}
    year = session.current_year

    if traits.get("探索欲", 50) >= 55:
        narrative = f"这一年，{year} 年。你感到熟悉的生活正在向你发出挑战——新的领域、新的问题不断出现，内心有个声音在问：要不要走得更远一点？"
        choices = [
            {"text": "接受邀请，踏入新领域", "gain": "探索欲+、技术能力+", "cost": "专注度-、稳定性-"},
            {"text": "留在熟悉的赛道深耕", "gain": "专注度+、专业能力+", "cost": "探索欲-、新鲜感-"},
            {"text": "边做边看，保持观望", "gain": "抗挫力+", "cost": "行动力-"},
        ]
    elif traits.get("社交需求", 50) >= 55:
        narrative = f"{year} 年。这一年里，人的连接变得比事情本身更重要。一次合作、一次对话，可能改变你对某件事的看法。"
        choices = [
            {"text": "主动组织一次跨团队协作", "gain": "管理能力+、社交需求+", "cost": "独立时间-"},
            {"text": "深入一段关系，认真倾听", "gain": "共情+、社交需求+", "cost": "独处空间-"},
            {"text": "保持距离，专注自己的事", "gain": "专注度+", "cost": "社交需求-"},
        ]
    else:
        narrative = f"{year} 年。日子平稳向前，你在自己的节奏里慢慢积累。这一年没有大事发生——但那些微小的坚持，正在悄悄改变你。"
        choices = [
            {"text": "坚持每天固定的积累", "gain": "坚持+、专业能力+", "cost": "新鲜感-"},
            {"text": "尝试一次小型突破", "gain": "行动力+、探索欲+", "cost": "稳定性-"},
            {"text": "放慢脚步，重新整理方向", "gain": "自我认知+", "cost": "进度-"},
        ]
    return {"narrative": narrative, "choices": choices}


async def generate_scene(db: AsyncSession, session: SimulationSession, last_result: dict = None):
    """生成当前年份场景（LLM 优先 + 规则回退），注入 Chroma 真实记忆"""
    memories = []
    try:
        from backend.services.vector_store import search

        memories = [r.get("content", str(r)) for r in search(session.user_id, "人生经历 选择 成长", n_results=6) if r]
    except Exception:
        pass

    scene = await _llm_scene(session, memories)
    if scene is None:
        scene = _rule_scene(session)

    scene["current_traits"] = session.current_state or {}
    scene["trait_deltas"] = {}
    if last_result:
        scene["trait_deltas"] = last_result.get("trait_deltas", {})
    return scene


def _apply_trait_change(traits: dict, deltas: dict) -> dict:
    """人格状态应用变化（增量合并，边界 5-95）"""
    new_traits = dict(traits)
    for key, delta in deltas.items():
        if key in new_traits:
            new_traits[key] = min(95, max(5, new_traits[key] + delta))
    return new_traits


async def process_choice(db: AsyncSession, session: SimulationSession, choice_idx: int, scene: dict) -> dict:
    """处理用户选择：更新人格状态、推进年份、记录事件"""
    choices = scene.get("choices", [])
    if not choices:
        raise ValueError("no_choices")
    choice = choices[min(choice_idx, len(choices) - 1)]

    # 人格变化（基于选项 gain/cost 关键词）
    deltas = {}
    gain = str(choice.get("gain", ""))
    cost = str(choice.get("cost", ""))
    for trait in STABLE_TRAITS + GROWING_TRAITS:
        if trait in gain:
            deltas[trait] = 4
        elif trait in cost:
            deltas[trait] = -3

    traits = _apply_trait_change(session.current_state or {}, deltas)
    session.current_state = traits
    session.current_year += 1
    if session.current_age is not None:
        session.current_age += 1

    event_log = list(session.event_log or [])
    event_log.append({
        "year": session.current_year - 1,
        "choice": choice.get("text", ""),
        "outcome": f"{gain}；{cost}",
    })
    session.event_log = event_log
    if session.current_year - session.start_year >= 15:
        session.status = "finished"
    await db.commit()
    await db.refresh(session)

    return {
        "year": session.current_year - 1,
        "choice": choice.get("text", ""),
        "gain": gain,
        "cost": cost,
        "trait_deltas": deltas,
        "current_traits": traits,
    }
