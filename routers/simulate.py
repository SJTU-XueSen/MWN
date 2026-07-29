"""人生模拟路由"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import FutureSelf
from sqlalchemy import select as sa_select
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
    value_pursuit: str = Form("50"),
    uncertainty: str = Form("50"),
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
        "价值追求": value_pursuit,
        "不确定性接受": uncertainty,
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

    # 获取关联的 FutureSelf ID 列表
    futures = (await db.execute(
        sa_select(FutureSelf).where(
            FutureSelf.simulation_id == sim_id,
            FutureSelf.user_id == uid,
        ).order_by(FutureSelf.id.asc())
    )).scalars().all()

    return _render(request, "simulation/detail.html", active="simulation",
                   sim=sim, SCENARIO_LABELS=SCENARIO_LABELS, futures=futures)


# ── 删除 ──────────────────────────────────────────────

@router.post("/{sim_id}/to-goal/{path_index}")
async def convert_to_goal(request: Request, sim_id: int, path_index: int, db: AsyncSession = Depends(get_db)):
    """将认同的未来路径一键设为目标"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sim = await get_simulation_by_id(db, sim_id)
    if not sim or sim.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    paths = sim.output_paths or []
    if path_index < 0 or path_index >= len(paths):
        return RedirectResponse(url=f"/simulation/{sim_id}", status_code=302)

    path = paths[path_index]
    from database.models import LifeGoal

    # 主目标
    goal = LifeGoal(
        user_id=uid,
        title=f"成为{path.get('label', '未来的自己')}",
        goal_type="other",
        description=path.get("description", "")[:200],
        importance=80,
        target_period="长期",
        status="active",
    )
    db.add(goal)

    # 从建议拆分子目标
    for s in path.get("gap_suggestions", [])[:3]:
        sub = LifeGoal(
            user_id=uid,
            title=s[:100],
            goal_type="skill",
            importance=60,
            target_period="中期",
            status="active",
        )
        db.add(sub)

    await db.commit()
    return RedirectResponse(url="/goals", status_code=302)


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


@router.post("/{sim_id}/save-future/{path_index}")
async def save_future_path(request: Request, sim_id: int, path_index: int, db: AsyncSession = Depends(get_db)):
    """将一个模拟路径显式保存为 FutureSelf"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sim = await get_simulation_by_id(db, sim_id)
    if not sim or sim.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    paths = sim.output_paths or []
    if path_index < 0 or path_index >= len(paths):
        return RedirectResponse(url=f"/simulation/{sim_id}", status_code=302)

    from database.models import FutureSelf
    from sqlalchemy import select
    futures = (await db.execute(
        select(FutureSelf).where(
            FutureSelf.simulation_id == sim_id,
            FutureSelf.user_id == uid,
        )
    )).scalars().all()

    if path_index < len(futures):
        futures[path_index].basis_summary = "⭐ 已保存 | " + (futures[path_index].basis_summary or "")
        await db.commit()

    return RedirectResponse(url=f"/future-chat/{futures[path_index].id if path_index < len(futures) else ''}", status_code=302)


@router.post("/{sim_id}/to-goal/{path_index}")
async def convert_path_to_goals(request: Request, sim_id: int, path_index: int, db: AsyncSession = Depends(get_db)):
    """将认同的未来路径转化为人生目标"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    sim = await get_simulation_by_id(db, sim_id)
    if not sim or sim.user_id != uid:
        return RedirectResponse(url="/simulation", status_code=302)

    paths = sim.output_paths or []
    if path_index < 0 or path_index >= len(paths):
        return RedirectResponse(url=f"/simulation/{sim_id}", status_code=302)

    path = paths[path_index]
    from database.models import LifeGoal

    # 创建主目标
    main_goal = LifeGoal(
        user_id=uid,
        title=f"成为{path.get('label', '未来的自己')}",
        goal_type="other",
        description=path.get('description', '')[:200],
        importance=80,
        target_period="长期",
        status="active",
    )
    db.add(main_goal)

    # 从成长杠杆拆分为中短期子目标
    levers = path.get('growth_levers', [])
    for lever in levers[:3]:
        sub_goal = LifeGoal(
            user_id=uid,
            title=lever.get('action', ''),
            goal_type="skill",
            description=f"来自「{path.get('label', '')}」未来路径的行动建议",
            importance=60,
            target_period="中期",
            status="active",
        )
        db.add(sub_goal)

    await db.commit()
    return RedirectResponse(url="/goals", status_code=302)
