"""认证 API（JSON 版）— 注册 / 登录 / 登出 / 当前用户"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.database import get_db
from backend.database.models import User
from backend.services.auth_service import (
    authenticate,
    create_user,
    get_user_by_email,
    get_user_by_username,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name or user.username,
        "email": user.email,
    }


def _set_session(request: Request, user: User):
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name or user.username,
        "email": user.email,
    }


@router.post("/register")
async def register(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", ""))
    confirm_password = str(body.get("confirm_password", ""))
    real_name = str(body.get("real_name", "")).strip() or None
    agree_terms = body.get("agree_terms", False)

    if not username or len(username) < 2 or len(username) > 50:
        return JSONResponse({"error": "用户名需为2-50个字符"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"error": "密码至少6位"}, status_code=400)
    if password != confirm_password:
        return JSONResponse({"error": "两次密码不一致"}, status_code=400)
    if not agree_terms:
        return JSONResponse({"error": "请阅读并同意用户协议和隐私政策"}, status_code=400)

    if await get_user_by_username(db, username):
        return JSONResponse({"error": "用户名已存在"}, status_code=400)
    if email and await get_user_by_email(db, email):
        return JSONResponse({"error": "邮箱已被注册"}, status_code=400)
    if not email:
        email = f"{username}@mirror.local"

    user = await create_user(db, username, email, password, real_name, True)
    _set_session(request, user)
    return JSONResponse({"ok": True, "user": _user_payload(user)})


@router.post("/login")
async def login(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    user = await authenticate(db, username, password)
    if not user:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    _set_session(request, user)
    return JSONResponse({"ok": True, "user": _user_payload(user)})


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"ok": True})


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    # 账户已注销时清空陈旧会话
    db_user = await db.get(User, int(user["id"]))
    if not db_user:
        request.session.clear()
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    return JSONResponse(user)
