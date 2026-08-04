import { useEffect, useRef, useState } from "react";
import { api } from "../auth";

const STATUS_MAP: Record<string, string> = {
  recruiting: "招募中",
  full: "已满员",
  closed: "已关闭",
  pending: "进行中",
  in_progress: "进行中",
  done: "已完成",
};

export default function WorkPage() {
  const [data, setData] = useState<any>(null);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDesc, setTaskDesc] = useState("");
  const [taskDeadline, setTaskDeadline] = useState("");
  const [roles, setRoles] = useState<any[]>([]);
  const [breaking, setBreaking] = useState(false);
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState("");
  const [myId, setMyId] = useState<number | null>(null);

  const load = () => api("/api/work/data").then(setData).catch(() => {});
  useEffect(() => {
    load();
    api("/api/auth/me").then((u) => setMyId(u.id)).catch(() => {});
  }, []);

  async function openTask(taskId: number) {
    const d = await api(`/api/task/${taskId}/data`);
    setSelectedTask(d);
  }

  async function breakdown() {
    setBreaking(true);
    try {
      const res = await api("/api/breakdown-task", {
        method: "POST",
        body: JSON.stringify({ title: taskTitle, description: taskDesc }),
      });
      setRoles(res.roles || []);
      setMsg("AI 已拆解任务角色，可调整后发布");
    } finally {
      setBreaking(false);
    }
  }

  async function createTask() {
    setCreating(true);
    try {
      const res = await api("/api/create-task", {
        method: "POST",
        body: JSON.stringify({ title: taskTitle, description: taskDesc, roles, deadline: taskDeadline || "" }),
      });
      setMsg(res.error || "任务已发布");
      if (!res.error) {
        setTaskTitle("");
        setTaskDesc("");
        setRoles([]);
        setTaskDeadline("");
        load();
      }
    } finally {
      setCreating(false);
    }
  }

  async function apply(role: string) {
    if (!selectedTask) return;
    const res = await api(`/api/task/${selectedTask.task.id}/apply`, {
      method: "POST",
      body: JSON.stringify({ role }),
    });
    setMsg(res.error || (res.status === "approved" ? "申请通过（队长自动批准）" : "已提交申请，等待队长审核"));
    openTask(selectedTask.task.id);
  }

  async function review(assignmentId: number, action: string) {
    if (!selectedTask) return;
    await api(`/api/task/${selectedTask.task.id}/review`, {
      method: "POST",
      body: JSON.stringify({ assignment_id: assignmentId, action }),
    });
    openTask(selectedTask.task.id);
  }

  if (!data) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  if (!data.has_team) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "80px 24px", textAlign: "center" }}>
        <p style={{ fontSize: "3rem", marginBottom: 16 }}>🧰</p>
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: 8 }}>工作台</h1>
        <p style={{ color: "var(--text4)", fontSize: "0.88rem", lineHeight: 1.8 }}>
          你还没有加入任何战队。<br />先到<a href="/connections" style={{ color: "var(--accent)" }}>活动大厅</a>加入或创建一支战队吧
        </p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>🧰 工作台</h1>
        <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
          {data.team.name} · {data.my_role === "leader" ? "队长" : "成员"}
        </span>
      </div>
      {msg && <p style={{ fontSize: "0.8rem", color: "var(--accent)", margin: "8px 0" }}>{msg}</p>}
      {data.is_working_phase && (
        <p style={{ fontSize: "0.78rem", color: "#FBBF24", margin: "8px 0" }}>💡 已进入工作阶段——开始认领任务并协作产出</p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 20, marginTop: 16 }}>
        {/* 左栏：战队信息 + 任务列表 */}
        <div>
          <div className="card" style={{ marginBottom: 14 }}>
            <h3 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 8 }}>战队信息</h3>
            <p style={{ fontSize: "0.82rem", fontWeight: 600 }}>{data.team.slogan || data.team.description || data.team.name}</p>
            {data.competition?.registration_deadline && (
              <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginTop: 6 }}>
                ⏰ 活动截止：{data.competition.registration_deadline}
              </p>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
              {data.members.map((m: any) => (
                <span key={m.user_id} className="tag" style={{ background: "var(--surface2)", color: "var(--text3)" }}>
                  {m.name}{m.role === "leader" ? "（队长）" : ""}
                </span>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 10 }}>任务列表（{data.tasks.length}）</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {data.tasks.length === 0 && <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>还没有任务</p>}
              {data.tasks.map((t: any) => (
                <div key={t.id} style={{ padding: 10, borderRadius: 10, border: "1px solid var(--border)", cursor: "pointer" }} onClick={() => openTask(t.id)}>
                  <p style={{ fontSize: "0.82rem", fontWeight: 600 }}>{t.title}</p>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "var(--text4)", marginTop: 4 }}>
                    <span>{STATUS_MAP[t.status] || t.status}</span>
                    {t.deadline && <span>截止 {t.deadline}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 右栏：发布任务 / 任务详情 */}
        <div>
          {data.my_role === "leader" && (
            <div className="card" style={{ marginBottom: 14 }}>
              <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 10 }}>发布新任务（AI 拆解）</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <input className="input" placeholder="任务名称" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
                <textarea className="input" rows={2} placeholder="任务描述（AI 会拆解为角色）" value={taskDesc} onChange={(e) => setTaskDesc(e.target.value)} />
                <input className="input" type="date" value={taskDeadline} onChange={(e) => setTaskDeadline(e.target.value)} />
                <button className="btn-ghost" onClick={breakdown} disabled={breaking}>
                  {breaking ? "AI 拆解中..." : "🤖 AI 拆解任务角色"}
                </button>
                {roles.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {roles.map((r, i) => (
                      <div key={i} style={{ padding: 8, borderRadius: 8, background: "var(--surface2)", fontSize: "0.78rem" }}>
                        <p style={{ fontWeight: 600 }}>{r.role} ×{r.count}（约 {r.estimated_hours} 小时）</p>
                        <p style={{ color: "var(--text4)", fontSize: "0.7rem" }}>{(r.skills || []).join("、")}</p>
                      </div>
                    ))}
                    <button className="btn" onClick={createTask} disabled={creating}>发布任务</button>
                  </div>
                )}
              </div>
            </div>
          )}

          {selectedTask ? (
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>{selectedTask.task.title}</h3>
                  <p style={{ fontSize: "0.72rem", color: "var(--text4)" }}>
                    {selectedTask.task.description} · {STATUS_MAP[selectedTask.task.status]}
                  </p>
                </div>
                <button className="btn-ghost" style={{ fontSize: "0.7rem" }} onClick={() => setSelectedTask(null)}>关闭</button>
              </div>

              {/* 角色申请 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedTask.roles.map((r: any) => (
                  <div key={r.name} style={{ padding: 10, borderRadius: 10, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <p style={{ fontSize: "0.82rem", fontWeight: 600 }}>{r.name} <span style={{ color: "var(--text4)", fontWeight: 400 }}>（{r.approved}/{r.needed} 已招）</span></p>
                      <p style={{ fontSize: "0.7rem", color: "var(--text4)" }}>{r.skills.join("、")} · {r.hours} 小时</p>
                    </div>
                    <button className="btn" style={{ padding: "6px 14px", fontSize: "0.72rem" }} onClick={() => apply(r.name)}>
                      申请
                    </button>
                  </div>
                ))}
              </div>

              {/* 申请人列表 */}
              {selectedTask.applicants.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <h4 style={{ fontSize: "0.8rem", fontWeight: 700, marginBottom: 8 }}>申请人</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {selectedTask.applicants.map((a: any) => (
                      <div key={a.id} style={{ padding: 10, borderRadius: 10, background: "var(--surface2)", fontSize: "0.8rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontWeight: 600 }}>{a.user_name}</span>
                          <span style={{ color: "var(--text4)" }}>{a.role} · 匹配 {Math.round((a.match_score || 0) * 100)}%</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
                          <span className="tag" style={{ background: "var(--surface)", color: "var(--text3)" }}>
                            {a.status === "pending" ? "待审核" : a.status === "approved" ? "已通过" : "已拒绝"}
                          </span>
                          {a.status === "pending" && data.my_role === "leader" && (
                            <div style={{ display: "flex", gap: 6 }}>
                              <button className="btn" style={{ padding: "4px 12px", fontSize: "0.7rem" }} onClick={() => review(a.id, "approve")}>通过</button>
                              <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.7rem", color: "#F87171" }} onClick={() => review(a.id, "reject")}>拒绝</button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
              点击左侧任务查看详情、申请或审核
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
