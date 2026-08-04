"""仪表盘聚合 — 全部数据来自真实记录"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    DailyRecord,
    InterestTrack,
    LifeEvent,
    LifeGoal,
    PersonaProfile,
)


async def get_dashboard_data(db: AsyncSession, user_id: int) -> dict:
    """聚合仪表盘数据：统计 / 人格 / 洞察 / 近期事件 / 活跃目标 / 兴趣"""
    records = (
        await db.execute(
            select(DailyRecord).where(DailyRecord.user_id == user_id)
            .order_by(DailyRecord.record_date.desc()).limit(30)
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == user_id)
            .order_by(LifeEvent.occurred_at.desc()).limit(10)
        )
    ).scalars().all()
    goals = (
        await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == user_id, LifeGoal.status == "active")
            .order_by(LifeGoal.importance.desc()).limit(5)
        )
    ).scalars().all()
    persona = (
        await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == user_id, PersonaProfile.is_current == True)
            .limit(1)
        )
    ).scalar_one_or_none()
    tracks = (
        await db.execute(
            select(InterestTrack).where(InterestTrack.user_id == user_id)
            .order_by(InterestTrack.tracked_at.desc()).limit(20)
        )
    ).scalars().all()

    # 连续记录天数（streak）
    record_dates = sorted({r.record_date.date() for r in records if r.record_date})
    streak = 0
    today = datetime.utcnow().date()
    if record_dates:
        day = today
        if day not in record_dates:
            day = today - timedelta(days=1)
        while day in record_dates:
            streak += 1
            day -= timedelta(days=1)

    # 周对比（记录数）
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week = sum(1 for r in records if r.record_date and r.record_date >= week_ago)
    last_week = sum(
        1 for r in records
        if r.record_date and week_ago - timedelta(days=7) <= r.record_date < week_ago
    )

    # 兴趣聚合
    interests: dict = defaultdict(int)
    for t in tracks:
        interests[t.field] = max(interests.get(t.field, 0), int(t.score or 0))
    for r in records:
        if r.ai_analysis:
            for f in r.ai_analysis.get("interest_fields", []):
                interests[f] += 5

    # AI 洞察（规则生成，基于真实数据）
    insight = _generate_insight(records, events, persona, streak)

    return {
        "stats": {
            "streak": streak,
            "record_count": len(records),
            "event_count": len(events),
            "goal_count": len(goals),
            "this_week": this_week,
            "last_week": last_week,
            "persona_confidence": round(persona.confidence, 2) if persona else 0,
        },
        "persona": persona,
        "insight": insight,
        "recent_events": events,
        "active_goals": goals,
        "interests": dict(sorted(interests.items(), key=lambda x: -x[1])[:8]),
    }


def _generate_insight(records, events, persona, streak) -> str:
    """基于真实数据的规则洞察"""
    if not records and not events:
        return "还没有任何记录——你的第一笔数据，是未来一切分析的基础。"
    parts = []
    if streak >= 3:
        parts.append(f"已连续记录 {streak} 天，这个节奏正在帮你积累人生数据")
    if persona:
        parts.append(f"数字人格置信度 {int(persona.confidence * 100)}%" + ("，数据仍在积累中" if persona.confidence < 0.5 else "，画像已趋于稳定"))
    if events:
        e = events[0]
        parts.append(f"最近一次重要事件：{e.title}")
    return "。".join(parts) + "。"


# ── 活动匹配打分（数据锚定：只用用户真实兴趣/画像 vs 活动文本） ──

def score_activity(user_interests: dict, text: str, extra_fields: list[str] = None) -> dict:
    """计算用户与活动的匹配度（0-100）与推荐理由

    user_interests: {兴趣领域: 权重}（来自兴趣追踪/人格画像）
    text: 活动标题+描述+分类+标签 拼接
    """
    if not user_interests:
        return {"match_score": 0, "matched": [], "reason": "数据积累中——记录更多经历后，这里会出现为你量身匹配的活动"}
    matched = []
    score = 0
    for field, weight in user_interests.items():
        field = str(field)
        if field and field in text:
            matched.append(field)
            score += min(int(weight or 50), 100)
    score = min(100, score // 2 if score else 0)  # 归一化，防止单一字段撑爆
    score = max(5, score) if matched else 0
    if matched:
        reason = "匹配你的兴趣：{0}".format("、".join(matched[:4]))
    else:
        reason = "与你当前画像关联较弱的探索方向——新的领域可能带来新的成长"
    return {"match_score": score, "matched": matched[:4], "reason": reason}
