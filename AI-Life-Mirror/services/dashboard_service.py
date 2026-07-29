"""首页仪表盘数据服务"""
from datetime import datetime, timedelta, date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, LifeEvent, DailyRecord, PersonaProfile,
    InterestTrack, LifeGoal, Simulation, GrowthReport,
)


async def get_dashboard_data(db: AsyncSession, user_id: int) -> dict:
    """聚合首页所需数据"""

    now = datetime.utcnow()
    today = now.date()

    # 用户信息
    user = await db.get(User, user_id)

    # ── 基础统计 ──────────────────────────────────────
    event_count = (await db.execute(
        select(func.count()).select_from(LifeEvent).where(LifeEvent.user_id == user_id)
    )).scalar() or 0

    record_count = (await db.execute(
        select(func.count()).select_from(DailyRecord).where(DailyRecord.user_id == user_id)
    )).scalar() or 0

    goal_count = (await db.execute(
        select(func.count()).select_from(LifeGoal).where(
            LifeGoal.user_id == user_id, LifeGoal.status == "active"
        )
    )).scalar() or 0

    achieved_goal_count = (await db.execute(
        select(func.count()).select_from(LifeGoal).where(
            LifeGoal.user_id == user_id, LifeGoal.status == "achieved"
        )
    )).scalar() or 0

    sim_count = (await db.execute(
        select(func.count()).select_from(Simulation).where(Simulation.user_id == user_id)
    )).scalar() or 0

    report_count = (await db.execute(
        select(func.count()).select_from(GrowthReport).where(GrowthReport.user_id == user_id)
    )).scalar() or 0

    # ── 连续记录天数（streak）─────────────────────────
    streak = 0
    all_records = (await db.execute(
        select(DailyRecord.record_date).where(DailyRecord.user_id == user_id)
        .order_by(DailyRecord.record_date.desc()).limit(60)
    )).scalars().all()

    if all_records:
        record_dates = set()
        for rd in all_records:
            if rd:
                record_dates.add(rd.date() if hasattr(rd, 'date') else rd)

        check_date = today
        # 如果今天还没记录，从昨天开始算
        if check_date not in record_dates:
            check_date = today - timedelta(days=1)

        while check_date in record_dates:
            streak += 1
            check_date -= timedelta(days=1)

    # ── 本周 vs 上周记录数 ────────────────────────────
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    this_week = (await db.execute(
        select(func.count()).select_from(DailyRecord).where(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date >= week_ago,
        )
    )).scalar() or 0

    last_week = (await db.execute(
        select(func.count()).select_from(DailyRecord).where(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date >= two_weeks_ago,
            DailyRecord.record_date < week_ago,
        )
    )).scalar() or 0

    week_change = this_week - last_week

    # ── 本周事件数 ────────────────────────────────────
    this_week_events = (await db.execute(
        select(func.count()).select_from(LifeEvent).where(
            LifeEvent.user_id == user_id,
            LifeEvent.occurred_at >= week_ago,
        )
    )).scalar() or 0

    # ── 最新人格画像 ──────────────────────────────────
    persona = (await db.execute(
        select(PersonaProfile).where(
            PersonaProfile.user_id == user_id,
            PersonaProfile.is_current == True,
        ).order_by(PersonaProfile.generated_at.desc()).limit(1)
    )).scalar_one_or_none()

    # ── 最近人生事件 ──────────────────────────────────
    recent_events = (await db.execute(
        select(LifeEvent).where(LifeEvent.user_id == user_id)
        .order_by(LifeEvent.occurred_at.desc()).limit(5)
    )).scalars().all()

    # ── 兴趣追踪 ──────────────────────────────────────
    interest_fields = (await db.execute(
        select(InterestTrack.field, InterestTrack.score, InterestTrack.tracked_at)
        .where(InterestTrack.user_id == user_id)
        .order_by(InterestTrack.tracked_at.desc()).limit(20)
    )).all()

    latest_interests = {}
    for field, score, _ in interest_fields:
        if field not in latest_interests:
            latest_interests[field] = score

    # ── 活跃目标 ──────────────────────────────────────
    active_goals = (await db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == user_id,
            LifeGoal.status == "active",
        ).order_by(LifeGoal.importance.desc()).limit(3)
    )).scalars().all()

    # ── 访问行为追踪 ──────────────────────────────────
    from services.activity_service import get_visit_summary
    try:
        visit_summary = await get_visit_summary(db, user_id)
    except Exception:
        visit_summary = {"total_visits": 0, "top_pages": [], "insight": "", "unique_pages": 0}

    # ── AI 洞察生成 ───────────────────────────────────
    insight = _generate_insight(
        streak=streak,
        this_week=this_week,
        last_week=last_week,
        record_count=record_count,
        event_count=event_count,
        goal_count=goal_count,
        achieved_count=achieved_goal_count,
        persona=persona,
    )
    if visit_summary.get("insight"):
        insight = visit_summary["insight"] + "。" + insight

    # ── 人生参考兴趣 ──────────────────────────────────
    from services.activity_service import get_reference_interests
    ref_interests = {}
    try:
        ref_interests = await get_reference_interests(db, user_id)
        if ref_interests.get("insight"):
            insight = ref_interests["insight"] + "。" + insight
    except Exception:
        pass

    return {
        "user": user,
        "stats": {
            "events": event_count,
            "records": record_count,
            "goals": goal_count,
            "simulations": sim_count,
            "reports": report_count,
            "week_records": this_week,
            "streak": streak,
            "last_week": last_week,
            "week_change": week_change,
            "this_week_events": this_week_events,
            "achieved_goals": achieved_goal_count,
        },
        "persona": persona,
        "recent_events": recent_events,
        "interests": latest_interests,
        "active_goals": active_goals,
        "insight": insight,
        "visit_summary": visit_summary,
        "ref_interests": ref_interests,
    }


def _generate_insight(**kw) -> str:
    """基于数据生成简短反馈洞察"""
    parts = []

    # 连续记录
    streak = kw.get("streak", 0)
    if streak >= 7:
        parts.append(f"🔥 你已经连续 {streak} 天记录人生，这是很可贵的自我觉察习惯")
    elif streak >= 3:
        parts.append(f"✅ 连续 {streak} 天记录了，保持这个节奏")
    elif streak == 0:
        parts.append("今天还没有记录，花 2 分钟写下今天的感受吧")

    # 周对比
    change = kw.get("week_change", 0)
    if change > 0:
        parts.append(f"本周记录比上周多了 {change} 条，状态在回升")
    elif change < 0:
        parts.append(f"本周记录比上周少了 {abs(change)} 条，是不是最近比较忙？")

    # 目标
    achieved = kw.get("achieved_count", 0)
    active = kw.get("goal_count", 0)
    if achieved > 0:
        parts.append(f"已经完成了 {achieved} 个目标，每一步都算数")
    if active == 0 and kw.get("record_count", 0) > 5:
        parts.append("还没有设定目标？设定一两个方向会让 AI 更准确地理解你")

    # 数据积累
    total = kw.get("record_count", 0) + kw.get("event_count", 0)
    if total >= 20:
        parts.append("数据积累已经比较丰富了，AI 对你的理解越来越准确")
    elif total >= 5:
        parts.append("数据在慢慢积累，再多记录一些，AI 就能更好地理解你了")

    return parts[0] if parts else "开始记录你的第一个人生片段吧"

