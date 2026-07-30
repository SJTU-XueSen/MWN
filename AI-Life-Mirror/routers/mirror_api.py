"""Mirror 全部 API — 供 React 前端调用，零 iframe 依赖"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db, AsyncSessionLocal
from database.models import (
    User, DailyRecord, LifeEvent, PersonaProfile, LifeGoal,
    Simulation, FutureSelf, ChatMessage, GrowthReport, LifeMemory,
    MemorySourceType, EmotionType, EventType,
)

router = APIRouter(prefix="/api/mirror", tags=["mirror-api"])

# ── 认证状态（供侧边栏用）──────────────────────

from fastapi import APIRouter as _APIRouter
_auth_router = _APIRouter(prefix="/api/auth", tags=["auth-api"])

@_auth_router.get("/me")
async def api_auth_me(request: Request):
    u = request.session.get("user")
    if not u: return JSONResponse({})
    async with AsyncSessionLocal() as db:
        user = await db.get(User, u["id"])
        return JSONResponse({"id":user.id,"username":user.username,"real_name":user.real_name} if user else {})

def _uid(request: Request):
    uid = request.session.get("user", {}).get("id")
    if not uid:
        uid = request.cookies.get("mirror_uid") or 1
    return int(uid)


# ── 仪表盘 ────────────────────────────────────────

@router.get("/dashboard")
async def api_dashboard(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    from services.dashboard_service import get_dashboard_data
    async with AsyncSessionLocal() as db:
        data = await get_dashboard_data(db, uid)
        # 补充活动数据
        activities = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get("http://127.0.0.1:3001/api/activities")
                if r.status_code == 200:
                    activities = r.json().get("items", [])[:4]
        except Exception:
            pass

        p = data.get("persona")
        persona_dict = None
        if p:
            try:
                ab = p.ability_profile
                if isinstance(ab, str): import json as _j; ab = _j.loads(ab)
                persona_dict = {"persona_type": p.persona_type or "", "confidence": float(p.confidence or 0),
                    "ability": dict(ab) if ab else {}, "version": int(p.version or 0)}
            except Exception: persona_dict = {"persona_type": str(p.persona_type), "confidence": 0.5, "ability": {}, "version": 1}

        events_list = []
        for e in data.get("recent_events", []):
            try:
                events_list.append({"id": e.id, "title": e.title or "", "type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type or ""), "date": e.occurred_at.strftime("%m月%d日") if e.occurred_at else "", "ai_impact": e.ai_impact or "", "persona_delta": dict(e.persona_delta) if e.persona_delta else {}})
            except Exception: pass
        goals_list = []
        for g in data.get("active_goals", []):
            try:
                goals_list.append({"id": g.id, "title": g.title or "", "importance": g.importance or 50, "period": g.target_period or ""})
            except Exception: pass
        interests_dict = dict(data.get("interests", {}) or {})

        result = {"stats": data.get("stats", {}), "persona": persona_dict, "insight": data.get("insight", ""),
            "recent_events": events_list, "active_goals": goals_list, "interests": interests_dict,
            "activities": [{"id": a.get("id"), "title": a.get("title"), "summary": (a.get("summary") or "")[:100], "date": a.get("publishDate",""), "url": a.get("url","")} for a in activities]}
        return JSONResponse(result)


# ── 日常记录 ──────────────────────────────────────

@router.get("/journal")
async def api_journal_list(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        records = (await db.execute(
            select(DailyRecord).where(DailyRecord.user_id == uid).order_by(DailyRecord.record_date.desc()).limit(30)
        )).scalars().all()
        return JSONResponse([{
            "id": r.id, "content": r.content[:200], "mood": r.mood,
            "date": r.record_date.strftime("%Y-%m-%d %H:%M") if r.record_date else "",
            "ai_analysis": r.ai_analysis,
        } for r in records])


@router.get("/journal/{record_id}")
async def api_journal_detail(request: Request, record_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        r = await db.get(DailyRecord, record_id)
        if not r or r.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        return JSONResponse({"id": r.id, "content": r.content, "mood": r.mood, "date": r.record_date.strftime("%Y-%m-%d %H:%M") if r.record_date else "", "ai_analysis": r.ai_analysis})


@router.post("/journal")
async def api_journal_create(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        rdate = datetime.utcnow()
        if body.get("record_date"):
            try: rdate = datetime.fromisoformat(body["record_date"])
            except Exception: pass
        record = DailyRecord(user_id=uid, content=body.get("content",""), mood=body.get("mood",""), record_date=rdate, created_at=datetime.utcnow())
        db.add(record)
        await db.commit()
        await db.refresh(record)
        # AI 分析
        try:
            from services.memory_service import process_daily_record
            from services.vector_store import add_ai_memory, add_journal
            memory = await process_daily_record(db, record, uid)
            if memory:
                try:
                    add_ai_memory(memory.id, uid, memory.memory_content, {"importance": memory.importance_score, "source": "daily_record"})
                except Exception: pass
            try:
                add_journal(record.id, uid, record.content, {"mood": record.mood or "", "date": str(record.record_date)})
            except Exception: pass
        except Exception: pass
        # 后台自动更新人格
        try:
            from services.persona_service import should_regenerate_persona, regenerate_persona_background
            import asyncio as _asyncio
            should, reason = await should_regenerate_persona(db, uid)
            if should:
                _asyncio.create_task(regenerate_persona_background(uid, reason))
        except Exception:
            pass
        return JSONResponse({"id": record.id, "ok": True})


@router.put("/journal/{record_id}")
async def api_journal_update(request: Request, record_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        record = await db.get(DailyRecord, record_id)
        if not record or record.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        if body.get("content"): record.content = body["content"]
        if body.get("mood"): record.mood = body["mood"]
        if body.get("record_date"):
            try: record.record_date = datetime.fromisoformat(body["record_date"])
            except Exception: pass
        await db.commit()
        return JSONResponse({"ok": True})


@router.delete("/journal/{record_id}")
async def api_journal_delete(request: Request, record_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        record = await db.get(DailyRecord, record_id)
        if not record or record.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        # 删除关联记忆
        from database.models import LifeMemory, MemorySourceType
        memories = (await db.execute(select(LifeMemory).where(LifeMemory.source_type == MemorySourceType.DIARY, LifeMemory.source_id == record_id))).scalars().all()
        for m in memories: await db.delete(m)
        await db.delete(record)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 人生事件 ──────────────────────────────────────

@router.get("/events")
async def api_events(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        events = (await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.occurred_at.desc()).limit(50)
        )).scalars().all()
        return JSONResponse([{
            "id": e.id, "title": e.title, "description": e.description,
            "type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
            "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
            "emotion": e.emotion.value if hasattr(e.emotion, 'value') else str(e.emotion) if e.emotion else "",
            "ai_impact": e.ai_impact, "persona_delta": e.persona_delta, "interest_tags": e.interest_tags,
        } for e in events])


# ── 数字人格 ──────────────────────────────────────

@router.post("/persona")
async def api_persona_generate(request: Request):
    """生成/更新数字人格"""
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    import threading
    from services.persona_service import regenerate_persona_background
    def _bg():
        import asyncio as _aio
        _aio.run(regenerate_persona_background(uid, "手动生成"))
    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse({"ok": True, "message": "人格生成已启动，请稍后刷新"})


@router.get("/persona")
async def api_persona(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    version_id = request.query_params.get("version")
    async with AsyncSessionLocal() as db:
        if version_id:
            # 获取指定版本
            persona = await db.get(PersonaProfile, int(version_id))
            if not persona or persona.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
            return JSONResponse({
                "current": {"id": persona.id, "version": persona.version, "persona_type": persona.persona_type,
                    "summary": persona.persona_summary, "confidence": persona.confidence,
                    "ability": persona.ability_profile, "interest": persona.interest_profile,
                    "value": persona.value_profile, "decision": persona.decision_style,
                    "behavior": persona.behavior_profile, "is_current": persona.is_current,
                    "date": persona.generated_at.strftime("%Y-%m-%d") if persona.generated_at else "",
                } if persona else None,
                "history": [],
            })
        persona = (await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == uid, PersonaProfile.is_current == True).order_by(PersonaProfile.generated_at.desc()).limit(1)
        )).scalar_one_or_none()
        history = (await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == uid).order_by(PersonaProfile.version.desc())
        )).scalars().all()
        return JSONResponse({
            "current": {
                "id": persona.id, "version": persona.version, "persona_type": persona.persona_type,
                "summary": persona.persona_summary, "confidence": persona.confidence,
                "ability": persona.ability_profile, "interest": persona.interest_profile,
                "value": persona.value_profile, "decision": persona.decision_style,
                "behavior": persona.behavior_profile, "date": persona.generated_at.strftime("%Y-%m-%d") if persona.generated_at else "",
            } if persona else None,
            "history": [{"id": h.id, "version": h.version, "is_current": h.is_current, "confidence": h.confidence, "date": h.generated_at.strftime("%Y-%m-%d") if h.generated_at else ""} for h in history],
        })


# ── 人生模拟 ──────────────────────────────────────

@router.get("/simulations")
async def api_simulations(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        sims = (await db.execute(
            select(Simulation).where(Simulation.user_id == uid).order_by(Simulation.created_at.desc())
        )).scalars().all()
        return JSONResponse([{"id": s.id, "scenario": s.scenario_type.value if hasattr(s.scenario_type, 'value') else str(s.scenario_type), "question": s.question, "paths": s.output_paths, "date": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "", "persona_snapshot_id": s.persona_snapshot_id} for s in sims])


@router.get("/simulations/{sim_id}")
async def api_simulation_detail(request: Request, sim_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        futures = (await db.execute(select(FutureSelf).where(FutureSelf.simulation_id == sim_id, FutureSelf.user_id == uid).order_by(FutureSelf.id.asc()))).scalars().all()
        return JSONResponse({"id": sim.id, "scenario": sim.scenario_type.value if hasattr(sim.scenario_type, 'value') else str(sim.scenario_type), "question": sim.question, "paths": sim.output_paths, "date": sim.created_at.strftime("%Y-%m-%d %H:%M") if sim.created_at else "", "futures": [{"id": f.id, "label": f.persona_label} for f in futures]})


# ── 目标 ──────────────────────────────────────

@router.get("/goals")
async def api_goals(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        goals = (await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == uid).order_by(LifeGoal.importance.desc())
        )).scalars().all()
        return JSONResponse([{"id": g.id, "title": g.title, "type": g.goal_type, "description": g.description, "importance": g.importance, "target_year": g.target_year, "period": g.target_period, "status": g.status, "ai_gap_analysis": g.ai_gap_analysis} for g in goals])


# ── 成长报告 ──────────────────────────────────────

@router.post("/reports")
async def api_reports_generate(request: Request):
    """生成成长报告（后台异步）"""
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    import threading, json as _json
    body = {}
    try: body = await request.json()
    except Exception: pass
    def _bg():
        import asyncio as _aio
        async def _gen():
            async with AsyncSessionLocal() as db:
                from services.report_service import generate_report
                from datetime import timedelta
                end = datetime.utcnow()
                start = end - timedelta(days=body.get("days", 30))
                # 支持前端表单传入的自定义日期范围
                try:
                    ps = body.get("period_start", "")
                    pe = body.get("period_end", "")
                    if ps: start = datetime.fromisoformat(ps)
                    if pe: end = datetime.fromisoformat(pe)
                except Exception: pass
                title = body.get("title", "").strip() or f"成长报告 {start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')}"
                await generate_report(db, uid, title, start, end, body.get("context", ""))
        _aio.run(_gen())
    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse({"ok": True, "message": "报告生成已启动，生成完毕后刷新页面查看"})


@router.get("/reports")
async def api_reports(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        reports = (await db.execute(
            select(GrowthReport).where(GrowthReport.user_id == uid).order_by(GrowthReport.generated_at.desc())
        )).scalars().all()
        return JSONResponse([{"id": r.id, "title": r.title, "period_start": r.period_start.strftime("%Y-%m-%d") if r.period_start else "", "period_end": r.period_end.strftime("%Y-%m-%d") if r.period_end else "", "content": r.content, "date": r.generated_at.strftime("%Y-%m-%d") if r.generated_at else ""} for r in reports])


@router.get("/reports/{report_id}")
async def api_report_detail(request: Request, report_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        r = await db.get(GrowthReport, report_id)
        if not r or r.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        return JSONResponse({"id": r.id, "title": r.title, "period_start": r.period_start.strftime("%Y-%m-%d") if r.period_start else "", "period_end": r.period_end.strftime("%Y-%m-%d") if r.period_end else "", "content": r.content, "date": r.generated_at.strftime("%Y-%m-%d %H:%M") if r.generated_at else ""})


@router.delete("/reports/{report_id}")
async def api_report_delete(request: Request, report_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        r = await db.get(GrowthReport, report_id)
        if not r or r.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        await db.delete(r)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 人生体验 ──────────────────────────────────────

@router.post("/experience/start/{future_self_id}")
async def api_experience_start(request: Request, future_self_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    from services.life_experience_service import start_experience, generate_scene
    async with AsyncSessionLocal() as db:
        session = await start_experience(db, uid, future_self_id)
        scene = await generate_scene(db, session)
        traits = session.current_state or {}
        stable_keys = ['专注度', '独立性', '探索欲', '社交需求', '抗挫力']
        growing_keys = ['技术能力', '表达能力', '管理能力', '行动力']
        stable_traits = {k: v for k, v in traits.items() if k in stable_keys}
        growing_traits = {k: v for k, v in traits.items() if k in growing_keys}
        life_state = {k: v for k, v in traits.items() if k.startswith('_')}
        return JSONResponse({
            "session_id": session.id, "current_year": session.current_year,
            "current_age": session.current_age, "random_seed": session.random_seed,
            "traits": traits, "stable_traits": stable_traits, "growing_traits": growing_traits,
            "life_state": life_state,
            "scene": {"narrative": scene.get("narrative", ""), "choices": scene.get("choices", []),
                       "current_traits": scene.get("current_traits", {}), "trait_deltas": scene.get("trait_deltas", {})},
        })


@router.post("/experience/play/{session_id}")
async def api_experience_play(request: Request, session_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    choice_idx = body.get("choice", 0)
    custom_choice = body.get("custom_choice", "")
    from services.life_experience_service import get_session, generate_scene, process_choice
    async with AsyncSessionLocal() as db:
        session = await get_session(db, session_id)
        if not session or session.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        scene = await generate_scene(db, session)
        if choice_idx == -1 and custom_choice.strip():
            custom = {"text": custom_choice.strip(), "gain": "你自由选择了这条路", "cost": "不确定的代价", "hint": "这是你自己的选择——结果完全取决于你的判断和人格倾向"}
            original_choices = scene.get("choices", [])
            scene["choices"] = original_choices + [custom]
            choice_idx = len(original_choices)
        result = await process_choice(db, session, choice_idx, scene)
        next_scene = await generate_scene(db, session, result)
        return JSONResponse({
            "last_result": result,
            "scene": {"narrative": next_scene.get("narrative", ""), "choices": next_scene.get("choices", []),
                       "current_traits": next_scene.get("current_traits", {}), "trait_deltas": next_scene.get("trait_deltas", {})},
            "session": {"current_year": session.current_year, "current_age": session.current_age, "random_seed": session.random_seed},
        })


# ── 创建人生事件 ──────────────────────────────────

@router.post("/events")
async def api_event_create(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    import traceback, logging
    _log = logging.getLogger(__name__)
    async with AsyncSessionLocal() as db:
        from services.event_service import create_event as _create_event, EVENT_TYPE_CONFIG
        from datetime import datetime as _dt
        occurred_at = body.get("occurred_at", "")
        try: date = _dt.fromisoformat(occurred_at) if occurred_at else _dt.utcnow()
        except Exception: date = _dt.utcnow()
        try:
            event = await _create_event(db, uid, body.get("title", ""), body.get("description", ""), body.get("event_type", "study"), date)
        except Exception as e:
            _log.error(f"Event creation failed: {e}\n{traceback.format_exc()}")
            # 回退：规则引擎分析
            from services.event_service import analyze_event as _rule_analyze
            analysis = _rule_analyze(body.get("title", ""), body.get("description", ""), body.get("event_type", "study"))
            event = LifeEvent(user_id=uid, title=body.get("title", ""), description=body.get("description", ""),
                              event_type=body.get("event_type", "study"),
                              emotion=EmotionType(analysis.get("emotion", "neutral")),
                              interest_tags=analysis.get("interest_tags", []),
                              ai_impact=analysis.get("ai_impact", ""),
                              persona_delta=analysis.get("persona_delta", {}),
                              occurred_at=date, created_at=_dt.utcnow())
            db.add(event)
            await db.commit()
            await db.refresh(event)
            # 回退路径也创建 LifeMemory
            try:
                from services.event_service import _rule_event_memory, EVENT_TYPE_CONFIG as _ETC
                etype = body.get("event_type", "study")
                label = _ETC.get(etype, {}).get("label", etype)
                memory_content = _rule_event_memory(body.get("title", ""), body.get("description", ""), label, etype, analysis)
                mem = LifeMemory(user_id=uid, source_type=MemorySourceType.EVENT, source_id=event.id,
                    memory_content=memory_content, importance_score=0.5, persona_impact=analysis.get("persona_delta", {}),
                    embedding_id=f"rule:event:{event.id}", created_at=_dt.utcnow())
                db.add(mem)
                await db.commit()
            except Exception: pass
        try:
            from services.vector_store import add_ai_memory as _add_ai_memory
            _add_ai_memory(event.id, uid, f"{event.title}：{event.description or ''}"[:500], {"importance": 0.7, "source": "life_event", "event_type": body.get("event_type", "study")})
        except Exception: pass
        try:
            from services.persona_service import should_regenerate_persona, regenerate_persona_background
            import asyncio as _asyncio
            should, reason = await should_regenerate_persona(db, uid)
            if should: _asyncio.create_task(regenerate_persona_background(uid, reason))
        except Exception: pass
        return JSONResponse({"id": event.id, "ok": True})


# ── 事件详情 ──────────────────────────────────────

@router.get("/events/{event_id}")
async def api_event_detail(request: Request, event_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        from services.event_service import get_event_by_id, EVENT_TYPE_CONFIG
        event = await get_event_by_id(db, event_id)
        if not event or event.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        display = EVENT_TYPE_CONFIG.get(
            event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            {"icon": "📌", "label": str(event.event_type), "color": "gray"},
        )
        # 查询关联记忆
        memory = (await db.execute(
            select(LifeMemory).where(
                LifeMemory.user_id == uid,
                LifeMemory.source_type == MemorySourceType.EVENT,
                LifeMemory.source_id == event_id,
            ).limit(1)
        )).scalar_one_or_none()
        return JSONResponse({
            "id": event.id, "title": event.title, "description": event.description,
            "type": event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            "date": event.occurred_at.strftime("%Y-%m-%d") if event.occurred_at else "",
            "emotion": event.emotion.value if hasattr(event.emotion, 'value') else str(event.emotion) if event.emotion else "",
            "ai_impact": event.ai_impact, "persona_delta": event.persona_delta,
            "interest_tags": event.interest_tags or [],
            "display_icon": display["icon"], "display_label": display["label"],
            "memory": {"id": memory.id, "memory_content": memory.memory_content, "importance_score": memory.importance_score} if memory else None,
        })


@router.put("/events/{event_id}")
async def api_event_update(request: Request, event_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        from services.event_service import get_event_by_id
        event = await get_event_by_id(db, event_id)
        if not event or event.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        if body.get("title"): event.title = body["title"]
        if body.get("description"): event.description = body["description"]
        if body.get("event_type"):
            try: event.event_type = EventType(body["event_type"])
            except Exception: pass
        if body.get("occurred_at"):
            try: event.occurred_at = datetime.fromisoformat(body["occurred_at"])
            except Exception: pass
        await db.commit()
        return JSONResponse({"ok": True})


@router.delete("/events/{event_id}")
async def api_event_delete(request: Request, event_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        from services.event_service import get_event_by_id, delete_event
        event = await get_event_by_id(db, event_id)
        if not event or event.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        await delete_event(db, event)
        return JSONResponse({"ok": True})


# ── 设置 ──────────────────────────────────────────

@router.get("/settings")
async def api_settings(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        return JSONResponse({"username": user.username, "real_name": user.real_name, "email": getattr(user, 'email', ''),
            "university": getattr(user, 'university', '') or '', "major": getattr(user, 'major', '') or '',
            "grade": getattr(user, 'grade', '') or '', "bio": getattr(user, 'bio', '') or '',
            "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else ""} if user else {})

@router.post("/settings")
async def api_settings_update(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user: return JSONResponse({"error": "not_found"}, 404)
        if body.get("real_name"): user.real_name = body["real_name"]
        if body.get("email"): user.email = body["email"]
        if "university" in body: user.university = body["university"]
        if "major" in body: user.major = body["major"]
        if "grade" in body: user.grade = body["grade"]
        if "bio" in body: user.bio = body["bio"]
        await db.commit()
        return JSONResponse({"ok": True})


# ── 人生参考 ──────────────────────────────────────

@router.get("/references")
async def api_references(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        from services.activity_service import get_reference_interests
        try:
            ref_data = await get_reference_interests(db, uid)
            return JSONResponse({
                "category_counts": ref_data.get("category_counts", {}),
                "insight": ref_data.get("insight", ""),
            })
        except Exception:
            return JSONResponse({"category_counts": {}, "insight": ""})


# ── 创建目标 ──────────────────────────────────────

@router.post("/goals")
async def api_goal_create(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        goal = LifeGoal(user_id=uid, title=body.get("title", ""), description=body.get("description", ""),
                        goal_type=body.get("goal_type", "personal"), importance=body.get("importance", 50),
                        target_period=body.get("target_period", ""), target_year=body.get("target_year", 0),
                        status="active")
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return JSONResponse({"id": goal.id, "ok": True})


@router.post("/goals/{goal_id}/complete")
async def api_goal_complete(request: Request, goal_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        goal.status = "achieved"
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/goals/{goal_id}/delete")
async def api_goal_delete(request: Request, goal_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        await db.delete(goal)
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/goals/{goal_id}/analyze")
async def api_goal_analyze(request: Request, goal_id: int):
    """AI 分析目标差距"""
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid: return JSONResponse({"error": "not_found"}, 404)

        # 先尝试 LLM
        analysis = None
        try:
            from config import LLM_ENABLED, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
            if LLM_ENABLED:
                import httpx
                prompt = f"""你是目标分析助手。根据以下目标生成一段简洁的差距分析和3条具体建议步骤。
目标：{goal.title}
类型：{goal.goal_type}
描述：{goal.description or '无'}
时间规划：{goal.target_period or '未设定'}
重要度：{goal.importance}%
格式要求：先一句话概括差距，再列3条具体可执行的建议步骤（每条用"1. 2. 3."开头）。不超过200字。"""
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5, "max_tokens": 400},
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        analysis = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception: pass

        # LLM 失败 → 规则引擎
        if not analysis:
            goal_type = goal.goal_type or "personal"
            title = goal.title or ""
            period = goal.target_period or ""
            desc = goal.description or ""

            templates = {
                "study": f"差距分析：尚未建立系统化的{title}学习路径与知识输出习惯\n建议步骤：\n1. 每日投入固定时间学习{title}核心内容并做笔记\n2. 每周进行一次知识复盘，检验学习效果\n3. 通过实际项目或教学输出检验学习成果",
                "technical": f"差距分析：{title}方面的技术深度和实践经验仍有提升空间\n建议步骤：\n1. 每周完成至少一个{title}相关的动手实践\n2. 阅读该领域经典文献或开源项目源码\n3. 寻找导师或同路人，定期交流反馈",
                "career": f"差距分析：{title}方向的职业准备还不够系统\n建议步骤：\n1. 梳理该方向所需的技能树，逐项评估自己的水平\n2. 寻找实习或项目机会积累实际经验\n3. 每季度更新一次自己的职业规划",
                "personal": f"差距分析：{title}方面还需要更持续的行动和更清晰的衡量标准\n建议步骤：\n1. 将目标拆解为可量化的月度小目标\n2. 建立每周检查和调整的习惯\n3. 找到能给你反馈的人或社群",
            }
            analysis = templates.get(goal_type, templates["personal"])
            if desc and len(desc) > 5:
                analysis = analysis.replace("尚未建立", f"基于你的描述「{desc[:30]}」，尚未建立")

        goal.ai_gap_analysis = analysis
        await db.commit()
        return JSONResponse({"ok": True, "analysis": analysis})


@router.post("/simulations/{sim_id}/to-goal/{path_index}")
async def api_sim_to_goal(request: Request, sim_id: int, path_index: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        paths = sim.output_paths or []
        if path_index >= len(paths): return JSONResponse({"error": "invalid_path_index"}, 400)
        path = paths[path_index]
        goal = LifeGoal(user_id=uid, title=path.get("label", f"路径{path_index+1}"),
                        description=path.get("description", "")[:200],
                        goal_type="personal", importance=70,
                        target_period=f"约{path.get('confidence',0.5)*100:.0f}%匹配度",
                        status="active")
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return JSONResponse({"id": goal.id, "ok": True, "title": goal.title})


# ── 创建模拟 ──────────────────────────────────────

@router.post("/simulations")
async def api_simulation_create(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        from services.simulation_service import run_simulation
        # run_simulation 内部会创建 Simulation、生成路径、创建 FutureSelf，全部在一个事务里
        sim = await run_simulation(db, uid, body.get("scenario_type", "further_study"), body.get("question", ""))
        return JSONResponse({"id": sim.id, "ok": True, "paths": len(sim.output_paths or [])})


@router.delete("/simulations/{sim_id}")
async def api_simulation_delete(request: Request, sim_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        # 删除关联 FutureSelf
        futures = (await db.execute(select(FutureSelf).where(FutureSelf.simulation_id == sim_id))).scalars().all()
        for f in futures: await db.delete(f)
        await db.delete(sim)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 推演人生 ──────────────────────────────────────

@router.post("/projection")
async def api_life_projection(request: Request):
    """基于全部记忆 + 人格，生成无干预式人生推演"""
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    years = body.get("years", 10)

    async with AsyncSessionLocal() as db:
        # 获取人格
        persona = (await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == uid, PersonaProfile.is_current == True).limit(1)
        )).scalar_one_or_none()

        # 获取事件
        events = (await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.occurred_at.desc()).limit(20)
        )).scalars().all()

        # 获取目标
        goals = (await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == uid, LifeGoal.status == "active").limit(10)
        )).scalars().all()

        # ChromaDB 全部记忆
        memories = []
        try:
            from services.vector_store import search
            queries = ["人生经历 成长 转折", "兴趣 探索 学习", "关系 社交 团队", "目标 梦想 未来"]
            seen = set()
            for q in queries:
                for r in search(uid, q, n_results=10):
                    txt = r.get("content", "") if isinstance(r, dict) else str(r)
                    if txt and txt not in seen:
                        seen.add(txt)
                        memories.append(txt[:200])
        except Exception:
            pass

        persona_text = ""
        if persona:
            ab = persona.ability_profile or {}
            ip = persona.interest_profile or {}
            persona_text = f"人格类型：{persona.persona_type}\n能力：{json.dumps(ab, ensure_ascii=False)}\n兴趣：{json.dumps(ip, ensure_ascii=False)}"
        events_text = "\n".join([f"- {e.occurred_at.strftime('%Y/%m') if e.occurred_at else '?'} {e.title}: {e.description or ''}" for e in events[:10]])
        goals_text = "\n".join([f"- [{g.importance}%] {g.title}" for g in goals[:5]])
        memory_text = "\n".join([f"- {m}" for m in memories[:20]])

        # 调用 LLM
        result = None
        try:
            from config import LLM_ENABLED, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
            if LLM_ENABLED:
                import httpx
                prompt = f"""你是一个人生推演引擎。基于以下用户真实数据，生成一份未来{min(years,20)}年的人生推演报告。

## 用户人格画像
{persona_text or '(暂无)'}

## 重要人生事件
{events_text or '(暂无)'}

## 活跃目标
{goals_text or '(暂无)'}

## 长期记忆库
{memory_text or '(暂无)'}

## 要求
生成一份 JSON，包含未来年份的人生节点。每个节点包含：
- year: 年份
- age: 大致年龄
- event: 一句话描述这一年发生的关键事件
- detail: 2-3句话描述这个阶段的状态和感受
- trait_shift: 人格倾向变化（用 ↑↓ 表示）

格式：
{{"projection": [{{"year":2027,"age":23,"event":"...","detail":"...","trait_shift":{{"技术能力":"↑","社交投入":"→"}}}}, ...]}}

★ 核心约束：
- 基于用户的真实记忆、人格、目标推演——不是随机编造
- 人生有起伏——不是每年都在进步。有些年份平淡，有些年份有转折
- 事件要和用户记忆中的兴趣、经历保持一致
- 不要编造用户从未接触过的领域
- 总节点数约{min(years, 20)}个，覆盖未来{min(years, 20)}年
- 用中文

只返回 JSON。"""
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.6, "max_tokens": 2500, "response_format": {"type": "json_object"}},
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        if content.startswith("```"): content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                        result = json.loads(content)
        except Exception:
            pass

        if not result:
            # 规则引擎回退
            proj = []
            start_year = datetime.utcnow().year
            base_age = 22
            for i in range(min(years, 10)):
                yr = start_year + i + 1
                age = base_age + i + (start_year - 2026)
                nodes = [
                    {"year": yr, "age": age, "event": f"在现有方向上持续积累，{'' if i % 3 == 0 else '遇到了一些'}{'小的突破' if i % 2 == 0 else '瓶颈和反思'}",
                     "detail": f"这一年你{age}岁。{'对自己的方向有了更清晰的认识。' if i % 2 == 0 else '开始思考是否要调整策略。'}经历是连续的——每一年的选择都在为下一年铺路。",
                     "trait_shift": {"专注度": "↑" if i % 2 == 0 else "→", "抗挫力": "↑"}},
                ]
                if i % 4 == 0:
                    nodes[0]["event"] = "一个意料之外的机会出现了，可能改变接下来的方向"
                    nodes[0]["detail"] = f"你{age}岁这一年发生的事让你重新审视了自己的优先级。不是每次转折都是轰轰烈烈的——有时候只是一次对话、一本书、或者一个突如其来的想法。"
                    nodes[0]["trait_shift"] = {"探索欲": "↑", "抗挫力": "↑", "专注度": "↓"}
                proj.extend(nodes)
            result = {"projection": proj}

        return JSONResponse({"ok": True, "projection": result.get("projection", [])})


# ── 语音转文字 ──────────────────────────────────────

@router.get("/stt/status")
async def api_stt_status(request: Request):
    """模型加载状态"""
    from services.stt_service import is_ready, is_loading
    return JSONResponse({"ok": True, "ready": is_ready(), "loading": is_loading()})


@router.post("/stt")
async def api_speech_to_text(request: Request):
    """接收音频，返回 FunASR 识别文本"""
    from services.stt_service import speech_to_text, add_hotwords, get_hotwords
    form = await request.form()
    file = form.get("audio")
    hotword_str = form.get("hotwords", "")
    if not file:
        return JSONResponse({"ok": False, "error": "缺少音频文件"}, 400)

    audio_bytes = await file.read()
    hotwords = [w.strip() for w in hotword_str.split(",") if w.strip()] if hotword_str else get_hotwords()
    text = await speech_to_text(audio_bytes, hotwords)
    return JSONResponse({"ok": True, "text": text, "hotwords_used": hotwords})


@router.get("/stt/hotwords")
async def api_get_hotwords(request: Request):
    """获取当前热词"""
    from services.stt_service import get_hotwords
    return JSONResponse({"ok": True, "hotwords": get_hotwords()})


@router.post("/stt/hotwords")
async def api_set_hotwords(request: Request):
    """设置全局热词"""
    from services.stt_service import add_hotwords, get_hotwords
    body = await request.json()
    words = body.get("words", [])
    if words:
        add_hotwords(words)
    return JSONResponse({"ok": True, "hotwords": get_hotwords()})


# ── 发送对话消息 ──────────────────────────────────

@router.post("/future-chats/{fs_id}/messages")
async def api_chat_send(request: Request, fs_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    body = await request.json()
    content = body.get("content", "").strip()
    if not content: return JSONResponse({"error": "empty_message"}, 400)
    async with AsyncSessionLocal() as db:
        future = await db.get(FutureSelf, fs_id)
        if not future or future.user_id != uid: return JSONResponse({"error": "not_found"}, 404)
        # 保存用户消息
        user_msg = ChatMessage(user_id=uid, future_self_id=fs_id, role="user", content=content, created_at=datetime.utcnow())
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)
        # 同步生成 AI 回复
        ai_reply = None
        try:
            from config import LLM_ENABLED, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
            if LLM_ENABLED:
                import httpx
                persona_label = future.persona_label or "未来的自己"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": f"你是用户的未来人格「{persona_label}」。请以这个人格的身份回复，语气温暖、有洞察力。回复用中文，不超过300字。"},
                                {"role": "user", "content": content},
                            ],
                            "temperature": 0.7, "max_tokens": 800,
                        },
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        ai_reply = resp.json()["choices"][0]["message"]["content"].strip()
                        ai_msg = ChatMessage(user_id=uid, future_self_id=fs_id, role="assistant", content=ai_reply, created_at=datetime.utcnow())
                        db.add(ai_msg)
                        await db.commit()
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"AI reply failed: {e}")
            ai_reply = "（AI 暂时无法回复，请稍后重试）"
        return JSONResponse({
            "ok": True,
            "user": {"id": user_msg.id, "role": "user", "content": content, "time": datetime.utcnow().strftime("%H:%M")},
            "assistant": {"role": "assistant", "content": ai_reply or "（思考中...）", "time": datetime.utcnow().strftime("%H:%M")} if ai_reply else None,
        })


async def _generate_ai_reply(fs_id: int, uid: int, future: FutureSelf, user_content: str):
    """已废弃——改为同步生成"""
    pass


# ── 未来对话列表 ──────────────────────────────────

@router.get("/future-chats")
async def api_future_chats(request: Request):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        futures = (await db.execute(select(FutureSelf).where(FutureSelf.user_id == uid).order_by(FutureSelf.created_at.desc()))).scalars().all()
        return JSONResponse([{"id": f.id, "label": f.persona_label, "target_year": f.target_year, "confidence": f.confidence, "path_type": f.path_type, "basis": f.basis_summary} for f in futures])


@router.get("/future-chats/{fs_id}/messages")
async def api_chat_messages(request: Request, fs_id: int):
    uid = _uid(request)
    if not uid: return JSONResponse({"error": "not_logged_in"}, 401)
    async with AsyncSessionLocal() as db:
        msgs = (await db.execute(select(ChatMessage).where(ChatMessage.user_id == uid, ChatMessage.future_self_id == fs_id).order_by(ChatMessage.created_at.asc()))).scalars().all()
        return JSONResponse([{"id": m.id, "role": m.role, "content": m.content, "time": m.created_at.strftime("%H:%M") if m.created_at else ""} for m in msgs])
