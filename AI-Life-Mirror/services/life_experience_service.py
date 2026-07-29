"""
人生拟真体验服务 — 基于人格权重的条件叙事模拟

核心理念：不是预测，而是基于当前人格状态的推演。
每一次模拟都是独立不可再现的人生。
"""
import json
import random
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SimulationSession, FutureSelf, PersonaProfile
from config import LLM_ENABLED

logger = logging.getLogger(__name__)


async def start_experience(
    db: AsyncSession,
    user_id: int,
    future_self_id: int,
    start_year: int = 2032,
) -> SimulationSession:
    """开始一次人生拟真体验"""

    future_self = await db.get(FutureSelf, future_self_id)
    persona = (await db.execute(
        select(PersonaProfile).where(
            PersonaProfile.user_id == user_id,
            PersonaProfile.is_current == True,
        ).limit(1)
    )).scalar_one_or_none()

    # ★ 人格倾向（稳定，短期不变）+ 成长能力（可变，受事件影响）
    if persona and persona.ability_profile:
        ab = persona.ability_profile
        personality = {
            "专注度": min(95, ab.get("自我认知", ab.get("self_awareness", 50))),
            "独立性": min(95, ab.get("创造力", ab.get("creative", 50)) + 10),
            "探索欲": min(95, ab.get("创造力", ab.get("creative", 50))),
            "社交需求": min(95, ab.get("社交力", ab.get("social", 50))),
        }
        abilities = {
            "技术能力": min(95, ab.get("技术能力", ab.get("tech", 50))),
            "表达能力": max(20, ab.get("社交力", ab.get("social", 30)) - 10),
            "行动力": max(20, ab.get("创造力", ab.get("creative", 40)) - 5),
            "管理能力": 30,
        }
    else:
        personality = {"专注度": 50, "独立性": 50, "探索欲": 50, "社交需求": 50}
        abilities = {"技术能力": 50, "表达能力": 30, "行动力": 50, "管理能力": 25}

    if persona and persona.behavior_profile:
        bp = persona.behavior_profile
        personality["抗挫力"] = min(95, 100 - bp.get("回避型", bp.get("回避", 30)))
    else:
        personality["抗挫力"] = 50

    traits = {**personality, **abilities}

    random_seed = random.randint(10000, 99999)

    session = SimulationSession(
        user_id=user_id,
        future_self_id=future_self_id,
        simulation_id=future_self.simulation_id if future_self else None,
        random_seed=random_seed,
        start_year=start_year,
        current_year=start_year,
        current_age=22 + (start_year - 2026),
        persona_snapshot=traits,
        current_state=dict(traits),
        event_log=[],
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


async def generate_scene(
    db: AsyncSession,
    session: SimulationSession,
    choice_result: Optional[dict] = None,
) -> dict:
    """生成当前场景：叙事文本 + 选择项"""

    traits = session.current_state or session.persona_snapshot or {}
    event_log = session.event_log or []

    # 应用上一次选择的影响
    if choice_result:
        for trait, delta in choice_result.get("trait_changes", {}).items():
            traits[trait] = max(10, min(95, traits.get(trait, 50) + delta))

        # ★ 追踪重大生活状态变化
        life_state = (session.current_state or {}).get("_life_state", {})
        life_change = choice_result.get("life_state_change", {})
        life_state.update(life_change)
        traits["_life_state"] = life_state

        event_log.append({
            "year": session.current_year,
            "event": choice_result.get("event", ""),
            "choice": choice_result.get("chosen", ""),
            "outcome": choice_result.get("outcome", ""),
            "life_state": dict(life_state),
        })

        session.current_state = traits
        session.event_log = event_log
        session.current_year += 1
        await db.commit()

    # 计算与初始状态的差异
    initial = session.persona_snapshot or {}
    trait_deltas = {}
    for k, v in traits.items():
        if k.startswith("_"): continue
        old = initial.get(k, 50)
        if v != old:
            trait_deltas[k] = v - old

    # ★ 当前生活状态（从上一次选择继承）
    life_state = traits.get("_life_state", {})
    life_context = ""
    if life_state:
        life_context = "当前生活状态：" + "、".join([f"{k}={v}" for k, v in life_state.items()])

    # ★ 从 ChromaDB 检索一段相关记忆注入场景
    memory_snippet = ""
    try:
        from services.vector_store import search
        results = search(session.user_id, "人生经历 转折 成长", n_results=1)
        if results:
            memory_snippet = results[0].get("content", "")[:150] if isinstance(results[0], dict) else str(results[0])[:150]
    except Exception:
        pass

    # 生成叙事
    if LLM_ENABLED:
        scene = await _llm_scene(traits, event_log, session, memory_snippet, life_context)
        if scene:
            scene["trait_deltas"] = trait_deltas
            scene["current_traits"] = traits
            return scene

    scene = _rule_scene(traits, event_log, session, memory_snippet)
    scene["trait_deltas"] = trait_deltas
    scene["current_traits"] = traits
    return scene


async def _llm_scene(traits: dict, event_log: list, session: SimulationSession, memory_snippet: str = "", life_context: str = "") -> Optional[dict]:
    """LLM 生成叙事场景"""
    try:
        import httpx
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

        traits_text = "\n".join([f"{k}: {v}" for k, v in traits.items()])
        history_text = ""
        for e in event_log[-3:]:
            history_text += f"{e['year']}年：{e['event']} → 选择了「{e['choice']}」 → {e['outcome']}\n"
        memory_text = f"\n## 用户的一段真实记忆（可在叙事中自然地回忆起来）\n{memory_snippet}" if memory_snippet else ""

        prompt = f"""你是一个人生叙事引擎。基于用户的人格权重生成一段人生场景。{memory_text}

## ★ 当前生活状态（上一年的选择带来的持续影响）
{life_context if life_context else '(初始状态)'}

## 当前人格权重（0-100）
{traits_text}

## 近期经历
{history_text if history_text else '(这是你的第一年)'}

## 当前信息
年份：{session.current_year}年
年龄：{session.current_age}岁
随机种子：{session.random_seed}

## 请生成一段场景
格式为 JSON：
{{
  "narrative": "一段200字以内的人生叙事，描述这一年发生了什么。用第二人称'你'。风格：像一段回忆或日记。要有细节，像一个真实的人生片段",
  "choices": [
    {{"text": "选择描述A", "gain": "这么做能得到什么", "cost": "这么做会失去什么", "hint": "基于人格权重的概率提示"}},
    {{"text": "选择描述B", "gain": "得到", "cost": "失去", "hint": "概率提示"}},
    {{"text": "选择描述C", "gain": "得到", "cost": "失去", "hint": "概率提示"}}
  ]
}}

要求：
- 叙事基于人格权重推演，不是随机编造
- 选择项要体现真实的人生取舍——有得有失，不可能全都要
- gain要具体，cost也要真实。每个选择都有代价。
- 不要写"+5技能"这种游戏化表达，用生活中的自然语言
- 人格倾向（专注度/独立性/探索欲/社交需求/抗挫力）是稳定的，短期不怎么变
- 成长能力（技术能力/表达力/管理能力/行动力）可以被事件改变

只返回 JSON。"""

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6, "max_tokens": 800,
                    "response_format": {"type": "json_object"},
                },
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(content)
    except Exception as e:
        logger.warning(f"LLM scene failed: {e}")
    return None


def _rule_scene(traits: dict, event_log: list, session: SimulationSession, memory_snippet: str = "") -> dict:
    """规则引擎生成叙事场景"""
    year = session.current_year
    creativity = traits.get("创造力", 50)
    discipline = traits.get("自律", 50)
    tech = traits.get("技术能力", 50)

    # 基于权重选择场景类型
    if tech > 60:
        narrative = f"{year}年，你正深入一个技术项目。每天花大量时间调试和优化——这让你感到充实，但也开始意识到自己很少与人交流。"
        choices = [
            {"text": "继续深入技术，追求完美", "hint": f"基于你的技术能力({tech})，成功率较高"},
            {"text": "花时间参与团队讨论和分享", "hint": "可能降低短期产出，但打开新的合作机会"},
            {"text": "暂时放下项目，给自己一个喘息的机会", "hint": f"自律度({discipline})决定你能否在休息后重新投入"},
        ]
    elif creativity > 60:
        narrative = f"{year}年，一个新的想法让你兴奋不已。你在笔记本上画满了草图，但把想法变成现实需要的不只是灵感。"
        choices = [
            {"text": "立刻开始动手实现", "hint": f"创造力({creativity})很高，但需要执行力配合"},
            {"text": "先做详细规划再行动", "hint": "降低失败风险，但可能损失热情和时机"},
            {"text": "找一个伙伴一起做", "hint": f"社交力({traits.get('社交力', 50)})影响合作效果"},
        ]
    else:
        narrative = f"{year}年，日子平淡但安稳。你在按部就班地推进手头的事，偶尔会想：这是不是我想要的生活？"
        choices = [
            {"text": "接受现状，稳步前进", "hint": "稳定积累，但可能错过意外机会"},
            {"text": "主动寻求变化和挑战", "hint": "可能打破舒适区，带来新的可能"},
            {"text": "花时间思考自己真正想要什么", "hint": "不急于行动，但方向比速度更重要"},
        ]

    return {"narrative": narrative, "choices": choices}


async def process_choice(
    db: AsyncSession,
    session: SimulationSession,
    choice_index: int,
    scene: dict,
) -> dict:
    """处理用户选择，返回结果并更新人格权重"""
    choices = scene.get("choices", [])
    if choice_index >= len(choices):
        choice_index = 0

    chosen = choices[choice_index]
    traits = session.current_state or {}

    # 基于人格权重计算结果
    r = random.Random(session.random_seed + session.current_year * 100 + choice_index)
    luck = r.randint(-15, 15)  # 随机因子

    if choice_index == 0:  # 积极/主动选择
        success_base = (traits.get("行动力", 50) + traits.get("专注度", 50)) // 2
        success = min(95, success_base + luck)
        outcome = f"你的行动带来了变化。{'一切比预期顺利。' if success > 60 else '过程虽有波折，但你坚持了下来。'}"
        trait_changes = {"行动力": 3, "专注度": 2, "表达力": -1, "社交需求": -1} if success > 50 else {"抗挫力": 3, "表达力": -2}
    elif choice_index == 1:  # 平衡/中间选择
        success_base = (traits.get("专注度", 50) + traits.get("探索欲", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你选择了折中的方式。{'平衡带来了稳定。' if success > 50 else '有些事需要更果断的决策。'}"
        trait_changes = {"专注度": 2, "探索欲": 1, "行动力": -2, "独立性": -1}
    else:  # 冒险/变化选择
        success_base = (traits.get("探索欲", 50) + traits.get("抗挫力", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你走出了舒适区。{'这次冒险是值得的。' if success > 50 else '结果不如预期，但你学到了很多。'}"
        trait_changes = {"探索欲": 3, "抗挫力": 2, "专注度": -3, "行动力": -1} if success > 50 else {"抗挫力": 5, "专注度": -2}

    # ★ 检测重大生活事件并标记状态变化
    life_state_change = {}
    chosen_text = chosen.get("text", "")
    if "辞职" in chosen_text or "离开" in chosen_text or "放弃" in chosen_text:
        life_state_change = {"就业": "已辞职", "稳定性": "↓"}
    elif "创业" in chosen_text or "自己" in chosen_text or "独立" in chosen_text:
        life_state_change = {"创业": "进行中", "稳定性": "↓", "自由度": "↑"}
    elif "合作" in chosen_text or "团队" in chosen_text or "伙伴" in chosen_text:
        life_state_change = {"协作模式": "团队", "独立性": "↓"}

    return {
        "chosen": chosen_text,
        "outcome": outcome,
        "trait_changes": trait_changes,
        "life_state_change": life_state_change,
        "event": scene.get("narrative", "")[:80],
    }


async def get_session(db: AsyncSession, session_id: int) -> Optional[SimulationSession]:
    return await db.get(SimulationSession, session_id)
