"""人生事件服务 — 事件类型配置 + 规则分析 + CRUD + 记忆提炼"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import LifeEvent, LifeMemory


EVENT_TYPE_CONFIG = {
    "project":       {"icon": "📁", "label": "项目经历", "color": "indigo"},
    "competition":   {"icon": "🏆", "label": "比赛经历", "color": "amber"},
    "study":         {"icon": "📖", "label": "学习经历", "color": "emerald"},
    "social":        {"icon": "👥", "label": "社交经历", "color": "teal"},
    "decision":      {"icon": "🧭", "label": "重要决定", "color": "purple"},
    "turning_point": {"icon": "🔀", "label": "人生转折", "color": "fuchsia"},
    "habit":         {"icon": "🔄", "label": "长期习惯", "color": "cyan"},
    "failure":       {"icon": "💪", "label": "失败经历", "color": "rose"},
    "achievement":   {"icon": "🌟", "label": "成就突破", "color": "yellow"},
    "relationship":  {"icon": "💞", "label": "重要关系", "color": "orange"},
    "emotion":       {"icon": "💭", "label": "情绪波动", "color": "violet"},
}

TYPE_PERSONA_MAP = {
    "project":       {"creative": 3, "专业能力": 3},
    "competition":   {"竞争意识": 3, "抗压能力": 3},
    "study":         {"学习能力": 3, "专注": 2},
    "social":        {"社交能力": 3, "同理心": 2},
    "decision":      {"决策力": 4, "自主性": 3},
    "turning_point": {"适应性": 4, "勇气": 4},
    "habit":         {"自律": 4, "坚持": 3},
    "failure":       {"韧性": 4, "反思": 3},
    "achievement":   {"自信": 4, "成就感": 3},
    "relationship":  {"共情": 3, "责任": 3},
    "emotion":       {"情绪觉察": 3, "自我认知": 2},
}

IMPORTANCE_MAP = {
    "turning_point": 0.9, "achievement": 0.8, "decision": 0.85, "failure": 0.75,
    "competition": 0.7, "project": 0.7, "relationship": 0.65, "study": 0.5,
    "social": 0.45, "habit": 0.5, "emotion": 0.35,
}

_TYPE_INSIGHT = {
    "competition": "竞技环境往往会放大一个人的抗压能力和临场反应模式",
    "project": "项目经历反映了一个人在长期投入中的专注度和执行力",
    "study": "学习过程中的方法选择暗示了一个人获取知识的偏好方式",
    "decision": "重大决定背后通常隐藏着一个人的核心价值观和取舍逻辑",
    "turning_point": "转折点事件往往能看出一个人面对变化时的适应策略",
    "failure": "失败的真正价值不在于教训本身，而在于之后的行动调整",
    "achievement": "成就不仅是能力的证明——也反映了一个人追求认可的方式",
    "relationship": "重要关系中往往能看出一个人在亲密连接中的需求和边界",
    "social": "社交经历的质量通常比数量更能反映一个人的社交动机",
    "habit": "习惯的持续性比习惯本身更能说明一个人的自驱力模式",
    "emotion": "情绪波动的背后通常有未被满足的期待或未被察觉的成长信号",
}

_ENCOURAGEMENTS = {
    "competition": "你愿意站上竞技场本身就已经是一种勇气——无论结果如何，选择参与而不是旁观，这个决定本身就值得认真对待",
    "project": "能够把一个项目从头到尾推动下来的人并不多——你在这个过程中展现的执行力，未来会在更多场合被验证",
    "study": "持续学习是少数能产生复利效应的事——你今天积累的每一点理解，都可能在未来的某个时刻突然串联起来",
    "decision": "做出决定比做出完美的决定更重要——你选择了面对而不是逃避，这本身就是一种成熟",
    "failure": "能够诚实地面对一次不理想的结果，并且把它记录下来——这本身就是反思能力的体现",
    "achievement": "你走到了一个值得被记住的节点——花一点时间真正感受这份成就感，而不是立刻奔向下一个目标",
    "turning_point": "站在转折点上的人往往看不到全貌——但回头看时，你会发现这段经历改变了你看世界的方式",
    "relationship": "愿意在关系中投入真心的人，也在同时了解自己——你在关系中学到的东西会持续塑造你",
    "social": "走出自己的小世界去和他人连接，这个动作本身就是成长——社交能力是在一次一次尝试中积累的",
    "habit": "习惯的力量不在于每一天的变化——而在于时间拉长后，你成为了一个不一样的人",
    "emotion": "你愿意去感受和记录自己的情绪——这是自我认知中非常重要但常常被忽略的一步",
}

_REFLECTIONS = {
    "competition": "值得想一想的是：你在竞赛中追求的是赢，还是验证自己？如果是前者，一次失败就可能动摇自信；如果是后者，每次参与都在加深对自己的理解",
    "project": "有时候我们会把'忙碌'等同于'进步'——值得审视的是，这个项目是你真正想做的，还是你觉得应该做的",
    "study": "学习效率高不等于学习方向对——偶尔停下来问自己：我学的东西真的是我需要的吗，还是只是别人告诉我'应该学'的",
    "decision": "每一个决定背后都有未被说出来的假设——你当时是基于什么信息做出的判断？如果信息变了，你愿意调整吗",
    "failure": "失败本身并不可怕——但如果你没有从中提炼出具体的行为调整，同样的模式可能会在另一个场景下重复",
    "achievement": "成就是一个很好的锚点——但它不应该定义你是谁。如果下次没有达到这个高度，你依然是有价值的",
    "turning_point": "转折点的意义往往不是当下能看清楚的——与其急着定义'这改变了我'，不如保持开放，让答案自己浮现",
    "relationship": "在关系中，我们常常看到的不是对方——而是自己在关系中的投射。这段经历让你对自己有了什么新认识？",
    "social": "社交不是收集联系人的游戏——真正的连接往往发生在你不再刻意'社交'的时候",
    "habit": "习惯的形成过程中有一个危险期：当你觉得'已经养成了'的时候——恰恰是最容易松懈的时候",
    "emotion": "情绪是信号，不是事实——当你感受到强烈情绪时，试着问自己：这个情绪想告诉我什么，而不是被它带着走",
}

_OUTLOOKS = {
    "competition": "未来如果再遇到类似的竞技场景，你可能会更清楚自己在压力下的反应模式——这是比比赛结果更宝贵的收获",
    "project": "这个项目积累的经验和方法，可能会在你完全意想不到的地方派上用场——保持连接，不要急着归档",
    "study": "学习是一个长线游戏——你今天建立的思维框架，会在未来处理更复杂问题时成为你的直觉",
    "decision": "这次决定的后果会在时间中慢慢显现——保持观察，你可能会对自己的判断力有新的认识",
    "turning_point": "未来的路不会是一条直线，但这次转折会成为你人生叙事中的一个关键章节",
    "failure": "任何一次失败放在足够长的时间线上，都只是故事的一部分——真正重要的不是这一次结果，而是你在这之后做出的选择",
    "achievement": "把这个成就放进你的成长档案——它是你能力的一个锚点，但不是你能力的上限",
    "relationship": "每一段重要的关系都在为你的未来关系模式提供模板——请好好保存这段经历的正面遗产",
    "social": "你正在建立的人际网络会在未来某个时刻产生意想不到的连接——保持真诚，比保持活跃更重要",
    "habit": "如果这个习惯能持续超过半年，它对你的改变会超出现在能想象的范围——耐心是习惯最好的朋友",
    "emotion": "未来当你再次经历类似的情绪时，今天的记录会成为你的参照系——你可能会发现自己已经成长了很多",
}


def analyze_event(title: str, description: str, event_type: str) -> dict:
    """规则引擎分析人生事件（LLM 不可用/失败时的兜底，全部基于用户输入）"""
    from backend.services.memory_service import _detect_emotion, _detect_interests, _detect_behaviors

    text = f"{title} {description}"
    emotion = _detect_emotion(text)
    interest_tags = _detect_interests(text)

    persona_delta: dict = {}
    for pattern in _detect_behaviors(text):
        key = pattern.rstrip("型").lower()
        persona_delta[key] = persona_delta.get(key, 0) + 2
    for key, val in TYPE_PERSONA_MAP.get(event_type, {}).items():
        persona_delta[key] = persona_delta.get(key, 0) + val

    # AI 影响摘要
    event_label = EVENT_TYPE_CONFIG.get(event_type, {}).get("label", event_type)
    impacts = [_TYPE_INSIGHT.get(event_type, f"这次{event_label}是你的个人数据库中的一个重要节点")]
    impacts.append(
        f"这件事与你在{'、'.join(interest_tags[:3])}方面的积累产生了关联" if interest_tags
        else "从标题和描述中暂未检测到明确的兴趣领域标签"
    )
    impacts.append({
        "positive": "整体情绪偏积极——值得关注的是，积极体验中是否包含了真正的成长，还是仅仅因为结果符合预期",
        "negative": "负面情绪并不意味着这次经历没有价值——相反，不适感往往是成长信号最密集的区域",
        "neutral": "中性情绪有时比强烈的情绪更有信息量——说明这件事对你来说可能需要更深的投入才能激发意义感",
    }[emotion])
    if persona_delta:
        top = sorted(persona_delta.items(), key=lambda x: -abs(x[1]))[:3]
        trait_parts = []
        for tname, tval in top:
            direction = "增强" if tval > 0 else "调整"
            trait_parts.append(f"{tname}({direction})")
        impacts.append(f"主要人格维度受到的影响：{'、'.join(trait_parts)}")
    else:
        impacts.append("暂未检测到显著的人格维度变化——不是所有重要的事都会立刻改变你")
    ai_impact = "。".join(impacts) + "。"

    return {
        "emotion": emotion,
        "emotion_detail": "",
        "interest_tags": interest_tags,
        "behavior_patterns": _detect_behaviors(text),
        "ai_impact": ai_impact,
        "long_term_impact": ai_impact,
        "persona_delta": persona_delta,
        "knowledge_domains": interest_tags,
        "search_insight": "",
        "encouragement": _ENCOURAGEMENTS.get(event_type, "每一次记录自己的人生，都是在为未来的自己留下线索——这种习惯本身就值得被认真对待"),
        "outlook": _OUTLOOKS.get(event_type, "这次经历会随着时间推移在你的生命叙事中找到它的位置——关键是保持记录和反思的习惯"),
        "honest_reflection": _REFLECTIONS.get(event_type, "值得思考的是：这次经历中，有哪些是你主动选择的，哪些是顺势发生的？区分这两者，能帮你更好地理解自己的决策模式"),
        "engine": "rule_based",
    }


def _rule_event_memory(title: str, desc: str, label: str, etype: str, analysis: dict) -> str:
    """规则引擎生成更自然的生命记忆"""
    emotion_text = {
        "positive": "这次经历让你感到充实和满足",
        "negative": "这次经历带来了挫败感，但也让你开始反思",
        "neutral": "这次经历平平淡淡，但作为一段经历被记住",
    }.get(analysis.get("emotion", ""), "")
    impact = analysis.get("ai_impact", "")

    templates = {
        "turning_point": f"一个改变了方向的关键时刻——{title}。{impact}",
        "achievement": f"一次值得记住的突破——{title}。{emotion_text}。{impact}",
        "failure": f"一次让你成长的失败——{title}。{emotion_text}。{impact}",
        "decision": f"一个需要勇气的决定——{title}。{impact}",
        "competition": f"一次全力以赴的较量——{title}。{impact}",
        "project": f"一段投入了大量时间和精力的经历——{title}。{impact}",
        "relationship": f"一段重要的人际关系变化——{title}。{impact}",
        "study": f"一段持续学习的旅程——{title}。{impact}",
        "social": f"一次有意义的社交经历——{title}。{impact}",
        "habit": f"一个逐渐融入生活的习惯——{title}。{impact}",
        "emotion": f"一次让你印象深刻的情绪波动——{title}。{impact}",
    }
    template = templates.get(etype, f"{label}：{title}。{impact}")
    if desc and len(desc) > 5:
        template += f" 具体来说：{desc[:120]}"
    return template[:300]


async def _llm_event_memory(title: str, desc: str, label: str, analysis: dict) -> str:
    """LLM 生成有洞察力的生命记忆"""
    from backend.config import LLM_ENABLED
    from backend.services.llm_service import _call_deepseek

    if not LLM_ENABLED:
        return ""
    prompt = f"""从以下人生事件中提取一句话生命记忆。这句话将被存入长期记忆库，用于构建数字人格。

事件类型：{label}
事件标题：{title}
事件描述：{desc or '(无)'}

AI 分析：
- 情绪：{analysis.get('emotion', '')}
- 影响：{analysis.get('ai_impact', '')}
- 人格影响：{analysis.get('persona_delta', {})}

要求：一句话，40字以内，抓住这件事对这个人意味着什么。不是复述事件，而是提炼这件事对人格的塑造。
只返回这句话。"""
    raw = await _call_deepseek("你是擅长提炼人生记忆的 AI。输出简洁、有洞察力。", prompt, temperature=0.3, max_tokens=150, json_mode=False)
    return raw or ""


async def _process_event_to_memory(db: AsyncSession, event: LifeEvent, user_id: int, analysis: dict):
    """事件 → 生命记忆（LLM 优先，规则回退）"""
    etype = event.event_type
    label = EVENT_TYPE_CONFIG.get(etype, {}).get("label", etype)

    memory_content = await _llm_event_memory(event.title, event.description or "", label, analysis)
    if not memory_content:
        memory_content = _rule_event_memory(event.title, event.description or "", label, etype, analysis)

    importance = IMPORTANCE_MAP.get(etype, 0.5)
    importance = min(0.95, importance + len(analysis.get("interest_tags", [])) * 0.03)

    memory = LifeMemory(
        user_id=user_id,
        source_type="event",
        source_id=event.id,
        memory_content=memory_content,
        importance_score=importance,
        persona_impact=analysis.get("persona_delta", {}),
        embedding_id=f"ai_memory:event:{event.id}",
        created_at=datetime.utcnow(),
    )
    db.add(memory)
    await db.commit()


# ── CRUD ──────────────────────────────────────────────

async def create_event(
    db: AsyncSession,
    user_id: int,
    title: str,
    description: str,
    event_type: str,
    occurred_at: datetime,
) -> LifeEvent:
    """创建事件（LLM 分析优先，规则引擎回退），并提炼生命记忆"""
    from backend.services.llm_service import analyze_event as llm_analyze

    analysis = await llm_analyze(title, description, event_type)

    event = LifeEvent(
        user_id=user_id,
        title=title,
        description=description,
        event_type=event_type if event_type in EVENT_TYPE_CONFIG else "study",
        emotion=analysis["emotion"],
        interest_tags=analysis["interest_tags"],
        ai_impact=analysis["ai_impact"],
        persona_delta=analysis["persona_delta"],
        occurred_at=occurred_at,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    await _process_event_to_memory(db, event, user_id, analysis)
    return event


async def get_user_events(db: AsyncSession, user_id: int, limit: int = 50, event_type: Optional[str] = None) -> list[LifeEvent]:
    q = select(LifeEvent).where(LifeEvent.user_id == user_id)
    if event_type:
        q = q.where(LifeEvent.event_type == event_type)
    q = q.order_by(LifeEvent.occurred_at.desc()).limit(limit)
    return (await db.execute(q)).scalars().all()


async def get_event_by_id(db: AsyncSession, event_id: int) -> Optional[LifeEvent]:
    return await db.get(LifeEvent, event_id)


async def delete_event(db: AsyncSession, event: LifeEvent):
    """删除事件及其关联记忆（含 ChromaDB 向量）"""
    memories = (
        await db.execute(
            select(LifeMemory).where(
                LifeMemory.user_id == event.user_id,
                LifeMemory.source_type == "event",
                LifeMemory.source_id == event.id,
            )
        )
    ).scalars().all()
    for m in memories:
        await db.delete(m)
    await db.delete(event)
    await db.commit()

    try:
        from backend.services.vector_store import _get_collection

        _get_collection().delete(where={"user_id": str(event.user_id), "type": "event"})
    except Exception:
        pass


async def get_event_timeline_data(db: AsyncSession, user_id: int) -> dict:
    """时间线聚合：按月份分组 + 类型统计"""
    from collections import defaultdict

    events = (
        await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == user_id)
            .order_by(LifeEvent.occurred_at.desc()).limit(100)
        )
    ).scalars().all()

    periods: dict = defaultdict(list)
    type_counts: dict = defaultdict(int)
    for e in events:
        key = e.occurred_at.strftime("%Y年%m月") if e.occurred_at else "未知"
        periods[key].append(e)
        type_counts[e.event_type] += 1

    return {
        "events": events,
        "periods": dict(periods),
        "type_counts": dict(type_counts),
        "total": len(events),
        "event_type_config": EVENT_TYPE_CONFIG,
    }
