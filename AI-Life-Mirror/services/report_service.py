"""
AI 成长报告服务 — 阶段性人生总结

汇总一段时间内的日常记录 + 人生事件，
通过 LLM 或规则引擎生成结构化成长报告。
"""
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    DailyRecord, LifeEvent, LifeMemory, GrowthReport,
    InterestTrack, LifeGoal, EventType,
)
from config import LLM_ENABLED

logger = logging.getLogger(__name__)


# ── 数据收集 ──────────────────────────────────────────

async def _gather_period_data(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> dict:
    """收集一段时间内的所有人生数据"""

    # 日常记录
    records = (await db.execute(
        select(DailyRecord).where(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date >= start,
            DailyRecord.record_date <= end,
        ).order_by(DailyRecord.record_date.asc())
    )).scalars().all()

    # 人生事件
    events = (await db.execute(
        select(LifeEvent).where(
            LifeEvent.user_id == user_id,
            LifeEvent.occurred_at >= start,
            LifeEvent.occurred_at <= end,
        ).order_by(LifeEvent.occurred_at.asc())
    )).scalars().all()

    # 生命记忆
    memories = (await db.execute(
        select(LifeMemory).where(
            LifeMemory.user_id == user_id,
            LifeMemory.created_at >= start,
            LifeMemory.created_at <= end,
        ).order_by(LifeMemory.importance_score.desc()).limit(20)
    )).scalars().all()

    # 兴趣追踪
    interests = (await db.execute(
        select(InterestTrack).where(
            InterestTrack.user_id == user_id,
            InterestTrack.tracked_at >= start,
            InterestTrack.tracked_at <= end,
        ).order_by(InterestTrack.tracked_at.asc())
    )).scalars().all()

    # 活跃目标
    goals = (await db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == user_id,
            LifeGoal.status == "active",
        )
    )).scalars().all()

    return {
        "records": records,
        "events": events,
        "memories": memories,
        "interests": interests,
        "goals": goals,
        "record_count": len(records),
        "event_count": len(events),
        "memory_count": len(memories),
    }


# ── 规则引擎生成（LLM 不可用时的回退）─────────────────

def _rule_based_report(data: dict, start: datetime, end: datetime) -> dict:
    """基于规则聚合生成报告"""

    records = data["records"]
    events = data["events"]

    # 1. 兴趣统计
    interest_counter = defaultdict(int)
    emotion_counter = defaultdict(int)
    for r in records:
        if r.ai_analysis:
            for field in r.ai_analysis.get("interest_fields", []):
                interest_counter[field] += 1
            emotion_counter[r.ai_analysis.get("emotion", "neutral")] += 1

    top_interests = sorted(interest_counter.items(), key=lambda x: -x[1])[:5]

    # 2. 情绪趋势
    pos = emotion_counter.get("positive", 0)
    neg = emotion_counter.get("negative", 0)
    neu = emotion_counter.get("neutral", 0)
    total_emo = pos + neg + neu
    if total_emo > 0:
        pos_pct = round(pos / total_emo * 100)
        neg_pct = round(neg / total_emo * 100)
    else:
        pos_pct = neg_pct = 0

    # 3. 关键事件摘要
    key_events = [
        {"title": e.title, "type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
         "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else ""}
        for e in events[:10]
    ]

    # 4. 摘要
    summary_parts = []
    if records:
        summary_parts.append(f"在此期间共记录了 {len(records)} 条日常经历")
    if events:
        summary_parts.append(f"发生了 {len(events)} 个重要人生事件")
    if top_interests:
        top_names = ", ".join([f[0] for f in top_interests[:3]])
        summary_parts.append(f"最关注的领域是{top_names}")
    if pos_pct > neg_pct:
        summary_parts.append("整体情绪偏积极")
    elif neg_pct > pos_pct:
        summary_parts.append("这段时间经历了一些挑战")

    return {
        "interest_changes": [{"field": f, "count": c} for f, c in top_interests],
        "ability_growth": {"tech": 0, "creative": 0, "social": 0, "self_awareness": 0},
        "key_events": key_events,
        "personality_changes": "数据积累中，随着记录增多将呈现更清晰的人格变化趋势。",
        "goal_progress": {},
        "gap_analysis": "继续积累人生数据，AI 将在未来提供更深入的差距分析。",
        "summary": "。".join(summary_parts) + "。",
        "emotional_trend": {"positive": pos_pct, "negative": neg_pct, "neutral": 100 - pos_pct - neg_pct},
        "recommendation": "坚持记录日常经历和重要事件，数据越多，AI 对你的理解越深。",
        "engine": "rule_based",
    }


# ── LLM 生成 ──────────────────────────────────────────

async def _llm_report(data: dict, start: datetime, end: datetime, user_context: str) -> Optional[dict]:
    """用 LLM 生成深度成长报告"""
    if not LLM_ENABLED:
        return None

    # 压缩数据用于 prompt
    records_text = "\n".join([
        f"- [{r.record_date.strftime('%m/%d') if r.record_date else '?'}] {r.content[:150]}"
        for r in data["records"][:30]
    ]) or "(无记录)"

    events_text = "\n".join([
        f"- [{e.occurred_at.strftime('%m/%d') if e.occurred_at else '?'}] ({e.event_type.value if hasattr(e.event_type, 'value') else e.event_type}) {e.title}"
        for e in data["events"][:20]
    ]) or "(无事件)"

    memories_text = "\n".join([
        f"- [{m.importance_score:.1f}] {m.memory_content[:100]}"
        for m in data["memories"][:10]
    ]) or "(无记忆)"

    prompt = f"""你是一位深度陪伴用户成长的 AI 人生分析师。请根据用户在一段时间内积累的人生数据，生成一份温暖的成长报告。

## 时间段
{start.strftime('%Y年%m月%d日')} 至 {end.strftime('%Y年%m月%d日')}

## 日常记录
{records_text}

## 重要事件
{events_text}

## 长期记忆
{memories_text}

## 用户背景
{user_context or '(待补充)'}

## 请输出 JSON
{{
  "summary": "200字以内的总体概览，温暖、有洞察力",
  "interest_changes": [
    {{"field": "领域名", "trend": "上升/稳定/下降", "detail": "变化说明"}}
  ],
  "ability_growth": {{
    "tech": 0-100,
    "creative": 0-100,
    "social": 0-100,
    "self_awareness": 0-100
  }},
  "key_events_analysis": [
    {{"title": "事件", "significance": "为什么重要"}}
  ],
  "personality_changes": "人格层面的变化趋势，80字以内",
  "emotional_trend": {{
    "description": "情绪变化趋势描述，40字以内",
    "positive_pct": 0-100,
    "negative_pct": 0-100
  }},
  "gap_analysis": "当前状态与潜在可能之间的差距分析，80字以内",
  "recommendation": "2-3条具体的行动建议，格式为换行分隔的字符串（不是JSON数组），每条一行",
  "encouragement": "温暖的鼓励，60字以内"
}}

只返回 JSON。"""

    try:
        import httpx
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是温暖而有洞察力的 AI 人生分析师。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"},
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                result = json.loads(content)
                result["engine"] = "deepseek"
                return result
    except Exception as e:
        logger.warning(f"LLM report generation failed: {e}")

    return None


# ── 公开接口 ──────────────────────────────────────────

async def generate_report(
    db: AsyncSession,
    user_id: int,
    title: str,
    period_start: datetime,
    period_end: datetime,
    user_context: str = "",
) -> GrowthReport:
    """生成一份成长报告"""

    # 1. 收集数据
    data = await _gather_period_data(db, user_id, period_start, period_end)

    # 2. 生成报告内容（LLM 优先）
    content = await _llm_report(data, period_start, period_end, user_context)
    if content is None:
        content = _rule_based_report(data, period_start, period_end)

    # 3. 存入数据库
    report = GrowthReport(
        user_id=user_id,
        title=title,
        period_start=period_start,
        period_end=period_end,
        content=content,
        generated_at=datetime.utcnow(),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


async def get_user_reports(db: AsyncSession, user_id: int) -> List[GrowthReport]:
    """获取用户的所有报告，按时间降序"""
    return (await db.execute(
        select(GrowthReport).where(GrowthReport.user_id == user_id)
        .order_by(GrowthReport.generated_at.desc())
    )).scalars().all()


async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[GrowthReport]:
    """获取单份报告"""
    return await db.get(GrowthReport, report_id)
