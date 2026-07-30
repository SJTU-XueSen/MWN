"""认证路由：注册、登录、登出、个人资料"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.auth_service import (
    create_user, authenticate, get_user_by_username,
    get_user_by_email, update_user_profile,
)
from templating import render

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(request: Request):
    """从 session 中获取当前登录用户"""
    return request.session.get("user")


def require_login(request: Request):
    """检查是否登录，未登录返回 None"""
    user = request.session.get("user")
    if not user:
        return None
    return user


# ── 页面路由 ─────────────────────────────────────────

@router.get("/login")
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(render("auth/login.html", {
        "request": request,
        "error": request.query_params.get("error", ""),
    }))


@router.get("/register")
async def register_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(render("auth/register.html", {
        "request": request,
        "error": request.query_params.get("error", ""),
    }))


# ── API 路由 ─────────────────────────────────────────

async def _parse_auth_body(request: Request):
    """同时支持 JSON 和 Form 数据"""
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        return await request.json()
    form = await request.form()
    return {k: v for k, v in form.items()}

@router.post("/register")
async def handle_register(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await _parse_auth_body(request)
    username = body.get("username", "")
    email = body.get("email", "")
    password = body.get("password", "")
    confirm_password = body.get("confirm_password", "")
    real_name = body.get("real_name", "")
    agree_terms = body.get("agree_terms", "")
    if password != confirm_password:
        return RedirectResponse(url="/auth/register?error=两次密码不一致", status_code=302)
    if len(password) < 6:
        return RedirectResponse(url="/auth/register?error=密码至少6位", status_code=302)
    if len(username) < 2 or len(username) > 50:
        return RedirectResponse(url="/auth/register?error=用户名2-50个字符", status_code=302)
    if not agree_terms:
        return RedirectResponse(url="/auth/register?error=请阅读并同意用户协议和隐私政策", status_code=302)

    if await get_user_by_username(db, username):
        return RedirectResponse(url="/auth/register?error=用户名已存在", status_code=302)
    if email and await get_user_by_email(db, email):
        return RedirectResponse(url="/auth/register?error=邮箱已被注册", status_code=302)
    if not email:
        email = f"{username}@mirror.local"

    user = await create_user(db, username, email, password, real_name or None, True)

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name or user.username,
        "email": user.email,
    }
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("mirror_uid", str(user.id), httponly=False)
    resp.set_cookie("mirror_username", user.username, httponly=False)
    return resp


@router.post("/login")
async def handle_login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await _parse_auth_body(request)
    username = body.get("username", "")
    password = body.get("password", "")
    user = await authenticate(db, username, password)
    if not user:
        return RedirectResponse(url="/auth/login?error=用户名或密码错误", status_code=302)

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("mirror_uid", str(user.id), httponly=False)
    resp.set_cookie("mirror_username", user.username, httponly=False)
    return resp


@router.get("/logout")
async def handle_logout(request: Request):
    request.session.clear()
    resp = RedirectResponse(url="/auth/login", status_code=302)
    resp.delete_cookie("mirror_uid")
    resp.delete_cookie("mirror_username")
    return resp
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/profile")
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse(url="/auth/login", status_code=302)

    from services.auth_service import get_user_by_id
    user = await get_user_by_id(db, user_session["id"])

    return HTMLResponse(render("auth/profile.html", {
        "request": request,
        "user": request.session.get("user"),
        "profile": user,
        "success": request.query_params.get("success", ""),
    }))


@router.post("/profile")
async def handle_profile_update(
    request: Request,
    major: str = Form(""),
    university: str = Form(""),
    grade: str = Form(""),
    age: str = Form(""),
    bio: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse(url="/auth/login", status_code=302)

    await update_user_profile(
        db, user_session["id"],
        major=major or None,
        university=university or None,
        grade=grade or None,
        age=int(age) if age else None,
        bio=bio or None,
    )
    return RedirectResponse(url="/auth/profile?success=资料已更新", status_code=302)
