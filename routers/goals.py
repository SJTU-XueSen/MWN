"""人生目标路由 — 完整 CRUD"""
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import LifeGoal
from templating import render

router = APIRouter(prefix="/goals", tags=["goals"])


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


# ── 目标列表 ──────────────────────────────────────────

@router.get("")
async def goal_list(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    active_goals = (await db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == uid, LifeGoal.status == "active"
        ).order_by(LifeGoal.importance.desc())
    )).scalars().all()

    achieved_goals = (await db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == uid, LifeGoal.status == "achieved"
        ).order_by(LifeGoal.updated_at.desc())
    )).scalars().all()

    return _render(request, "goals/list.html", active="goals",
                   active_goals=active_goals, achieved_goals=achieved_goals)


# ── 创建目标 ──────────────────────────────────────────

@router.get("/new")
async def goal_new_form(request: Request):
    if r := _require_login(request): return r
    return _render(request, "goals/form.html", active="goals", goal=None, editing=False)


@router.post("/new")
async def goal_create(
    request: Request,
    title: str = Form(...),
    goal_type: str = Form("other"),
    description: str = Form(""),
    importance: str = Form("50"),
    target_year: str = Form(""),
    target_period: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    goal = LifeGoal(
        user_id=uid,
        title=title,
        goal_type=goal_type,
        description=description or None,
        importance=int(importance) if importance else 50,
        target_year=int(target_year) if target_year else None,
        target_period=target_period or None,
        status="active",
    )
    db.add(goal)
    await db.commit()

    return RedirectResponse(url="/goals", status_code=302)


# ── 编辑目标 ──────────────────────────────────────────

@router.get("/{goal_id}/edit")
async def goal_edit_form(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if not goal or goal.user_id != uid:
        return RedirectResponse(url="/goals", status_code=302)
    return _render(request, "goals/form.html", active="goals", goal=goal, editing=True)


@router.post("/{goal_id}/edit")
async def goal_edit(
    request: Request, goal_id: int,
    title: str = Form(...),
    goal_type: str = Form("other"),
    description: str = Form(""),
    importance: str = Form("50"),
    target_year: str = Form(""),
    target_period: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if not goal or goal.user_id != uid:
        return RedirectResponse(url="/goals", status_code=302)

    goal.title = title
    goal.goal_type = goal_type
    goal.description = description or None
    goal.importance = int(importance) if importance else 50
    goal.target_year = int(target_year) if target_year else None
    goal.target_period = target_period or None
    goal.updated_at = datetime.utcnow()
    await db.commit()

    return RedirectResponse(url="/goals", status_code=302)


# ── 状态操作 ──────────────────────────────────────────

@router.get("/{goal_id}/done")
async def goal_done(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if goal and goal.user_id == uid:
        goal.status = "achieved"
        goal.updated_at = datetime.utcnow()
        await db.commit()
    return RedirectResponse(url="/goals", status_code=302)


@router.get("/{goal_id}/reactivate")
async def goal_reactivate(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if goal and goal.user_id == uid:
        goal.status = "active"
        goal.updated_at = datetime.utcnow()
        await db.commit()
    return RedirectResponse(url="/goals", status_code=302)


@router.get("/{goal_id}/delete")
async def goal_delete(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if goal and goal.user_id == uid:
        await db.delete(goal)
        await db.commit()
    return RedirectResponse(url="/goals", status_code=302)
