"""数据隐私与账户设置路由"""
import json
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import io

from database.database import get_db
from database.models import (
    User, DailyRecord, LifeEvent, LifeMemory, PersonaProfile,
    InterestTrack, LifeGoal, Simulation, SimulationVariable,
    FutureSelf, ChatMessage, GrowthReport,
)
from templating import render

router = APIRouter(prefix="/settings", tags=["settings"])


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


# ── 隐私仪表盘 ────────────────────────────────────────

@router.get("")
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    # 统计各表数据量
    from sqlalchemy import func
    stats = {}
    for name, model in [
        ("records", DailyRecord), ("events", LifeEvent),
        ("memories", LifeMemory), ("personas", PersonaProfile),
        ("interests", InterestTrack), ("goals", LifeGoal),
        ("simulations", Simulation), ("future_selves", FutureSelf),
        ("chat_messages", ChatMessage), ("reports", GrowthReport),
    ]:
        stats[name] = (await db.execute(
            select(func.count()).select_from(model).where(model.user_id == uid)
        )).scalar() or 0

    total = sum(stats.values())

    return _render(request, "settings/index.html", active="settings",
                   stats=stats, total=total)


# ── 导出数据 ──────────────────────────────────────────

@router.get("/export")
async def export_data(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    # 收集所有用户数据
    user = await db.get(User, uid)

    def _rows(model):
        """同步查询辅助"""
        return []

    # 异步收集
    records = (await db.execute(
        select(DailyRecord).where(DailyRecord.user_id == uid)
    )).scalars().all()

    events = (await db.execute(
        select(LifeEvent).where(LifeEvent.user_id == uid)
    )).scalars().all()

    memories = (await db.execute(
        select(LifeMemory).where(LifeMemory.user_id == uid)
    )).scalars().all()

    personas = (await db.execute(
        select(PersonaProfile).where(PersonaProfile.user_id == uid)
    )).scalars().all()

    goals = (await db.execute(
        select(LifeGoal).where(LifeGoal.user_id == uid)
    )).scalars().all()

    simulations = (await db.execute(
        select(Simulation).where(Simulation.user_id == uid)
    )).scalars().all()

    future_selves = (await db.execute(
        select(FutureSelf).where(FutureSelf.user_id == uid)
    )).scalars().all()

    chat_messages = (await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == uid)
    )).scalars().all()

    reports = (await db.execute(
        select(GrowthReport).where(GrowthReport.user_id == uid)
    )).scalars().all()

    def serialize(obj):
        """序列化模型对象为 dict"""
        if obj is None:
            return None
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__table__'):
            data = {}
            for col in obj.__table__.columns:
                val = getattr(obj, col.name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                data[col.name] = val
            return data
        return str(obj)

    export = {
        "exported_at": datetime.utcnow().isoformat(),
        "app": "AI人生镜像",
        "user": serialize(user),
        "daily_records": [serialize(r) for r in records],
        "life_events": [serialize(e) for e in events],
        "life_memories": [serialize(m) for m in memories],
        "persona_profiles": [serialize(p) for p in personas],
        "life_goals": [serialize(g) for g in goals],
        "simulations": [serialize(s) for s in simulations],
        "future_selves": [serialize(f) for f in future_selves],
        "chat_messages": [serialize(c) for c in chat_messages],
        "growth_reports": [serialize(r) for r in reports],
        "total_records": len(records) + len(events) + len(memories),
    }

    json_str = json.dumps(export, ensure_ascii=False, indent=2)
    buffer = io.BytesIO(json_str.encode('utf-8'))

    filename = f"ai-life-mirror-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── 删除账户 ──────────────────────────────────────────

@router.get("/delete-account")
async def delete_account_page(request: Request):
    if r := _require_login(request): return r
    return _render(request, "settings/delete_confirm.html", active="settings")


@router.post("/delete-account")
async def delete_account_action(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    # 级联删除所有数据（Cascade 已在模型中定义）
    user = await db.get(User, uid)
    if user:
        # 手动清理 ChromaDB（外键无法级联到向量库）
        try:
            from services.vector_store import delete_user_data
            delete_user_data(uid)
        except Exception:
            pass

        await db.delete(user)
        await db.commit()

    request.session.clear()
    return RedirectResponse(url="/auth/login?msg=account_deleted", status_code=302)
