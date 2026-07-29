"""数字人格画像路由"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.persona_service import (
    generate_persona, get_current_persona, get_persona_history,
    get_persona_by_id,
)
from templating import render

router = APIRouter(prefix="/persona", tags=["persona"])


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


# ── 画像主页 ──────────────────────────────────────────

@router.get("")
async def persona_page(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    persona = await get_current_persona(db, uid)
    history = await get_persona_history(db, uid)

    # 兴趣图标映射
    interest_icons = {
        "AI": "🤖", "编程": "💻", "工程实践": "🔧", "数学": "📐",
        "哲学": "💭", "创业": "🚀", "科研": "🔬", "社交": "👥",
        "艺术": "🎨", "运动": "🏃",
    }

    return _render(request, "persona/detail.html", active="persona",
                   persona=persona, history=history,
                   interest_icons=interest_icons)


# ── 生成/更新画像 ─────────────────────────────────────

@router.post("/generate")
async def persona_generate(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    await generate_persona(db, uid, "用户手动触发生成")
    return RedirectResponse(url="/persona", status_code=302)


@router.get("/version/{persona_id}")
async def persona_version(request: Request, persona_id: int, db: AsyncSession = Depends(get_db)):
    """查看历史版本的画像"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    persona = await get_persona_by_id(db, persona_id)
    if not persona or persona.user_id != uid:
        return RedirectResponse(url="/persona", status_code=302)

    history = await get_persona_history(db, uid)
    interest_icons = {
        "AI": "🤖", "编程": "💻", "工程实践": "🔧", "数学": "📐",
        "哲学": "💭", "创业": "🚀", "科研": "🔬", "社交": "👥",
        "艺术": "🎨", "运动": "🏃",
    }

    return _render(request, "persona/detail.html", active="persona",
                   persona=persona, history=history,
                   interest_icons=interest_icons, viewing_history=True)
