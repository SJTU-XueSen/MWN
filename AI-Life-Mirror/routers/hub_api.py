"""Horizon 活动平台 API — 供 React 前端调用，爬虫代理到 Express 3001"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["hub"])


@router.get("/activities")
async def api_activities(request: Request, refresh: str = "0"):
    """代理到 Express 3001 爬虫服务"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"http://127.0.0.1:3001/api/activities?refresh={refresh}")
            return JSONResponse(resp.json())
    except Exception:
        return JSONResponse({"items": [], "stats": {}, "error": "爬虫服务不可用"})


@router.get("/hub/health")
async def api_health():
    return {"status": "ok", "service": "hub-api"}


# ── 行为追踪（供 React 前端）───────────────────

@router.post("/track")
async def api_track(request: Request):
    """React 前端页面访问/搜索/点击追踪"""
    from services.activity_service import track_visit, track_reference_click
    uid = request.session.get("user", {}).get("id")
    if not uid: return JSONResponse({"ok": False})
    body = await request.json()
    # 兼容新旧格式
    event_type = body.get("event") or body.get("type") or "pageview"
    detail = body.get("detail", {})
    if event_type in ("search",):
        await track_reference_click(uid, "search", {"query": body.get("query", detail.get("query", "")), "category": "search"})
    elif event_type in ("click", "article_click"):
        await track_reference_click(uid, "article", detail)
    else:
        path = body.get("path", detail.get("path", "/"))
        await track_visit(uid, path)
    return JSONResponse({"ok": True})


# ── 备忘录 ──────────────────────────────────────────

_memos_store: dict[str, list[dict]] = {}

@router.get("/memos")
async def api_memos(request: Request):
    uid = request.session.get("user", {}).get("id", "anon")
    return JSONResponse(_memos_store.get(str(uid), []))

@router.post("/memos")
async def api_memo_create(request: Request):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    body = await request.json()
    memo = {"id": str(len(_memos_store.get(uid, [])) + 1), "title": body.get("title", ""), "content": body.get("content", ""), "createdAt": body.get("createdAt", "")}
    _memos_store.setdefault(uid, []).append(memo)
    return JSONResponse(memo)

@router.delete("/memos/{memo_id}")
async def api_memo_delete(request: Request, memo_id: str):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    _memos_store[uid] = [m for m in _memos_store.get(uid, []) if m["id"] != memo_id]
    return JSONResponse({"ok": True})


# ── 通知 ──────────────────────────────────────────

_notifications_store: dict[str, list[dict]] = {}

@router.get("/notifications")
async def api_notifications(request: Request):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    return JSONResponse(_notifications_store.get(uid, []))

@router.post("/notifications")
async def api_notification_create(request: Request):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    body = await request.json()
    n = {"id": str(len(_notifications_store.get(uid, [])) + 1), "title": body.get("title", ""), "message": body.get("message", ""), "read": False}
    _notifications_store.setdefault(uid, []).append(n)
    return JSONResponse(n)

@router.delete("/notifications/{notif_id}")
async def api_notification_delete(request: Request, notif_id: str):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    _notifications_store[uid] = [n for n in _notifications_store.get(uid, []) if n["id"] != notif_id]
    return JSONResponse({"ok": True})


# ── 学生活动 ──────────────────────────────────────

_student_activities_store: dict[str, list[dict]] = {}

@router.get("/student-activities")
async def api_student_activities(request: Request):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    return JSONResponse(_student_activities_store.get(uid, []))

@router.post("/student-activities")
async def api_student_activity_create(request: Request):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    body = await request.json()
    a = {"id": str(len(_student_activities_store.get(uid, [])) + 1), "title": body.get("title", ""), "url": body.get("url", ""), "status": body.get("status", "pending")}
    _student_activities_store.setdefault(uid, []).append(a)
    return JSONResponse(a)

@router.delete("/student-activities/{act_id}")
async def api_student_activity_delete(request: Request, act_id: str):
    uid = str(request.session.get("user", {}).get("id", "anon"))
    _student_activities_store[uid] = [a for a in _student_activities_store.get(uid, []) if a["id"] != act_id]
    return JSONResponse({"ok": True})


# ── AI 搜索（代理到 Express 3001）─────────────────

@router.post("/ai-search")
async def api_ai_search(request: Request):
    """代理到 Express 3001 AI 搜索服务"""
    import httpx
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("http://127.0.0.1:3001/api/ai-search", json=body)
            return JSONResponse(resp.json())
    except Exception:
        return JSONResponse({"success": False, "error": "搜索服务不可用"})
