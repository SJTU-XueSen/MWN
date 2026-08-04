import re
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

# 抽象维度词 → 真实内容词展开（维度名在记忆原文中几乎不出现，
# 必须映射到用户实际会写下的词，才能让各维度召回不同的真实证据）
DIMENSION_EXPANSION: dict[str, list[str]] = {
    "技术能力": ["技术", "工程", "代码", "开发", "编程", "实验", "调试", "算法", "机器人", "电路", "实现", "搭建"],
    "创造力": ["创造", "设计", "创意", "创新", "灵感", "作品", "方案", "想法"],
    "社交力": ["社交", "朋友", "团队", "合作", "交流", "分享", "社区", "同学", "队友", "讨论"],
    "自我认知": ["反思", "认知", "思考", "自我", "总结", "复盘", "认识", "感悟", "习惯"],
    "执行力": ["执行", "完成", "推进", "落地", "坚持", "行动"],
    "领导力": ["领导", "组织", "带队", "负责", "管理"],
    "学习能力": ["学习", "课程", "阅读", "论文", "笔记", "知识"],
    "表达能力": ["表达", "演讲", "分享", "汇报", "讲解", "发言"],
    "分析能力": ["分析", "研究", "调研", "理解", "拆解"],
    "组织能力": ["组织", "协调", "策划", "安排", "筹备"],
    "适应力": ["适应", "调整", "变化", "转变", "重新"],
    "探索型": ["探索", "尝试", "发现", "新领域", "未知", "好奇"],
    "坚持型": ["坚持", "持续", "努力", "克服", "不放弃"],
    "社交型": ["交流", "分享", "团队", "协作", "帮助", "讨论"],
    "创造型": ["创造", "构建", "设计", "制作", "创作", "开发"],
    "反思型": ["反思", "总结", "复盘", "思考", "回顾", "分析"],
    "探索": ["探索", "尝试", "发现", "新领域", "未知", "好奇"],
    "坚持": ["坚持", "持续", "努力", "克服", "不放弃"],
    "反思": ["反思", "总结", "复盘", "思考", "回顾", "分析"],
    "成就": ["成就", "收获", "突破", "成功", "获奖", "进步"],
    "求知": ["求知", "学习", "好奇", "阅读", "论文", "知识"],
    "自主": ["自主", "独立", "自己决定", "选择"],
    "认知": ["认知", "思考", "理解", "认识", "感悟"],
    "独立": ["独立", "自己", "独自"],
    "专注": ["专注", "沉浸", "集中", "认真"],
    "抗压": ["压力", "高压", "坚持", "克服", "扛住"],
}


def _expand_query(query: str) -> list[str]:
    """把 query 中的抽象维度词展开为真实内容词（匹配用）"""
    expanded: list[str] = []
    for word in query.replace("，", " ").replace("、", " ").split():
        if not word:
            continue
        if word in DIMENSION_EXPANSION:
            expanded.extend(DIMENSION_EXPANSION[word])
        elif len(word) >= 2:
            expanded.append(word)
    return list(dict.fromkeys(expanded))  # 去重保序


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
    keywords = _expand_query(query) if query else []
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

    # ── 4. ChromaDB 语义补充（关键词命中不足时，按展开词逐词检索） ──
    if len(evidence) < limit and keywords:
        try:
            from backend.services.vector_store import search

            # 收集库中仍存在的来源 id（过滤已删除数据）
            existing_ids: set = set()
            for model, prefix in [(DailyRecord, "journal"), (LifeEvent, "event"), (LifeMemory, "ai_memory")]:
                rows = (await db.execute(select(model.id).where(model.user_id == user_id))).scalars().all()
                existing_ids.update(f"{prefix}:{i}" for i in rows)
            seen_snippets = {e["snippet"] for e in evidence}
            for sq in keywords[:6]:
                if len(evidence) >= limit:
                    break
                for r in search(user_id, sq, n_results=limit):
                    content = r.get("content", "")
                    vid = str(r.get("id", ""))
                    # 存在性校验：已删除来源的向量不进入证据链
                    # （journal:{记录id} / event:{事件id} / ai_memory:{记忆id} 均须在库中存在）
                    if vid and not vid.startswith(("report:", "chat:")) and vid not in existing_ids:
                        continue
                    if content and content[:60] not in seen_snippets:
                        seen_snippets.add(content[:60])
                        evidence.append({
                            "type": "memory",
                            "title": "长期记忆",
                            "snippet": content[:200],
                            "date": "",
                            "importance": 0.5,
                            "source_id": None,
                        })
                        if len(evidence) >= limit:
                            break
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
