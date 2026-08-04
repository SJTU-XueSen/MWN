"""人生模拟服务 — ChromaDB 真实记忆锚定的 3 路径未来推演

核心：路径内容由用户真实记忆/人格/事件驱动；不编造经历、不预测职业、三路无优劣。
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import LLM_ENABLED
from backend.database.models import (
    FutureSelf,
    InterestTrack,
    LifeEvent,
    LifeGoal,
    PersonaProfile,
    Simulation,
    SimulationVariable,
)
from backend.services.llm_service import _call_deepseek, _parse_json_content

logger = logging.getLogger(__name__)

SCENARIO_LABELS = {
    "further_study": "继续深造",
    "employment": "直接就业",
    "entrepreneurship": "创业探索",
    "cross_discipline": "跨学科发展",
}


async def _collect_simulation_context(db: AsyncSession, user_id: int) -> dict:
    """收集模拟上下文：SQLite 结构化数据 + ChromaDB 语义记忆（全部真实数据）"""
    persona = (
        await db.execute(
            select(PersonaProfile).where(
                PersonaProfile.user_id == user_id, PersonaProfile.is_current == True
            ).limit(1)
        )
    ).scalar_one_or_none()
    goals = (
        await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == user_id, LifeGoal.status == "active")
            .order_by(LifeGoal.importance.desc()).limit(5)
        )
    ).scalars().all()
    interests = (
        await db.execute(
            select(InterestTrack).where(InterestTrack.user_id == user_id)
            .order_by(InterestTrack.tracked_at.desc()).limit(10)
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == user_id)
            .order_by(LifeEvent.occurred_at.desc()).limit(10)
        )
    ).scalars().all()

    chroma_memories: list[str] = []
    try:
        from backend.services.vector_store import search

        if persona and persona.persona_summary:
            query = persona.persona_summary[:200]
        elif goals:
            query = " ".join([g.title for g in goals[:3]])
        else:
            query = "人生经历 成长 兴趣"
        chroma_memories = [r.get("content", str(r)) for r in search(user_id, query, n_results=8) if r]
    except Exception as e:
        logger.debug(f"ChromaDB 检索失败: {e}")

    return {
        "persona": persona, "goals": goals, "interests": interests,
        "events": events, "chroma_memories": chroma_memories,
        "chroma_count": len(chroma_memories),
    }


def _rule_based_paths(scenario: str, question: str, context: dict) -> list:
    """规则引擎兜底路径（全部引用真实数据数量，不虚构内容）"""
    goals = context.get("goals", [])
    events = context.get("events", [])
    memories = context.get("chroma_memories", [])
    top_goal = goals[0].title if goals else "个人成长"
    memory_refs = f"基于 {len(memories)} 条长期记忆推演" if memories else "长期记忆积累中"

    return [
        {
            "label": "深度探索者",
            "path_type_hint": "在某个方向上持续深入",
            "description": f"你保留了现在对未知问题那种纯粹的好奇。比起快速得到结果，你更享受深入理解一个问题的过程。{top_goal}不是头衔——而是满足内心持续的求知欲。如果继续这样，你会成为一个在专业领域有独立见解的人。{memory_refs}",
            "persona_shift": {"专注深度": "↑", "独立思考": "↑", "社交投入": "↓", "现实反馈需求": "↓"},
            "confidence": 0.6,
            "milestones": [
                "如果持续投入某个方向，可能逐渐形成自己独特的研究方法",
                "长期专注后，可能在一个问题上积累出超越多数人的理解深度",
                "一次复杂问题的解决，可能让你更加确信这条路的适合程度",
            ],
            "turning_points": [
                "一次实验或项目失败可能让你重新审视：是方向不对，还是方法需要调整",
                "一次跨领域合作可能意外打开新的研究视角",
            ],
            "grounding": f"基于你{len(events)}个关键事件和{len(memories)}条长期记忆中的深度探索倾向推断",
            "gap_suggestions": [
                f"投入连续时间在{top_goal}上，形成自己的研究方法",
                "阅读相关领域的论文或资料，建立知识体系",
                "找一个导师或同路人交流，获得外部反馈",
            ],
        },
        {
            "label": "实践创造者",
            "path_type_hint": "将想法转化为实际产出",
            "description": f"你没有放弃创造欲——只是把它从个人探索转移到了真实场景中。你享受将技术变成产品、让想法影响更多人的过程。如果继续这样，你会成为一个能用技术解决实际问题的人——满足感来自看到自己的东西被真实使用。{memory_refs}",
            "persona_shift": {"实践能力": "↑", "用户导向思维": "↑", "技术纯粹性": "↓", "独立工作时间": "↓"},
            "confidence": 0.55,
            "milestones": [
                "如果能完成第一个被真实用户使用的项目，可能极大增强实践信心",
                "随着项目经验积累，可能逐渐形成自己的技术判断力",
                "带领或参与一个完整项目后，可能开始理解技术与商业的平衡",
            ],
            "turning_points": [
                "一次产品失败可能让你重新理解：用户真正需要的是什么",
                "可能需要放弃一些技术上的完美主义，来换取实际影响力",
            ],
            "grounding": f"基于你{len(events)}个关键事件中展现的实践创造倾向推断",
            "gap_suggestions": [
                "完成一个完整的实践项目并让真实用户使用",
                "参与或观察一个产品的完整开发流程",
                "学习如何把技术想法转化为用户能理解的语言",
            ],
        },
        {
            "label": "跨界建构者",
            "path_type_hint": "在多个领域之间建立独特连接",
            "description": f"你反复出现的'想在不同领域之间找到关联'的倾向，可能在积累足够后转化为独特的视角。你不是为了跨界而跨界——而是自然地被不同领域的交叉点吸引。你会成为一个能把看似无关的东西连接起来的人。这条路最不确定，但也最接近你内心对多元的渴望。{memory_refs}",
            "persona_shift": {"跨领域连接力": "↑", "创造性思维": "↑", "单一领域深度": "↓", "职业路径确定性": "↓"},
            "confidence": 0.45,
            "milestones": [
                "如果能在两个不同领域间完成一个交叉项目，可能第一次验证跨界方向",
                "随着在不同领域的积累，可能逐渐找到自己独特的交叉视角",
                "如果持续探索，可能在某一天发现：我的价值就在于把A和B连起来",
            ],
            "turning_points": [
                "一次合作中的理念冲突，可能让你重新思考独立探索与团队协作的平衡",
                "某个偶然的连接可能让你发现：原来这两个领域之间的交叉点才是你最擅长的地方",
            ],
            "grounding": f"基于你{len(events)}个关键事件中展现的多元探索倾向推断",
            "gap_suggestions": [
                "完成一个跨领域的小项目，验证交叉方向的价值",
                "系统学习另一个领域的基础知识",
                "找到一个也在做跨领域探索的人交流",
            ],
        },
    ]


async def _llm_paths(scenario: str, question: str, context: dict):
    """LLM 生成锚定真实记忆的 3 条未来路径（失败返回 None → 规则回退）"""
    if not LLM_ENABLED:
        return None

    persona = context.get("persona")
    goals = context.get("goals", [])
    events = context.get("events", [])
    chroma_memories = context.get("chroma_memories", [])

    persona_text = ""
    if persona:
        persona_text = f"""人格类型：{persona.persona_type}
置信度：{int(persona.confidence * 100)}%
能力画像：{json.dumps(persona.ability_profile or {}, ensure_ascii=False)}
兴趣画像：{json.dumps(persona.interest_profile or {}, ensure_ascii=False)}
价值观：{json.dumps(persona.value_profile or {}, ensure_ascii=False)}
决策风格：{json.dumps(persona.decision_style or {}, ensure_ascii=False)}
概述：{persona.persona_summary}"""
    else:
        persona_text = "(尚未生成数字人格，请基于用户的兴趣和目标推断)"

    goals_text = "\n".join([
        f"- [{g.target_period or '?'}] {g.title}（重要度{g.importance}%）{': ' + g.description if g.description else ''}"
        for g in goals
    ]) or "(无目标)"

    events_text = "\n".join([
        f"- [{e.occurred_at.strftime('%Y/%m') if e.occurred_at else '?'}] ({e.event_type}) {e.title}: {e.description or ''}"
        for e in events[:8]
    ]) or "(无事件)"

    if chroma_memories:
        memories_text = "## 用户的真实长期记忆（ChromaDB 语义检索）\n⚠️ 以下是从用户长期记忆库中检索到的真实记忆片段，路径必须与这些记忆保持一致：\n\n" + "\n".join(
            f"{i}. {mem[:200]}" for i, mem in enumerate(chroma_memories[:8], 1)
        ) + "\n"
    else:
        memories_text = "(长期记忆库暂无数据)\n"

    prompt = f"""你是一位严谨的未来学家 AI。你的任务不是凭空想象，而是基于用户真实的过去和现在，推演可能的未来。

## ⚠️ 核心约束
- 你必须基于下面提供的用户真实记忆、人格画像和经历来推演
- 不要在用户从未涉足的领域编造"天赋"或"兴趣"
- 每条路径的推理依据要能追溯到具体记忆或事件
- 如果某条记忆明确了用户的方向（如"喜欢强化学习"），路径必须反映这一点

## 用户数字人格画像
{persona_text}

## 活跃目标
{goals_text}

## 关键人生事件
{events_text}

{memories_text}

## 模拟场景
类型：{SCENARIO_LABELS.get(scenario, scenario)}
用户的问题：{question or '基于当前数据，探索不同的未来可能性'}

## 请生成 3 条差异化路径

⚠️ 核心要求：这不是职业规划。不要写"进入XX公司""成为XX职位""薪资XX"。要写的是：用户的人格特质被放大后，会成为一个怎样的人。职业结果是人格的自然延伸，不是路径的主题。

每条路径需要包含：
- label：人格化标签，中性不含贬义。不要用"深渊""独行""堕落""平庸"等负面词
- path_type_hint：简短方向说明
- description：180字以内。必须包含：保留了什么特质 + 放大了什么 + 可能放下了什么 + 为什么这还是"你自己"
- persona_shift：人格倾向变化，用 ↑↓ 表示方向而非具体数值
- confidence：0.0-1.0（未来人格匹配度——不是概率预测，而是基于当前人格，这个未来与你的内在一致性）
- milestones：3个"可能出现的人生节点"。用条件语气，不要写确定事件
- turning_points：2个可能的成长课题。不要创造具体创伤事件，写理念层面的挑战
- grounding：推导依据

输出格式：
{{"paths": [{{"label": "...", "path_type_hint": "...", "description": "...", "persona_shift": {{...}}, "confidence": 0.X, "milestones": ["可能出现1", "可能出现2", "可能出现3"], "turning_points": ["成长课题1", "成长课题2"], "grounding": "...", "gap_suggestions": ["90天建议1", "90天建议2", "90天建议3"]}}]}}

gap_suggestions 必须是每条路径专属的、有差异的90天行动建议，不能用通用模板。
三条路径不存在好坏之分，不要暗示某条路更成功。
只返回 JSON。"""

    raw = await _call_deepseek(
        "你是严谨的未来学家。基于真实数据推演，不凭空编造。输出精确 JSON。",
        prompt, temperature=0.45, max_tokens=2500,
    )
    result = _parse_json_content(raw) if raw else None
    if not result:
        return None

    paths = result.get("paths", list(result.values())[0] if result else [])
    if isinstance(paths, list):
        for path in paths:
            if isinstance(path, dict) and "gap_suggestions" not in path:
                path["gap_suggestions"] = [
                    f"在{path.get('label', '核心')}方向上完成一个实践项目",
                    "建立持续的学习和记录习惯",
                    "主动接触该方向的前辈或社群",
                ]
        return paths
    return None


async def run_simulation(
    db: AsyncSession,
    user_id: int,
    scenario: str,
    question: str = "",
    variables: dict = None,
) -> Simulation:
    """执行一次人生模拟：生成 3 路径 + FutureSelf（单事务）"""
    context = await _collect_simulation_context(db, user_id)
    persona = context.get("persona")
    persona_id = persona.id if persona else None

    paths = await _llm_paths(scenario, question, context)
    engine = "deepseek" if paths else "rule_based"
    if paths is None:
        paths = _rule_based_paths(scenario, question, context)

    sim = Simulation(
        user_id=user_id,
        persona_snapshot_id=persona_id,
        scenario_type=scenario if scenario in SCENARIO_LABELS else "further_study",
        question=question,
        input_variables=variables or {},
        output_paths=paths,
        created_at=datetime.utcnow(),
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)

    if variables:
        for name, value in variables.items():
            db.add(SimulationVariable(simulation_id=sim.id, variable_name=name, variable_value=str(value)))
        await db.commit()

    persona_type = persona.persona_type if persona else "探索中"
    for i, path in enumerate(paths):
        db.add(FutureSelf(
            user_id=user_id,
            simulation_id=sim.id,
            based_on_persona_id=persona_id,
            persona_label=path.get("label", f"路径{i+1}"),
            target_year=datetime.utcnow().year + 5,
            path_type=scenario,
            confidence=path.get("confidence", 0.5),
            profile=path,
            basis_summary=path.get("grounding", f"引擎：{engine} | 基于{persona_type}人格模拟"),
        ))
    await db.commit()
    return sim


async def get_user_simulations(db: AsyncSession, user_id: int) -> list:
    return (
        await db.execute(
            select(Simulation).where(Simulation.user_id == user_id)
            .order_by(Simulation.created_at.desc())
        )
    ).scalars().all()


async def get_simulation_by_id(db: AsyncSession, sim_id: int):
    return await db.get(Simulation, sim_id)
