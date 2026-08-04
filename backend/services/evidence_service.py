"""证据链服务 — 为每个 AI 结论召回真实数据来源（数据铁律 1.3）

从三类真实数据源召回证据：
1. life_memories（AI 提炼的生命记忆，按重要度排序）
2. life_events（人生事件，按时间倒序）
3. daily_records（日常记录，按时间倒序）
+ ChromaDB 语义检索（query 相关记忆）

证据必须真实存在——禁止任何编造/占位。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import DailyRecord, LifeEvent, LifeMemory


async def build_evidence(
    db: AsyncSession,
    user_id: int,
    query: str = "",
    target_type: str = "",
    target_id: int | None = None,
    limit: int = 8,
) -> list[dict]:
    """召回证据列表（全部带 user_id 过滤）"""
    query = (query or "").strip()
    keywords = [k for k in query.replace("，", " ").replace("、", " ").split() if len(k) >= 2] if query else []
    evidence: list[dict] = []

    # ── 1. 生命记忆（最重要来源） ──
    mem_q = select(LifeMemory).where(LifeMemory.user_id == user_id)
    if target_type == "event" and target_id:
        mem_q = mem_q.where(LifeMemory.source_type == "event", LifeMemory.source_id == target_id)
    elif target_type == "record" and target_id:
        mem_q = mem_q.where(LifeMemory.source_type == "diary", LifeMemory.source_id == target_id)
    else:
        mem_q = mem_q.order_by(LifeMemory.importance_score.desc())
    memories = (await db.execute(mem_q.limit(30))).scalars().all()
    for m in memories:
        if keywords and not any(k in (m.memory_content or "") for k in keywords):
            continue
        evidence.append({
            "type": "memory",
            "title": "生命记忆",
            "snippet": (m.memory_content or "")[:200],
            "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
            "importance": round(m.importance_score or 0, 2),
            "source_id": m.source_id,
        })
        if len(evidence) >= limit:
            return _dedupe(evidence)

    # ── 2. 人生事件 ──
    ev_q = select(LifeEvent).where(LifeEvent.user_id == user_id).order_by(LifeEvent.occurred_at.desc())
    events = (await db.execute(ev_q.limit(30))).scalars().all()
    for e in events:
        text = f"{e.title} {e.description or ''}"
        if keywords and not any(k in text for k in keywords):
            continue
        evidence.append({
            "type": "event",
            "title": e.title or "人生事件",
            "snippet": (e.description or e.title or "")[:200],
            "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
            "importance": 0.7,
            "source_id": e.id,
        })
        if len(evidence) >= limit:
            return _dedupe(evidence)

    # ── 3. 日常记录 ──
    rec_q = select(DailyRecord).where(DailyRecord.user_id == user_id).order_by(DailyRecord.record_date.desc())
    records = (await db.execute(rec_q.limit(30))).scalars().all()
    for r in records:
        if keywords and not any(k in (r.content or "") for k in keywords):
            continue
        evidence.append({
            "type": "record",
            "title": "日常记录",
            "snippet": (r.content or "")[:200],
            "date": r.record_date.strftime("%Y-%m-%d") if r.record_date else "",
            "importance": 0.5,
            "source_id": r.id,
        })
        if len(evidence) >= limit:
            return _dedupe(evidence)

    # ── 4. ChromaDB 语义补充（无关键词命中时） ──
    if not evidence and query:
        try:
            from backend.services.vector_store import search

            for r in search(user_id, query, n_results=limit):
                content = r.get("content", "")
                if content:
                    evidence.append({
                        "type": "memory",
                        "title": "长期记忆",
                        "snippet": content[:200],
                        "date": "",
                        "importance": 0.5,
                        "source_id": None,
                    })
        except Exception:
            pass

    return _dedupe(evidence)[:limit]


def _dedupe(items: list[dict]) -> list[dict]:
    """按片段去重"""
    seen = set()
    out = []
    for item in items:
        key = (item["type"], item["snippet"][:60])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
