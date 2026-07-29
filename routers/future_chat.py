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


# ── 流式发送（SSE）────────────────────────────────────

@router.post("/{future_self_id}/stream")
async def chat_stream(request: Request, future_self_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    body = await request.json()
    message = body.get("message", "")

    from services.chat_service import get_future_self, stream_reply
    from database.models import ChatMessage
    from datetime import datetime

    future_self = await get_future_self(db, future_self_id)
    if not future_self or future_self.user_id != uid:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "not found"}, status_code=404)

    from fastapi.responses import StreamingResponse
    import json as _json

    async def event_stream():
        # 1. 保存用户消息
        user_msg = ChatMessage(
            user_id=uid, future_self_id=future_self_id,
            role="user", content=message,
            created_at=datetime.utcnow(),
        )
        db.add(user_msg)
        await db.commit()

        # 2. 发送用户消息确认
        yield f"data: {_json.dumps({'type': 'user_saved', 'id': user_msg.id})}\n\n"

        # 3. 流式 AI 回复
        full_reply = ""
        async for token in stream_reply(future_self, uid, message):
            full_reply += token
            yield f"data: {_json.dumps({'type': 'token', 'text': token})}\n\n"

        # 4. 保存 AI 回复
        ai_msg = ChatMessage(
            user_id=uid, future_self_id=future_self_id,
            role="assistant", content=full_reply,
            created_at=datetime.utcnow(),
        )
        db.add(ai_msg)
        await db.commit()

        # 5. 完成
        yield f"data: {_json.dumps({'type': 'done', 'id': ai_msg.id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── 清除对话 ──────────────────────────────────────────

@router.get("/{future_self_id}/clear")
async def chat_clear(request: Request, future_self_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    await delete_future_self_chat(db, future_self_id, uid)
    return RedirectResponse(url=f"/future-chat/{future_self_id}", status_code=302)
