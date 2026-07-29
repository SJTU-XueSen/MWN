"""
用户行为追踪服务 — 页面访问/点击率作为轻量人格信号
"""
import logging
from datetime import datetime
from typing import List

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PageVisit

logger = logging.getLogger(__name__)

# 路径 → 中文标签映射
PATH_LABELS = {
    "/": "首页",
    "/journal": "日常记录",
    "/journal/new": "写记录",
    "/events": "人生地图",
    "/events/new": "记录事件",
    "/persona": "数字人格",
    "/goals": "人生目标",
    "/simulation": "人生模拟",
    "/simulation/new": "新建模拟",
    "/future-chat": "未来对话",
    "/reports": "成长报告",
    "/references": "人生参考",
    "/settings": "隐私设置",
    "/auth/profile": "个人资料",
}


async def track_visit(user_id: int, path: str):
    """记录一次页面访问（upsert：存在则+1，不存在则新建）"""
    from database.database import AsyncSessionLocal

    label = _guess_label(path)

    async with AsyncSessionLocal() as db:
        try:
            existing = (await db.execute(
                select(PageVisit).where(
                    PageVisit.user_id == user_id,
                    PageVisit.path == path,
                )
            )).scalar_one_or_none()

            if existing:
                existing.visit_count += 1
                existing.last_visited = datetime.utcnow()
            else:
                visit = PageVisit(
                    user_id=user_id,
                    path=path,
                    label=label,
                    visit_count=1,
                    last_visited=datetime.utcnow(),
                    first_visited=datetime.utcnow(),
                )
                db.add(visit)

            await db.commit()
        except Exception as e:
            logger.debug(f"Track visit failed: {e}")
            await db.rollback()


def _guess_label(path: str) -> str:
    """根据路径猜测页面标签"""
    # 精确匹配
    if path in PATH_LABELS:
        return PATH_LABELS[path]
    # 前缀匹配
    for prefix, label in sorted(PATH_LABELS.items(), key=lambda x: -len(x[0])):
        if path.startswith(prefix) and prefix != "/":
            return label
    return "其他"


async def get_user_top_pages(db: AsyncSession, user_id: int, limit: int = 6) -> List[PageVisit]:
    """获取用户最常访问的页面"""
    return (await db.execute(
        select(PageVisit).where(PageVisit.user_id == user_id)
        .order_by(PageVisit.visit_count.desc()).limit(limit)
    )).scalars().all()


async def get_visit_summary(db: AsyncSession, user_id: int) -> dict:
    """获取访问行为摘要——供 AI 分析使用"""

    visits = (await db.execute(
        select(PageVisit).where(PageVisit.user_id == user_id)
        .order_by(PageVisit.visit_count.desc())
    )).scalars().all()

    total_visits = sum(v.visit_count for v in visits)
    top_pages = [
        {"path": v.path, "label": v.label, "count": v.visit_count}
        for v in visits[:5]
    ]

    # 生成简短的行为洞察文本
    insight = ""
    if top_pages:
        top_labels = [p["label"] for p in top_pages[:3] if p["label"] != "首页"]
        if top_labels:
            insight = f"你最常访问：{'、'.join(top_labels)}"
            # 如果是功能页面（不是首页），说明用户有明确兴趣方向
            if visits and len(visits) >= 5:
                insight += "。你的探索范围较广，对多个方向有兴趣"

    return {
        "total_visits": total_visits,
        "top_pages": top_pages,
        "insight": insight,
        "unique_pages": len(visits),
    }


# ── 人生参考点击追踪 ──────────────────────────────────

# 参考分类标签
REF_CATEGORY_LABELS = {
    "kaoyan": "考研深造", "job": "求职就业", "startup": "创业经历",
    "cross": "转行跨界", "life": "大学生活", "failure": "失败教训",
}


async def track_reference_click(user_id: int, click_type: str, detail: dict):
    """记录人生参考点击（分类切换 / 文章点击）"""
    from database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            cat_key = detail.get("category", "")
            cat_label = REF_CATEGORY_LABELS.get(cat_key, cat_key)

            if click_type == "category_view":
                # 分类查看 → 存为 page_visit
                path = f"/references?category={cat_key}"
            elif click_type == "article":
                # 文章点击 → 存具体标题
                title = detail.get("title", "")[:80]
                path = f"/references/article/{cat_key}"
            else:
                path = f"/references/click/{click_type}"

            existing = (await db.execute(
                select(PageVisit).where(
                    PageVisit.user_id == user_id,
                    PageVisit.path == path,
                )
            )).scalar_one_or_none()

            if existing:
                existing.visit_count += 1
                existing.last_visited = datetime.utcnow()
            else:
                visit = PageVisit(
                    user_id=user_id, path=path,
                    label=f"📖 {cat_label}",
                    visit_count=1,
                    last_visited=datetime.utcnow(),
                    first_visited=datetime.utcnow(),
                )
                db.add(visit)

            await db.commit()
        except Exception as e:
            logger.debug(f"Track ref click failed: {e}")
            await db.rollback()


async def get_reference_interests(db: AsyncSession, user_id: int) -> dict:
    """获取用户在人生参考中的兴趣分布"""
    visits = (await db.execute(
        select(PageVisit).where(
            PageVisit.user_id == user_id,
            PageVisit.path.like("/references%"),
        )
    )).scalars().all()

    # 按分类聚合
    cat_counts = {}
    total = 0
    for v in visits:
        label = v.label or ""
        # 提取分类名
        for key, cat_label in REF_CATEGORY_LABELS.items():
            if cat_label in label or key in v.path:
                cat_counts[cat_label] = cat_counts.get(cat_label, 0) + v.visit_count
                total += v.visit_count
                break

    top_cats = sorted(cat_counts.items(), key=lambda x: -x[1])[:3]
    insight = ""
    if top_cats:
        names = [c[0] for c in top_cats]
        insight = f"你对「{'」「'.join(names)}」类的真实经历特别关注"

    return {
        "category_counts": cat_counts,
        "top_categories": top_cats,
        "total_ref_clicks": total,
        "insight": insight,
    }
