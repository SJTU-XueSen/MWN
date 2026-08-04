"""行为追踪 — 页面访问 + 参考点击 → 兴趣权重信号"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import PageVisit

# 参考分类 → 兴趣领域映射（点击权重参与人格聚合）
REFERENCE_CATEGORY_MAP = {
    "考研深造": "科研",
    "求职就业": "编程",
    "创业经历": "创业",
    "转行跨界": "社交",
    "大学生活": "社交",
    "失败教训": "哲学",
}


async def track_visit(db: AsyncSession, user_id: int, path: str, label: str = ""):
    """记录页面访问（upsert 计数）"""
    visit = (
        await db.execute(
            select(PageVisit).where(PageVisit.user_id == user_id, PageVisit.path == path)
        )
    ).scalar_one_or_none()
    if visit:
        visit.visit_count = (visit.visit_count or 0) + 1
        visit.last_visited = datetime.utcnow()
        if label and not visit.label:
            visit.label = label
    else:
        db.add(PageVisit(user_id=user_id, path=path, label=label, visit_count=1))
    await db.commit()


async def track_reference_click(db: AsyncSession, user_id: int, category: str, detail: dict = None):
    """记录参考分类点击（作为兴趣权重信号）"""
    path = f"/references/{category or 'unknown'}"
    label = str(detail.get("label", ""))[:50] if detail else ""
    await track_visit(db, user_id, path, label)


async def get_visit_summary(db: AsyncSession, user_id: int) -> dict:
    """页面访问统计"""
    visits = (
        await db.execute(
            select(PageVisit).where(PageVisit.user_id == user_id).order_by(PageVisit.visit_count.desc())
        )
    ).scalars().all()
    return {
        "total": sum(v.visit_count or 0 for v in visits),
        "paths": [{"path": v.path, "label": v.label or v.path, "count": v.visit_count} for v in visits[:20]],
    }


async def get_reference_interests(db: AsyncSession, user_id: int) -> dict:
    """参考分类点击 → 兴趣权重 + 简单洞察"""
    visits = (
        await db.execute(
            select(PageVisit).where(PageVisit.user_id == user_id, PageVisit.path.like("/references/%"))
        )
    ).scalars().all()

    category_counts: dict = {}
    for v in visits:
        category = v.path.split("/")[-1] or "unknown"
        category_counts[category] = category_counts.get(category, 0) + (v.visit_count or 1)

    total = sum(category_counts.values())
    insight = ""
    if total >= 3:
        top = sorted(category_counts.items(), key=lambda x: -x[1])[0]
        insight = f"你最近持续浏览「{top[0]}」相关内容，这个方向正在成为你注意力的重心"
    elif total > 0:
        insight = "你开始浏览人生参考内容——兴趣正在形成中"
    else:
        insight = "尚未浏览人生参考内容——建议从感兴趣的领域开始探索"

    return {"category_counts": category_counts, "insight": insight}
