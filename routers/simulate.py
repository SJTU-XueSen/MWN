"""人生模拟路由"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.simulation_service import (
    run_simulation, get_user_simulations, get_simulation_by_id,
    SCENARIO_LABELS,
)
from templating import render

router = APIRouter(prefix="/simulation", tags=["simulation"])


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


# ── 模拟列表 ──────────────────────────────────────────

@router.get("")
async def simulation_list(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sims = await get_user_simulations(db, uid)
    return _render(request, "simulation/list.html", active="simulation",
                   simulations=sims, SCENARIO_LABELS=SCENARIO_LABELS)


# ── 新建模拟 ──────────────────────────────────────────

@router.get("/new")
async def simulation_new(request: Request):
    if r := _require_login(request): return r
    return _render(request, "simulation/new.html", active="simulation",
                   SCENARIO_LABELS=SCENARIO_LABELS)


@router.post("/new")
async def simulation_create(
    request: Request,
    scenario: str = Form(...),
    question: str = Form(""),
    exploration: str = Form("50"),
    stability: str = Form("50"),
    creativity: str = Form("50"),
    social: str = Form("50"),
    tech_depth: str = Form("50"),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    variables = {
        "探索程度": exploration,
        "稳定偏好": stability,
        "创造投入": creativity,
        "社交网络": social,
        "技术深耕": tech_depth,
    }

    sim = await run_simulation(db, uid, scenario, question, variables)

    return RedirectResponse(url=f"/simulation/{sim.id}", status_code=302)


# ── 模拟详情 ──────────────────────────────────────────

@router.get("/{sim_id}")
async def simulation_detail(request: Request, sim_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sim = await get_simulation_by_id(db, sim_id)
    if not sim or sim.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    return _render(request, "simulation/detail.html", active="simulation",
                   sim=sim, SCENARIO_LABELS=SCENARIO_LABELS)


# ── 删除 ──────────────────────────────────────────────

@router.get("/{sim_id}/delete")
async def simulation_delete(request: Request, sim_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sim = await get_simulation_by_id(db, sim_id)
    if not sim or sim.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)
    await db.delete(sim)
    await db.commit()
    return RedirectResponse(url="/simulation", status_code=302)
