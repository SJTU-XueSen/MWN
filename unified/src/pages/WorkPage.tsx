import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

const STATUS_MAP: Record<string, string> = { recruiting: "招募中", full: "已满员", closed: "已截止", pending: "待办", in_progress: "进行中", done: "已完成" };
const STATUS_TAG: Record<string, string> = {
  recruiting: "tag bg-blue-500/20 text-blue-400", full: "tag bg-amber-500/20 text-amber-400",
  closed: "tag bg-gray-500/20 text-gray-400", pending: "tag bg-gray-500/20 text-gray-400",
  in_progress: "tag bg-indigo-500/20 text-indigo-400", done: "tag bg-emerald-500/20 text-emerald-400",
};

export default function WorkPage() {
  const nav = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [aiRoles, setAiRoles] = useState<any[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", description: "", deadline: "" });
  const [message, setMessage] = useState("");

  // 聊天
  const [chatType, setChatType] = useState<"group" | "team">("group");
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [showChat, setShowChat] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  // DeepSeek
  const [dsMessages, setDsMessages] = useState<{ role: string; content: string }[]>([]);
  const [dsInput, setDsInput] = useState("");
  const [dsKey, setDsKey] = useState(() => localStorage.getItem("deepseek_api_key") || "");

  // 倒计时
  const [countdown, setCountdown] = useState("");

  // 确认弹窗
  const [quitModal, setQuitModal] = useState<{ mode: string; taskId?: string } | null>(null);
  const [quitTimer, setQuitTimer] = useState(5);
  const quitInterval = useRef<any>(null);

  useEffect(() => { loadData(); return () => clearInterval(quitInterval.current); }, []);

  async function loadData() {
    const r = await fetch("/nexus/api/work/data");
    if (r.ok) {
      const d = await r.json();
      setData(d);
    }
    setLoading(false);
  }

  async function loadTaskDetail(taskId: string) {
    const r = await fetch(`/nexus/api/task/${taskId}/data`);
    if (r.ok) setSelectedTask(await r.json());
  }

  async function aiBreakdown() {
    if (!taskForm.title || !taskForm.description) { setMessage("请先填写任务标题和描述"); return; }
    setAiLoading(true);
    const r = await fetch("/nexus/api/breakdown-task", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: taskForm.title, description: taskForm.description }),
    });
    if (r.ok) { const d = await r.json(); setAiRoles(d.roles || []); }
    setAiLoading(false);
  }

  async function publishTask() {
    if (aiRoles.length === 0) { setMessage("请先用 AI 拆解任务"); return; }
    const r = await fetch("/nexus/api/create-task", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: taskForm.title, description: taskForm.description, roles: aiRoles, deadline: taskForm.deadline }),
    });
    if (r.ok) { setMessage("任务发布成功！"); setShowCreateForm(false); setAiRoles([]); setTaskForm({ title: "", description: "", deadline: "" }); loadData(); }
    else { const d = await r.json(); setMessage(d.error || "发布失败"); }
    setTimeout(() => setMessage(""), 4000);
  }

  async function applyRole(taskId: string, roleName: string) {
    const r = await fetch(`/nexus/api/task/${taskId}/apply`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role: roleName }),
    });
    const d = await r.json();
    setMessage(d.ok ? (d.status === "approved" ? "自动通过！" : "申请已提交") : (d.error || "失败"));
    if (d.ok) loadTaskDetail(taskId);
    setTimeout(() => setMessage(""), 4000);
  }

  async function review(taskId: string, assignmentId: string, action: string) {
    await fetch(`/nexus/api/task/${taskId}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assignment_id: assignmentId, action }),
    });
    loadTaskDetail(taskId);
  }

  async function sendChat() {
    if (!chatInput.trim()) return;
    await fetch("/nexus/api/chat/send", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: chatInput, chat_type: chatType }),
    });
    setChatInput("");
    loadChatMessages(chatType);
  }

  async function loadChatMessages(type: string) {
    const r = await fetch(`/nexus/api/chat/messages/${type}`);
    if (r.ok) { const d = await r.json(); setChatMessages(d.messages || []); }
  }

  async function sendDeepseek() {
    const msg = dsInput.trim();
    if (!msg) return;
    if (msg.startsWith("sk-") && !msg.includes(" ")) { localStorage.setItem("deepseek_api_key", msg); setDsKey(msg); setDsInput(""); return; }
    if (!dsKey) { setDsMessages(prev => [...prev, { role: "bot", content: "请先粘贴你的 DeepSeek API Key（以 sk- 开头）。" }]); return; }
    const history = [...dsMessages, { role: "user", content: msg }];
    setDsMessages(prev => [...prev, { role: "user", content: msg }]);
    setDsInput("");
    const r = await fetch("/nexus/api/deepseek/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history.map(m => ({ role: m.role === "bot" ? "assistant" : "user", content: m.content })), api_key: dsKey }),
    });
    const d = await r.json();
    setDsMessages(prev => [...prev, { role: "bot", content: d.reply || d.error || "请求失败" }]);
  }

  // 倒计时
  useEffect(() => {
    if (!data?.competition?.registration_deadline) return;
    const timer = setInterval(() => {
      const diff = new Date(data.competition.registration_deadline).getTime() - Date.now();
      if (diff <= 0) { setCountdown("已截止"); clearInterval(timer); return; }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${d > 0 ? d + "天 " : ""}${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);
    }, 1000);
    return () => clearInterval(timer);
  }, [data?.competition?.registration_deadline]);

  // 确认弹窗
  function showQuitModal(mode: string, taskId?: string) {
    setQuitModal({ mode, taskId }); setQuitTimer(5);
    quitInterval.current = setInterval(() => setQuitTimer(prev => { if (prev <= 1) { clearInterval(quitInterval.current); return 0; } return prev - 1; }), 1000);
  }
  function closeQuitModal() { setQuitModal(null); clearInterval(quitInterval.current); }
  async function confirmQuit() {
    if (!quitModal || quitTimer > 0) return;
    const { mode, taskId } = quitModal;
    let url = "";
    if (mode === "quit") url = `/nexus/api/task/${taskId}/leave`;
    else if (mode === "cancel") url = `/nexus/api/task/${taskId}/cancel`;
    else if (mode === "disband") url = "/nexus/api/team/disband";
    await fetch(url, { method: "POST" });
    closeQuitModal();
    loadData();
  }

  if (loading) return null;

  // 无团队
  if (!data || !data.has_team) {
    return (
      <div className="max-w-2xl mx-auto px-8 py-16 text-center">
        <div className="text-5xl mb-4">📝</div>
        <h2 className="text-xl font-bold mb-2">还没有加入任何团队</h2>
        <p className="#475569 text-sm mb-6">去活动大厅找一个感兴趣的活动加入战队吧</p>
        <button onClick={() => nav("/connections")} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold">
          <i className="fa-solid fa-compass mr-2"></i>去活动大厅
        </button>
      </div>
    );
  }

  const team = data.team;
  const isLeader = data.my_role === "leader";
  const isWorking = data.is_working_phase;

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {message && <div className={`card p-3 mb-4 text-center text-sm ${message.includes("成功") || message.includes("通过") ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border border-rose-500/20 text-rose-400"}`}>{message}</div>}

      {/* 顶栏 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => nav("/connections")} className="text-gray-500 hover:text-gray-400 transition"><i className="fa-solid fa-arrow-left"></i></button>
          <h2 className="text-xl font-bold">工作台</h2>
          <span className={`tag text-xs ${isWorking ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"}`}>
            {isWorking ? "🚀 工作阶段" : "📋 招募阶段"} — {team.name}
          </span>
        </div>
        <div className="flex gap-2">
          {!isWorking && isLeader && (
            <button onClick={async () => {
              const r = await fetch(`/nexus/api/team/${team.id}/close`, { method: "POST" });
              if (r.ok) { setMessage("招募已关闭"); loadData(); }
            }} className="px-3 py-1.5 rounded-lg text-xs text-amber-400 hover:bg-amber-500/10 transition border border-amber-500/20">
              关闭招募
            </button>
          )}
          <button onClick={() => showQuitModal("disband")} className="px-3 py-1.5 rounded-lg text-xs text-rose-400 hover:bg-rose-500/10 transition border border-rose-500/20">
            解散团队
          </button>
        </div>
      </div>

      <div className="grid gap-5" style={{ gridTemplateColumns: "1fr 380px" }}>
        {/* 左侧 */}
        <div>
          {!isWorking ? (
            <>
              {/* 招募阶段 */}
              {isLeader && (
                <div className="mb-4">
                  <button onClick={() => setShowCreateForm(!showCreateForm)} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold w-full">
                    {showCreateForm ? "收起表单 ▲" : "+ 发布新任务"}
                  </button>

                  {showCreateForm && (
                    <div className="card p-5 mt-3 space-y-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">任务标题 *</label>
                        <input className="input" value={taskForm.title} onChange={e => setTaskForm(f => ({ ...f, title: e.target.value }))} placeholder="输入任务名称" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">详细描述 *</label>
                        <textarea className="input" rows={4} value={taskForm.description} onChange={e => setTaskForm(f => ({ ...f, description: e.target.value }))} placeholder="描述任务目标、产出等" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">截止日期</label>
                        <input type="date" className="input" value={taskForm.deadline} onChange={e => setTaskForm(f => ({ ...f, deadline: e.target.value }))} />
                      </div>
                      <button onClick={aiBreakdown} disabled={aiLoading} className="btn text-white px-4 py-2 rounded-lg text-sm w-full">
                        <i className={`fa-solid ${aiLoading ? "fa-spinner animate-spin" : "fa-robot"} mr-2`}></i>
                        {aiLoading ? "AI 分析中..." : "🤖 AI 智能拆解"}
                      </button>

                      {aiRoles.length > 0 && (
                        <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10">
                          <p className="text-xs text-indigo-400 font-semibold mb-2">AI 拆解结果（可编辑）</p>
                          {aiRoles.map((r: any, i: number) => (
                            <div key={i} className="flex items-center gap-3 mb-2 p-2 rounded bg-white/5">
                              <input className="input text-sm py-1 px-2 w-24" value={r.role} onChange={e => { const copy = [...aiRoles]; copy[i].role = e.target.value; setAiRoles(copy); }} />
                              <input className="input text-sm py-1 px-2 w-16" type="number" value={r.count} onChange={e => { const copy = [...aiRoles]; copy[i].count = parseInt(e.target.value); setAiRoles(copy); }} />
                              <span className="text-xs text-gray-500">人</span>
                              <input className="input text-sm py-1 px-2 w-20" type="number" value={r.estimated_hours} onChange={e => { const copy = [...aiRoles]; copy[i].estimated_hours = parseFloat(e.target.value); setAiRoles(copy); }} />
                              <span className="text-xs text-gray-500">小时</span>
                              <span className="text-xs text-gray-600 flex-1">{(r.skills || []).join(", ")}</span>
                            </div>
                          ))}
                          <button onClick={publishTask} className="btn text-white px-4 py-2 rounded-lg text-sm w-full mt-2">发布任务</button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* 任务列表 */}
              <div className="space-y-2">
                {data.tasks?.map((t: any) => (
                  <div key={t.id} onClick={() => loadTaskDetail(t.id)}
                    className={`card p-4 cursor-pointer transition ${selectedTask?.task?.id === t.id ? "border-indigo-500/30 bg-indigo-500/5" : "hover:border-white/20"}`}>
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{t.title}</h4>
                      <span className={STATUS_TAG[t.status] || "tag bg-gray-500/20 text-gray-400"}>{STATUS_MAP[t.status] || t.status}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{t.description?.slice(0, 100)}</p>
                    {t.deadline && <p className="text-xs text-rose-400 mt-1">⏰ {t.deadline?.split("T")[0]} 截止</p>}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              {/* 工作阶段 */}
              <div className="card p-4 mb-4 bg-gradient-to-r from-emerald-500/5 to-teal-500/5 border-emerald-500/10">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-semibold text-emerald-400">📊 团队进度</span>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full" style={{ width: "40%" }} />
                  </div>
                  <span className="text-sm font-bold text-indigo-400">40%</span>
                </div>
              </div>

              {/* 任务卡片 */}
              <div className="space-y-2">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">团队任务</p>
                {[].map ? null : (
                  <div className="card p-8 text-center">
                    <p className="text-sm text-gray-500">任务列表加载中...请先通过招募阶段创建任务</p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* 右侧面板 */}
        <div className="space-y-3">
          {/* 倒计时 */}
          {data.competition?.registration_deadline && (
            <div className="card p-3 bg-gradient-to-r from-rose-500/5 to-amber-500/5 border-rose-500/10">
              <div className="flex items-center gap-2">
                <span>⏰</span>
                <div>
                  <p className="text-xs text-rose-400">截止倒计时</p>
                  <p className="text-lg font-bold text-white">{countdown || "计算中..."}</p>
                </div>
              </div>
            </div>
          )}

          {/* DeepSeek 助手 */}
          <div className="card flex flex-col" style={{ maxHeight: 300 }}>
            <div className="p-2 px-3 flex items-center gap-2 border-b border-white/5 flex-shrink-0" style={{ background: "linear-gradient(135deg, #1a1a2e, #16213e)" }}>
              <span>🤖</span><span className="text-xs font-semibold text-white">DeepSeek 助手</span>
              <button onClick={() => { setDsMessages([]); localStorage.removeItem("deepseek_api_key"); setDsKey(""); }} className="ml-auto text-xs text-gray-500 hover:text-gray-400">清空</button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2" style={{ minHeight: 100 }}>
              {dsMessages.length === 0 && <p className="text-xs text-gray-500 p-2">粘贴 API Key 发送，然后直接提问。</p>}
              {dsMessages.map((m, i) => (
                <div key={i} className={`text-xs ${m.role === "user" ? "text-right" : ""}`}>
                  <span className={`inline-block px-3 py-2 rounded-xl max-w-[85%] ${m.role === "user" ? "bg-indigo-500 text-white rounded-br-sm" : "bg-white/5 text-gray-400 rounded-bl-sm"}`}>{m.content}</span>
                </div>
              ))}
            </div>
            <div className="p-2 border-t border-white/5 flex gap-2 flex-shrink-0">
              <input className="input text-xs py-1.5 flex-1" value={dsInput} onChange={e => setDsInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendDeepseek()} placeholder="输入问题或 API Key..." />
              <button onClick={sendDeepseek} className="w-7 h-7 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center flex-shrink-0">↑</button>
            </div>
          </div>

          {/* 任务详情（招募阶段） */}
          {selectedTask && !isWorking && (
            <div className="card p-4">
              <h4 className="text-sm font-semibold text-white mb-2">{selectedTask.task?.title}</h4>
              <p className="text-xs text-gray-400 mb-3">{selectedTask.task?.description}</p>
              {selectedTask.roles?.map((r: any) => {
                const pct = r.needed > 0 ? Math.round((r.approved / r.needed) * 100) : 0;
                return (
                  <div key={r.name} className="mb-2 p-2 rounded bg-white/5">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="#475569">{r.name}</span>
                      <span className="text-gray-500">{r.approved}/{r.needed}人 · {r.hours}h</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-1">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">{(r.skills || []).join(", ")}</span>
                      {r.needed > r.approved && (
                        <button onClick={() => applyRole(selectedTask.task.id, r.name)}
                          className="px-3 py-1 rounded-lg bg-indigo-500/20 text-indigo-400 text-xs hover:bg-indigo-500/30 transition">
                          申请
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
              {isLeader && selectedTask.applicants?.filter((a: any) => a.status === "pending").length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <p className="text-xs text-amber-400 mb-2">待审核申请</p>
                  {selectedTask.applicants.filter((a: any) => a.status === "pending").map((a: any) => (
                    <div key={a.id} className="flex items-center gap-2 text-xs mb-1">
                      <span className="#475569">{a.user_name}</span>
                      <span className="text-gray-500">→ {a.role}</span>
                      <span className="#8b5e3c">{Math.round(a.match_score * 100)}%</span>
                      <button onClick={() => review(selectedTask.task.id, a.id, "approve")} className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 ml-auto">通过</button>
                      <button onClick={() => review(selectedTask.task.id, a.id, "reject")} className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400">拒绝</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 聊天频道 */}
          <div className="card p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-semibold text-gray-400">💬 聊天频道</span>
              <div className="flex gap-2 ml-auto">
                <button onClick={() => { setChatType("group"); setShowChat(!showChat); if (!showChat) loadChatMessages("group"); }}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${showChat && chatType === "group" ? "bg-indigo-500 text-white" : "bg-white/5 text-gray-400"}`}>👥</button>
                <button onClick={() => { setChatType("team"); setShowChat(!showChat); if (!showChat) loadChatMessages("team"); }}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${showChat && chatType === "team" ? "bg-amber-500 text-white" : "bg-white/5 text-gray-400"}`}>🏠</button>
              </div>
            </div>

            {showChat && (
              <div className="border border-white/10 rounded-xl overflow-hidden">
                <div className="p-2 px-3 flex items-center justify-between border-b border-white/5 bg-white/3">
                  <span className="text-xs font-semibold text-gray-400">{chatType === "group" ? "组内聊天" : "团队聊天"}</span>
                  <button onClick={() => setShowChat(false)} className="text-gray-500 text-xs">×</button>
                </div>
                <div className="p-2 space-y-2" style={{ maxHeight: 200, overflowY: "auto" }} ref={chatRef}>
                  {chatMessages.length === 0 && <p className="text-xs text-gray-500 text-center py-4">暂无消息</p>}
                  {chatMessages.map(m => (
                    <div key={m.id} className={`flex gap-2 text-xs ${m.is_mine ? "flex-row-reverse" : ""}`}>
                      <div className="w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs flex-shrink-0">{m.user_name?.[0] || "?"}</div>
                      <div className={`px-3 py-1.5 rounded-xl max-w-[75%] ${m.is_mine ? "bg-indigo-500 text-white rounded-br-sm" : "bg-white/5 text-gray-400 rounded-bl-sm"}`}>
                        {m.content}
                        {m.image_url && <img src={m.image_url} className="max-w-[120px] rounded mt-1" />}
                        <div className={`text-[10px] mt-0.5 ${m.is_mine ? "text-indigo-300" : "text-gray-600"}`}>{m.user_name} · {m.created_at}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="p-2 border-t border-white/5 flex gap-2">
                  <input className="input text-xs py-1.5 flex-1" value={chatInput} onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && sendChat()} placeholder="输入消息..." />
                  <button onClick={sendChat} className="w-7 h-7 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center">➤</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 确认弹窗 */}
      {quitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={closeQuitModal}>
          <div className="card p-8 max-w-sm w-full mx-4 text-center" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-rose-400 mb-2">
              ⚠ {quitModal.mode === "quit" ? "退出任务" : quitModal.mode === "cancel" ? "取消任务" : "解散团队"}
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              {quitModal.mode === "quit" ? "退出后你将失去该任务的角色分配。" :
               quitModal.mode === "cancel" ? "所有成员的角色分配将被清除。" :
               "团队下所有任务、成员、聊天记录将被永久删除。"}
            </p>
            <p className="text-xs text-rose-400 font-semibold mb-4 p-3 rounded-xl bg-rose-500/5 border border-rose-500/10">
              此操作不可撤销，请谨慎操作！
            </p>
            <div className="flex gap-3">
              <button onClick={closeQuitModal} className="flex-1 px-4 py-2 rounded-lg bg-white/5 text-gray-400 text-sm">取消</button>
              <button onClick={confirmQuit} disabled={quitTimer > 0}
                className={`flex-1 px-4 py-2 rounded-lg text-sm font-semibold ${quitTimer > 0 ? "bg-rose-500/20 text-rose-400" : "bg-rose-500 text-white"}`}>
                {quitTimer > 0 ? `确认 (${quitTimer}s)` : "确认执行"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
