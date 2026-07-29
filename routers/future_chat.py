"""未来自我对话路由"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.chat_service import (
    get_user_future_selves, get_future_self, get_chat_messages,
    send_message, delete_future_self_chat,
)
from templating import render

router = APIRouter(prefix="/future-chat", tags=["future-chat"])


def _require_login(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return None


def _render(request: Request, template: str, **kwargs):
    return HTMLResponse(render(template, {
        "request": request,
        "user": request.session.get("user"),
        **kwargs,
    }))


# ── 未来人格列表 ──────────────────────────────────────

@router.get("")
async def future_chat_list(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    future_selves = await get_user_future_selves(db, uid)
    return _render(request, "chat/list.html", active="future_chat",
                   future_selves=future_selves)


# ── 对话房间 ──────────────────────────────────────────

@router.get("/{future_self_id}")
async def chat_room(request: Request, future_self_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    future_self = await get_future_self(db, future_self_id)
    if not future_self or future_self.user_id != uid:
        return RedirectResponse(url="/future-chat", status_code=302)

    messages = await get_chat_messages(db, future_self_id)
    return _render(request, "chat/room.html", active="future_chat",
                   future_self=future_self, messages=messages)


# ── 发送消息 ──────────────────────────────────────────

@router.post("/{future_self_id}/send")
async def chat_send(
    request: Request,
    future_self_id: int,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    await send_message(db, uid, future_self_id, message)
    return RedirectResponse(url=f"/future-chat/{future_self_id}", status_code=302)


# ── 清除对话 ──────────────────────────────────────────

@router.get("/{future_self_id}/clear")
async def chat_clear(request: Request, future_self_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    await delete_future_self_chat(db, future_self_id, uid)
    return RedirectResponse(url=f"/future-chat/{future_self_id}", status_code=302)
