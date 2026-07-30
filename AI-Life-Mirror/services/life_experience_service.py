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
        session.current_age += 1
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

    # ★ 从 ChromaDB 检索全部相关记忆注入场景
    memory_snippets = []
    try:
        from services.vector_store import search
        # 多角度检索，每个查询多取结果，尽量覆盖全部记忆
        top_traits = sorted([(k,v) for k,v in traits.items() if not k.startswith("_")], key=lambda x:-x[1])[:5]
        queries = [
            " ".join([t[0] for t in top_traits]),
            " ".join([e.get("event","") for e in (event_log or [])[-3:]]),
            "人生经历 成长 转折 选择",
            " ".join([t[0] for t in top_traits[:2]]) + " 经历",
        ]
        seen = set()
        for q in queries:
            if not q.strip(): continue
            results = search(session.user_id, q, n_results=8)
            for r in results:
                txt = r.get("content", "") if isinstance(r, dict) else str(r)
                if txt and txt not in seen:
                    seen.add(txt)
                    memory_snippets.append(txt[:200])
        import logging; logging.getLogger(__name__).info(f"Retrieved {len(memory_snippets)} memories for scene")
    except Exception:
        pass
    memory_snippet = "\n".join([f"- {m}" for m in memory_snippets]) if memory_snippets else ""

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
        memory_text = f"\n## 用户的全部长期记忆（必须在叙事中自然融入至少1-2段）\n{memory_snippet}" if memory_snippet else "\n## 用户暂无长期记忆，基于人格权重生成通用叙事"

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
- ★ 叙事必须基于用户的长期记忆推演——如果记忆中有具体事件（如"参加过FTC机器人比赛"），在叙事中自然地回忆起来
- ★ 记忆中提到的人和事，可以合理地在场景中延续或发展
- 选择项要体现真实的人生取舍——有得有失，不可能全都要
- gain要具体，cost也要真实。每个选择都有代价。
- 不要写"+5技能"这种游戏化表达，用生活中的自然语言
- 人格倾向（专注度/独立性/探索欲/社交需求/抗挫力）是稳定的，短期不怎么变
- 成长能力（技术能力/表达力/管理能力/行动力）可以被事件改变
- 叙事应该和用户真实记忆中的兴趣、经历保持一致——不要编造用户从未接触过的领域

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
    """规则引擎生成叙事场景 — 基于人格权重 + 事件历史"""
    year = session.current_year
    age = session.current_age
    tech = traits.get("技术能力", 50)
    creativity = traits.get("创造力", traits.get("探索欲", 50))
    social = traits.get("社交需求", traits.get("表达力", 50))
    focus = traits.get("专注度", 50)
    resilience = traits.get("抗挫力", 50)
    action = traits.get("行动力", 50)

    memory_hint = f"你偶尔回想起：{memory_snippet[:80]}" if memory_snippet else ""

    # 多种场景模板，基于权重选择
    scenes = []
    if tech >= 60:
        scenes.append({
            "narrative": f"{year}年，{age}岁。一个技术难题已经困扰你几周了。深夜的屏幕光映在你脸上——你比大多数人有耐心，但这个问题需要的也许不只是耐心。{memory_hint}",
            "choices": [
                {"text": "继续独立钻研，直到攻克", "gain": "完全掌握核心技术，建立深度自信", "cost": "社交圈进一步缩小，可能错过外部机会"},
                {"text": "向更有经验的人请教", "gain": "快速突破瓶颈，建立有价值的人脉", "cost": "需要放弃'自己解决一切'的习惯，短期的自尊受挫"},
                {"text": "暂时搁置，转向其他方向积累", "gain": "避免钻牛角尖，保持心态健康", "cost": "这个难题可能会一直留在你的'未完成'清单里"},
            ],
        })
    if creativity >= 60 or action >= 60:
        scenes.append({
            "narrative": f"{year}年，{age}岁。一个念头突然冒了出来——你看到了一个别人没注意到的可能性。但想法和现实之间的距离，需要一步一步走过去。{memory_hint}",
            "choices": [
                {"text": "立刻动手，试错中前进", "gain": "抢占先机，在实践中快速学习", "cost": "可能浪费时间和资源在错误的方向上"},
                {"text": "先做市场调研和详细规划", "gain": "降低风险，提高成功率", "cost": "可能错过最好的时机，热情也可能在规划中消退"},
                {"text": "找一个互补的伙伴一起启动", "gain": "弥补自己的短板，分享风险和压力", "cost": "需要分权分利，理念可能产生分歧"},
            ],
        })
    if social >= 55:
        scenes.append({
            "narrative": f"{year}年，{age}岁。你身边出现了一些有趣的人——有人邀请你参与一个项目，有人想和你聊聊人生方向。你的社交圈子正在发生微妙的变化。{memory_hint}",
            "choices": [
                {"text": "积极参与，拓展人脉和机会", "gain": "打开新的可能性，获得意想不到的资源", "cost": "时间被分散，深度工作的时间减少"},
                {"text": "谨慎选择，只投入最重要的关系", "gain": "维护高质量的连接，不影响主要目标", "cost": "可能错过一些'看起来不重要但实际很重要'的人和事"},
                {"text": "保持距离，专注于自己的事情", "gain": "深度聚焦，产出最大化", "cost": "长期来看，孤军奋战的天花板可能来得更早"},
            ],
        })

    if not scenes:
        scenes = [{
            "narrative": f"{year}年，{age}岁。日子一天天过去，你偶尔会想：按照现在这个轨迹走下去，五年后的自己会是什么样？",
            "choices": [
                {"text": "保持现状，稳步积累", "gain": "稳定可预期的成长", "cost": "可能错过转折性的机会"},
                {"text": "主动寻求改变，尝试新的方向", "gain": "打开新的可能性", "cost": "意味着放弃已经积累的部分成果"},
                {"text": "先花时间想清楚自己到底想要什么", "gain": "减少盲目行动带来的浪费", "cost": "思考太多而行动太少，可能一直停留在原地"},
            ],
        }]

    # 随机选取但保证连续两年不重复
    import random as _random
    r = _random.Random(session.random_seed + year)
    idx = r.randint(0, len(scenes) - 1)
    if event_log and event_log[-1].get("year", 0) == year - 1:
        # 和上一年同一类型就换一个
        idx = (idx + 1) % len(scenes)

    return scenes[idx]


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

    # 基于人格权重 + 选择内容计算结果
    r = random.Random(session.random_seed + session.current_year * 100 + choice_index)
    luck = r.randint(-10, 15)

    # 根据选择文本的内容判断选择类型
    txt = chosen.get("text", "")
    gain = chosen.get("gain", "")
    cost = chosen.get("cost", "")

    if any(w in txt for w in ["请教", "合作", "团队", "伙伴", "参与", "人脉", "社交", "分享"]):
        # 社交/合作型选择
        success_base = (traits.get("社交需求", 50) + traits.get("表达力", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你走出了自己的小世界。{'这次连接带来了意想不到的收获。' if success > 50 else '社交让你有些疲惫，但有些关系会慢慢沉淀下来。'}"
        trait_changes = {"社交需求": 3, "表达力": 2, "专注度": -1, "抗挫力": 1} if success > 50 else {"抗挫力": 2, "专注度": -2}
    elif any(w in txt for w in ["钻研", "技术", "独立", "自己", "专注", "深入"]):
        # 独立/深度型选择
        success_base = (traits.get("专注度", 50) + traits.get("技术能力", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你选择了深入。{'这段时间的专注带来了扎实的进步。' if success > 50 else '独自前行的路上也有迷茫，但你正在变得更坚韧。'}"
        trait_changes = {"专注度": 3, "技术能力": 2, "社交需求": -1, "抗挫力": 2} if success > 50 else {"抗挫力": 3, "专注度": -1}
    elif any(w in txt for w in ["动手", "试错", "冒险", "改变", "挑战", "立刻", "尝试", "创业"]):
        # 行动/冒险型选择
        success_base = (traits.get("行动力", 50) + traits.get("探索欲", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你迈出了这一步。{'行动带来了实实在在的改变。' if success > 50 else '虽然结果不如预期，但你对自己的选择有了更深的理解。'}"
        trait_changes = {"行动力": 3, "探索欲": 2, "专注度": -2, "抗挫力": 2} if success > 50 else {"抗挫力": 4, "行动力": -1}
    else:
        # 思考/规划型选择
        success_base = (traits.get("专注度", 50) + traits.get("抗挫力", 50)) // 2
        success = min(90, success_base + luck)
        outcome = f"你选择了停下来想一想。{'这段时间的思考让你对方向更清晰了。' if success > 50 else '想得太多而行动太少，你隐约感到有些焦虑。'}"
        trait_changes = {"专注度": 2, "行动力": -1, "探索欲": 1, "抗挫力": 1}

    # 检测重大生活事件
    life_state_change = {}
    if any(w in txt for w in ["创业", "自己干", "独立"]):
        life_state_change = {"创业": "进行中", "自由度": "↑"}
    elif any(w in txt for w in ["合作", "团队", "伙伴", "加入"]):
        life_state_change = {"协作": "团队模式", "独立性": "↓"}

    return {
        "chosen": chosen_text,
        "outcome": outcome,
        "trait_changes": trait_changes,
        "life_state_change": life_state_change,
        "event": scene.get("narrative", "")[:80],
    }


async def get_session(db: AsyncSession, session_id: int) -> Optional[SimulationSession]:
    return await db.get(SimulationSession, session_id)
