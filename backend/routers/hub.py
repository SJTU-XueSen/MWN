"""Hub API — 备忘录/通知/学生活动（SQLite 持久化）+ 行为追踪 + AI 检索 + SJTU 活动

原实现为进程内内存 dict（重启即丢），现已全部落库。
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import Memo, Notification, StudentActivity

router = APIRouter(prefix="/api", tags=["hub"])


# ── 行为追踪 ──────────────────────────────────────────

@router.post("/track")
async def api_track(request: Request):
    """页面访问/搜索/点击追踪（登录用户）"""
    uid = require_uid(request)
    body = await request.json()
    from backend.services.activity_service import track_reference_click, track_visit

    event_type = body.get("event") or body.get("type") or "pageview"
    detail = body.get("detail", {})
    async with AsyncSessionLocal() as db:
        if event_type in ("search",):
            await track_reference_click(db, uid, "search", {"query": body.get("query", detail.get("query", ""))})
        elif event_type in ("click", "article_click"):
            await track_reference_click(db, uid, "article", detail)
        else:
            path = body.get("path", detail.get("path", "/"))
            await track_visit(db, uid, path)
    return JSONResponse({"ok": True})


# ── 备忘录（SQLite 持久化）──────────────────────────

@router.get("/memos")
async def api_memos(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        memos = (
            await db.execute(
                select(Memo).where(Memo.user_id == uid).order_by(Memo.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse({"items": [
            {
                "id": str(m.id), "title": m.title, "note": m.note, "deadline": m.deadline,
                "createdAt": m.created_at.isoformat() if m.created_at else "",
            }
            for m in memos
        ]})


@router.post("/memos")
async def api_memo_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        memo = Memo(
            user_id=uid,
            title=body.get("title", ""),
            note=body.get("content", body.get("note", "")),
            deadline=body.get("deadline", ""),
        )
        db.add(memo)
        await db.commit()
        await db.refresh(memo)
        return JSONResponse({
            "id": str(memo.id), "title": memo.title, "note": memo.note, "deadline": memo.deadline,
            "createdAt": memo.created_at.isoformat() if memo.created_at else "",
        })


@router.delete("/memos/{memo_id}")
async def api_memo_delete(request: Request, memo_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        memo = await db.get(Memo, memo_id)
        if not memo or memo.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await db.delete(memo)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 通知 ──────────────────────────────────────────────

@router.get("/notifications")
async def api_notifications(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        items = (
            await db.execute(
                select(Notification).where(Notification.user_id == uid).order_by(Notification.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": n.id, "title": n.title, "message": n.message, "read": n.read,
             "createdAt": n.created_at.isoformat() if n.created_at else ""}
            for n in items
        ])


@router.post("/notifications")
async def api_notification_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        n = Notification(user_id=uid, title=body.get("title", ""), message=body.get("message", ""), read=False)
        db.add(n)
        await db.commit()
        await db.refresh(n)
        return JSONResponse({"id": n.id, "title": n.title, "message": n.message, "read": n.read})


@router.delete("/notifications/{notif_id}")
async def api_notification_delete(request: Request, notif_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        n = await db.get(Notification, notif_id)
        if not n or n.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await db.delete(n)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 学生活动 ──────────────────────────────────────────

@router.get("/student-activities")
async def api_student_activities(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        items = (
            await db.execute(
                select(StudentActivity).where(StudentActivity.user_id == uid)
                .order_by(StudentActivity.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": a.id, "title": a.title, "description": a.description, "url": a.url,
             "date": a.date, "location": a.location, "organizer": a.organizer, "contact": a.contact,
             "status": a.status}
            for a in items
        ])


@router.post("/student-activities")
async def api_student_activity_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        a = StudentActivity(
            user_id=uid,
            title=body.get("title", ""),
            description=body.get("description", ""),
            url=body.get("url", ""),
            date=body.get("date", ""),
            location=body.get("location", ""),
            organizer=body.get("organizer", ""),
            contact=body.get("contact", ""),
            status="pending",
        )
        db.add(a)
        await db.commit()
        await db.refresh(a)
        return JSONResponse({"id": a.id, "ok": True})


@router.delete("/student-activities/{act_id}")
async def api_student_activity_delete(request: Request, act_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        a = await db.get(StudentActivity, act_id)
        if not a or a.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await db.delete(a)
        await db.commit()
        return JSONResponse({"ok": True})


# ── SJTU 活动（本地爬虫，不再代理 3001）─────────────

@router.get("/activities")
async def api_activities(request: Request, refresh: str = "0"):
    """SJTU 官网通知爬虫（本地 Python 实现，30 分钟缓存）"""
    try:
        from backend.services.sjtu_crawler import get_activities

        return JSONResponse(await get_activities(force_refresh=(refresh == "1")))
    except Exception as e:
        return JSONResponse({"items": [], "stats": {}, "error": f"爬虫服务不可用: {e}"})


# ── AI 检索（本地实现，不再代理 3001）───────────────

@router.post("/ai-search")
async def api_ai_search(request: Request):
    """DeepSeek 语义匹配活动 + 推荐理由"""
    body = await request.json()
    query = str(body.get("query", "")).strip()
    if not query:
        return JSONResponse({"success": False, "error": "请输入搜索内容"})
    try:
        from backend.services.ai_matcher import ai_search

        result = await ai_search(query)
        result["success"] = True
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"搜索服务不可用: {e}"})
