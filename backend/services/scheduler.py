"""爬虫调度器 — 每天 00:00 / 12:00 爬取 6 个 SJTU 站点 + AI 筛选入库 + 定期清理

由 main.py lifespan 启动（uvicorn 必须 --workers 1，进程内单例）。
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from backend.database.database import AsyncSessionLocal
from backend.database.models import Competition, ScrapeLog

logger = logging.getLogger(__name__)

_last_run_at = 0.0
_last_scrape_result: dict = {"raw": 0, "new": 0, "ai_filtered": 0, "errors": []}


async def do_scrape() -> dict:
    """执行一次全量爬取：6 站点 → 初筛 → 详情 → AI 分析 → 入库"""
    global _last_run_at, _last_scrape_result
    import time

    from backend.services.scraper.sjtu_scraper import (
        fetch_details_batch,
        is_competition_related,
        scrape_all,
    )

    items, errors = await asyncio.to_thread(scrape_all)
    related = [i for i in items if is_competition_related(i.get("title", ""))]
    details = await asyncio.to_thread(fetch_details_batch, related)

    from backend.services.ai_filter import analyze_competition_page

    # 并发 AI 分析（4 线程并行，单条 GLM 调用 ~10s，串行会拖到 5 分钟+）
    def _analyze_one(item):
        detail_text = details.get(item["url"], "")
        if not detail_text or detail_text.startswith("[抓取失败"):
            return item, None
        try:
            return item, analyze_competition_page(
                title=item["title"], url=item["url"],
                source=item["source"], detail_text=detail_text,
            )
        except Exception:
            return item, None

    def _run_concurrent():
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as ex:
            return list(ex.map(_analyze_one, related))

    analyzed = await asyncio.to_thread(_run_concurrent)

    new_count = 0
    ai_filtered = 0
    async with AsyncSessionLocal() as db:
        existing_urls = set(
            (await db.execute(select(Competition.source_url))).scalars().all()
        )
        for item, result in analyzed:
            if result is None:
                ai_filtered += 1
                continue
            if result.get("source_url") in existing_urls:
                continue
            # ── 筛选机制：只剔除无效内容 ──
            # 1) 学生无需主动参与（needs_participation=False，如纯通知/讲座）
            if result.get("needs_participation") is False:
                ai_filtered += 1
                continue
            # 2) 已过报名截止
            if result.get("deadline"):
                try:
                    dl = datetime.fromisoformat(result["deadline"])
                    if dl < datetime.utcnow():
                        ai_filtered += 1
                        continue
                except Exception:
                    pass
            # 3) 规则引擎兜底路径无 is_competition 标记：按关键词判断
            #    竞赛（is_competition=True）入库后由「竞赛」tab 播报，
            #    组队活动（False）由活动大厅展示——两条通道都保留
            deadline = None
            if result.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(result["deadline"])
                except Exception:
                    pass
            comp = Competition(
                title=result.get("title", "")[:200],
                source_url=result.get("source_url", ""),
                source_site=result.get("source_site", "上海交通大学"),
                category=result.get("category", ""),
                level=result.get("level", ""),
                description=result.get("description", ""),
                registration_deadline=deadline,
                organizer=result.get("organizer", ""),
                max_team_size=result.get("max_team_size", 5),
                min_team_size=result.get("min_team_size", 1),
                credit_info=result.get("credit_info", ""),
                tags=result.get("tags", []),
                ai_confidence=result.get("ai_confidence", 0.0),
                raw_content="",
                status="active",
                approval_status="approved",
                publisher_type="scraped",
                publisher_name=result.get("source_site", "爬虫"),
                # 使用 AI 判定：学科竞赛/创新创业类 → 竞赛通道；活动类 → 组队活动通道
                is_competition=bool(result.get("is_competition", False)),
            )
            db.add(comp)
            existing_urls.add(comp.source_url)
            new_count += 1
        log = ScrapeLog(
            source_url="6 个 SJTU 站点",
            status="success" if not errors else "partial",
            items_found=len(items),
            ai_filtered=ai_filtered + (len(related) - len(analyzed)),
            error_msg="; ".join(str(e.get("error")) for e in errors[:3]),
        )
        db.add(log)
        await db.commit()

    _last_run_at = time.time()
    _last_scrape_result = {"raw": len(items), "new": new_count, "ai_filtered": ai_filtered, "errors": errors[:3]}
    logger.info(f"爬取完成: 扫描{len(items)}条, 新增{new_count}条, 过滤{ai_filtered}条")
    return _last_scrape_result


async def _cleanup_activities():
    """清理：过期活动、低置信度、标题重复（照搬原 nexus 清理逻辑）"""
    async with AsyncSessionLocal() as db:
        # 过期
        expired = (
            await db.execute(
                select(Competition).where(
                    Competition.registration_deadline < datetime.utcnow(),
                    Competition.status == "active",
                )
            )
        ).scalars().all()
        for c in expired:
            c.status = "expired"

        # 标题重复（保留最新一条）
        titles = (await db.execute(select(Competition.title))).scalars().all()
        seen: dict = {}
        for t in titles:
            seen[t] = seen.get(t, 0) + 1
        dup_titles = [t for t, cnt in seen.items() if cnt > 1]
        for t in dup_titles:
            rows = (
                await db.execute(
                    select(Competition).where(Competition.title == t).order_by(Competition.created_at.asc())
                )
            ).scalars().all()
            for r in rows[:-1]:
                r.status = "archived"
        await db.commit()


async def start_scheduler():
    """调度循环：每天 00:00 / 12:00 触发爬取"""
    while True:
        now = datetime.utcnow()
        targets = [now.replace(hour=0, minute=0, second=0, microsecond=0),
                   now.replace(hour=12, minute=0, second=0, microsecond=0)]
        next_target = min((t for t in targets if t > now), default=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))

        delay = (next_target - now).total_seconds()
        await asyncio.sleep(max(1, delay))

        try:
            await do_scrape()
            await _cleanup_activities()
        except Exception as e:
            logger.error(f"定时爬取失败: {e}")
