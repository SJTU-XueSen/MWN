"""成长报告服务 — 基于周期内真实数据生成成长总结"""
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import LLM_ENABLED
from backend.database.models import (
    DailyRecord,
    GrowthReport,
    InterestTrack,
    LifeEvent,
    LifeGoal,
    PersonaProfile,
)
from backend.services.llm_service import _call_deepseek, _parse_json_content

logger = logging.getLogger(__name__)


async def _gather_period_data(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> dict:
    """收集周期内真实数据"""
    records = (
        await db.execute(
            select(DailyRecord).where(
                DailyRecord.user_id == user_id,
                DailyRecord.record_date >= start,
                DailyRecord.record_date <= end,
            ).order_by(DailyRecord.record_date.asc())
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(LifeEvent).where(
                LifeEvent.user_id == user_id,
                LifeEvent.occurred_at >= start,
                LifeEvent.occurred_at <= end,
            ).order_by(LifeEvent.occurred_at.asc())
        )
    ).scalars().all()
    goals = (
        await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == user_id, LifeGoal.status == "active")
        )
    ).scalars().all()
    tracks = (
        await db.execute(
            select(InterestTrack).where(
                InterestTrack.user_id == user_id,
                InterestTrack.tracked_at >= start,
            ).order_by(InterestTrack.tracked_at.asc())
        )
    ).scalars().all()
    persona = (
        await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == user_id, PersonaProfile.is_current == True)
        )
    ).scalar_one_or_none()

    # 情绪统计
    mood_counts: dict = defaultdict(int)
    interest_counts: dict = defaultdict(int)
    for r in records:
        if r.ai_analysis:
            mood_counts[r.ai_analysis.get("emotion", "neutral")] += 1
            for f in r.ai_analysis.get("interest_fields", []):
                interest_counts[f] += 1

    return {
        "record_count": len(records),
        "event_count": len(events),
        "records": records,
        "events": events,
        "goals": goals,
        "tracks": tracks,
        "persona": persona,
        "mood_counts": dict(mood_counts),
        "interest_counts": dict(interest_counts),
    }


def _rule_based_report(data: dict) -> dict:
    """规则引擎兜底报告（全部基于真实计数）"""
    interest_changes = []
    for field, count in sorted(data["interest_counts"].items(), key=lambda x: -x[1])[:5]:
        interest_changes.append({"field": field, "count": count})

    ability_growth: dict = {}
    if data["persona"]:
        ab = data["persona"].ability_profile or {}
        for k, v in ab.items():
            ability_growth[k] = round(v * data["persona"].confidence, 1)

    key_decisions = [{"id": e.id, "title": e.title, "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else ""} for e in data["events"]]

    goal_progress = [{"title": g.title, "status": g.status, "importance": g.importance} for g in data["goals"]]

    mood_summary = ""
    if data["mood_counts"]:
        pos = data["mood_counts"].get("positive", 0)
        neg = data["mood_counts"].get("negative", 0)
        total = sum(data["mood_counts"].values())
        if total:
            mood_summary = f"周期内共 {total} 次情绪记录，积极 {pos} 次、消极 {neg} 次" + ("，整体积极" if pos > neg else "，情绪起伏较多")

    summary = f"本周期共记录 {data['record_count']} 条日常记录、{data['event_count']} 个重要事件。" + (mood_summary + "。" if mood_summary else "")
    if not data["record_count"] and not data["event_count"]:
        summary = "本周期暂无记录数据——真实的数据积累是成长分析的起点，建议从一条日常记录开始。"

    return {
        "interest_changes": interest_changes,
        "ability_growth": ability_growth,
        "key_decisions": key_decisions,
        "personality_changes": data["persona"].persona_summary if data["persona"] else "尚未生成数字人格",
        "goal_progress": goal_progress,
        "gap_analysis": "基于本周期数据，建议继续积累真实记录，并定期回顾兴趣变化与目标进展",
        "mood_summary": mood_summary,
        "summary": summary,
        "engine": "rule_based",
    }


async def _llm_report(data: dict, start: datetime, end: datetime, context: str = ""):
    """LLM 生成深度报告（失败返回 None）"""
    if not LLM_ENABLED:
        return None

    records_text = "\n".join([f"- {r.record_date.strftime('%m/%d') if r.record_date else '?'} [{r.ai_analysis.get('emotion','') if r.ai_analysis else ''}] {r.content[:80]}" for r in data["records"][:15]]) or "(无)"
    events_text = "\n".join([f"- {e.occurred_at.strftime('%m/%d') if e.occurred_at else '?'} ({e.event_type}) {e.title}" for e in data["events"][:15]]) or "(无)"
    goals_text = "\n".join([f"- [{g.importance}%] {g.title}" for g in data["goals"]]) or "(无)"

    prompt = f"""你是一位成长分析师。基于用户周期内真实数据，生成一份成长报告 JSON。

## 数据周期
{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}

## 日常记录（{data['record_count']}条）
{records_text}

## 重要事件（{data['event_count']}个）
{events_text}

## 活跃目标
{goals_text}

## 情绪分布
{json.dumps(data['mood_counts'], ensure_ascii=False)}

## 兴趣分布
{json.dumps(data['interest_counts'], ensure_ascii=False)}

## 输出 JSON
{{
  "interest_changes": [{{"field": "领域", "count": 次数}}],
  "ability_growth": {{"能力名": 0-100}},
  "key_decisions": [{{"title": "事件标题", "insight": "这个决定的意义"}}],
  "personality_changes": "人格变化描述（80字以内）",
  "goal_progress": [{{"title": "目标", "status": "active", "note": "进展说明"}}],
  "gap_analysis": "目标与现实之间的差距分析（60字以内）",
  "mood_summary": "情绪趋势总结（40字以内）",
  "summary": "整体总结（120字以内）"
}}

★ 约束：
- 一切结论必须来自上面的真实数据，数据为空就诚实说明，不要虚构经历
- 用"你经历了…""你的记录显示…"而非编造用户没做过的事
- 不要用"失败""风险""危机"等词汇，用"成长机会""需要注意的方向"
- 只返回 JSON。"""

    raw = await _call_deepseek(
        "你是专业的成长分析师，输出精确的 JSON。", prompt, temperature=0.4, max_tokens=1500
    )
    result = _parse_json_content(raw) if raw else None
    if result:
        result["engine"] = "deepseek"
    return result


async def generate_report(
    db: AsyncSession,
    user_id: int,
    title: str,
    start: datetime,
    end: datetime,
    context: str = "",
) -> GrowthReport:
    """生成成长报告并入库"""
    data = await _gather_period_data(db, user_id, start, end)

    content = await _llm_report(data, start, end, context)
    if content is None:
        content = _rule_based_report(data)

    report = GrowthReport(
        user_id=user_id,
        title=title,
        period_start=start,
        period_end=end,
        content=content,
        generated_at=datetime.utcnow(),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    try:
        from backend.services.vector_store import add_entry

        add_entry(
            f"report:{report.id}", user_id,
            f"成长报告（{start.strftime('%Y.%m.%d')}-{end.strftime('%Y.%m.%d')}）：{content.get('summary', '')[:200]}",
            "report", {"period": f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"},
        )
    except Exception:
        pass
    return report
