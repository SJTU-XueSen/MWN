# -*- coding: utf-8 -*-
"""agent 工具注册表 — 把 ai-camp services 包装为 StructuredTool

- user_id 通过 ContextVar 注入（不污染 LLM 看到的工具 schema）
- DB 工具保持 async 且自开 AsyncSession（aiosqlite 绑定事件循环，禁止进 to_thread）
- Chroma/联网等同步工具由引擎以 asyncio.to_thread 执行
- 全部工具遵守数据铁律：数据不足返回空/错误，不编造
"""
import asyncio, json
from contextvars import ContextVar
from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from pydantic import create_model, Field
from sqlalchemy import select, desc

from backend.config import BASE_DIR
from backend.database.database import AsyncSessionLocal
from backend.database import models as M
from backend.services import (
    ai_filter, ai_matcher, event_service, evidence_service, persona_service,
    report_service, search_service, simulation_service, vector_store,
)

uid_var: ContextVar[int] = ContextVar("agent_uid", default=0)


def _fmt_date(dt):
    return dt.strftime("%Y-%m-%d") if dt else ""


# ── 工具工厂（仿 PhiAgent engine_langgraph._build_tools）─────────────────
def make_tool(name, description, properties, required, impl):
    """impl(user_id, **args) -> dict（同步或异步皆可）"""
    props = properties or {}
    fields = {}
    for pname, pmeta in props.items():
        ptype = pmeta.get("type", "string")
        ann = str
        if ptype == "integer":
            ann = int
        elif ptype == "number":
            ann = float
        elif ptype == "boolean":
            ann = bool
        pdesc = pmeta.get("description", "") or ""
        fields[pname] = (ann, Field(description=pdesc) if pname in (required or [])
                         else Field(default=None, description=pdesc))
    schema = create_model(f"{name}_args", **fields) if fields else None

    async def execute(**kwargs):
        # 所有 impl 均经 _guard 包装为 async; 同步底层（Chroma/联网）在实现内 to_thread
        return await impl(uid_var.get(), **kwargs)

    # 注意: langchain-core 1.5.x 的 from_function 不会自动检测 async func,
    # 必须显式传 coroutine=execute, 否则 ainvoke 走同步路径返回未 await 的 coroutine
    return StructuredTool.from_function(
        func=None, coroutine=execute, name=name, description=description,
        args_schema=schema if schema else None)


def _guard(fn):
    """工具统一兜底：异常返回 {"error": ...}，不中断 agent"""
    async def awrap(uid, **kw):
        try:
            return await fn(uid, **kw)
        except Exception as e:
            return {"error": f"工具执行失败: {str(e)[:200]}"}
    return awrap


# ── 工具实现 ─────────────────────────────────────────────

@_guard
async def _memory_search(uid, **kw):
    query = kw.get("query") or ""
    n = kw.get("n_results") or 8
    if not query:
        return {"error": "缺少检索词"}
    rows = await asyncio.to_thread(vector_store.search, uid, query, n, None)
    if not rows:
        return {"note": "未检索到相关记忆", "results": []}
    return {"results": [{
        "content": r["content"][:300],
        "type": (r.get("metadata") or {}).get("type", ""),
        "distance": round(r.get("distance") or 0, 3),
    } for r in rows]}


@_guard
async def _current_persona(uid, **kw):
    async with AsyncSessionLocal() as db:
        p = await persona_service.get_current_persona(db, uid)
        if not p:
            return {"persona": None, "note": "尚无当前人格画像（数据不足）"}
        return {"persona": {
            "version": p.version, "confidence": round(p.confidence or 0, 2),
            "persona_summary": p.persona_summary,
            "trigger_event": p.trigger_event,
            "generated_at": _fmt_date(p.generated_at),
            "ability_profile": p.ability_profile,
            "interest_profile": p.interest_profile,
            "value_profile": p.value_profile,
            "decision_style": p.decision_style,
            "behavior_profile": p.behavior_profile,
        }}


@_guard
async def _recent_events(uid, **kw):
    limit = kw.get("limit") or 20
    async with AsyncSessionLocal() as db:
        evs = await event_service.get_user_events(db, uid, limit=limit)
        if not evs:
            return {"note": "暂无人生事件记录", "events": []}
        return {"events": [{
            "title": e.title, "event_type": e.event_type, "emotion": e.emotion,
            "occurred_at": _fmt_date(e.occurred_at),
            "ai_impact": (e.ai_impact or "")[:200],
            "persona_delta": e.persona_delta or {},
        } for e in evs]}


@_guard
async def _recent_journals(uid, **kw):
    limit = kw.get("limit") or 20
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(M.DailyRecord).where(M.DailyRecord.user_id == uid)
            .order_by(desc(M.DailyRecord.record_date)).limit(limit))).scalars().all()
        if not rows:
            return {"note": "暂无日记记录", "journals": []}
        return {"journals": [{
            "date": _fmt_date(r.record_date), "mood": r.mood,
            "content": (r.content or "")[:300],
            "ai_analysis": r.ai_analysis or {},
        } for r in rows]}


@_guard
async def _life_goals(uid, **kw):
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(M.LifeGoal).where(M.LifeGoal.user_id == uid,
                                     M.LifeGoal.status.in_(["active", "achieved"]))
            .order_by(desc(M.LifeGoal.updated_at)).limit(15))).scalars().all()
        if not rows:
            return {"note": "暂无人生目标记录", "goals": []}
        return {"goals": [{
            "title": g.title, "goal_type": g.goal_type, "status": g.status,
            "importance": g.importance, "target_year": g.target_year,
            "description": (g.description or "")[:150],
            "ai_gap_analysis": (g.ai_gap_analysis or "")[:200],
        } for g in rows]}


@_guard
async def _interest_tracks(uid, **kw):
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(M.InterestTrack).where(M.InterestTrack.user_id == uid)
            .order_by(desc(M.InterestTrack.score)).limit(15))).scalars().all()
        if not rows:
            return {"note": "暂无兴趣轨迹记录", "tracks": []}
        return {"tracks": [{"field": t.field, "score": t.score,
                            "source": t.source or "", "tracked_at": _fmt_date(t.tracked_at)}
                           for t in rows]}


@_guard
async def _future_paths(uid, **kw):
    async with AsyncSessionLocal() as db:
        selves = (await db.execute(
            select(M.FutureSelf).where(M.FutureSelf.user_id == uid)
            .order_by(desc(M.FutureSelf.created_at)).limit(3))).scalars().all()
        sims = (await db.execute(
            select(M.Simulation).where(M.Simulation.user_id == uid)
            .order_by(desc(M.Simulation.created_at)).limit(2))).scalars().all()
        if not selves and not sims:
            return {"note": "暂无未来路径模拟（可调用 future_simulation 生成）", "paths": []}
        out = {"paths": [{
            "persona_label": s.persona_label, "target_year": s.target_year,
            "path_type": s.path_type, "confidence": round(s.confidence or 0, 2),
            "basis_summary": (s.basis_summary or "")[:200],
            "profile": s.profile or {},
        } for s in selves]}
        if sims:
            out["simulations"] = [{
                "scenario_type": s.scenario_type, "question": s.question,
                "created_at": _fmt_date(s.created_at),
                "output_paths": s.output_paths or {},
            } for s in sims]
        return out


@_guard
async def _growth_report(uid, **kw):
    period_days = kw.get("period_days") or 30
    force = bool(kw.get("force"))
    async with AsyncSessionLocal() as db:
        latest = (await db.execute(
            select(M.GrowthReport).where(M.GrowthReport.user_id == uid)
            .order_by(desc(M.GrowthReport.generated_at)).limit(1))).scalar_one_or_none()
        if latest and not force:
            return {"report": {
                "title": latest.title, "period": f"{_fmt_date(latest.period_start)} ~ {_fmt_date(latest.period_end)}",
                "generated_at": _fmt_date(latest.generated_at), "content": latest.content}}
        end = datetime.utcnow()
        start = end - timedelta(days=period_days)
        rep = await report_service.generate_report(
            db, uid, f"成长报告（近{period_days}天）", start, end)
        return {"report": {
            "title": rep.title, "period": f"{_fmt_date(start)} ~ {_fmt_date(end)}",
            "generated_at": _fmt_date(rep.generated_at), "content": rep.content}}


@_guard
async def _evidence_chain(uid, **kw):
    query = kw.get("query") or ""
    limit = kw.get("limit") or 8
    async with AsyncSessionLocal() as db:
        evs = await evidence_service.build_evidence(db, uid, query=query, limit=limit)
        if not evs:
            return {"note": "未找到相关证据（数据不足）", "evidence": []}
        return {"evidence": evs}


@_guard
async def _future_simulation(uid, **kw):
    scenario = kw.get("scenario") or "further_study"
    question = kw.get("question") or "请基于我的真实记录推演未来路径"
    async with AsyncSessionLocal() as db:
        sim = await simulation_service.run_simulation(db, uid, scenario, question)
        out = {"scenario_type": sim.scenario_type, "question": sim.question,
               "created_at": _fmt_date(sim.created_at), "output_paths": sim.output_paths or {}}
        # 附带本次生成的未来人格
        selves = (await db.execute(
            select(M.FutureSelf).where(M.FutureSelf.simulation_id == sim.id)
            .order_by(desc(M.FutureSelf.created_at)))).scalars().all()
        out["future_selves"] = [{
            "persona_label": s.persona_label, "target_year": s.target_year,
            "path_type": s.path_type, "confidence": round(s.confidence or 0, 2),
            "basis_summary": (s.basis_summary or "")[:200],
        } for s in selves]
        return out


@_guard
async def _activity_search(uid, **kw):
    query = kw.get("query") or ""
    if not query:
        return {"error": "缺少检索词"}
    res = await ai_matcher.ai_search(query)
    recs = res.get("recommendations") or []
    if not recs:
        return {"note": "未找到匹配活动", "recommendations": []}
    return {"recommendations": recs[:8],
            "campusCount": res.get("campusCount", 0), "webCount": res.get("webCount", 0)}


@_guard
async def _web_search(uid, **kw):
    """联网检索（合一）: 来源链接列表 + 背景摘要文本一次返回"""
    query = kw.get("query") or ""
    n = kw.get("max_results") or 5
    if not query:
        return {"error": "缺少检索词"}
    rows = await asyncio.to_thread(ai_filter.web_search, query, n)
    background = ""
    try:
        background = await search_service.extract_and_search(query)
    except Exception:
        pass
    out = {"results": rows}
    if background:
        out["background"] = background[:600]
    if not rows and not background:
        out["note"] = "联网无结果"
    return out


# ── 中国古文学板块: 古语回响（知识库匹配心境）────────────────

# 心境关键词 → 标签映射（句子 tags 与之匹配打分）
TAG_KEYWORDS = {
    "迷茫": ["迷茫", "方向", "不知道", "没方向", "困惑", "犹豫", "选择", "何去何从", "看不清"],
    "焦虑": ["焦虑", "紧张", "担心", "压力", "着急", "不安", "烦", "慌", "内耗", "紧绷"],
    "低谷": ["低谷", "失败", "挫败", "挫折", "跌倒", "没信心", "灰心", "难过", "失落", "沮丧", "颓", "沉", "不顺"],
    "坚持": ["坚持", "放弃", "继续", "撑", "咬牙", "坚持不下去", "想放弃"],
    "行动": ["行动", "做", "开始", "动手", "拖延", "执行", "落实", "实践", "启动"],
    "学习": ["学习", "读书", "知识", "考试", "学", "练", "进步", "复习"],
    "独处": ["孤独", "一个人", "独处", "寂寞", "没人", "孤"],
    "成长": ["成长", "改变", "提升", "变好", "进化", "突破"],
    "淡泊": ["淡", "放下", "看开", "无所谓", "不计较", "名利"],
    "自信": ["自信", "相信", "肯定", "价值", "自卑", "否定自己"],
    "勇气": ["勇气", "怕", "害怕", "敢", "不敢", "胆怯"],
    "耐心": ["耐心", "慢慢", "急", "快不了", "长期", "等"],
    "志向": ["志向", "梦想", "目标", "理想", "抱负", "想成为"],
    "自省": ["反思", "自省", "错", "检讨", "哪里不好", "后悔"],
    "当下": ["当下", "现在", "此刻", "眼前", "珍惜"],
    "格局": ["格局", "眼光", "胸怀", "更远", "长远"],
    "希望": ["希望", "未来", "转机", "还有机会", "会好吗"],
    "定力": ["静", "定", "浮躁", "心乱", "安静"],
    "坚韧": ["坚", "硬", "扛", "熬", "顶住", "不容易"],
}
QUOTES_FILE = BASE_DIR / "data" / "ancient_quotes.json"
_quotes_cache = None


def _load_quotes():
    global _quotes_cache
    if _quotes_cache is None:
        try:
            with open(QUOTES_FILE, "r", encoding="utf-8") as f:
                _quotes_cache = json.load(f)
        except Exception:
            _quotes_cache = []
    return _quotes_cache


def _match_quotes(situation):
    """规则匹配: 心境描述 → 标签命中 → 句子打分, 返回 top3"""
    quotes = _load_quotes()
    hit_tags = set()
    for tag, kws in TAG_KEYWORDS.items():
        if any(k in situation for k in kws):
            hit_tags.add(tag)
    scored = []
    for q in quotes:
        qtags = set(q.get("tags", []))
        overlap = qtags & hit_tags
        if not overlap:
            continue
        scored.append((len(overlap) + (0.5 if q.get("author") in situation else 0), q))
    scored.sort(key=lambda x: -x[0])
    return [q for _, q in scored[:3]]


@_guard
async def _ancient_wisdom(uid, **kw):
    """古语回响: 从古籍名句库挑一句契合用户当前心境/境遇的话（正向）+ 双重解释"""
    situation = (kw.get("situation") or "").strip()
    if not situation:
        # 用户没说心境 → 从最近记录自动推断（让"给我古语"直接给合适的）
        try:
            async with AsyncSessionLocal() as db:
                recent = (await db.execute(
                    select(M.DailyRecord).where(M.DailyRecord.user_id == uid)
                    .order_by(desc(M.DailyRecord.record_date)).limit(3))).scalars().all()
                evs = (await db.execute(
                    select(M.LifeEvent).where(M.LifeEvent.user_id == uid)
                    .order_by(desc(M.LifeEvent.occurred_at)).limit(3))).scalars().all()
            inferred = " ".join((r.content or "")[:60] for r in recent) + " " + \
                       " ".join(e.title for e in evs)
            situation = inferred.strip()[:200] or "成长 前进"
        except Exception:
            situation = "成长 前进"
        inferred_flag = True
    else:
        inferred_flag = False
    candidates = _match_quotes(situation)
    if not candidates:
        # 无标签命中 → 按"成长/希望"兜底 + 原文关键词宽松匹配
        candidates = [q for q in _load_quotes() if "成长" in q.get("tags", [])][:3]
    if not candidates:
        return {"error": "知识库暂无匹配"}

    chosen = candidates[0]
    match_reason = ""
    try:
        from backend.services.ai_filter import deepseek_chat
        cand_text = "\n".join(
            f"{i + 1}. {q['text']}（{q['source']} {q['author']}）释义：{q['meaning']}"
            for i, q in enumerate(candidates[:3]))
        prompt = (
            f"用户当前的心境/处境：「{situation}」\n以下三句古语，选最契合的一句，并写一句"
            f"「为什么与你的当下匹配」（≤50字，温暖、点到即止，不评判）：\n{cand_text}")
        reply = await asyncio.to_thread(deepseek_chat,
                                        [{"role": "user", "content": prompt}],
                                        max_tokens=300, temperature=0.4)
        if reply:
            for i, q in enumerate(candidates[:3]):
                if q["text"][:6] in reply:
                    chosen = q
                    break
            # 提取理由（取回复中"匹配/因为/这句"之后的内容, 简化: 整句兜底）
            match_reason = reply.replace(chosen["text"], "").strip()[:100]
    except Exception:
        pass
    if not match_reason:
        hit_tags = [t for t, kws in TAG_KEYWORDS.items()
                    if any(k in situation for k in kws)]
        if inferred_flag:
            match_reason = "我翻了翻你最近的记录，觉得这句正适合现在的你。"
        else:
            match_reason = (f"这句正契合你当下的心境——"
                            + ("、".join(hit_tags[:2]) + "的时刻，需要这样一句定住心的话。" if hit_tags
                               else "它说的，正是你现在正在经历的状态。"))
    return {"quote": {"text": chosen["text"], "source": chosen["source"],
                      "author": chosen["author"], "meaning": chosen["meaning"]},
            "match_reason": match_reason}


# ── 写操作工具（agent 内完成主站全部功能）───────────────────

@_guard
async def _record_entry(uid, **kw):
    """统一记录入口（type 三选一, 一次调用只记录一条——避免重复写入）:
    - journal 日常/流水（心情、琐事、过程）→ 写日记 + AI 分析 + 自动提炼记忆
    - event 重要节点/成就/转折（比赛、面试、重要决定）→ 记录人生事件 + AI 影响分析 + 自动提炼记忆
    - memory 重要感悟/洞见（值得长期记住的一句话、一个领悟）→ 直接保存为记忆
    判断标准: 有明确标题的事件用 event; 日常叙述用 journal; 抽象感悟用 memory。"""
    type_ = (kw.get("type") or "journal").strip().lower()
    content = (kw.get("content") or "").strip()
    title = (kw.get("title") or "").strip()
    if not content and not title:
        return {"error": "记录内容不能为空"}
    if type_ == "event":
        if not title:
            title = content[:30]
        description = content
        event_type = (kw.get("event_type") or "study").strip()
        occurred_at = kw.get("occurred_at") or datetime.utcnow().strftime("%Y-%m-%d")
        try:
            dt = datetime.strptime(str(occurred_at)[:10], "%Y-%m-%d")
        except ValueError:
            dt = datetime.utcnow()
        async with AsyncSessionLocal() as db:
            ev = await event_service.create_event(db, uid, title, description,
                                                  event_type, dt)
            return {"record_type": "event", "event_id": ev.id,
                    "event_type": ev.event_type, "emotion": ev.emotion,
                    "ai_impact": (ev.ai_impact or "")[:200],
                    "persona_delta": ev.persona_delta or {},
                    "note": "已记录事件并完成 AI 分析"}
    if type_ == "memory":
        importance = kw.get("importance") or 0.5
        async with AsyncSessionLocal() as db:
            m = M.LifeMemory(user_id=uid, source_type="ai_memory",
                             memory_content=content, importance_score=float(importance),
                             persona_impact={})
            db.add(m)
            await db.commit()
            await db.refresh(m)
            vector_store.add_ai_memory(m.id, uid, content)
            return {"record_type": "memory", "memory_id": m.id,
                    "importance": float(importance), "note": "记忆已保存"}
    # journal（默认）
    mood = (kw.get("mood") or "").strip()
    async with AsyncSessionLocal() as db:
        rec = M.DailyRecord(user_id=uid, content=content, mood=mood or None,
                            tags=[], record_date=datetime.utcnow())
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        from backend.services import memory_service
        mem = await memory_service.process_daily_record(db, rec, uid)
        return {"record_type": "journal", "journal_id": rec.id,
                "date": _fmt_date(rec.record_date),
                "memory_created": bool(mem),
                "note": "已记录并完成 AI 分析" + ("，提炼出生命记忆" if mem else "")}


async def analyze_goal_gap(title, goal_type="other", description="", importance=50):
    """AI 差距分析（LLM → 模板回退, 同主站 goals/analyze）——创建与详情补分析共用"""
    analysis = None
    try:
        from backend.services.ai_filter import deepseek_chat
        prompt = (f"你是目标分析助手。根据以下目标生成一段简洁的差距分析和3条具体建议步骤。\n"
                  f"目标：{title}\n类型：{goal_type}\n描述：{description or '无'}\n重要度：{importance}%\n"
                  f"格式要求：先一句话概括差距，再列3条具体可执行的建议步骤（每条用\"1. 2. 3.\"开头）。不超过200字。")
        raw = await asyncio.to_thread(deepseek_chat,
                                      [{"role": "user", "content": prompt}],
                                      max_tokens=400, temperature=0.5)
        if raw:
            analysis = raw.strip()
    except Exception:
        analysis = None
    if not analysis:
        templates = {
            "study": f"差距分析：尚未建立系统化的{title}学习路径与知识输出习惯\n建议步骤：\n1. 每日投入固定时间学习{title}核心内容并做笔记\n2. 每周进行一次知识复盘，检验学习效果\n3. 通过实际项目或教学输出检验学习成果",
            "career": f"差距分析：{title}方向的职业准备还不够系统\n建议步骤：\n1. 梳理该方向所需的技能树，逐项评估自己的水平\n2. 寻找实习或项目机会积累实际经验\n3. 每季度更新一次自己的职业规划",
            "skill": f"差距分析：{title}技能尚未形成稳定的练习节奏\n建议步骤：\n1. 每周安排固定练习时段并记录进展\n2. 寻找可量化的练习反馈（作品/测试/复盘）\n3. 定期向该领域的实践者请教",
            "lifestyle": f"差距分析：{title}尚未融入日常节奏\n建议步骤：\n1. 从小习惯开始，降低启动门槛\n2. 用日历固定时间，减少决策消耗\n3. 每周复盘一次执行情况",
        }
        analysis = templates.get(goal_type) or (
            f"差距分析：{title}还需要具体的行动计划\n建议步骤：\n1. 把目标拆成本周可完成的第一个小任务\n2. 记录每天与目标相关的行动\n3. 每周回顾进度并调整方法")
        if description and len(description) > 5:
            analysis = analysis.replace("尚未建立", f"基于你的描述「{description[:30]}」，尚未建立")
    return analysis


@_guard
async def _create_goal(uid, **kw):
    title = (kw.get("title") or "").strip()
    goal_type = (kw.get("goal_type") or "other").strip()
    description = (kw.get("description") or "").strip()
    importance = kw.get("importance") or 50
    target_year = kw.get("target_year")
    if not title:
        return {"error": "目标标题不能为空"}
    if goal_type not in M.GOAL_TYPES:
        goal_type = "other"
    async with AsyncSessionLocal() as db:
        g = M.LifeGoal(user_id=uid, title=title, goal_type=goal_type,
                       description=description or None, importance=int(importance),
                       target_year=int(target_year) if target_year else None,
                       status="active")
        db.add(g)
        await db.commit()
        await db.refresh(g)
        analysis = await analyze_goal_gap(title, goal_type, description, importance)
        g.ai_gap_analysis = analysis
        await db.commit()
        return {"goal_id": g.id, "title": g.title, "goal_type": g.goal_type,
                "status": g.status, "ai_gap_analysis": analysis[:200],
                "note": "目标已创建并完成差距分析"}


@_guard
async def _update_goal(uid, **kw):
    goal_id = kw.get("goal_id")
    status = (kw.get("status") or "").strip()
    if not goal_id:
        return {"error": "缺少 goal_id"}
    if status not in ("active", "achieved", "abandoned"):
        return {"error": "status 需为 active/achieved/abandoned"}
    async with AsyncSessionLocal() as db:
        g = (await db.execute(
            select(M.LifeGoal).where(M.LifeGoal.id == int(goal_id),
                                     M.LifeGoal.user_id == uid))).scalar_one_or_none()
        if not g:
            return {"error": "目标不存在"}
        g.status = status
        await db.commit()
        return {"goal_id": g.id, "title": g.title, "status": status, "note": "目标状态已更新"}


@_guard
async def _regenerate_persona(uid, **kw):
    """重新生成/刷新当前人格画像（基于全部真实数据）"""
    async with AsyncSessionLocal() as db:
        p = await persona_service.generate_persona(db, uid)
        return {"persona_id": p.id, "version": p.version,
                "persona_type": p.persona_type, "confidence": round(p.confidence or 0, 2),
                "persona_summary": (p.persona_summary or "")[:200],
                "note": "人格画像已刷新"}


@_guard
async def _create_task(uid, **kw):
    """AI 拆解团队任务并创建（自动选用用户所在战队）"""
    title = (kw.get("title") or "").strip()
    description = (kw.get("description") or "").strip()
    if not title:
        return {"error": "任务标题不能为空"}
    async with AsyncSessionLocal() as db:
        member = (await db.execute(
            select(M.TeamMember).where(M.TeamMember.user_id == uid))).scalars().first()
        if not member:
            return {"error": "你尚未加入任何战队，无法创建团队任务"}
        roles = await asyncio.to_thread(ai_filter.breakdown_task, title, description, [])
        t = M.TeamTask(team_id=member.team_id, title=title, description=description or "",
                       required_roles=roles or [], created_by=uid, status="recruiting")
        db.add(t)
        await db.commit()
        await db.refresh(t)
        return {"task_id": t.id, "team_id": t.team_id, "roles": roles or [],
                "note": "任务已创建并完成角色拆解"}


@_guard
async def _future_chat(uid, **kw):
    """与未来的我对话（基于未来路径人格 + 记忆 RAG + 最近事件）——对话记录存主站 chat_messages 表"""
    message = (kw.get("message") or "").strip()
    if not message:
        return {"error": "消息不能为空"}
    from backend.services.ai_filter import deepseek_chat
    async with AsyncSessionLocal() as db:
        future = (await db.execute(
            select(M.FutureSelf).where(M.FutureSelf.user_id == uid)
            .order_by(desc(M.FutureSelf.created_at)).limit(1))).scalar_one_or_none()
        if not future:
            return {"error": "尚无未来路径模拟，请先让 agent 做一次人生模拟（future_simulation）"}
        persona = (await db.execute(
            select(M.PersonaProfile).where(M.PersonaProfile.user_id == uid,
                                           M.PersonaProfile.is_current == True)
            .limit(1))).scalar_one_or_none()
        # 上下文: 未来人格 + 当前人格 + 记忆 RAG + 最近事件
        path = future.profile or {}
        path_text = (f"未来标签：{future.persona_label}\n路径描述：{path.get('description', '')}\n"
                     f"人格倾向：{json.dumps(path.get('persona_shift', path.get('personality_traits', {})), ensure_ascii=False)}\n"
                     f"置信度：{int((future.confidence or 0.7) * 100)}%\n推导依据：{future.basis_summary or ''}")
        persona_text = ""
        if persona:
            persona_text = (f"当前人格：{persona.persona_type}\n"
                            f"概述：{persona.persona_summary or ''}")
        mem_text = ""
        try:
            seen = set()
            mems = []
            for q in [persona.persona_type if persona else "人生经历", path.get("description", "")[:100], "成长 转折 选择"]:
                for r in await asyncio.to_thread(vector_store.search, uid, q, 6, None):
                    txt = r.get("content", "")[:150] if isinstance(r, dict) else str(r)[:150]
                    if txt and txt not in seen:
                        seen.add(txt)
                        mems.append(txt)
            if mems:
                mem_text = "用户的真实记忆：\n" + "\n".join(f"- {m}" for m in mems[:15])
        except Exception:
            pass
        events = (await db.execute(
            select(M.LifeEvent).where(M.LifeEvent.user_id == uid)
            .order_by(desc(M.LifeEvent.occurred_at)).limit(5))).scalars().all()
        events_text = "\n".join(f"- {e.occurred_at.strftime('%Y/%m') if e.occurred_at else '?'} {e.title}"
                                for e in events)
        system = (
            f"你是用户未来某个版本的自己（{future.persona_label}，置信度 {int((future.confidence or 0.7) * 100)}%）。\n"
            f"{path_text}\n{persona_text}\n{mem_text}\n最近经历：\n{events_text}\n\n"
            "以'未来的我'第一人称回答用户，语气温暖、有洞察，基于上述真实材料推演，严禁编造用户未经历的事件。"
            "所有输出使用中文。")
        reply = await asyncio.to_thread(deepseek_chat,
                                        [{"role": "system", "content": system},
                                         {"role": "user", "content": message}],
                                        max_tokens=1200, temperature=0.8)
        reply = (reply or "").strip() or "（未能生成回复）"
        # 存主站 chat_messages 表（future_self_id 关联, 主站"未来对话"页可见）
        user_msg = M.ChatMessage(user_id=uid, future_self_id=future.id, role="user", content=message)
        ai_msg = M.ChatMessage(user_id=uid, future_self_id=future.id, role="assistant", content=reply)
        db.add_all([user_msg, ai_msg])
        await db.commit()
        return {"future_label": future.persona_label, "reply": reply[:2000],
                "saved": True, "note": "对话已存入主站未来对话记录"}


@_guard
async def _team_context(uid, **kw):
    async with AsyncSessionLocal() as db:
        members = (await db.execute(
            select(M.TeamMember).where(M.TeamMember.user_id == uid))).scalars().all()
        if not members:
            return {"note": "你尚未加入任何战队", "teams": []}
        out = []
        for m in members:
            team = await db.get(M.Team, m.team_id)
            if not team:
                continue
            tasks = (await db.execute(
                select(M.TeamTask).where(M.TeamTask.team_id == team.id)
                .order_by(desc(M.TeamTask.created_at)).limit(8))).scalars().all()
            my_assigns = (await db.execute(
                select(M.TaskAssignment).where(M.TaskAssignment.user_id == uid))).scalars().all()
            out.append({
                "team": {"name": team.name, "slogan": team.slogan,
                         "status": team.status, "description": (team.description or "")[:150]},
                "my_role": m.role,
                "tasks": [{"title": t.title, "status": t.status,
                           "required_roles": t.required_roles or [],
                           "deadline": _fmt_date(t.deadline),
                           "description": (t.description or "")[:150]} for t in tasks],
                "my_assignments": [{"task_id": a.task_id, "role": a.role, "status": a.status,
                                    "match_score": round(a.match_score or 0, 1)} for a in my_assigns],
            })
        return {"teams": out}


# ── 注册表（工具名 → 定义）────────────────────────────
TOOL_DEFS = {
    "memory_search": ("记忆检索", {"query": {"type": "string", "description": "检索主题（用户的经历/事件/情绪关键词）"},
                                  "n_results": {"type": "integer", "description": "返回条数"}},
                      ["query"], _memory_search),
    "current_persona": ("当前人格画像", {}, [], _current_persona),
    "recent_events": ("最近人生事件", {"limit": {"type": "integer", "description": "返回条数（默认20）"}},
                      [], _recent_events),
    "recent_journals": ("最近日记", {"limit": {"type": "integer", "description": "返回条数（默认20）"}},
                        [], _recent_journals),
    "life_goals": ("人生目标", {}, [], _life_goals),
    "interest_tracks": ("兴趣轨迹", {}, [], _interest_tracks),
    "future_paths": ("未来路径", {}, [], _future_paths),
    "growth_report": ("成长报告", {"period_days": {"type": "integer", "description": "统计周期天数（默认30）"},
                                  "force": {"type": "boolean", "description": "true 强制重新生成（较慢）"}},
                      [], _growth_report),
    "evidence_chain": ("星图证据", {"query": {"type": "string", "description": "证据主题"}},
                       [], _evidence_chain),
    "future_simulation": ("模拟未来", {"scenario": {"type": "string", "description": "情景（further_study读研/work就业/self_dev自我提升等）"},
                                       "question": {"type": "string", "description": "推演问题"}},
                          [], _future_simulation),
    "activity_search": ("活动检索", {"query": {"type": "string", "description": "活动/比赛需求描述"}},
                        ["query"], _activity_search),
    "web_search": ("联网检索", {"query": {"type": "string", "description": "搜索主题（返回来源链接 + 背景摘要）"},
                                "max_results": {"type": "integer", "description": "返回条数（默认5）"}},
                   ["query"], _web_search),
    "team_context": ("团队任务", {}, [], _team_context),
    "ancient_wisdom": ("古语回响", {"situation": {"type": "string", "description": "用户当前的心境/处境描述（迷茫、焦虑、低谷、坚持、成长等）；不确定可留空"}},
                       [], _ancient_wisdom,
                       "用户索要古语/名言/古人智慧/心灵鸡汤/鼓励安慰的话，或流露心境时，**必须调用本工具**从知识库取句——"
                       "禁止凭记忆直接引用（库里的话才带出处与释义）。situation 传用户当前心境/处境；用户没说清楚时从对话上下文推断，"
                       "实在没有就用空串。"),
    # ── 写操作 ──
    "record_entry": ("记录一条",
                     {"type": {"type": "string", "description": "类型：journal 日常流水（默认）/ event 重要节点（比赛、面试、决定）/ memory 重要感悟"},
                      "content": {"type": "string", "description": "内容（日常叙述 / 事件描述 / 感悟）"},
                      "title": {"type": "string", "description": "事件标题（type=event 时必填）"},
                      "mood": {"type": "string", "description": "心情（type=journal 可选）"},
                      "event_type": {"type": "string", "description": "事件类型（study/academic/competition/activity/social/emotion/health/family/other，type=event 可选）"},
                      "occurred_at": {"type": "string", "description": "发生日期 YYYY-MM-DD（type=event 可选，默认今天）"},
                      "importance": {"type": "number", "description": "重要度 0-1（type=memory 可选，默认0.5）"}},
                      [], _record_entry,
                     "用户明确要求记录，或以「今天/昨天/刚才」开头描述具体经历/心情，或分享重要事件（比赛/决定/转折），或回答每日一问时——**必须调用本工具记录**。"
                     "type 选择：journal=日常流水（做了什么/心情）；event=重要节点（有标题感、值得写进履历：比赛/面试/决定）；memory=抽象感悟（领悟/一句话）。"
                     "拿不准用 journal；同一件事只记录一次。用户只是提问/求助/泛泛观点讨论时**不要**调用。"),
    "create_goal": ("创建目标", {"title": {"type": "string", "description": "目标标题"},
                                 "goal_type": {"type": "string", "description": "类型（career/study/skill/lifestyle/relationship/other）"},
                                 "description": {"type": "string", "description": "目标描述"},
                                 "target_year": {"type": "integer", "description": "目标年份（可选）"},
                                 "importance": {"type": "integer", "description": "重要度 1-100（默认50）"}},
                    ["title"], _create_goal),
    "update_goal": ("更新目标", {"goal_id": {"type": "integer", "description": "目标 ID"},
                                 "status": {"type": "string", "description": "新状态 active/achieved/abandoned"}},
                    ["goal_id", "status"], _update_goal),
    "regenerate_persona": ("刷新人格画像", {}, [], _regenerate_persona),
    "create_task": ("创建团队任务", {"title": {"type": "string", "description": "任务标题"},
                                    "description": {"type": "string", "description": "任务描述"}},
                    ["title"], _create_task),
    "future_chat": ("未来对话", {"message": {"type": "string", "description": "对未来的我说的话"}},
                    ["message"], _future_chat),
}

# 工具中文标签（前端 ToolCard 显示）
TOOL_LABELS = {name: desc[0] for name, desc in TOOL_DEFS.items()}

# 构建 StructuredTool 缓存（每个工具一个实例, 惰性创建）
_tools_cache = {}


def get_agent_tools(agent_key):
    """按 agent 注册表返回工具集（按名过滤 + 缓存）"""
    from backend.agent_prompts import AGENTS
    if agent_key in _tools_cache:
        return _tools_cache[agent_key]
    names = AGENTS.get(agent_key, {}).get("tools", [])
    tools = []
    for n in names:
        if n not in TOOL_DEFS:
            continue
        defn = TOOL_DEFS[n]
        if len(defn) >= 5:
            label, props, req, impl, desc_override = defn
        else:
            label, props, req, impl = defn
            desc_override = None
        tools.append(make_tool(n, desc_override or label, props, req, impl))
    _tools_cache[agent_key] = tools
    return tools
