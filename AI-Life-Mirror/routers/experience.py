"""人生拟真体验路由"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.life_experience_service import (
    start_experience, generate_scene, process_choice, get_session,
)
from templating import render

router = APIRouter(prefix="/experience", tags=["experience"])


def _req(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return None


def _render(request: Request, template: str, **kw):
    return HTMLResponse(render(template, {"request": request, "user": request.session.get("user"), **kw}))


@router.get("/start/{future_self_id}")
async def start(request: Request, future_self_id: int, db: AsyncSession = Depends(get_db)):
    if r := _req(request): return r
    uid = request.session["user"]["id"]

    session = await start_experience(db, uid, future_self_id)
    scene = await generate_scene(db, session)

    return _render(request, "experience/play.html", active="simulation",
                   session=session, scene=scene)


@router.post("/play/{session_id}")
async def play(request: Request, session_id: int, choice: str = Form("0"), custom_choice: str = Form(""), db: AsyncSession = Depends(get_db)):
    if r := _req(request): return r
    uid = request.session["user"]["id"]

    session = await get_session(db, session_id)
    if not session or session.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    scene = await generate_scene(db, session)
    choice_idx = int(choice)

    if choice_idx == -1 and custom_choice.strip():
        # 开放式选择：构造自定义 choice 对象
        custom = {
            "text": custom_choice.strip(),
            "gain": "你自由选择了这条路",
            "cost": "不确定的代价",
            "hint": "这是你自己的选择——结果完全取决于你的判断和人格倾向",
        }
        # 临时加入 scene.choices 以便 process_choice 处理
        original_choices = scene.get("choices", [])
        scene["choices"] = original_choices + [custom]
        choice_idx = len(original_choices)

    result = await process_choice(db, session, choice_idx, scene)

    # 恢复原始的 choices
    if choice_idx == len(scene.get("choices", [])) - 1 and custom_choice.strip():
        scene["choices"] = scene["choices"][:-1]

    next_scene = await generate_scene(db, session, result)

    return _render(request, "experience/play.html", active="simulation",
                   session=session, scene=next_scene, last_result=result)


@router.get("/restart/{session_id}")
async def restart(request: Request, session_id: int, db: AsyncSession = Depends(get_db)):
    if r := _req(request): return r
    uid = request.session["user"]["id"]

    old = await get_session(db, session_id)
    if not old or old.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    fs_id = old.future_self_id or 0
    await db.delete(old)
    await db.commit()

    return RedirectResponse(url=f"/experience/start/{fs_id}", status_code=302)
