"""活动平台 — 团队聊天 + DeepSeek 协作助手"""
import base64
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select

from backend.auth import require_uid
from backend.config import UPLOAD_DIR
from backend.database.database import AsyncSessionLocal
from backend.database.models import Team, TeamChatMessage, TeamMember, User

router = APIRouter(prefix="/api", tags=["chat"])


async def _user_team(db, user_id: int):
    return (
        await db.execute(
            select(TeamMember).where(TeamMember.user_id == user_id).limit(1)
        )
    ).scalar_one_or_none()


@router.post("/chat/send")
async def api_chat_send(request: Request):
    uid = require_uid(request)
    body = await request.json()
    content = str(body.get("content", "")).strip()
    chat_type = str(body.get("chat_type", "group"))  # group 组内 / team 团队
    image_url = str(body.get("image_url", ""))
    image_data = body.get("image_data", "")

    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"error": "未加入战队"}, 404)
        team = await db.get(Team, tm.team_id)

        if image_data and not image_url:
            try:
                raw = base64.b64decode(image_data.split(",")[-1])
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                fname = f"chat_{uuid.uuid4().hex}.png"
                with open(UPLOAD_DIR / fname, "wb") as f:
                    f.write(raw)
                image_url = f"/uploads/{fname}"
            except Exception:
                pass

        if not content and not image_url:
            return JSONResponse({"error": "消息不能为空"}, 400)

        msg = TeamChatMessage(team_id=team.id, user_id=uid, chat_type=chat_type, content=content, image_url=image_url)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

        user = await db.get(User, uid)
        return JSONResponse({"ok": True, "msg": {
            "id": msg.id,
            "user_name": user.real_name or user.username,
            "user_id": user.id,
            "content": msg.content,
            "image_url": msg.image_url,
            "chat_type": msg.chat_type,
            "created_at": msg.created_at.strftime("%H:%M") if msg.created_at else "",
        }})


@router.get("/chat/messages/{chat_type}")
async def api_chat_messages(request: Request, chat_type: str):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"messages": []})
        msgs = (
            await db.execute(
                select(TeamChatMessage).where(
                    TeamChatMessage.team_id == tm.team_id, TeamChatMessage.chat_type == chat_type
                ).order_by(TeamChatMessage.created_at.asc()).limit(100)
            )
        ).scalars().all()
        messages = []
        for m in msgs:
            user = await db.get(User, m.user_id)
            messages.append({
                "id": m.id,
                "user_name": user.real_name if user else "",
                "user_id": m.user_id,
                "content": m.content, "image_url": m.image_url,
                "created_at": m.created_at.strftime("%H:%M") if m.created_at else "",
            })
        return JSONResponse({"messages": messages})


@router.post("/chat/upload-image")
async def api_chat_upload_image(request: Request, file: UploadFile = File(...)):
    uid = require_uid(request)
    if not file or not file.filename:
        return JSONResponse({"error": "未选择文件"}, 400)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".png"
    fname = f"chat_{uuid.uuid4().hex}{ext}"
    content = await file.read()
    with open(UPLOAD_DIR / fname, "wb") as f:
        f.write(content)
    return JSONResponse({"ok": True, "image_url": f"/uploads/{fname}"})


@router.post("/deepseek/chat")
async def api_deepseek_chat(request: Request):
    """团队协作 DeepSeek 助手（用户可自填 key）"""
    import asyncio

    uid = require_uid(request)
    body = await request.json()
    messages = body.get("messages", [])
    api_key = str(body.get("api_key", "")).strip()
    if not messages:
        return JSONResponse({"error": "消息不能为空"}, 400)

    from backend.config import DEEPSEEK_API_KEY

    has_backend_key = bool(DEEPSEEK_API_KEY)
    if not has_backend_key and not api_key:
        return JSONResponse({
            "reply": "⚠ 请先点击右上角设置按钮，输入你的 DeepSeek API Key。",
            "need_config": True,
        })

    def _call():
        from backend.services.ai_filter import deepseek_chat, deepseek_chat_with_key

        system = [{"role": "system", "content": "你是团队协作助手，帮助团队成员完成任务协作。回答简洁、实用、有建设性。"}]
        if api_key and has_backend_key:
            return deepseek_chat_with_key(api_key, system + messages)
        if api_key:
            return deepseek_chat_with_key(api_key, system + messages)
        return deepseek_chat(system + messages, max_tokens=2000, temperature=0.7)

    try:
        reply = await asyncio.to_thread(_call)
        if not reply:
            return JSONResponse({"error": "API 调用失败"}, 500)
        return JSONResponse({"ok": True, "reply": reply})
    except Exception as e:
        return JSONResponse({"error": f"DeepSeek API 错误: {str(e)[:200]}"}, 500)
