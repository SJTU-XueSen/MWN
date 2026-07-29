"""人生事件 & 日常记录路由"""
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import DailyRecord, LifeEvent, MemorySourceType
from services.memory_service import analyze_daily_record, process_daily_record
from services.event_service import (
    create_event, get_user_events, get_event_by_id, delete_event,
    get_event_timeline_data, EVENT_TYPE_CONFIG,
)
from services.vector_store import add_ai_memory, add_journal
from templating import render

router = APIRouter(tags=["events"])


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


# ══════════════════════════════════════════════════════
#  日常记录 (Journal)
# ══════════════════════════════════════════════════════

@router.get("/journal")
async def journal_list(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    records = (await db.execute(
        select(DailyRecord).where(DailyRecord.user_id == uid)
        .order_by(DailyRecord.record_date.desc()).limit(30)
    )).scalars().all()
    return _render(request, "events/journal_list.html", active="journal", records=records,
                   emotion_map={"positive": "😊 积极", "neutral": "😐 中性", "negative": "😔 消极"})


@router.get("/journal/new")
async def journal_new(request: Request):
    if r := _require_login(request): return r
    return _render(request, "events/journal_new.html", active="journal")


@router.post("/journal/new")
async def journal_create(
    request: Request,
    content: str = Form(...),
    mood: str = Form("neutral"),
    record_date: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    date = datetime.utcnow() if not record_date else datetime.fromisoformat(record_date)

    record = DailyRecord(
        user_id=uid, content=content,
        mood=mood if mood else None, record_date=date,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Memory Pipeline
    try:
        memory = await process_daily_record(db, record, uid)
        if memory:
            try:
                add_ai_memory(memory.id, uid, memory.memory_content, {
                    "importance": memory.importance_score, "source": "daily_record",
                })
            except Exception:
                pass
        try:
            add_journal(record.id, uid, record.content, {
                "mood": record.mood or "",
                "date": str(record.record_date),
            })
        except Exception:
            pass
    except Exception:
        pass

    return RedirectResponse(url=f"/journal/{record.id}", status_code=302)


@router.get("/journal/{record_id}")
async def journal_detail(request: Request, record_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    record = await db.get(DailyRecord, record_id)
    if not record or record.user_id != uid:
        return RedirectResponse(url="/journal", status_code=302)
    return _render(request, "events/journal_detail.html", active="journal", record=record)


@router.get("/journal/{record_id}/edit")
async def journal_edit_form(request: Request, record_id: int, db: AsyncSession = Depends(get_db)):
    """编辑记录表单"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    record = await db.get(DailyRecord, record_id)
    if not record or record.user_id != uid:
        return RedirectResponse(url="/journal", status_code=302)
    return _render(request, "events/journal_edit.html", active="journal", record=record)


@router.post("/journal/{record_id}/edit")
async def journal_edit(
    request: Request, record_id: int,
    content: str = Form(...),
    mood: str = Form(""),
    record_date: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """更新记录并重新 AI 分析"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    record = await db.get(DailyRecord, record_id)
    if not record or record.user_id != uid:
        return RedirectResponse(url="/journal", status_code=302)

    date = datetime.utcnow() if not record_date else datetime.fromisoformat(record_date)

    record.content = content
    record.mood = mood if mood else None
    record.record_date = date
    await db.commit()

    # 删除旧的关联记忆
    from database.models import LifeMemory
    old_memories = (await db.execute(
        select(LifeMemory).where(
            LifeMemory.source_type == MemorySourceType.DIARY,
            LifeMemory.source_id == record_id,
        )
    )).scalars().all()
    for m in old_memories:
        await db.delete(m)
    await db.commit()

    # 重新分析
    try:
        memory = await process_daily_record(db, record, uid)
        if memory:
            try:
                add_ai_memory(memory.id, uid, memory.memory_content, {
                    "importance": memory.importance_score, "source": "daily_record",
                })
            except Exception:
                pass
    except Exception:
        pass

    return RedirectResponse(url=f"/journal/{record_id}", status_code=302)


@router.get("/journal/{record_id}/delete")
async def journal_delete(request: Request, record_id: int, db: AsyncSession = Depends(get_db)):
    """删除记录及其关联记忆"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    record = await db.get(DailyRecord, record_id)
    if not record or record.user_id != uid:
        return RedirectResponse(url="/journal", status_code=302)

    # 删除关联的 life_memories
    from database.models import LifeMemory
    memories = (await db.execute(
        select(LifeMemory).where(
            LifeMemory.source_type == MemorySourceType.DIARY,
            LifeMemory.source_id == record_id,
        )
    )).scalars().all()
    for m in memories:
        await db.delete(m)

    await db.delete(record)
    await db.commit()

    return RedirectResponse(url="/journal", status_code=302)


# ══════════════════════════════════════════════════════
#  人生事件 (Life Events) — 时间线 + 分类
# ══════════════════════════════════════════════════════

@router.get("/events")
async def event_timeline(request: Request, db: AsyncSession = Depends(get_db)):
    """人生事件时间线主页"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    data = await get_event_timeline_data(db, uid)
    return _render(request, "events/timeline.html", active="events", **data)


@router.get("/events/new")
async def event_new(request: Request):
    """新建人生事件表单"""
    if r := _require_login(request): return r
    return _render(request, "events/event_new.html", active="events",
                   event_types=EVENT_TYPE_CONFIG)


@router.post("/events/new")
async def event_create(
    request: Request,
    title: str = Form(...),
    event_type: str = Form(...),
    description: str = Form(""),
    occurred_at: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """创建人生事件（含 AI 分析 + Chroma 写入）"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    date = datetime.utcnow() if not occurred_at else datetime.fromisoformat(occurred_at)

    event = await create_event(db, uid, title, description, event_type, date)

    # ChromaDB 向量写入
    try:
        add_ai_memory(event.id, uid, f"{event.title}：{event.description or ''}"[:500], {
            "importance": 0.7,
            "source": "life_event",
            "event_type": event_type,
        })
    except Exception:
        pass

    return RedirectResponse(url=f"/events/{event.id}", status_code=302)


@router.get("/events/{event_id}")
async def event_detail(request: Request, event_id: int, db: AsyncSession = Depends(get_db)):
    """人生事件详情页"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    event = await get_event_by_id(db, event_id)
    if not event or event.user_id != uid:
        return RedirectResponse(url="/events", status_code=302)

    # 获取关联的生命记忆
    from database.models import LifeMemory
    memory = (await db.execute(
        select(LifeMemory).where(
            LifeMemory.source_type == MemorySourceType.EVENT,
            LifeMemory.source_id == event_id,
        ).limit(1)
    )).scalar_one_or_none()

    display = EVENT_TYPE_CONFIG.get(
        event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
        {"icon": "📌", "label": str(event.event_type), "color": "gray"},
    )

    return _render(request, "events/event_detail.html", active="events",
                   event=event, display=display, memory=memory)


@router.get("/events/{event_id}/delete")
async def event_delete(request: Request, event_id: int, db: AsyncSession = Depends(get_db)):
    """删除人生事件"""
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    event = await get_event_by_id(db, event_id)
    if not event or event.user_id != uid:
        return RedirectResponse(url="/events", status_code=302)
    await delete_event(db, event)
    return RedirectResponse(url="/events", status_code=302)
