"""真实人生参考路由"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User, PersonaProfile
from sqlalchemy import select
from services.life_reference_service import search_category, get_all_categories
from templating import render

router = APIRouter(prefix="/references", tags=["references"])


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


@router.get("")
async def references_list(request: Request, category: str = "kaoyan", db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    # 获取用户专业和兴趣，用于精准推送
    user = await db.get(User, uid)
    persona = (await db.execute(
        select(PersonaProfile).where(
            PersonaProfile.user_id == uid,
            PersonaProfile.is_current == True,
        ).limit(1)
    )).scalar_one_or_none()

    user_context = ""
    if user and user.major:
        user_context += user.major
    if persona and persona.interest_profile:
        top_interests = list(persona.interest_profile.keys())[:3]
        if top_interests:
            user_context += " " + " ".join(top_interests)

    categories = get_all_categories()
    results = await search_category(category, user_context.strip())

    return _render(request, "references/list.html", active="references",
                   categories=categories, results=results, current=category,
                   user_context=user_context.strip())
