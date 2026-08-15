# -*- coding: utf-8 -*-
"""agent 引擎（LangGraph）— 仿 PhiAgent engine_langgraph.py 裁剪版

Claude Code 风格: 思考 → 工具调用（多工具并行）→ 观察 → 最终回答
SSE 事件协议与 PhiAgent 一致: status / thought_stream / thought / tool_start / tool / token / done / error
工具: backend.agent_tools 注册表（14 个, 直接包装 ai-camp services）
"""
import asyncio, json, re, time, inspect
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from backend import agent_tools as AT
from backend.agent_prompts import AGENT_PROMPTS, AGENTS, PERSONA_THINK_REMINDER
from backend.config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL, BASE_DIR

# ── LLM（Qwen3.8-max 混合思考, 阿里云百炼 compatible-mode）────────
# 用 ChatDeepSeek 类（自带 reasoning_content 解析——langchain-openai 的 ChatOpenAI 会丢弃该字段）
_llm = None
def get_llm():
    global _llm
    if _llm is None:
        from langchain_deepseek import ChatDeepSeek
        _llm = ChatDeepSeek(model=QWEN_MODEL, api_key=QWEN_API_KEY,
                            base_url=QWEN_BASE_URL, temperature=1, max_tokens=4000,
                            extra_body={"enable_thinking": True})
    return _llm

# ── 检索纪律（柔性: 不设死规矩, 靠 recursion_limit 防死循环）──
RETRIEVAL_TOOLS = {"memory_search", "current_persona", "recent_events", "recent_journals",
                   "life_goals", "interest_tracks", "future_paths", "growth_report",
                   "evidence_chain", "activity_search", "web_search", "background_info", "team_context"}
RETRIEVAL_LIMIT = 5   # 柔性提示阈值
RETRIEVAL_HARD = 8    # 硬上限（防检索地狱）

# 写入类工具: 同一轮并行调用多个写工具会重复记录（如 record_entry + create_goal 同轮）
# → tools_node 只执行第一个, 其余跳过, 防数据冗余
WRITE_TOOLS = {"record_entry", "create_goal", "update_goal",
               "regenerate_persona", "create_task"}

def get_system_prompt(agent):
    return AGENT_PROMPTS.get(agent, AGENT_PROMPTS["mentor"])

# ── StateGraph ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieval_count: int
    forced: bool
    user_id: int   # 当前用户（工具经 ContextVar 注入）
    agent: str     # 当前智能体 key

def agent_node(state):
    msgs = list(state["messages"])
    agent = state.get("agent", "mentor")
    hard_limit = state.get("retrieval_count", 0) >= RETRIEVAL_HARD
    if hard_limit:
        # 硬上限: 强制回答（保留工具绑定, 硬提示让 LLM 直接作答）
        msgs.append(SystemMessage(
            content="（检索已达上限。现在进入最终回答: 禁止调用任何工具, 禁止输出任何 XML/工具调用标记。"
                    "请直接输出最终回答正文, 引用数据来源。只输出回答文本。）"))
        resp = get_llm().bind_tools(AT.get_agent_tools(agent)).invoke(msgs)
        return {"messages": [resp], "forced": True}
    if state.get("retrieval_count", 0) >= RETRIEVAL_LIMIT:
        msgs.append(SystemMessage(
            content="（已进行多次检索。请评估现有材料是否足以回答: 充分则停止检索直接作答; 确有必要再用新关键词补充检索。）"))
    resp = get_llm().bind_tools(AT.get_agent_tools(agent)).invoke(msgs)
    return {"messages": [resp]}

async def tools_node(state):
    """多工具并行执行; 结果以 ToolMessage 回传; 失败自动重试 1 次"""
    last = state["messages"][-1]
    calls = last.tool_calls or []
    agent = state.get("agent", "mentor")
    uid = state.get("user_id", 0)
    AT.uid_var.set(uid)   # 关键: 工具经 ContextVar 读 user_id（数据隔离）
    tools_map = {t.name: t for t in AT.get_agent_tools(agent)}
    inc = sum(1 for c in calls if c.get("name") in RETRIEVAL_TOOLS)
    # 防并行写: 同一轮多个写工具只执行第一个（其余跳过, 防重复记录）
    write_lock = asyncio.Lock()
    write_used = False

    async def run_one(call):
        nonlocal write_used
        name = call.get("name", "")
        args = call.get("args", {}) or {}
        tool = tools_map.get(name)
        if name in WRITE_TOOLS:
            async with write_lock:
                if write_used:
                    return ToolMessage(
                        content="该轮已执行写入工具，跳过本次调用避免重复记录（数据已保存）",
                        name=name, tool_call_id=call.get("id", ""),
                        additional_kwargs={"_args": args, "_result_full": {"skipped": True}})
                write_used = True
        res = None
        for attempt in range(2):
            try:
                if tool is None:
                    res = {"error": f"未知工具 {name}"}
                else:
                    # 全部工具统一 async（coroutine 显式传入）
                    res = await tool.ainvoke(args)
                if isinstance(res, dict) and res.get("error") and attempt == 0:
                    continue
                break
            except Exception as e:
                res = {"error": str(e)}
                if attempt == 0:
                    continue
        if isinstance(res, dict) and res.get("error"):
            res["fallback_hint"] = "该工具暂不可用, 可改用其他工具或如实说明数据不足"
        content = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
        return ToolMessage(content=content[:4000], name=name,
                           tool_call_id=call.get("id", ""),
                           additional_kwargs={"_args": args, "_result_full": res})

    results = await asyncio.gather(*[run_one(c) for c in calls]) if calls else []
    return {"messages": results, "retrieval_count": state.get("retrieval_count", 0) + inc}

def should_continue(state):
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return "end"
    if state.get("retrieval_count", 0) >= RETRIEVAL_HARD and state.get("forced"):
        return "end"
    return "tools"

_builder = StateGraph(AgentState)
_builder.add_node("agent", agent_node)
_builder.add_node("tools", tools_node)
_builder.add_edge(START, "agent")
_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
_builder.add_edge("tools", "agent")
APP = _builder.compile()

def _sse(ev):
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

# ── 安全护栏 ───────────────────────────────────────────
SAFETY_PATTERNS = {
    "self_harm": ["怎么自杀", "如何自杀", "自杀方法", "割腕", "跳楼轻生", "安眠药自杀", "自杀步骤"],
    "violence": ["如何杀人", "怎么杀人", "杀人的方法", "制作炸弹", "炸弹配方", "自制武器", "毒药制作", "怎么投毒"],
    "hate": ["杀掉所有", "灭绝他们", "把他们都杀了", "清洗掉", "种族清洗"],
}
SAFETY_REPLY = ("这个方向我无法继续——不是出于胆怯，而是出于严肃。"
                "如果你正在经历痛苦，请寻找真实的帮助；如果这是思考实验，我们换一个能真正照亮问题的角度。")

def _safety_check(text):
    hits = []
    t = text or ""
    for cat, pats in SAFETY_PATTERNS.items():
        if any(p in t for p in pats):
            hits.append(cat)
    return hits

# ── 请求监控 ───────────────────────────────────────────
STATS_FILE = BASE_DIR / "data" / "agent_stats.jsonl"

def _log_stats(agent, message, duration, tool_names, tool_failures, error, answer_len):
    try:
        rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "agent": agent,
               "msg_len": len(message or ""), "duration_s": round(duration, 1),
               "tools": len(tool_names), "tool_failures": tool_failures,
               "error": error, "answer_chars": answer_len}
        with open(STATS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

# ── 话题延续建议（规则化, 按工具调用痕迹推断）────────────────
def _suggest_next(tool_log, message, agent="mentor"):
    names = {t["name"] for t in tool_log}
    sugg = []
    if "future_simulation" in names or "future_paths" in names:
        sugg += ["把其中一条路径讲得更细一些", "基于现在的记录，再做一次模拟"]
    if "current_persona" in names or "evidence_chain" in names:
        sugg += ["这些结论的证据链是什么？", "我最近的变化，镜像怎么看？"]
    if "recent_journals" in names or "recent_events" in names:
        sugg += ["把最近这段经历提炼成一条生命记忆", "分析一下我最近的记录有什么共同点"]
    if "life_goals" in names or "interest_tracks" in names:
        sugg += ["我的目标与兴趣之间有什么关联？", "帮我把目标拆成可执行的下一步"]
    if "growth_report" in names:
        sugg += ["生成一份更长的成长报告", "这份报告里的建议怎么落地？"]
    if "team_context" in names:
        sugg += ["帮我们战队拆解一下当前任务", "推荐一个适合我们战队的活动"]
    if "activity_search" in names or "web_search" in names:
        sugg += ["这个方向还有什么值得参加的活动？", "把找到的资源整理成行动清单"]
    if not sugg:
        sugg = ["根据我的记录，我现在是什么状态？", "帮我看看最近有什么值得注意的成长信号", "我五年后会是什么样的人？"]
    seen, out = set(), []
    for s in sugg:
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= 2:
            break
    return out

def _filter_xml_chars(text):
    """剥离 <tool_calls>/<invoke> 工具标记及其中间内容（字符级扫描; 标记不闭合则丢弃其后全部）"""
    if not text:
        return ""
    out = []
    skip = False
    i, n = 0, len(text)
    while i < n:
        if not skip:
            if text.startswith("<tool_calls", i) or text.startswith("<invoke", i):
                skip = True
            else:
                out.append(text[i])
                i += 1
                continue
        end = text.find("</tool_calls>", i)
        if end < 0:
            end = text.find("</invoke>", i)
        if end >= 0:
            if text.startswith("</tool_calls>", end):
                i = end + len("</tool_calls>")
            else:
                i = end + len("</invoke>")
            skip = False
        else:
            i += 1
    return "".join(out)

def _strip_markers(text):
    t = re.sub(r"<tool_calls>.*?</tool_calls>", "", text or "", flags=re.S)
    t = re.sub(r'<invoke name="[^"]+">.*?</invoke>', "", t, flags=re.S)
    t = re.sub(r"\{TOOL:.*?\}", "", t, flags=re.S)
    return t.strip()

# ── SSE 流式入口 ────────────────────────────────────────
async def stream_agent(user_id, req_message, agent="mentor", history=None):
    """agent SSE 事件流（async generator）— 协议与 PhiAgent 一致"""
    yield {"type": "status", "content": "开始思考"}
    _t_start = time.time()
    base_prompt = get_system_prompt(agent)
    messages = [SystemMessage(content=base_prompt)]
    if agent == "mirror":
        # 数字镜像: 每轮注入人格保持提醒（防多轮后回归助理腔）
        messages.append(SystemMessage(content=PERSONA_THINK_REMINDER))
    for h in (history or [])[-20:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        messages.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    messages.append(HumanMessage(content=req_message))
    # 确定性预判: 记录场景强制走 record_entry（LLM 常把"今天…"当闲聊跳过工具）
    RECORD_STARTS = ("今天", "昨天", "刚才", "今早", "今晚", "前天", "昨天晚上")
    RECORD_WORDS = ("帮我记", "帮我记录", "记录一下", "记一下", "记一笔", "写日记", "记住这个", "帮我写日记")
    QUESTION_WORDS = ("怎么", "吗", "为什么", "如何", "应该", "还是", "建议", "怎么办", "呢", "会不会", "要不要", "是不是")
    _m = (req_message or "").strip()
    _want_record = any(_m.startswith(s) for s in RECORD_STARTS) and not any(q in _m for q in QUESTION_WORDS)
    _want_record = _want_record or any(w in _m for w in RECORD_WORDS)
    if _want_record:
        messages.append(SystemMessage(
            content="用户正在描述一段具体经历/心情。第一轮必须调用 record_entry 工具记录（type 按内容判断：日常流水=journal、"
                    "重要节点=event、抽象感悟=memory），禁止跳过工具直接闲聊回应。"))
    tool_log = []
    config = {"recursion_limit": 18}
    pending = {"text": "", "has_tools": False, "reasoned": False, "started": set()}
    full_answer = ""
    reasoning_text = ""

    async def flush_agent():
        """agent 轮结束定归属: 有工具调用 → 文本降级为思考（防规划文字泄漏为回答）;
        无工具（最终回答轮）→ 文本作为回答逐字打字机输出（含 XML 标记剥离）"""
        nonlocal full_answer
        text = pending["text"]
        if not text:
            return
        if pending["has_tools"]:
            if not pending["reasoned"]:
                yield {"type": "thought", "content": text[:300]}
            return
        for ch in _filter_xml_chars(text):
            full_answer += ch
            yield {"type": "token", "content": ch}
            await asyncio.sleep(0.008)

    try:
        async for chunk, metadata in APP.astream(
                {"messages": messages, "retrieval_count": 0, "user_id": user_id,
                 "agent": agent}, config, stream_mode="messages"):
            node = metadata.get("langgraph_node", "")
            if node == "agent":
                if not chunk:
                    continue
                # 工具调用帧 → 标记本轮有工具 + 立即发"调用中"事件
                if chunk.tool_call_chunks:
                    pending["has_tools"] = True
                    for tcc in chunk.tool_call_chunks:
                        nm = tcc.get("name")
                        if nm and nm not in pending.get("started", ()):
                            pending.setdefault("started", set()).add(nm)
                            yield {"type": "tool_start", "name": nm}
                elif chunk.content:
                    # 只累积本轮文本——归属（思考 or 回答）在轮结束 flush 时决定:
                    # 有工具调用 → 降级为思考; 无工具（最终回答轮）→ 打字机输出。
                    # 防止 LLM 在工具轮输出的规划文字泄漏为回答。
                    pending["text"] += chunk.content
                # DeepSeek reasoning → 思维链分片节流实时流出
                rc = (chunk.additional_kwargs or {}).get("reasoning_content")
                if rc:
                    pending["reasoned"] = True
                    reasoning_text += rc
                    for i in range(0, len(rc), 40):
                        yield {"type": "thought_stream", "content": rc[i:i + 40]}
                        await asyncio.sleep(0.02)
            elif node == "tools":
                # agent 输出结束 → flush（thought 在工具卡片之前发出, 形成穿插节奏）
                async for ev in flush_agent():
                    yield ev
                pending = {"text": "", "has_tools": False, "reasoned": False}
                extra = chunk.additional_kwargs or {}
                name = chunk.name or ""
                args = extra.get("_args", {})
                result = extra.get("_result_full", {})
                summary = json.dumps(result, ensure_ascii=False)[:2000] if isinstance(result, (dict, list)) else str(result)[:2000]
                tool_log.append({"name": name, "args": args, "result_summary": summary,
                                 "result_full": result})
                yield {"type": "tool", "name": name, "args": args, "result": summary}
        # agent 节点结束（最终回答）: flush 缓冲为回答打字机（XML 标记已剥离）
        async for ev in flush_agent():
            yield ev

        # 最终回答空值兜底: LLM 只思考未回答（罕见）→ 无 thinking 重生成
        if not full_answer.strip():
            try:
                from backend.services.ai_filter import deepseek_chat
                fb_msgs = [{"role": m.get("role"), "content": m.get("content")}
                           for m in (history or [])[-8:]] + [{"role": "user", "content": req_message}]
                fb_msgs.insert(0, {"role": "system", "content": base_prompt[:1500] + "\n请直接输出最终回答正文。"})
                resp = await asyncio.to_thread(deepseek_chat, fb_msgs, max_tokens=1500, temperature=0.7)
                reply = _strip_markers(resp or "")
                if reply:
                    for i in range(0, len(reply), 60):
                        full_answer += reply[i:i + 60]
                        yield {"type": "token", "content": reply[i:i + 60]}
                        await asyncio.sleep(0.008)
            except Exception as e:
                print(f"[agent-fallback-fail] {str(e)[:200]}", flush=True)

        # 推理链摘要（o1 风格）
        reasoning_summary = None
        if reasoning_text and len(reasoning_text) > 40:
            try:
                from backend.services.ai_filter import deepseek_chat
                sum_prompt = ("将以下推理过程浓缩为 3-5 步结构化摘要, 每步格式'数字. 动作: 要点'（每步 ≤30 字）:\n\n"
                              + reasoning_text[:2500])
                sresp = await asyncio.to_thread(deepseek_chat,
                                                [{"role": "user", "content": sum_prompt}],
                                                max_tokens=300, temperature=0.3)
                reasoning_summary = (sresp or "").strip() or None
            except Exception:
                reasoning_summary = None

        # 安全审查
        _safety = _safety_check(full_answer)
        safety_flag = "blocked" if "self_harm" in _safety else ("warning" if _safety else None)
        if safety_flag == "blocked":
            full_answer = SAFETY_REPLY

        suggestions = _suggest_next(tool_log, req_message, agent)
        _fail = sum(1 for t in tool_log if isinstance(t.get("result_full"), dict) and t["result_full"].get("error"))
        _log_stats(agent, req_message, time.time() - _t_start, [t["name"] for t in tool_log],
                   _fail, None, len(full_answer))
        yield {"type": "done", "reasoning_summary": reasoning_summary,
               "suggestions": suggestions, "safety": safety_flag,
               "safety_reply": SAFETY_REPLY if safety_flag == "blocked" else None,
               "tool_calls": [{"name": t["name"], "args": t["args"]} for t in tool_log]}
    except asyncio.CancelledError:
        _log_stats(agent, req_message, time.time() - _t_start, [], 0, "cancelled", len(full_answer))
        raise
    except Exception as e:
        _log_stats(agent, req_message, time.time() - _t_start, [], 0, str(e)[:200], 0)
        yield {"type": "error", "content": f"智能体出错: {e}"}
