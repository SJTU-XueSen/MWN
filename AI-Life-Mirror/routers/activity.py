"""用户行为追踪路由"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.activity_service import track_visit

router = APIRouter(prefix="/track", tags=["tracking"])


@router.post("")
async def track_page(request: Request):
    """记录页面访问"""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"ok": False, "reason": "not_logged_in"})

    body = await request.json()
    path = body.get("path", "/")

    await track_visit(user["id"], path)
    return JSONResponse({"ok": True})


@router.post("/ref-click")
async def track_ref_click(request: Request):
    """记录人生参考点击"""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"ok": False, "reason": "not_logged_in"})

    from services.activity_service import track_reference_click
    body = await request.json()
    await track_reference_click(user["id"], body.get("type", ""), body.get("detail", {}))
    return JSONResponse({"ok": True})
