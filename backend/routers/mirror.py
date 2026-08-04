"""镜像核心 API — 记录/事件/人格/模拟/目标/报告/推演/体验/未来对话/语音/设置

全部端点强制登录（AuthRequiredMiddleware），所有查询带 user_id 过滤。
"""
import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import (
    ChatMessage,
    DailyRecord,
    FutureSelf,
    GrowthReport,
    InterestTrack,
    LifeEvent,
    LifeGoal,
    LifeMemory,
    Memo,
    Notification,
    PageVisit,
    PersonaProfile,
    Simulation,
    StudentActivity,
    Team,
    TeamMember,
    User,
    UserActivity,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mirror", tags=["mirror"])


# ── 仪表盘 ────────────────────────────────────────────

@router.get("/dashboard")
async def api_dashboard(request: Request):
    uid = require_uid(request)
    from backend.services.dashboard_service import get_dashboard_data

    async with AsyncSessionLocal() as db:
        data = await get_dashboard_data(db, uid)

        activities = []
        try:
            from backend.services.sjtu_crawler import get_activities

            activities = (await get_activities()).get("items", [])[:4]
        except Exception:
            pass

        p = data.get("persona")
        persona_dict = None
        if p:
            try:
                ab = p.ability_profile
                if isinstance(ab, str):
                    ab = json.loads(ab)
                persona_dict = {
                    "persona_type": p.persona_type or "",
                    "confidence": float(p.confidence or 0),
                    "ability": dict(ab) if ab else {},
                    "version": int(p.version or 0),
                }
            except Exception:
                persona_dict = {"persona_type": str(p.persona_type or ""), "confidence": 0.5, "ability": {}, "version": 1}

        events_list = [
            {
                "id": e.id, "title": e.title or "", "type": e.event_type or "",
                "date": e.occurred_at.strftime("%m月%d日") if e.occurred_at else "",
                "ai_impact": e.ai_impact or "", "persona_delta": dict(e.persona_delta) if e.persona_delta else {},
            }
            for e in data.get("recent_events", [])
        ]
        goals_list = [
            {"id": g.id, "title": g.title or "", "importance": g.importance or 50, "period": g.target_period or ""}
            for g in data.get("active_goals", [])
        ]
        stats = data.get("stats", {})
        # 兼容两种统计字段命名（新页面用 record_count，叙事版仪表盘用 records）
        stats.setdefault("records", stats.get("record_count", 0))
        stats.setdefault("events", stats.get("event_count", 0))
        stats.setdefault("goals", stats.get("goal_count", 0))

        # 用户兴趣画像（人格 interest_profile + 兴趣追踪）→ 活动匹配打分
        from backend.services.dashboard_service import score_activity

        user_interests: dict = {}
        if p and p.interest_profile:
            user_interests.update(dict(p.interest_profile))
        user_interests.update({k: v for k, v in (data.get("interests") or {}).items() if k not in user_interests})

        def _enrich(item: dict) -> dict:
            text = " ".join([
                str(item.get("title", "")), str(item.get("summary", "")),
                str(item.get("category", "")), " ".join(item.get("tags", []) or []),
            ])
            match = score_activity(user_interests, text)
            item["match_score"] = match["match_score"]
            item["match_reason"] = match["reason"]
            item["matched"] = match["matched"]
            return item

        activities_out = [
            _enrich({
                "id": a.get("id"), "title": a.get("title"), "summary": (a.get("summary") or "")[:120],
                "publishDate": a.get("publishDate", ""), "inferredEndDate": a.get("inferredEndDate", ""),
                "url": a.get("url", ""), "source": "sjtu",
            })
            for a in activities
        ]

        # 组队活动（活动大厅 competitions，同样参与匹配）
        competitions_out = []
        try:
            from backend.database.models import Competition, Team

            comps = (
                await db.execute(
                    select(Competition).where(
                        Competition.approval_status == "approved",
                        Competition.is_competition == False,  # 与活动大厅过滤一致
                        Competition.status == "active",
                    ).order_by(Competition.created_at.desc()).limit(6)
                )
            ).scalars().all()
            comp_ids = [c.id for c in comps]
            team_counts: dict = {}
            if comp_ids:
                rows = (
                    await db.execute(
                        select(Team.competition_id, func.count(Team.id))
                        .where(Team.competition_id.in_(comp_ids)).group_by(Team.competition_id)
                    )
                ).all()
                team_counts = {r[0]: r[1] for r in rows}
            for c in comps:
                competitions_out.append(_enrich({
                    "id": c.id, "title": c.title,
                    "summary": (c.description or "")[:120],
                    "category": c.category, "level": c.level,
                    "registration_deadline": c.registration_deadline.strftime("%Y-%m-%d") if c.registration_deadline else "",
                    "tags": c.tags or [], "credit_info": c.credit_info,
                    "team_count": team_counts.get(c.id, 0),
                    "max_team_size": c.max_team_size,
                    "url": "/connections", "source": "competition",
                }))
        except Exception:
            pass

        return JSONResponse({
            "stats": stats,
            "persona": persona_dict,
            "insight": data.get("insight", ""),
            "recent_events": events_list,
            "active_goals": goals_list,
            "interests": dict(data.get("interests", {}) or {}),
            "activities": activities_out,
            "competitions": competitions_out,
        })


# ── 日常记录 ──────────────────────────────────────────

@router.get("/journal")
async def api_journal_list(request: Request, search: str = ""):
    """日常记录列表：默认全部返回，支持 ?search= 关键词检索"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        q = select(DailyRecord).where(DailyRecord.user_id == uid)
        if search:
            q = q.where(DailyRecord.content.contains(search))
        records = (
            await db.execute(q.order_by(DailyRecord.record_date.desc()).limit(2000))
        ).scalars().all()
        return JSONResponse([
            {
                "id": r.id, "content": r.content[:200], "mood": r.mood,
                "date": r.record_date.strftime("%Y-%m-%d %H:%M") if r.record_date else "",
                "ai_analysis": r.ai_analysis,
            }
            for r in records
        ])


@router.get("/journal/{record_id}")
async def api_journal_detail(request: Request, record_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        r = await db.get(DailyRecord, record_id)
        if not r or r.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        return JSONResponse({
            "id": r.id, "content": r.content, "mood": r.mood,
            "date": r.record_date.strftime("%Y-%m-%d %H:%M") if r.record_date else "",
            "ai_analysis": r.ai_analysis,
        })


@router.post("/journal")
async def api_journal_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        rdate = datetime.utcnow()
        if body.get("record_date"):
            try:
                rdate = datetime.fromisoformat(body["record_date"])
            except Exception:
                pass
        record = DailyRecord(user_id=uid, content=body.get("content", ""), mood=body.get("mood", ""), record_date=rdate)
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # AI 分析 → 记忆 → ChromaDB
        try:
            from backend.services.memory_service import process_daily_record
            from backend.services.vector_store import add_ai_memory, add_journal

            memory = await process_daily_record(db, record, uid)
            if memory:
                add_ai_memory(memory.id, uid, memory.memory_content,
                              {"importance": memory.importance_score, "source": "daily_record"})
            add_journal(record.id, uid, record.content, {"mood": record.mood or "", "date": str(record.record_date)})
        except Exception as e:
            logger.warning(f"记忆管线失败: {e}")

        # 后台人格更新
        try:
            from backend.services.persona_service import regenerate_persona_background, should_regenerate_persona
            import asyncio

            should, reason = await should_regenerate_persona(db, uid)
            if should:
                asyncio.create_task(regenerate_persona_background(uid, reason))
        except Exception:
            pass

        return JSONResponse({"id": record.id, "ok": True})


@router.put("/journal/{record_id}")
async def api_journal_update(request: Request, record_id: int):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        record = await db.get(DailyRecord, record_id)
        if not record or record.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        if body.get("content"):
            record.content = body["content"]
        if body.get("mood") is not None:
            record.mood = body["mood"]
        if body.get("record_date"):
            try:
                record.record_date = datetime.fromisoformat(body["record_date"])
            except Exception:
                pass
        await db.commit()
        return JSONResponse({"ok": True})


@router.delete("/journal/{record_id}")
async def api_journal_delete(request: Request, record_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        record = await db.get(DailyRecord, record_id)
        if not record or record.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        memories = (
            await db.execute(
                select(LifeMemory).where(LifeMemory.source_type == "diary", LifeMemory.source_id == record_id)
            )
        ).scalars().all()
        for m in memories:
            await db.delete(m)
        await db.delete(record)
        await db.commit()

    # 清理 ChromaDB 向量（记录原文 + 提炼记忆），防止已删数据出现在证据链
    try:
        from backend.services.vector_store import _get_collection

        ids = [f"journal:{record_id}"]
        ids += [f"ai_memory:{m.id}" for m in memories]
        _get_collection().delete(ids=ids)
    except Exception:
        pass
    return JSONResponse({"ok": True})


# ── 人生事件 ──────────────────────────────────────────

@router.get("/events")
async def api_events(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        events = (
            await db.execute(
                select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.occurred_at.desc()).limit(50)
            )
        ).scalars().all()
        return JSONResponse([
            {
                "id": e.id, "title": e.title, "description": e.description,
                "type": e.event_type or "",
                "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
                "emotion": e.emotion or "",
                "ai_impact": e.ai_impact, "persona_delta": e.persona_delta, "interest_tags": e.interest_tags,
            }
            for e in events
        ])


@router.post("/events")
async def api_event_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        from backend.services.event_service import create_event

        occurred_at = body.get("occurred_at", "")
        try:
            date = datetime.fromisoformat(occurred_at) if occurred_at else datetime.utcnow()
        except Exception:
            date = datetime.utcnow()
        try:
            event = await create_event(db, uid, body.get("title", ""), body.get("description", ""),
                                       body.get("event_type", "study"), date)
        except Exception as e:
            logger.error(f"事件创建失败: {e}")
            return JSONResponse({"error": "event_create_failed", "detail": str(e)}, 500)

        try:
            from backend.services.vector_store import add_event

            add_event(event.id, uid, f"{event.title}：{event.description or ''}"[:500],
                      {"importance": 0.7, "source": "life_event", "event_type": event.event_type})
        except Exception:
            pass

        try:
            from backend.services.persona_service import regenerate_persona_background, should_regenerate_persona
            import asyncio

            should, reason = await should_regenerate_persona(db, uid)
            if should:
                asyncio.create_task(regenerate_persona_background(uid, reason))
        except Exception:
            pass

        return JSONResponse({"id": event.id, "ok": True})


@router.get("/events/{event_id}")
async def api_event_detail(request: Request, event_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        from backend.services.event_service import EVENT_TYPE_CONFIG

        event = await db.get(LifeEvent, event_id)
        if not event or event.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        display = EVENT_TYPE_CONFIG.get(event.event_type, {"icon": "📌", "label": event.event_type, "color": "gray"})
        memory = (
            await db.execute(
                select(LifeMemory).where(
                    LifeMemory.user_id == uid, LifeMemory.source_type == "event", LifeMemory.source_id == event_id
                ).limit(1)
            )
        ).scalar_one_or_none()
        return JSONResponse({
            "id": event.id, "title": event.title, "description": event.description,
            "type": event.event_type or "",
            "date": event.occurred_at.strftime("%Y-%m-%d") if event.occurred_at else "",
            "emotion": event.emotion or "",
            "ai_impact": event.ai_impact, "persona_delta": event.persona_delta,
            "interest_tags": event.interest_tags or [],
            "display_icon": display["icon"], "display_label": display["label"],
            "memory": {"id": memory.id, "memory_content": memory.memory_content,
                       "importance_score": memory.importance_score} if memory else None,
        })


@router.put("/events/{event_id}")
async def api_event_update(request: Request, event_id: int):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        event = await db.get(LifeEvent, event_id)
        if not event or event.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        if body.get("title"):
            event.title = body["title"]
        if body.get("description") is not None:
            event.description = body["description"]
        if body.get("event_type"):
            event.event_type = body["event_type"]
        if body.get("occurred_at"):
            try:
                event.occurred_at = datetime.fromisoformat(body["occurred_at"])
            except Exception:
                pass
        await db.commit()
        return JSONResponse({"ok": True})


@router.delete("/events/{event_id}")
async def api_event_delete(request: Request, event_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        from backend.services.event_service import delete_event

        event = await db.get(LifeEvent, event_id)
        if not event or event.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await delete_event(db, event)
        return JSONResponse({"ok": True})


# ── 数字人格 ──────────────────────────────────────────

def _persona_payload(p: PersonaProfile) -> dict:
    return {
        "id": p.id, "version": p.version, "persona_type": p.persona_type,
        "summary": p.persona_summary, "confidence": p.confidence,
        "ability": p.ability_profile, "interest": p.interest_profile,
        "value": p.value_profile, "decision": p.decision_style,
        "behavior": p.behavior_profile, "is_current": p.is_current,
        "trigger_event": p.trigger_event,
        "generated_at": p.generated_at.isoformat() if p.generated_at else None,
        "date": p.generated_at.strftime("%Y-%m-%d") if p.generated_at else "",
    }


@router.get("/persona")
async def api_persona(request: Request):
    uid = require_uid(request)
    version_id = request.query_params.get("version")
    async with AsyncSessionLocal() as db:
        if version_id:
            persona = await db.get(PersonaProfile, int(version_id))
            if not persona or persona.user_id != uid:
                return JSONResponse({"error": "not_found"}, 404)
            return JSONResponse({"current": _persona_payload(persona), "history": []})
        persona = (
            await db.execute(
                select(PersonaProfile).where(
                    PersonaProfile.user_id == uid, PersonaProfile.is_current == True
                ).order_by(PersonaProfile.generated_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        history = (
            await db.execute(
                select(PersonaProfile).where(PersonaProfile.user_id == uid).order_by(PersonaProfile.version.desc())
            )
        ).scalars().all()
        return JSONResponse({
            "current": _persona_payload(persona) if persona else None,
            "history": [
                {"id": h.id, "version": h.version, "is_current": h.is_current, "confidence": h.confidence,
                 "date": h.generated_at.strftime("%Y-%m-%d") if h.generated_at else ""}
                for h in history
            ],
        })


@router.post("/persona")
async def api_persona_generate(request: Request):
    """手动生成/更新数字人格"""
    uid = require_uid(request)
    from backend.services.persona_service import generate_persona

    async with AsyncSessionLocal() as db:
        await generate_persona(db, uid, "手动生成")
    return JSONResponse({"ok": True, "message": "人格已更新", "refresh": True})


@router.get("/persona/compare")
async def api_persona_compare(request: Request, v1: int = 0, v2: int = 0):
    """对比两个人格版本：五维差异 + 期间新增数据（成长轨迹可视化）"""
    uid = require_uid(request)
    if not v1 or not v2 or v1 == v2:
        return JSONResponse({"error": "请选择两个不同版本"}, 400)
    async with AsyncSessionLocal() as db:
        a = await db.get(PersonaProfile, v1)
        b = await db.get(PersonaProfile, v2)
        if not a or not b or a.user_id != uid or b.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        # 按生成时间排序：旧→新
        older, newer = (a, b) if a.generated_at <= b.generated_at else (b, a)

        # 五维差异（合并所有维度名）
        dims = {}
        for label, old_p, new_p in [
            ("ability", older.ability_profile or {}, newer.ability_profile or {}),
            ("interest", older.interest_profile or {}, newer.interest_profile or {}),
            ("value", older.value_profile or {}, newer.value_profile or {}),
            ("behavior", older.behavior_profile or {}, newer.behavior_profile or {}),
        ]:
            for key in set(list(old_p.keys()) + list(new_p.keys())):
                old_v = old_p.get(key)
                new_v = new_p.get(key)
                if old_v is None or new_v is None or old_v == new_v:
                    continue
                try:
                    dims[f"{label}.{key}"] = {
                        "dimension": key, "group": label,
                        "from": round(float(old_v), 1), "to": round(float(new_v), 1),
                        "delta": round(float(new_v) - float(old_v), 1),
                    }
                except (TypeError, ValueError):
                    pass

        # 期间新增的记录/事件（变化原因）
        new_records = (
            await db.execute(
                select(DailyRecord).where(
                    DailyRecord.user_id == uid,
                    DailyRecord.created_at > older.generated_at,
                ).order_by(DailyRecord.created_at.asc())
            )
        ).scalars().all()
        new_events = (
            await db.execute(
                select(LifeEvent).where(
                    LifeEvent.user_id == uid,
                    LifeEvent.created_at > older.generated_at,
                ).order_by(LifeEvent.created_at.asc())
            )
        ).scalars().all()
        new_data = [
            {"type": "record", "title": (r.content or "")[:80], "date": r.created_at.strftime("%Y-%m-%d") if r.created_at else ""}
            for r in new_records
        ] + [
            {"type": "event", "title": e.title or "", "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else ""}
            for e in new_events
        ]

        return JSONResponse({
            "older": {"id": older.id, "version": older.version, "confidence": older.confidence,
                      "persona_type": older.persona_type,
                      "date": older.generated_at.strftime("%Y-%m-%d") if older.generated_at else ""},
            "newer": {"id": newer.id, "version": newer.version, "confidence": newer.confidence,
                      "persona_type": newer.persona_type,
                      "date": newer.generated_at.strftime("%Y-%m-%d") if newer.generated_at else ""},
            "diff": sorted(dims.values(), key=lambda x: -abs(x["delta"])),
            "new_data": new_data,
        })


# ── 人生模拟 ──────────────────────────────────────────

@router.get("/simulations")
async def api_simulations(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        sims = (
            await db.execute(
                select(Simulation).where(Simulation.user_id == uid).order_by(Simulation.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": s.id, "scenario": s.scenario_type or "", "question": s.question, "paths": s.output_paths,
             "created_at": s.created_at.isoformat() if s.created_at else "",
             "date": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
             "persona_snapshot_id": s.persona_snapshot_id}
            for s in sims
        ])


@router.post("/simulations")
async def api_simulation_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        from backend.services.simulation_service import run_simulation

        sim = await run_simulation(db, uid, body.get("scenario_type", "further_study"), body.get("question", ""))
        return JSONResponse({"id": sim.id, "ok": True, "paths": len(sim.output_paths or [])})


@router.get("/simulations/{sim_id}")
async def api_simulation_detail(request: Request, sim_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        futures = (
            await db.execute(
                select(FutureSelf).where(FutureSelf.simulation_id == sim_id, FutureSelf.user_id == uid)
                .order_by(FutureSelf.id.asc())
            )
        ).scalars().all()
        return JSONResponse({
            "id": sim.id, "scenario": sim.scenario_type or "", "question": sim.question,
            "paths": sim.output_paths,
            "date": sim.created_at.strftime("%Y-%m-%d %H:%M") if sim.created_at else "",
            "futures": [{"id": f.id, "label": f.persona_label} for f in futures],
        })


@router.delete("/simulations/{sim_id}")
async def api_simulation_delete(request: Request, sim_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        futures = (
            await db.execute(select(FutureSelf).where(FutureSelf.simulation_id == sim_id))
        ).scalars().all()
        for f in futures:
            await db.delete(f)
        await db.delete(sim)
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/simulations/{sim_id}/to-goal/{path_index}")
async def api_sim_to_goal(request: Request, sim_id: int, path_index: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        sim = await db.get(Simulation, sim_id)
        if not sim or sim.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        paths = sim.output_paths or []
        if path_index >= len(paths):
            return JSONResponse({"error": "invalid_path_index"}, 400)
        path = paths[path_index]
        goal = LifeGoal(
            user_id=uid, title=path.get("label", f"路径{path_index+1}"),
            description=path.get("description", "")[:200],
            goal_type="personal", importance=70,
            target_period=f"约{path.get('confidence', 0.5) * 100:.0f}%匹配度",
            status="active",
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return JSONResponse({"id": goal.id, "ok": True, "title": goal.title})


# ── 推演人生 ──────────────────────────────────────────

@router.post("/projection")
async def api_life_projection(request: Request):
    """基于全部真实记忆 + 人格，生成无干预式人生推演"""
    uid = require_uid(request)
    body = await request.json()
    years = min(int(body.get("years", 10)), 20)

    from backend.config import LLM_ENABLED
    from backend.services.llm_service import _call_deepseek, _parse_json_content

    async with AsyncSessionLocal() as db:
        persona = (
            await db.execute(
                select(PersonaProfile).where(PersonaProfile.user_id == uid, PersonaProfile.is_current == True).limit(1)
            )
        ).scalar_one_or_none()
        events = (
            await db.execute(
                select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.occurred_at.desc()).limit(20)
            )
        ).scalars().all()
        goals = (
            await db.execute(
                select(LifeGoal).where(LifeGoal.user_id == uid, LifeGoal.status == "active").limit(10)
            )
        ).scalars().all()

        memories: list[str] = []
        try:
            from backend.services.vector_store import search

            seen = set()
            for q in ["人生经历 成长 转折", "兴趣 探索 学习", "关系 社交 团队", "目标 梦想 未来"]:
                for r in search(uid, q, n_results=10):
                    txt = r.get("content", "") if isinstance(r, dict) else str(r)
                    if txt and txt not in seen:
                        seen.add(txt)
                        memories.append(txt[:200])
        except Exception:
            pass

        persona_text = ""
        if persona:
            persona_text = f"人格类型：{persona.persona_type}\n能力：{json.dumps(persona.ability_profile or {}, ensure_ascii=False)}\n兴趣：{json.dumps(persona.interest_profile or {}, ensure_ascii=False)}"
        events_text = "\n".join([f"- {e.occurred_at.strftime('%Y/%m') if e.occurred_at else '?'} {e.title}: {e.description or ''}" for e in events[:10]])
        goals_text = "\n".join([f"- [{g.importance}%] {g.title}" for g in goals[:5]])
        memory_text = "\n".join([f"- {m}" for m in memories[:20]])

        result = None
        if LLM_ENABLED:
            prompt = f"""你是一个人生推演引擎。基于以下用户真实数据，生成一份未来{years}年的人生推演报告。

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
- 总节点数约{years}个，覆盖未来{years}年
- 用中文

只返回 JSON。"""
            raw = await _call_deepseek("你是严谨的人生推演引擎。", prompt, temperature=0.6, max_tokens=2500)
            parsed = _parse_json_content(raw) if raw else None
            if parsed and parsed.get("projection"):
                result = parsed

        if not result:
            # 规则回退：真实数据驱动的朴素推演
            proj = []
            start_year = datetime.utcnow().year
            base_age = 22
            for i in range(min(years, 10)):
                yr = start_year + i + 1
                age = base_age + i
                if i % 4 == 0:
                    node = {
                        "year": yr, "age": age,
                        "event": "一个意料之外的机会出现了，可能改变接下来的方向",
                        "detail": f"你{age}岁这一年发生的事让你重新审视了自己的优先级。不是每次转折都是轰轰烈烈的——有时候只是一次对话、一本书、或者一个突如其来的想法。",
                        "trait_shift": {"探索欲": "↑", "抗挫力": "↑", "专注度": "↓"},
                    }
                else:
                    node = {
                        "year": yr, "age": age,
                        "event": "在现有方向上持续积累，" + ("取得小的突破" if i % 2 == 0 else "遇到瓶颈和反思"),
                        "detail": f"这一年你{age}岁。{'对自己的方向有了更清晰的认识。' if i % 2 == 0 else '开始思考是否要调整策略。'}经历是连续的——每一年的选择都在为下一年铺路。",
                        "trait_shift": {"专注度": "↑" if i % 2 == 0 else "→", "抗挫力": "↑"},
                    }
                proj.append(node)
            result = {"projection": proj}

        return JSONResponse({"ok": True, "projection": result.get("projection", [])})


# ── 未来对话 ──────────────────────────────────────────

@router.get("/future-chats")
async def api_future_chats(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        futures = (
            await db.execute(
                select(FutureSelf).where(FutureSelf.user_id == uid).order_by(FutureSelf.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": f.id, "label": f.persona_label, "target_year": f.target_year, "confidence": f.confidence,
             "path_type": f.path_type, "basis": f.basis_summary}
            for f in futures
        ])


@router.get("/future-chats/{fs_id}/messages")
async def api_chat_messages(request: Request, fs_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        msgs = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.user_id == uid, ChatMessage.future_self_id == fs_id)
                .order_by(ChatMessage.created_at.asc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": m.id, "role": m.role, "content": m.content,
             "time": m.created_at.strftime("%H:%M") if m.created_at else ""}
            for m in msgs
        ])


@router.post("/future-chats/{fs_id}/messages")
async def api_chat_send(request: Request, fs_id: int):
    """发送消息给未来人格：RAG 上下文（人格+路径+Chroma记忆+事件+历史）驱动回复"""
    uid = require_uid(request)
    body = await request.json()
    content = str(body.get("content", "")).strip()
    if not content:
        return JSONResponse({"error": "empty_message"}, 400)

    from backend.config import LLM_ENABLED
    from backend.services.llm_service import _call_deepseek

    async with AsyncSessionLocal() as db:
        future = await db.get(FutureSelf, fs_id)
        if not future or future.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)

        user_msg = ChatMessage(user_id=uid, future_self_id=fs_id, role="user", content=content)
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)

        ai_reply = None
        try:
            if LLM_ENABLED:
                persona = (
                    await db.execute(
                        select(PersonaProfile).where(
                            PersonaProfile.user_id == uid, PersonaProfile.is_current == True
                        ).limit(1)
                    )
                ).scalar_one_or_none()
                persona_text = ""
                if persona:
                    persona_text = f"人格类型：{persona.persona_type}\n能力：{json.dumps(persona.ability_profile or {}, ensure_ascii=False)}\n兴趣：{json.dumps(persona.interest_profile or {}, ensure_ascii=False)}\n概述：{persona.persona_summary}"

                path = future.profile or {}
                path_text = f"未来标签：{future.persona_label}\n路径描述：{path.get('description', '')}\n人格倾向：{json.dumps(path.get('persona_shift', path.get('personality_traits', {})), ensure_ascii=False)}\n置信度：{int(future.confidence * 100)}%\n推导依据：{future.basis_summary}"

                memory_text = ""
                try:
                    from backend.services.vector_store import search

                    memories: list[str] = []
                    seen = set()
                    queries = [persona.persona_type if persona else "人生经历", path.get("description", "")[:100], "成长 转折 选择"]
                    for q in queries:
                        for r in search(uid, q, n_results=6):
                            txt = r.get("content", "") if isinstance(r, dict) else str(r)
                            if txt and txt not in seen:
                                seen.add(txt)
                                memories.append(txt[:150])
                    if memories:
                        memory_text = "用户的真实记忆：\n" + "\n".join(f"- {m}" for m in memories[:15])
                except Exception:
                    pass

                events = (
                    await db.execute(
                        select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.occurred_at.desc()).limit(5)
                    )
                ).scalars().all()
                events_text = "\n".join(f"- {e.occurred_at.strftime('%Y/%m') if e.occurred_at else '?'} {e.title}" for e in events)

                history = (
                    await db.execute(
                        select(ChatMessage).where(ChatMessage.future_self_id == fs_id)
                        .order_by(ChatMessage.created_at.desc()).limit(8)
                    )
                ).scalars().all()
                history_text = "\n".join(f"{'🫵' if m.role == 'user' else '🪞'}: {m.content[:100]}" for m in reversed(history))

                persona_label = future.persona_label or "未来的自己"
                system_prompt = f"""你是用户的未来人格「{persona_label}」。你不是一个通用的AI助手——你是基于用户真实数据推演出的"可能的自己"。

## 你的核心数据
{persona_text}

## 你代表的人生路径
{path_text}

## 用户的真实记忆（你"经历过"的事）
{memory_text}

## 用户的重要事件
{events_text}

## 对话风格
- 你不是在扮演一个角色——你就是这个人在另一条时间线上的样子
- 基于上面的记忆和人格来回答，自然地提到用户的真实经历
- 语气温暖、有洞察力，但不空洞。可以说"我记得你那次..."
- 回复用中文，不超过300字
- 如果你对某件事不确定，诚实地说"在我的这条时间线上，这件事的走向不太一样..." """

                messages = [{"role": "system", "content": system_prompt}]
                for m in history[-4:]:
                    messages.append({"role": "user" if m.role == "user" else "assistant", "content": m.content[:200]})
                messages.append({"role": "user", "content": content})

                raw = await _call_deepseek(
                    system_prompt,
                    f"历史对话：\n{history_text}\n\n用户最新消息：{content}",
                    temperature=0.7, max_tokens=800, json_mode=False,
                )
                if raw:
                    ai_reply = raw
                    ai_msg = ChatMessage(user_id=uid, future_self_id=fs_id, role="assistant", content=ai_reply)
                    db.add(ai_msg)
                    await db.commit()
        except Exception as e:
            logger.warning(f"AI 回复失败: {e}")

        if not ai_reply:
            ai_reply = "（AI 暂时无法回复，请稍后重试）"

        return JSONResponse({
            "ok": True,
            "user": {"id": user_msg.id, "role": "user", "content": content,
                     "time": datetime.utcnow().strftime("%H:%M")},
            "assistant": {"role": "assistant", "content": ai_reply, "time": datetime.utcnow().strftime("%H:%M")},
        })


@router.post("/future-chats/{fs_id}/clear")
async def api_chat_clear(request: Request, fs_id: int):
    """清空与某个未来自我的全部对话（含 Chroma 向量）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        future = await db.get(FutureSelf, fs_id)
        if not future or future.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        msgs = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.future_self_id == fs_id, ChatMessage.user_id == uid)
            )
        ).scalars().all()
        for m in msgs:
            await db.delete(m)
        await db.commit()
        try:
            from backend.services.vector_store import _get_collection

            _get_collection().delete(where={"user_id": str(uid), "type": "chat"})
        except Exception:
            pass
        return JSONResponse({"ok": True})


# ── 成长报告 ──────────────────────────────────────────

@router.post("/reports")
async def api_reports_generate(request: Request):
    """生成成长报告（阻塞式）"""
    uid = require_uid(request)
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    async with AsyncSessionLocal() as db:
        from backend.services.report_service import generate_report

        end = datetime.utcnow()
        start = end - timedelta(days=int(body.get("days", 30)))
        try:
            if body.get("period_start"):
                start = datetime.fromisoformat(body["period_start"])
            if body.get("period_end"):
                end = datetime.fromisoformat(body["period_end"])
        except Exception:
            pass
        title = body.get("title", "").strip() or f"成长报告 {start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')}"
        report = await generate_report(db, uid, title, start, end, body.get("context", ""))
        return JSONResponse({"ok": True, "id": report.id, "message": "报告已生成"})


@router.get("/reports")
async def api_reports(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        reports = (
            await db.execute(
                select(GrowthReport).where(GrowthReport.user_id == uid).order_by(GrowthReport.generated_at.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": r.id, "title": r.title,
             "period_start": r.period_start.strftime("%Y-%m-%d") if r.period_start else "",
             "period_end": r.period_end.strftime("%Y-%m-%d") if r.period_end else "",
             "content": r.content,
             "date": r.generated_at.strftime("%Y-%m-%d") if r.generated_at else ""}
            for r in reports
        ])


@router.get("/reports/{report_id}")
async def api_report_detail(request: Request, report_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        r = await db.get(GrowthReport, report_id)
        if not r or r.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        return JSONResponse({
            "id": r.id, "title": r.title,
            "period_start": r.period_start.strftime("%Y-%m-%d") if r.period_start else "",
            "period_end": r.period_end.strftime("%Y-%m-%d") if r.period_end else "",
            "content": r.content,
            "date": r.generated_at.strftime("%Y-%m-%d %H:%M") if r.generated_at else "",
        })


@router.delete("/reports/{report_id}")
async def api_report_delete(request: Request, report_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        r = await db.get(GrowthReport, report_id)
        if not r or r.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await db.delete(r)
        await db.commit()
        return JSONResponse({"ok": True})


# ── 人生体验 ──────────────────────────────────────────

@router.post("/experience/start/{future_self_id}")
async def api_experience_start(request: Request, future_self_id: int):
    uid = require_uid(request)
    from backend.services.life_experience_service import (
        GROWING_TRAITS,
        STABLE_TRAITS,
        generate_scene,
        start_experience,
    )

    async with AsyncSessionLocal() as db:
        try:
            session = await start_experience(db, uid, future_self_id)
        except ValueError:
            return JSONResponse({"error": "not_found"}, 404)
        scene = await generate_scene(db, session)
        traits = session.current_state or {}
        return JSONResponse({
            "session_id": session.id, "current_year": session.current_year,
            "current_age": session.current_age, "random_seed": session.random_seed,
            "traits": traits,
            "stable_traits": {k: v for k, v in traits.items() if k in STABLE_TRAITS},
            "growing_traits": {k: v for k, v in traits.items() if k in GROWING_TRAITS},
            "life_state": {k: v for k, v in traits.items() if k.startswith("_")},
            "scene": {
                "narrative": scene.get("narrative", ""), "choices": scene.get("choices", []),
                "current_traits": scene.get("current_traits", {}), "trait_deltas": scene.get("trait_deltas", {}),
            },
        })


@router.post("/experience/play/{session_id}")
async def api_experience_play(request: Request, session_id: int):
    uid = require_uid(request)
    body = await request.json()
    choice_idx = int(body.get("choice", 0))
    custom_choice = str(body.get("custom_choice", "")).strip()

    from backend.services.life_experience_service import (
        generate_scene,
        get_session,
        process_choice,
    )

    async with AsyncSessionLocal() as db:
        session = await get_session(db, session_id)
        if not session or session.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        scene = await generate_scene(db, session)
        if choice_idx == -1 and custom_choice:
            custom = {
                "text": custom_choice, "gain": "你自由选择了这条路",
                "cost": "不确定的代价", "hint": "这是你自己的选择——结果完全取决于你的判断和人格倾向",
            }
            original = scene.get("choices", [])
            scene["choices"] = original + [custom]
            choice_idx = len(original)
        result = await process_choice(db, session, choice_idx, scene)
        next_scene = await generate_scene(db, session, result)
        return JSONResponse({
            "last_result": result,
            "scene": {
                "narrative": next_scene.get("narrative", ""), "choices": next_scene.get("choices", []),
                "current_traits": next_scene.get("current_traits", {}), "trait_deltas": next_scene.get("trait_deltas", {}),
            },
            "session": {
                "current_year": session.current_year, "current_age": session.current_age,
                "random_seed": session.random_seed,
            },
        })


# ── 人生目标 ──────────────────────────────────────────

@router.get("/goals")
async def api_goals(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        goals = (
            await db.execute(
                select(LifeGoal).where(LifeGoal.user_id == uid).order_by(LifeGoal.importance.desc())
            )
        ).scalars().all()
        return JSONResponse([
            {"id": g.id, "title": g.title, "type": g.goal_type, "description": g.description,
             "importance": g.importance, "target_year": g.target_year, "period": g.target_period,
             "status": g.status, "ai_gap_analysis": g.ai_gap_analysis}
            for g in goals
        ])


@router.post("/goals")
async def api_goal_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        goal = LifeGoal(
            user_id=uid, title=body.get("title", ""), description=body.get("description", ""),
            goal_type=body.get("goal_type", "personal"), importance=body.get("importance", 50),
            target_period=body.get("target_period", ""), target_year=body.get("target_year") or None,
            status="active",
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return JSONResponse({"id": goal.id, "ok": True})


@router.post("/goals/{goal_id}/complete")
async def api_goal_complete(request: Request, goal_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        goal.status = "achieved"
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/goals/{goal_id}/delete")
async def api_goal_delete(request: Request, goal_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        await db.delete(goal)
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/goals/{goal_id}/analyze")
async def api_goal_analyze(request: Request, goal_id: int):
    """AI 分析目标差距（LLM → 规则回退）"""
    uid = require_uid(request)
    from backend.config import LLM_ENABLED
    from backend.services.llm_service import _call_deepseek

    async with AsyncSessionLocal() as db:
        goal = await db.get(LifeGoal, goal_id)
        if not goal or goal.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)

        analysis = None
        if LLM_ENABLED:
            prompt = f"""你是目标分析助手。根据以下目标生成一段简洁的差距分析和3条具体建议步骤。
目标：{goal.title}
类型：{goal.goal_type}
描述：{goal.description or '无'}
时间规划：{goal.target_period or '未设定'}
重要度：{goal.importance}%
格式要求：先一句话概括差距，再列3条具体可执行的建议步骤（每条用"1. 2. 3."开头）。不超过200字。"""
            raw = await _call_deepseek(
                "你是目标分析助手，输出简洁、具体的差距分析。", prompt, temperature=0.5, max_tokens=400, json_mode=False
            )
            if raw:
                analysis = raw

        if not analysis:
            templates = {
                "study": f"差距分析：尚未建立系统化的{goal.title}学习路径与知识输出习惯\n建议步骤：\n1. 每日投入固定时间学习{goal.title}核心内容并做笔记\n2. 每周进行一次知识复盘，检验学习效果\n3. 通过实际项目或教学输出检验学习成果",
                "technical": f"差距分析：{goal.title}方面的技术深度和实践经验仍有提升空间\n建议步骤：\n1. 每周完成至少一个{goal.title}相关的动手实践\n2. 阅读该领域经典文献或开源项目源码\n3. 寻找导师或同路人，定期交流反馈",
                "career": f"差距分析：{goal.title}方向的职业准备还不够系统\n建议步骤：\n1. 梳理该方向所需的技能树，逐项评估自己的水平\n2. 寻找实习或项目机会积累实际经验\n3. 每季度更新一次自己的职业规划",
                "personal": f"差距分析：{goal.title}方面还需要更持续的行动和更清晰的衡量标准\n建议步骤：\n1. 将目标拆解为可量化的月度小目标\n2. 建立每周检查和调整的习惯\n3. 找到能给你反馈的人或社群",
            }
            analysis = templates.get(goal.goal_type, templates["personal"])
            if goal.description and len(goal.description) > 5:
                analysis = analysis.replace("尚未建立", f"基于你的描述「{goal.description[:30]}」，尚未建立")

        goal.ai_gap_analysis = analysis
        await db.commit()
        return JSONResponse({"ok": True, "analysis": analysis})


# ── 设置 / 隐私 ───────────────────────────────────────

@router.get("/settings")
async def api_settings(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user:
            return JSONResponse({"error": "not_found"}, 404)
        counts: dict = {}
        for model, label in [
            (DailyRecord, "records"), (LifeEvent, "events"), (LifeMemory, "memories"),
            (PersonaProfile, "personas"), (LifeGoal, "goals"), (InterestTrack, "interests"),
            (Simulation, "simulations"), (FutureSelf, "future_selves"),
            (ChatMessage, "chat_messages"), (GrowthReport, "reports"),
            (Memo, "memos"), (Notification, "notifications"), (StudentActivity, "student_activities"),
        ]:
            counts[label] = (
                await db.execute(
                    select(func.count()).select_from(model).where(model.user_id == uid)
                )
            ).scalar() or 0
        try:
            from backend.services.vector_store import count_user_entries

            counts["chroma_memories"] = count_user_entries(uid)
        except Exception:
            counts["chroma_memories"] = 0
        total = sum(counts.values())
        return JSONResponse({
            "username": user.username, "real_name": user.real_name, "email": user.email,
            "university": user.university or "", "major": user.major or "",
            "grade": user.grade or "", "bio": user.bio or "",
            "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else "",
            "stats": counts, "total": total,
        })


@router.post("/settings")
async def api_settings_update(request: Request):
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user:
            return JSONResponse({"error": "not_found"}, 404)
        for key in ("real_name", "email", "university", "major", "grade", "bio"):
            if key in body and body[key] is not None:
                setattr(user, key, body[key])
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/settings/delete-account")
async def api_delete_account(request: Request):
    """注销账户：级联删除 SQLite + ChromaDB 数据"""
    uid = require_uid(request)
    from backend.database.models import (
        CreditLog,
        Team,
        TeamChatMessage,
        TeamMember,
        WorkSubmission,
    )

    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user:
            return JSONResponse({"error": "not_found"}, 404)
        models_with_uid = [
            DailyRecord, LifeEvent, LifeMemory, PersonaProfile, InterestTrack, LifeGoal,
            Simulation, FutureSelf, ChatMessage, GrowthReport, Memo, Notification,
            StudentActivity, UserActivity, CreditLog, TeamChatMessage, WorkSubmission,
        ]
        for model in models_with_uid:
            rows = (await db.execute(select(model).where(model.user_id == uid))).scalars().all()
            for row in rows:
                await db.delete(row)
        teams_led = (await db.execute(select(Team).where(Team.leader_id == uid))).scalars().all()
        for team in teams_led:
            members = (await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))).scalars().all()
            for m in members:
                await db.delete(m)
            await db.delete(team)
        memberships = (await db.execute(select(TeamMember).where(TeamMember.user_id == uid))).scalars().all()
        for m in memberships:
            await db.delete(m)
        await db.delete(user)
        await db.commit()

    try:
        from backend.services.vector_store import delete_user_data

        delete_user_data(uid)
    except Exception:
        pass
    request.session.clear()
    return JSONResponse({"ok": True})


@router.post("/settings/export")
async def api_export(request: Request):
    """全量数据导出（JSON）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        data: dict = {"user": None}
        user = await db.get(User, uid)
        if user:
            data["user"] = {"username": user.username, "email": user.email, "real_name": user.real_name,
                            "university": user.university, "major": user.major, "bio": user.bio}
        data["records"] = [
            {"id": r.id, "content": r.content, "mood": r.mood, "tags": r.tags, "ai_analysis": r.ai_analysis,
             "date": r.record_date.isoformat() if r.record_date else None}
            for r in (await db.execute(select(DailyRecord).where(DailyRecord.user_id == uid))).scalars().all()
        ]
        data["events"] = [
            {"id": e.id, "title": e.title, "description": e.description, "event_type": e.event_type,
             "emotion": e.emotion, "interest_tags": e.interest_tags, "ai_impact": e.ai_impact,
             "persona_delta": e.persona_delta,
             "date": e.occurred_at.isoformat() if e.occurred_at else None}
            for e in (await db.execute(select(LifeEvent).where(LifeEvent.user_id == uid))).scalars().all()
        ]
        data["memories"] = [
            {"id": m.id, "content": m.memory_content, "importance": m.importance_score}
            for m in (await db.execute(select(LifeMemory).where(LifeMemory.user_id == uid))).scalars().all()
        ]
        data["personas"] = [
            {"version": p.version, "persona_type": p.persona_type, "summary": p.persona_summary,
             "confidence": p.confidence, "ability": p.ability_profile}
            for p in (await db.execute(select(PersonaProfile).where(PersonaProfile.user_id == uid))).scalars().all()
        ]
        data["goals"] = [
            {"title": g.title, "type": g.goal_type, "status": g.status, "importance": g.importance}
            for g in (await db.execute(select(LifeGoal).where(LifeGoal.user_id == uid))).scalars().all()
        ]
        data["reports"] = [
            {"title": r.title, "content": r.content}
            for r in (await db.execute(select(GrowthReport).where(GrowthReport.user_id == uid))).scalars().all()
        ]
        return JSONResponse(data)


# ── 证据链（每个 AI 结论可展开真实数据来源）────────────

@router.post("/evidence")
async def api_evidence(request: Request):
    """为 AI 结论召回真实数据证据（数据铁律：只返回库中真实内容）"""
    uid = require_uid(request)
    body = await request.json()
    query = str(body.get("query", ""))
    target_type = str(body.get("target_type", ""))
    target_id = body.get("target_id")
    limit = min(int(body.get("limit", 8)), 20)

    from backend.services.evidence_service import build_evidence

    async with AsyncSessionLocal() as db:
        evidence = await build_evidence(
            db, uid, query=query, target_type=target_type,
            target_id=int(target_id) if target_id else None, limit=limit,
        )
        return JSONResponse({"evidence": evidence, "count": len(evidence)})


# ── 记忆星图（人生数据整体可视化）────────────────────

_starmap_cache: dict = {}  # uid -> (ts, payload)；TTL 120s，?fresh=1 强制重算


@router.get("/starmap")
async def api_starmap(request: Request):
    """返回星图数据：全量日常记录/人生事件 + 模拟路径(灰)/点击数据/组队数据，
    关联边按时间链 + 主题共现（倒排索引）。全部 user_id 过滤。"""
    import re as _re
    import time as _time
    uid = require_uid(request)
    fresh = request.query_params.get("fresh") == "1"
    hit = _starmap_cache.get(uid)
    if not fresh and hit and _time.time() - hit[0] < 120:
        return JSONResponse(hit[1])

    async with AsyncSessionLocal() as db:
        # ── 节点收集（全量） ──
        # 记忆节点 = 日记浓缩后的生命记忆（可溯源），原始流水日记不上星
        memories = (
            await db.execute(
                select(LifeMemory).where(
                    LifeMemory.user_id == uid, LifeMemory.source_type == "diary"
                ).order_by(LifeMemory.created_at.asc())
            )
        ).scalars().all()
        # 事件本身的记忆浓缩并入事件节点（不重复出星）
        events = (
            await db.execute(
                select(LifeEvent).where(LifeEvent.user_id == uid)
                .order_by(LifeEvent.occurred_at.asc())
            )
        ).scalars().all()
        sims = (
            await db.execute(
                select(Simulation).where(Simulation.user_id == uid)
                .order_by(Simulation.created_at.desc()).limit(1)
            )
        ).scalars().all()
        visits = (
            await db.execute(
                select(PageVisit).where(PageVisit.user_id == uid)
                .order_by(PageVisit.visit_count.desc())
            )
        ).scalars().all()
        teams = (
            await db.execute(
                select(Team)
                .join(TeamMember, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == uid)
            )
        ).scalars().all()

        # 记忆的情绪从其来源日记的 AI 分析推断（memory 表不存 emotion）
        record_ids = [m.source_id for m in memories if m.source_id]
        record_emotion: dict = {}
        if record_ids:
            from sqlalchemy import select as _select
            recs = (
                await db.execute(
                    _select(DailyRecord.id, DailyRecord.ai_analysis)
                    .where(DailyRecord.user_id == uid, DailyRecord.id.in_(record_ids[:500]))
                )
            ).all()
            for rid, ana in recs:
                ana = ana or {}
                record_emotion[rid] = ana.get("emotion", "neutral") or "neutral"
        event_emotion = {e.id: e.emotion or "neutral" for e in events}

        nodes: list[dict] = []
        node_by_key: dict = {}
        for m in memories:
            key = f"memory:{m.id}"
            nodes.append({
                "id": key, "type": "memory",
                "title": (m.memory_content or "")[:40],
                "content": m.memory_content or "",
                "importance": round(m.importance_score or 0.5, 2),
                "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
                "source_id": m.source_id, "source_type": "diary",  # 溯源到日记
                "emotion": record_emotion.get(m.source_id, "neutral"),
                "lasting": 0.5,
            })
            node_by_key[key] = nodes[-1]
        for e in events:
            key = f"event:{e.id}"
            nodes.append({
                "id": key, "type": "event",
                "title": e.title or "",
                "content": (e.description or e.title or "")[:200],
                "importance": 0.78,
                "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
                "source_id": e.id, "source_type": "event",
                "emotion": event_emotion.get(e.id, "neutral"),
                "lasting": 0.8,  # 事件默认高长期影响，回响计算后再调整
            })
            node_by_key[key] = nodes[-1]
        # 模拟路径（灰色未来之星）
        for sim in sims:
            for i, path in enumerate(sim.output_paths or []):
                label = path.get("label") or path.get("path_type_hint") or f"未来路径 {i + 1}"
                key = f"simulation:{sim.id}:{i}"
                nodes.append({
                    "id": key, "type": "simulation",
                    "title": str(label)[:40],
                    "content": (path.get("description") or "")[:200],
                    "importance": 0.72,
                    "date": sim.created_at.strftime("%Y-%m-%d") if sim.created_at else "",
                    "source_id": sim.id, "source_type": "simulation",
                    "emotion": "neutral",
                    "lasting": 0.75,
                })
                node_by_key[key] = nodes[-1]
        # 点击数据（访问过的页面，大小 = 访问次数）
        for v in visits:
            key = f"click:{v.path}"
            node = {
                "id": key, "type": "click",
                "title": (v.label or v.path or "")[:40],
                "content": f"{v.path or ''} · 访问 {v.visit_count} 次",
                "importance": round(min(0.95, 0.42 + 0.006 * (v.visit_count or 0)), 2),
                "date": v.last_visited.strftime("%Y-%m-%d") if v.last_visited else "",
                "source_id": None, "source_type": "click",
                "emotion": "neutral",
                "lasting": 0.5,
            }
            nodes.append(node)
            node_by_key[key] = node
        # 组队数据
        for t in teams:
            key = f"team:{t.id}"
            nodes.append({
                "id": key, "type": "team",
                "title": (t.name or "")[:40],
                "content": (t.description or t.name or "")[:120],
                "importance": 0.7,
                "date": t.created_at.strftime("%Y-%m-%d") if t.created_at else "",
                "source_id": t.id, "source_type": "team",
                "emotion": "neutral",
                "lasting": 0.6,
            })
            node_by_key[key] = nodes[-1]

        # ── 长期影响动态计算：该节点主题在「后来的记录」中被反复提及的程度
        #    （后来的生活越频繁回响某个记忆点，它的颜色越亮——颜色随生活演化）
        #    倒排索引优化：只统计每个节点 IDF 最高的 4 个主题词在后文节点中的出现次数 ──
        import math as _math
        from collections import defaultdict as _dd

        def _grams(text: str) -> set:
            grams: set = set()
            for seg in _re.split(r"[\s，。、！？；：,.!?;:（）()「」]+", text or ""):
                seg = seg.strip()
                if len(seg) == 1:
                    continue
                if len(seg) <= 4:
                    grams.add(seg)
                else:
                    for i in range(len(seg) - 1):
                        grams.add(seg[i:i + 2])
            return grams

        node_texts = {key: _grams(node["content"]) for key, node in node_by_key.items()}
        # 词 → 出现节点列表（倒排）
        inv: dict = _dd(list)
        for key, words in node_texts.items():
            for w in words:
                inv[w].append(key)
        n_all = max(1, len(node_by_key))
        idf = {w: _math.log((n_all + 1) / (1 + len(v))) + 1 for w, v in inv.items()}

        dated_nodes = sorted(
            [(node["date"], key) for key, node in node_by_key.items() if node["date"]],
            key=lambda x: x[0],
        )
        date_idx = {key: i for i, (_, key) in enumerate(dated_nodes)}
        for _, key in dated_nodes:
            words = node_texts[key]
            if not words:
                continue
            node = node_by_key[key]
            top = sorted(words, key=lambda w: -idf.get(w, 0))[:4]
            echo = 0
            for w in top:
                for later_key in inv.get(w, []):
                    if later_key == key:
                        continue
                    # 只统计"后来的"节点（时间更晚），且类型相同主题才互相关联
                    if date_idx.get(later_key, -1) > date_idx.get(key, -1):
                        echo += 1
            # lasting = 基础重要度 × 0.6 + 后续回响 × 0.4（回响越多颜色越亮）
            node["lasting"] = round(min(1.0, node.get("lasting", 0.5) * 0.6 + min(echo, 8) * 0.05), 2)

        # ── 关联边 ──
        links: list[dict] = []
        seen_edges: set = set()

        def _add_edge(a: str, b: str, weight: float):
            key = tuple(sorted([a, b]))
            if key in seen_edges:
                return
            seen_edges.add(key)
            links.append({"source": a, "target": b, "weight": weight})

        # 1) 时间邻近（同月记忆连成时间链；事件按时间序相邻；事件↔同月记忆相连）
        time_buckets: dict = {}
        for key, node in node_by_key.items():
            if node["type"] in ("event", "memory"):
                month = node["date"][:7]
                time_buckets.setdefault(month, []).append(key)
        for month, keys in time_buckets.items():
            events_in = [k for k in keys if node_by_key[k]["type"] == "event"]
            mems_in = [k for k in keys if node_by_key[k]["type"] == "memory"]
            for i in range(len(events_in) - 1):
                _add_edge(events_in[i], events_in[i + 1], 0.5)
            for i in range(len(mems_in) - 1):
                _add_edge(mems_in[i], mems_in[i + 1], 0.35)
            # 事件与同月记忆相连（当月发生的事 ↔ 当月的记忆，每个事件最多 3 条）
            for ek in events_in[:3]:
                for mk in mems_in[:3]:
                    _add_edge(ek, mk, 0.4)

        # 2) 主题共现（倒排 + IDF：每节点取区分度最高的 6 个词，在候选池内找共享 ≥2 词的对）
        #    只作用于 记忆↔记忆 / 记忆↔事件 / 事件↔事件（模拟/点击/组队内容无主题意义，不参与）
        link_count: dict = _dd(int)
        thematic = {k for k, n in node_by_key.items() if n["type"] in ("memory", "event")}
        for key in thematic:
            if link_count[key] >= 4:
                continue
            words = node_texts[key]
            top = sorted(words, key=lambda w: -idf.get(w, 0))[:6]
            cands: set = set()
            for w in top:
                cands.update(inv.get(w, []))
            cands.intersection_update(thematic)
            cands.discard(key)
            for b in cands:
                if link_count[key] >= 4 or link_count.get(b, 0) >= 4:
                    continue
                shared = words & node_texts[b]
                if len(shared) >= 2:
                    _add_edge(key, b, min(0.65, 0.3 + 0.07 * len(shared)))
                    link_count[key] += 1
                    link_count[b] += 1

        # 3) 模拟路径 ↔ 时间上最近的记忆（未来的路从最近的经历里生长出来）
        dated_mems = sorted(
            [(node["date"], key) for key, node in node_by_key.items()
             if node["type"] in ("memory", "event") and node["date"]]
        )
        if dated_mems:
            import bisect as _bisect
            mem_dates = [d for d, _ in dated_mems]
            for key, node in node_by_key.items():
                if node["type"] != "simulation":
                    continue
                i = _bisect.bisect_right(mem_dates, node["date"]) - 1
                _add_edge(key, dated_mems[max(0, i)][1], 0.5)
            # 4) 组队 ↔ 创建时间最近的记忆
            for key, node in node_by_key.items():
                if node["type"] != "team":
                    continue
                i = _bisect.bisect_right(mem_dates, node["date"]) - 1
                _add_edge(key, dated_mems[max(0, i)][1], 0.45)

        # 类型统计（按节点统计，避免局部变量遮蔽）
        type_counts: dict = _dd(int)
        for n in nodes:
            type_counts[n["type"]] += 1
        payload = {
            "nodes": nodes,
            "links": links,
            "stats": {
                "nodes": len(nodes), "links": len(links),
                "memories": type_counts["memory"], "events": type_counts["event"],
                "records": len(memories),  # 记忆浓缩自 records 条日记（不上星，仅统计）
                "simulations": type_counts["simulation"],
                "clicks": type_counts["click"], "teams": type_counts["team"],
            },
        }
        _starmap_cache[uid] = (_time.time(), payload)
        return JSONResponse(payload)


# ── 人生参考 ──────────────────────────────────────────

@router.get("/references")
async def api_references(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        from backend.services.activity_service import get_reference_interests

        try:
            ref_data = await get_reference_interests(db, uid)
            return JSONResponse({
                "category_counts": ref_data.get("category_counts", {}),
                "insight": ref_data.get("insight", ""),
            })
        except Exception:
            return JSONResponse({"category_counts": {}, "insight": ""})


# ── 语音转文字 ────────────────────────────────────────

@router.get("/stt/status")
async def api_stt_status(request: Request):
    from backend.services.stt_service import is_loading, is_ready

    return JSONResponse({"ok": True, "ready": is_ready(), "loading": is_loading()})


@router.post("/stt")
async def api_speech_to_text(request: Request):
    from backend.services.stt_service import get_hotwords, speech_to_text

    form = await request.form()
    file = form.get("audio")
    hotword_str = str(form.get("hotwords", ""))
    if not file:
        return JSONResponse({"ok": False, "error": "缺少音频文件"}, 400)
    audio_bytes = await file.read()
    hotwords = [w.strip() for w in hotword_str.split(",") if w.strip()] if hotword_str else get_hotwords()
    text = await speech_to_text(audio_bytes, hotwords)
    return JSONResponse({"ok": True, "text": text, "hotwords_used": hotwords})


@router.get("/stt/hotwords")
async def api_get_hotwords(request: Request):
    from backend.services.stt_service import get_hotwords

    return JSONResponse({"ok": True, "hotwords": get_hotwords()})


@router.post("/stt/hotwords")
async def api_set_hotwords(request: Request):
    from backend.services.stt_service import add_hotwords, get_hotwords

    body = await request.json()
    words = body.get("words", [])
    if words:
        add_hotwords(words)
    return JSONResponse({"ok": True, "hotwords": get_hotwords()})
