# -*- coding: utf-8 -*-
"""agent 独立后端（:5021）— 智能体对话层

- 认证复用主站 session cookie（同 SECRET_KEY, 同 host 跨端口自动携带, 零二次登录）
- 数据由主站进程内共享（同一 Python 进程双 uvicorn, Chroma/SQLite 单例）
- 静态伺服 agent_web/dist（同源）
"""
import asyncio, json
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from backend.auth import AuthRequiredMiddleware, require_uid
from backend.config import BASE_DIR, SECRET_KEY, UPLOAD_DIR
from backend.database import models as M
from backend.database.database import AsyncSessionLocal, init_db
from backend.services import auth_service

AGENT_APP_NAME = "镜·界·联 · 智能体"
AGENT_DIST = BASE_DIR / "agent_web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(BASE_DIR / "data", exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title=AGENT_APP_NAME, version="1.0.0", lifespan=lifespan)

# ── 中间件（与主站同构: CORS → Session → Auth）──
app.add_middleware(AuthRequiredMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,      # 与主站同一 key → 浏览器 cookie 直接复用
    same_site="lax",
    https_only=False,
    max_age=7 * 86400,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],   # dev 前端
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(ev):
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"


# ── 独立认证（同库注册/登录——session 结构与主站一致, 双向互通）──
auth_router = APIRouter(prefix="/api/auth")


def _set_session(request: Request, user):
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name or user.username,
        "email": user.email,
    }


def _user_dict(user):
    return {"id": user.id, "username": user.username,
            "real_name": user.real_name or user.username, "email": user.email}


@auth_router.post("/register")
async def auth_register(body: dict, request: Request):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    email = (body.get("email") or "").strip()
    real_name = (body.get("real_name") or "").strip() or None
    if len(username) < 2:
        return JSONResponse({"error": "用户名至少 2 个字符"}, status_code=400)
    if len(password) < 8:
        return JSONResponse({"error": "密码至少 8 个字符"}, status_code=400)
    if not email or "@" not in email:
        return JSONResponse({"error": "邮箱格式不正确"}, status_code=400)
    async with AsyncSessionLocal() as db:
        if await auth_service.get_user_by_username(db, username):
            return JSONResponse({"error": "用户名已存在"}, status_code=400)
        try:
            user = await auth_service.create_user(db, username, email, password, real_name)
        except Exception:
            return JSONResponse({"error": "邮箱已注册"}, status_code=400)
        _set_session(request, user)
    return {"ok": True, "user": _user_dict(user)}


@auth_router.post("/login")
async def auth_login(body: dict, request: Request):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    async with AsyncSessionLocal() as db:
        user = await auth_service.authenticate(db, username, password)
        if not user:
            return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
        _set_session(request, user)
    return {"ok": True, "user": _user_dict(user)}


@auth_router.post("/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}


app.include_router(auth_router)


# ── API ────────────────────────────────────────────────

@app.get("/api/agent/agents")
async def agent_agents():
    from backend.agent_prompts import AGENTS
    return {"agents": [{"key": k, "name": v["name"], "subtitle": v["subtitle"],
                        "tagline": v.get("tagline", ""), "questions": v["questions"]}
                       for k, v in AGENTS.items()]}


@app.post("/api/agent/chat/save")
async def agent_chat_save(request: Request):
    """保存一条对话消息（刷新后恢复用）"""
    uid = require_uid(request)
    body = await request.json()
    role = body.get("role") or "user"
    content = (body.get("content") or "").strip()
    agent = (body.get("agent") or "mentor").strip()
    if role not in ("user", "assistant") or not content:
        return {"ok": False, "error": "invalid"}
    from backend.database import models as M
    async with AsyncSessionLocal() as db:
        db.add(M.AgentChatMessage(user_id=uid, agent=agent, role=role, content=content))
        await db.commit()
    return {"ok": True}


@app.get("/api/agent/chat/history")
async def agent_chat_history(request: Request, agent: str = "mentor", limit: int = 50):
    """拉取对话历史"""
    uid = require_uid(request)
    from sqlalchemy import select, desc
    from backend.database import models as M
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(M.AgentChatMessage).where(M.AgentChatMessage.user_id == uid,
                                             M.AgentChatMessage.agent == agent)
            .order_by(desc(M.AgentChatMessage.created_at)).limit(limit))).scalars().all()
    rows = list(reversed(rows))
    return {"history": [{"role": r.role, "content": r.content} for r in rows]}


# ── 用户中心 API ─────────────────────────────────────────
@app.get("/api/agent/me")
async def agent_me_full(request: Request):
    """用户中心资料（扩展字段）"""
    uid = require_uid(request)
    s = request.session.get("user", {})
    async with AsyncSessionLocal() as db:
        u = await db.get(M.User, uid)
        return {"id": uid, "username": s.get("username", ""),
                "real_name": u.real_name or u.username if u else "",
                "email": u.email if u else "", "major": u.major or "",
                "university": u.university or "", "bio": u.bio or "",
                "skill_tags": u.skill_tags or []}


@app.put("/api/agent/profile")
async def agent_profile_update(body: dict, request: Request):
    """更新个人资料（real_name/major/university/bio/skill_tags）"""
    uid = require_uid(request)
    fields = {k: body.get(k) for k in ("real_name", "major", "university", "bio", "skill_tags")}
    fields = {k: v for k, v in fields.items() if v is not None}
    async with AsyncSessionLocal() as db:
        u = await db.get(M.User, uid)
        if not u:
            return {"ok": False, "error": "not_found"}
        auth_service.update_user_profile(db, u, **fields)
        await db.commit()
    if fields.get("real_name"):
        request.session["user"]["real_name"] = fields["real_name"]
    return {"ok": True, "profile": {k: v for k, v in fields.items()}}


@app.post("/api/agent/change-password")
async def agent_change_password(body: dict, request: Request):
    """修改密码（校验旧密码）"""
    uid = require_uid(request)
    old_p = body.get("old_password") or ""
    new_p = body.get("new_password") or ""
    if len(new_p) < 8:
        return {"ok": False, "error": "新密码至少 8 个字符"}
    async with AsyncSessionLocal() as db:
        u = await db.get(M.User, uid)
        if not u or not auth_service.verify_password(old_p, u.password_hash):
            return {"ok": False, "error": "旧密码不正确"}
        u.password_hash = auth_service.hash_password(new_p)
        await db.commit()
    return {"ok": True}


@app.put("/api/agent/records")
async def agent_records_update(request: Request):
    """更新记录状态（目标标注完成/放弃/恢复）"""
    uid = require_uid(request)
    body = await request.json()
    type_ = body.get("type")
    id_ = body.get("id")
    status = (body.get("status") or "").strip()
    if type_ != "goals" or status not in ("active", "achieved", "abandoned"):
        return {"ok": False, "error": "invalid"}
    async with AsyncSessionLocal() as db:
        g = await db.get(M.LifeGoal, id_)
        if not g or g.user_id != uid:
            return {"ok": False, "error": "not_found"}
        g.status = status
        await db.commit()
    return {"ok": True, "status": status}


@app.delete("/api/agent/chat/clear")
async def agent_chat_clear(request: Request):
    """清空对话历史"""
    uid = require_uid(request)
    from sqlalchemy import delete as sa_delete
    async with AsyncSessionLocal() as db:
        await db.execute(sa_delete(M.AgentChatMessage).where(M.AgentChatMessage.user_id == uid))
        await db.commit()
    return {"ok": True}


@app.delete("/api/agent/records")
async def agent_records_delete(request: Request, type: str = "journal", id: int = 0, all: int = 0):
    """删除记录（级联清库: 记忆 + Chroma 向量）: type=journal/events/goals/memories/all, id=单条 或 all=1 清空该类"""
    uid = require_uid(request)
    from sqlalchemy import select
    from backend.services.vector_store import _get_collection
    from backend.services.event_service import delete_event

    async def _drop_vector(ids):
        try:
            _get_collection().delete(ids=[i for i in ids if i])
        except Exception:
            pass

    async with AsyncSessionLocal() as db:
        if type == "journal":
            if id:
                rec = await db.get(M.DailyRecord, id)
                if not rec or rec.user_id != uid:
                    return {"ok": False, "error": "not_found"}
                mems = (await db.execute(select(M.LifeMemory).where(
                    M.LifeMemory.user_id == uid, M.LifeMemory.source_type == "diary",
                    M.LifeMemory.source_id == id))).scalars().all()
                ids = [f"journal:{id}"] + [f"ai_memory:{m.id}" for m in mems]
                for m in mems:
                    await db.delete(m)
                await db.delete(rec)
                await db.commit()
                await _drop_vector(ids)
                return {"ok": True, "deleted": 1}
            if all:
                recs = (await db.execute(select(M.DailyRecord).where(
                    M.DailyRecord.user_id == uid))).scalars().all()
                mems = (await db.execute(select(M.LifeMemory).where(
                    M.LifeMemory.user_id == uid, M.LifeMemory.source_type == "diary"))).scalars().all()
                ids = [f"journal:{r.id}" for r in recs] + [f"ai_memory:{m.id}" for m in mems]
                for m in mems:
                    await db.delete(m)
                for r in recs:
                    await db.delete(r)
                await db.commit()
                await _drop_vector(ids)
                return {"ok": True, "deleted": len(recs)}
        if type == "events":
            if id:
                ev = await db.get(M.LifeEvent, id)
                if not ev or ev.user_id != uid:
                    return {"ok": False, "error": "not_found"}
                await delete_event(db, ev)   # 含记忆 + 向量精确删除
                return {"ok": True, "deleted": 1}
            if all:
                evs = (await db.execute(select(M.LifeEvent).where(
                    M.LifeEvent.user_id == uid))).scalars().all()
                for ev in evs:
                    await delete_event(db, ev)
                return {"ok": True, "deleted": len(evs)}
        if type == "goals":
            q = select(M.LifeGoal).where(M.LifeGoal.user_id == uid)
            if id:
                q = q.where(M.LifeGoal.id == id)
            rows = (await db.execute(q)).scalars().all()
            for g in rows:
                await db.delete(g)
            await db.commit()
            return {"ok": True, "deleted": len(rows)}
        if type == "memories":
            if id:
                m = await db.get(M.LifeMemory, id)
                if not m or m.user_id != uid:
                    return {"ok": False, "error": "not_found"}
                await db.delete(m)
                await db.commit()
                await _drop_vector([m.embedding_id or f"ai_memory:{id}"])
                return {"ok": True, "deleted": 1}
            if all:
                mems = (await db.execute(select(M.LifeMemory).where(
                    M.LifeMemory.user_id == uid))).scalars().all()
                ids = [m.embedding_id or f"ai_memory:{m.id}" for m in mems]
                for m in mems:
                    await db.delete(m)
                await db.commit()
                await _drop_vector(ids)
                return {"ok": True, "deleted": len(mems)}
        if type == "all":
            # 清空全部记录: 日记/事件/目标/记忆 + 全量向量
            recs = (await db.execute(select(M.DailyRecord).where(
                M.DailyRecord.user_id == uid))).scalars().all()
            evs = (await db.execute(select(M.LifeEvent).where(
                M.LifeEvent.user_id == uid))).scalars().all()
            goals = (await db.execute(select(M.LifeGoal).where(
                M.LifeGoal.user_id == uid))).scalars().all()
            mems = (await db.execute(select(M.LifeMemory).where(
                M.LifeMemory.user_id == uid))).scalars().all()
            for ev in evs:
                await delete_event(db, ev)
            for r in recs:
                await db.delete(r)
            for g in goals:
                await db.delete(g)
            for m in mems:
                await db.delete(m)
            await db.commit()
            from backend.services.vector_store import delete_user_data
            try:
                delete_user_data(uid)
            except Exception:
                pass
            return {"ok": True, "deleted": len(recs) + len(evs) + len(goals) + len(mems)}
    return {"ok": False, "error": "unknown type"}


@app.delete("/api/agent/account")
async def agent_delete_account(request: Request):
    """注销账户: 级联删除 SQLite（含 agent 对话）+ Chroma 全量向量"""
    uid = require_uid(request)
    from sqlalchemy import select, delete as sa_delete
    from backend.database.models import (User, DailyRecord, LifeEvent, LifeMemory,
                                         PersonaProfile, InterestTrack, LifeGoal,
                                         Simulation, FutureSelf, ChatMessage, GrowthReport)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user:
            return {"ok": False, "error": "not_found"}
        models_with_uid = [DailyRecord, LifeEvent, LifeMemory, PersonaProfile,
                           InterestTrack, LifeGoal, Simulation, FutureSelf,
                           ChatMessage, GrowthReport, M.AgentChatMessage]
        for model in models_with_uid:
            rows = (await db.execute(select(model).where(model.user_id == uid))).scalars().all()
            for row in rows:
                await db.delete(row)
        await db.delete(user)
        await db.commit()
    from backend.services.vector_store import delete_user_data
    try:
        delete_user_data(uid)
    except Exception:
        pass
    request.session.clear()
    return {"ok": True}


@app.get("/api/agent/records")
async def agent_records(request: Request, type: str = "journal", limit: int = 200, q: str = ""):
    """我的记录查询（侧边栏面板）: journal/events/goals/memories; q=内容搜索; limit 可调大查看全部"""
    uid = require_uid(request)
    from sqlalchemy import select, desc, or_
    from backend.database import models as M
    kw = f"%{q.strip()}%" if q and q.strip() else None
    async with AsyncSessionLocal() as db:
        if type == "journal":
            qq = select(M.DailyRecord).where(M.DailyRecord.user_id == uid)
            if kw:
                qq = qq.where(or_(M.DailyRecord.content.like(kw), M.DailyRecord.mood.like(kw)))
            rows = (await db.execute(qq.order_by(desc(M.DailyRecord.record_date)).limit(limit))).scalars().all()
            return {"records": [{"id": r.id, "date": r.record_date.strftime("%Y-%m-%d") if r.record_date else "",
                                 "mood": r.mood or "", "content": (r.content or "")[:120]} for r in rows]}
        if type == "events":
            qq = select(M.LifeEvent).where(M.LifeEvent.user_id == uid)
            if kw:
                qq = qq.where(or_(M.LifeEvent.title.like(kw), M.LifeEvent.description.like(kw)))
            rows = (await db.execute(qq.order_by(desc(M.LifeEvent.occurred_at)).limit(limit))).scalars().all()
            return {"records": [{"id": e.id, "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
                                 "event_type": e.event_type, "title": e.title,
                                 "content": (e.description or "")[:120]} for e in rows]}
        if type == "goals":
            qq = select(M.LifeGoal).where(M.LifeGoal.user_id == uid)
            if kw:
                qq = qq.where(or_(M.LifeGoal.title.like(kw), M.LifeGoal.description.like(kw)))
            rows = (await db.execute(qq.order_by(desc(M.LifeGoal.updated_at)).limit(limit))).scalars().all()
            return {"records": [{"id": g.id, "date": g.created_at.strftime("%Y-%m-%d") if g.created_at else "",
                                 "status": g.status, "title": g.title,
                                 "content": (g.description or "")[:120]} for g in rows]}
        if type == "memories":
            qq = select(M.LifeMemory).where(M.LifeMemory.user_id == uid)
            if kw:
                qq = qq.where(M.LifeMemory.memory_content.like(kw))
            rows = (await db.execute(qq.order_by(desc(M.LifeMemory.importance_score), desc(M.LifeMemory.created_at)).limit(limit))).scalars().all()
            return {"records": [{"id": m.id, "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
                                 "importance": round(m.importance_score or 0, 2),
                                 "content": (m.memory_content or "")[:120]} for m in rows]}
        return {"records": []}


@app.get("/api/agent/record")
async def agent_record_detail(request: Request, type: str = "journal", id: int = 0):
    """记录详情（含入库时的 AI 分析——同主站展示）"""
    uid = require_uid(request)
    if not id:
        return {"ok": False, "error": "missing id"}
    async with AsyncSessionLocal() as db:
        if type == "journal":
            r = await db.get(M.DailyRecord, id)
            if not r or r.user_id != uid:
                return {"ok": False, "error": "not_found"}
            return {"ok": True, "record": {
                "type": "journal", "date": r.record_date.strftime("%Y-%m-%d") if r.record_date else "",
                "mood": r.mood or "", "content": r.content,
                "analysis": r.ai_analysis or {}}}
        if type == "events":
            e = await db.get(M.LifeEvent, id)
            if not e or e.user_id != uid:
                return {"ok": False, "error": "not_found"}
            return {"ok": True, "record": {
                "type": "event", "date": e.occurred_at.strftime("%Y-%m-%d") if e.occurred_at else "",
                "title": e.title, "content": e.description or "",
                "event_type": e.event_type, "emotion": e.emotion or "",
                "interest_tags": e.interest_tags or [],
                "ai_impact": e.ai_impact or "", "persona_delta": e.persona_delta or {}}}
        if type == "goals":
            g = await db.get(M.LifeGoal, id)
            if not g or g.user_id != uid:
                return {"ok": False, "error": "not_found"}
            # 旧目标无分析 → 惰性补生成并入库（只补一次）
            if not g.ai_gap_analysis:
                try:
                    from backend.agent_tools import analyze_goal_gap
                    g.ai_gap_analysis = await analyze_goal_gap(
                        g.title, g.goal_type, g.description or "", g.importance or 50)
                    await db.commit()
                except Exception:
                    pass
            return {"ok": True, "record": {
                "type": "goal", "title": g.title, "content": g.description or "",
                "goal_type": g.goal_type, "status": g.status,
                "importance": g.importance, "target_year": g.target_year,
                "ai_gap_analysis": g.ai_gap_analysis or ""}}
        if type == "memories":
            m = await db.get(M.LifeMemory, id)
            if not m or m.user_id != uid:
                return {"ok": False, "error": "not_found"}
            return {"ok": True, "record": {
                "type": "memory", "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
                "content": m.memory_content, "importance": round(m.importance_score or 0, 2),
                "source_type": m.source_type}}
        return {"ok": False, "error": "unknown type"}


@app.post("/api/agent/stream")
async def agent_stream(request: Request):
    uid = require_uid(request)
    body = await request.json()
    message = (body.get("message") or "").strip()
    agent = body.get("agent") or "mentor"
    history = body.get("history") or []

    async def gen():
        import backend.agent_engine as elg
        yield _sse({"type": "status", "content": "开始思考"})
        async for ev in elg.stream_agent(user_id=uid, req_message=message,
                                         agent=agent, history=history):
            yield _sse(ev)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


# ── 看板（真实指标 dashboard：StatCards + 图表数据源）──
MOOD_SCORE = {  # 情绪 → 效价（-2..+2），用于情绪趋势线
    "开心": 2, "兴奋": 2, "幸福": 2, "满足": 2, "成就感": 2, "期待": 1, "舒服": 1, "充实": 1,
    "平静": 1, "放松": 1, "感动": 1, "温暖": 1, "一般": 0, "平淡": 0, "疲惫": -1, "没精神": -1,
    "无聊": -1, "纠结": -1, "犹豫": -1, "迷茫": -2, "烦躁": -2, "焦虑": -2, "低落": -2, "emo": -2,
    "有点烦": -2, "难过": -2, "紧张": -1, "压力": -2, "挫败": -2, "孤独": -2, "想家": -1,
}


@app.get("/api/agent/dashboard")
async def agent_dashboard(request: Request):
    uid = require_uid(request)
    import json as _json
    from collections import defaultdict
    from sqlalchemy import select, desc, func
    from backend.services.dashboard_service import get_dashboard_data

    async with AsyncSessionLocal() as db:
        d = await get_dashboard_data(db, uid)
        p = d.get("persona")
        history = (await db.execute(
            select(M.PersonaProfile).where(M.PersonaProfile.user_id == uid)
            .order_by(M.PersonaProfile.version))).scalars().all()
        futures = (await db.execute(
            select(M.FutureSelf).where(M.FutureSelf.user_id == uid)
            .order_by(desc(M.FutureSelf.created_at)).limit(3))).scalars().all()
        # ── 记录时间线（全量按日: date → [count, mood_score]）──
        recs = (await db.execute(
            select(M.DailyRecord.record_date, M.DailyRecord.mood)
            .where(M.DailyRecord.user_id == uid))).all()
        # ── 事件 ──
        evs = (await db.execute(
            select(M.LifeEvent).where(M.LifeEvent.user_id == uid)
            .order_by(M.LifeEvent.occurred_at))).scalars().all()
        # ── 记忆增长（按月累计）──
        mems = (await db.execute(
            select(M.LifeMemory.created_at).where(M.LifeMemory.user_id == uid))).scalars().all()
        # ── agent 对话量 ──
        chat_n = (await db.execute(
            select(func.count()).select_from(M.AgentChatMessage)
            .where(M.AgentChatMessage.user_id == uid))).scalar() or 0

    def _persona_dict(pp):
        if pp is None:
            return None
        return {"version": pp.version, "persona_type": pp.persona_type,
                "confidence": round(pp.confidence or 0, 2),
                "persona_summary": pp.persona_summary or "",
                "ability": pp.ability_profile or {}, "interest": pp.interest_profile or {},
                "value": pp.value_profile or {}, "decision": pp.decision_style or {},
                "behavior": pp.behavior_profile or {}}

    # 记录时间线（按月聚合: 数量 + 平均效价）
    month_rec = defaultdict(lambda: [0, 0, 0])   # ym -> [n, score_sum, n_scored]
    mood_dist = defaultdict(int)
    for rd, mood in recs:
        ym = rd.strftime("%Y-%m") if rd else "?"
        month_rec[ym][0] += 1
        if mood:
            mood_dist[mood] += 1
            sc = MOOD_SCORE.get((mood or "").strip())
            if sc is not None:
                month_rec[ym][1] += sc
                month_rec[ym][2] += 1
    timeline = [{"month": ym, "count": v[0],
                 "mood": round(v[1] / v[2], 2) if v[2] else 0}
                for ym, v in sorted(month_rec.items())]
    mood_top = sorted(mood_dist.items(), key=lambda x: -x[1])[:10]

    # 事件分布 + 时间分布
    events_by_type = defaultdict(int)
    events_by_month = defaultdict(int)
    for e in evs:
        events_by_type[e.event_type] += 1
        if e.occurred_at:
            events_by_month[e.occurred_at.strftime("%Y-%m")] += 1

    # 记忆增长（按月累计）
    mem_month = defaultdict(int)
    for c in mems:
        if c:
            mem_month[c.strftime("%Y-%m")] += 1
    cum, memory_growth = 0, []
    for ym in sorted(set(mem_month) | set(events_by_month) | set(month_rec)):
        cum += mem_month.get(ym, 0)
        memory_growth.append({"month": ym, "total": cum, "new": mem_month.get(ym, 0)})

    # 智能体使用统计（agent_stats.jsonl 为进程级全局记录）
    agent_usage = {"requests": 0, "total_duration": 0, "tool_calls": 0,
                   "failures": 0, "errors": 0, "durations": []}
    try:
        with open(BASE_DIR / "data" / "agent_stats.jsonl", encoding="utf-8") as f:
            for line in f:
                try:
                    r = _json.loads(line)
                except Exception:
                    continue
                agent_usage["requests"] += 1
                agent_usage["total_duration"] += r.get("duration_s") or 0
                agent_usage["tool_calls"] += r.get("tools") or 0
                agent_usage["failures"] += r.get("tool_failures") or 0
                agent_usage["errors"] += 1 if r.get("error") else 0
                agent_usage["durations"].append(round(r.get("duration_s") or 0, 1))
    except Exception:
        pass
    dur = sorted(agent_usage.pop("durations"))
    if dur:
        agent_usage["avg_duration"] = round(sum(dur) / len(dur), 1)
        agent_usage["p95_duration"] = dur[min(len(dur) - 1, int(len(dur) * 0.95))]

    return {
        "me": request.session.get("user", {}),
        "stats": d.get("stats", {}),
        "insight": d.get("insight", ""),
        "interests": d.get("interests", {}),
        "persona": _persona_dict(p),
        "persona_history": [{"version": h.version,
                             "confidence": round(h.confidence or 0, 2),
                             "generated_at": h.generated_at.strftime("%Y-%m-%d") if h.generated_at else ""}
                            for h in history],
        "active_goals": [{"id": g.id, "title": g.title, "goal_type": g.goal_type,
                          "importance": g.importance, "period": g.target_period or "",
                          "status": g.status}
                         for g in d.get("active_goals", [])],
        "futures": [{"id": f.id, "label": f.persona_label, "path_type": f.path_type,
                     "confidence": round(f.confidence or 0.7, 2),
                     "target_year": f.target_year} for f in futures],
        # ── 指标数据 ──
        "timeline": timeline,                       # [{month, count, mood}] 按月
        "mood_dist": mood_top,                      # [[mood, n]] top10
        "events_by_type": dict(events_by_type),
        "events_by_month": dict(sorted(events_by_month.items())),
        "memory_growth": memory_growth,             # [{month, total, new}] 累计
        "memory_total": sum(mem_month.values()),
        "chat_messages": chat_n,
        "agent_usage": agent_usage,
        "competitions": [], "activities": [],
    }


# ── 今日镜像（主动观察: 登录后自动推送, 像 Apple Fitness 的每日摘要）──
DAILY_QUESTIONS = [
    "今天有没有一件事，让你感觉「这是我」的？",
    "有没有一个瞬间，让你觉得未来的你会感谢现在的你？",
    "今天最大的收获是什么？哪怕很小。",
    "如果今天重来一次，你会改变哪一步？",
    "最近有什么让你好奇、却还没行动的东西？",
]


@app.get("/api/agent/daily_mirror")
async def agent_daily_mirror(request: Request):
    uid = require_uid(request)
    import random
    from sqlalchemy import select, func, desc
    from datetime import datetime as _dt, timedelta
    from backend.database import models as M
    from backend.services.ai_filter import deepseek_chat

    since = _dt.utcnow() - timedelta(days=7)
    async with AsyncSessionLocal() as db:
        # 7 天聚合
        journals = (await db.execute(
            select(M.DailyRecord).where(M.DailyRecord.user_id == uid,
                                        M.DailyRecord.record_date >= since)
            .order_by(desc(M.DailyRecord.record_date)))).scalars().all()
        events = (await db.execute(
            select(M.LifeEvent).where(M.LifeEvent.user_id == uid,
                                      M.LifeEvent.occurred_at >= since)
            .order_by(desc(M.LifeEvent.occurred_at)))).scalars().all()
        tracks = (await db.execute(
            select(M.InterestTrack).where(M.InterestTrack.user_id == uid)
            .order_by(desc(M.InterestTrack.tracked_at)).limit(10))).scalars().all()
        persona = (await db.execute(
            select(M.PersonaProfile).where(M.PersonaProfile.user_id == uid,
                                           M.PersonaProfile.is_current == True)
            .limit(1))).scalar_one_or_none()
        user = await db.get(M.User, uid)
        records_total = (await db.execute(
            select(func.count()).select_from(M.DailyRecord)
            .where(M.DailyRecord.user_id == uid))).scalar() or 0

    data = {
        "name": user.real_name or user.username if user else "",
        "journal_count_7d": len(journals), "event_count_7d": len(events),
        "records_total": records_total,
        "recent_journals": [{"date": j.record_date.strftime("%m-%d") if j.record_date else "",
                             "content": (j.content or "")[:60], "mood": j.mood or ""}
                            for j in journals[:5]],
        "recent_events": [{"date": e.occurred_at.strftime("%m-%d") if e.occurred_at else "",
                           "title": e.title, "type": e.event_type} for e in events[:5]],
        "interests": [{"field": t.field, "score": t.score} for t in tracks[:8]],
        "persona_type": persona.persona_type if persona else None,
        "persona_confidence": round((persona.confidence or 0) * 100) if persona else None,
    }

    # LLM 提炼观察（失败则规则化兜底）
    observations = []
    suggestion = ""
    try:
        prompt = (
            "你是用户的个人成长镜像。基于以下 7 天真实数据，输出三段话（每段 ≤60 字，用「第一人称观察」语气，像朋友敏锐地指出）：\n"
            "① 兴趣/关注的变化（如果有）\n"
            "② 行为的变化或规律（记录节奏、事件模式）\n"
            "③ 一个矛盾或值得注意的地方（如果数据不足则说'数据还在积累'）\n"
            "最后给出今天最值得做的一件事（一行，可执行）。\n"
            "语气：像懂他的朋友——敏锐、松弛，可以在不轻浮的前提下带一点俏皮（比如拿他的记录节奏开个轻巧的玩笑）。\n"
            "严禁编造数据，严格基于给定数据。全部用中文。\n\n"
            f"数据：{json.dumps(data, ensure_ascii=False)}")
        reply = await asyncio.to_thread(deepseek_chat,
                                        [{"role": "user", "content": prompt}],
                                        max_tokens=500, temperature=0.5)
        if reply:
            lines = [l.strip() for l in reply.split("\n") if l.strip()]
            for l in lines:
                if l.startswith("今天最值得") or l.startswith("今天可以") or "值得" in l[:12]:
                    suggestion = l
                elif len(observations) < 3 and len(l) < 90:
                    observations.append(l)
    except Exception:
        pass
    if not observations:
        if journals:
            observations.append(f"过去 7 天你留下了 {len(journals)} 条记录，节奏{'稳定' if len(journals) >= 3 else '刚起步'}。")
        else:
            observations.append("过去 7 天还没有记录——镜子需要内容才能成像。")
        if events:
            observations.append(f"出现了 {len(events)} 个事件节点：{events[0].title}。")
        if not suggestion:
            suggestion = "记录一条今天的经历，让镜子开始成像。"

    question = DAILY_QUESTIONS[hash(str(uid) + _dt.now().strftime("%Y-%m-%d")) % len(DAILY_QUESTIONS)]
    return {"name": data["name"], "stats": {"journals_7d": data["journal_count_7d"],
                                            "events_7d": data["event_count_7d"],
                                            "records_total": data["records_total"]},
            "observations": observations, "suggestion": suggestion,
            "daily_question": question}


# ── 静态前端（agent_web/dist, 同源）────────────────────
if (AGENT_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(AGENT_DIST / "assets")), name="agent_assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """SPA fallback: 非 API 路径返回 index.html"""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    fp = AGENT_DIST / full_path if full_path else AGENT_DIST / "index.html"
    if fp.is_file():
        return FileResponse(fp)
    return FileResponse(AGENT_DIST / "index.html")
