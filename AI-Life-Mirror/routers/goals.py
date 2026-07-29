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


@router.get("/{goal_id}/analyze")
async def goal_analyze(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    """AI 分析距离目标的差距"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if not goal or goal.user_id != uid:
        return RedirectResponse(url="/goals", status_code=302)

    # 收集相关数据
    from services.persona_service import get_current_persona
    from database.models import DailyRecord, LifeEvent
    from sqlalchemy import select, func

    persona = await get_current_persona(db, uid)
    record_count = (await db.execute(
        select(func.count()).select_from(DailyRecord).where(DailyRecord.user_id == uid)
    )).scalar() or 0
    recent_events = (await db.execute(
        select(LifeEvent).where(LifeEvent.user_id == uid)
        .order_by(LifeEvent.occurred_at.desc()).limit(5)
    )).scalars().all()

    # 构建分析
    analysis = await _generate_gap_analysis(goal, persona, record_count, recent_events)
    goal.ai_gap_analysis = analysis
    await db.commit()

    return RedirectResponse(url="/goals", status_code=302)


async def _generate_gap_analysis(goal, persona, record_count: int, events: list) -> str:
    """生成差距分析"""
    from config import LLM_ENABLED

    # LLM 优先
    if LLM_ENABLED:
        try:
            import httpx, json
            from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

            persona_text = f"人格：{persona.persona_type}" if persona else ""
            events_text = "；".join([e.title for e in events[:3]])

            prompt = f"""用户设定了目标：「{goal.title}」（{goal.target_period or ''}，重要度{goal.importance}%）。
描述：{goal.description or ''}
当前人格：{persona_text}
近期事件：{events_text}
总记录数：{record_count}

请分析用户当前距离这个目标的差距，以及建议的行动步骤。格式：
差距分析：一句话
建议步骤（3条，每条20字以内，用换行分隔）"""

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3, "max_tokens": 300,
                    },
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 规则回退
    parts = [f"距离「{goal.title}」这个目标："]
    if record_count < 10:
        parts.append("当前人生记录较少，建议先保持持续记录的习馈。")
    else:
        parts.append(f"已有{record_count}条记录，数据积累良好。")
    if goal.target_year:
        parts.append(f"目标年份{goal.target_year}年，时间窗口内需要持续投入。")
    parts.append("建议：1. 将目标拆解为可执行的小步骤 2. 每周回顾进展 3. 在相关领域保持学习和实践。")
    return "\n".join(parts)


@router.get("/{goal_id}/delete")
async def goal_delete(request: Request, goal_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    goal = await db.get(LifeGoal, goal_id)
    if goal and goal.user_id == uid:
        await db.delete(goal)
        await db.commit()
    return RedirectResponse(url="/goals", status_code=302)
