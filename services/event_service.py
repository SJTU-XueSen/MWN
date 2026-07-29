"""
人生事件服务 — LifeEvent CRUD + AI 分析

处理用户的重要人生事件：
1. 创建/查询/删除事件
2. AI 分析：情绪检测、兴趣标签、人格影响值
3. Memory Pipeline：事件 → life_memories → ChromaDB
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import LifeEvent, LifeMemory, EventType, EmotionType, MemorySourceType
from services.memory_service import _EMOTION_KEYWORDS, _INTEREST_KEYWORDS, _BEHAVIOR_KEYWORDS


# ── 事件类型展示配置 ────────────────────────────────────

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


def get_event_display(event_type: str) -> dict:
    """获取事件类型的展示配置"""
    return EVENT_TYPE_CONFIG.get(
        event_type,
        {"icon": "📌", "label": event_type, "color": "gray"},
    )


# ── AI 分析 ────────────────────────────────────────────

def analyze_event(title: str, description: str, event_type: str) -> dict:
    """
    对人生事件进行 AI 分析（MVP：规则引擎）。

    Returns:
        {
            "emotion": str,           # positive/neutral/negative
            "interest_tags": [str],   # 兴趣领域标签
            "ai_impact": str,         # AI 生成的影响摘要
            "persona_delta": dict,    # 对人格各维度的影响值
        }
    """
    text = f"{title} {description}"

    # 1. 情绪检测
    pos_count = sum(1 for kw in _EMOTION_KEYWORDS[EmotionType.POSITIVE] if kw in text)
    neg_count = sum(1 for kw in _EMOTION_KEYWORDS[EmotionType.NEGATIVE] if kw in text)
    if pos_count > neg_count:
        emotion = "positive"
    elif neg_count > pos_count:
        emotion = "negative"
    else:
        emotion = "neutral"

    # 2. 兴趣领域检测
    interest_tags = []
    for field, keywords in _INTEREST_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            interest_tags.append(field)

    # 3. 行为模式检测（注入 persona_delta）
    persona_delta = {}
    for pattern, keywords in _BEHAVIOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            key = pattern.rstrip("型").lower()
            persona_delta.setdefault(key, 0)
            persona_delta[key] += 2

    # 4. 根据事件类型注入预设人格影响
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
    for key, val in (TYPE_PERSONA_MAP.get(event_type, {})).items():
        persona_delta[key] = persona_delta.get(key, 0) + val

    # 5. 生成 AI 影响摘要
    impacts = []
    event_label = EVENT_TYPE_CONFIG.get(event_type, {}).get("label", event_type)
    if interest_tags:
        impacts.append(f"与{', '.join(interest_tags[:3])}领域相关")
    if emotion == "positive":
        impacts.append(f"这是一次积极的{event_label}")
    elif emotion == "negative":
        impacts.append(f"这次{event_label}带来了负面情绪体验")
    else:
        impacts.append(f"这次{event_label}是一次中性经历")
    if persona_delta:
        top_traits = sorted(persona_delta.items(), key=lambda x: -x[1])[:2]
        impacts.append(f"主要影响了{'和'.join(t[0] for t in top_traits)}")

    ai_impact = "；".join(impacts) + "。"

    # 行为模式检测
    behavior_patterns = []
    for pattern, keywords in _BEHAVIOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            behavior_patterns.append(pattern)

    return {
        "emotion": emotion,
        "interest_tags": interest_tags,
        "ai_impact": ai_impact,
        "persona_delta": persona_delta,
        "emotion_detail": "",
        "behavior_patterns": behavior_patterns,
        "long_term_impact": ai_impact,
        "knowledge_domains": interest_tags,
        "search_insight": "",
        "encouragement": "",
        "outlook": "",
        "honest_reflection": "",
        "engine": "rule_based",
    }


def _rule_event_memory(title: str, desc: str, label: str, etype: str, analysis: dict) -> str:
    """规则引擎生成更自然的生命记忆"""

    emotion = analysis.get("emotion", "")
    emotion_text = {
        "positive": "这次经历让你感到充实和满足",
        "negative": "这次经历带来了挫败感，但也让你开始反思",
        "neutral": "这次经历平平淡淡，但作为一段经历被记住",
    }.get(emotion, "")

    impact = analysis.get("ai_impact", "")

    # 按事件类型写不同的句式
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
    # 添加描述细节
    if desc and len(desc) > 5:
        template += f" 具体来说：{desc[:120]}"

    return template[:300]


async def _llm_event_memory(title: str, desc: str, label: str, analysis: dict) -> str:
    """用 LLM 生成有洞察力的生命记忆"""
    from config import LLM_ENABLED
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

    try:
        import httpx
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是擅长提炼人生记忆的 AI。输出简洁、有洞察力。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


# ── CRUD ───────────────────────────────────────────────

async def create_event(
    db: AsyncSession,
    user_id: int,
    title: str,
    description: str,
    event_type: str,
    occurred_at: datetime,
) -> LifeEvent:
    """创建人生事件（LLM 分析优先，规则引擎回退）"""
    from services.llm_service import analyze_event as llm_analyze_event

    analysis = await llm_analyze_event(title, description, event_type)

    event = LifeEvent(
        user_id=user_id,
        title=title,
        description=description,
        event_type=EventType(event_type),
        emotion=EmotionType(analysis["emotion"]),
        interest_tags=analysis["interest_tags"],
        ai_impact=analysis["ai_impact"],
        persona_delta=analysis["persona_delta"],
        occurred_at=occurred_at,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Memory Pipeline: 生成生命记忆
    await _process_event_to_memory(db, event, user_id, analysis)

    return event


async def _process_event_to_memory(
    db: AsyncSession,
    event: LifeEvent,
    user_id: int,
    analysis: dict,
):
    """将人生事件提炼为生命记忆"""
    event_label = EVENT_TYPE_CONFIG.get(
        event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
        {},
    ).get("label", str(event.event_type))

    event_type_str = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)

    # ★ 尝试 LLM 生成有洞察力的记忆
    memory_content = await _llm_event_memory(event.title, event.description or "", event_label, analysis)
    if not memory_content:
        # 回退：更自然的规则生成
        memory_content = _rule_event_memory(event.title, event.description or "", event_label, event_type_str, analysis)

    # 重要性评分：基于事件类型
    IMPORTANCE_MAP = {
        "turning_point": 0.9,
        "achievement": 0.8,
        "decision": 0.85,
        "failure": 0.75,
        "competition": 0.7,
        "project": 0.7,
        "relationship": 0.65,
        "study": 0.5,
        "social": 0.45,
        "habit": 0.5,
        "emotion": 0.35,
    }
    importance = IMPORTANCE_MAP.get(event_type_str, 0.5)
    # 有更多兴趣标签会提高重要性
    importance = min(0.95, importance + len(analysis.get("interest_tags", [])) * 0.03)

    memory = LifeMemory(
        user_id=user_id,
        source_type=MemorySourceType.EVENT,
        source_id=event.id,
        memory_content=memory_content,
        importance_score=importance,
        persona_impact=analysis.get("persona_delta", {}),
        embedding_id=f"ai_memory:event:{event.id}",
        created_at=datetime.utcnow(),
    )
    db.add(memory)
    await db.commit()


async def get_user_events(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
    event_type: Optional[str] = None,
) -> List[LifeEvent]:
    """获取用户的人生事件列表，按时间降序"""
    q = select(LifeEvent).where(LifeEvent.user_id == user_id)
    if event_type:
        q = q.where(LifeEvent.event_type == EventType(event_type))
    q = q.order_by(LifeEvent.occurred_at.desc()).limit(limit)
    return (await db.execute(q)).scalars().all()


async def get_event_by_id(db: AsyncSession, event_id: int) -> Optional[LifeEvent]:
    """获取单个人生事件"""
    return await db.get(LifeEvent, event_id)


async def delete_event(db: AsyncSession, event: LifeEvent):
    """删除人生事件及其关联的生命记忆"""
    # 删除关联的 life_memories
    memories = (await db.execute(
        select(LifeMemory).where(
            LifeMemory.user_id == event.user_id,
            LifeMemory.source_type == MemorySourceType.EVENT,
            LifeMemory.source_id == event.id,
        )
    )).scalars().all()
    for m in memories:
        await db.delete(m)

    await db.delete(event)
    await db.commit()


async def get_event_timeline_data(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """
    获取时间线所需的聚合数据：
    - events_by_period: 按月份分组的事件
    - type_counts: 各类型事件数量
    - total: 事件总数
    """
    events = (await db.execute(
        select(LifeEvent).where(LifeEvent.user_id == user_id)
        .order_by(LifeEvent.occurred_at.desc()).limit(100)
    )).scalars().all()

    # 按月份分组
    from collections import defaultdict
    periods = defaultdict(list)
    for e in events:
        key = e.occurred_at.strftime("%Y年%m月") if e.occurred_at else "未知"
        periods[key].append(e)

    # 类型统计
    type_counts = defaultdict(int)
    for e in events:
        type_counts[e.event_type.value if isinstance(e.event_type, EventType) else e.event_type] += 1

    return {
        "events": events,
        "periods": dict(periods),
        "type_counts": dict(type_counts),
        "total": len(events),
        "event_type_config": EVENT_TYPE_CONFIG,
    }
