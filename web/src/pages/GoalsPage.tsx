import { useEffect, useState } from "react";
import { api } from "../auth";

const GOAL_TYPES = [
  { value: "study", label: "学习" },
  { value: "career", label: "职业" },
  { value: "skill", label: "技能" },
  { value: "lifestyle", label: "生活" },
  { value: "relationship", label: "关系" },
  { value: "personal", label: "个人" },
];

const STATUS_LABEL: Record<string, string> = {
  active: "进行中",
  achieved: "已完成",
  abandoned: "已放弃",
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [gtype, setGtype] = useState("study");
  const [importance, setImportance] = useState(70);
  const [period, setPeriod] = useState("中期");
  const [analyzing, setAnalyzing] = useState<number | null>(null);

  const load = () => api("/api/mirror/goals").then(setGoals).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!title.trim()) return;
    await api("/api/mirror/goals", {
      method: "POST",
      body: JSON.stringify({ title, description: desc, goal_type: gtype, importance, target_period: period }),
    });
    setTitle("");
    setDesc("");
    setShowForm(false);
    load();
  }

  async function analyze(goal: any) {
    setAnalyzing(goal.id);
    try {
      await api(`/api/mirror/goals/${goal.id}/analyze`, { method: "POST" });
      load();
    } finally {
      setAnalyzing(null);
    }
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>人生目标</h1>
        <button className="btn" onClick={() => setShowForm(!showForm)}>{showForm ? "取消" : "+ 新目标"}</button>
      </div>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>目标会参与人生模拟与差距分析</p>

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gap: 10 }}>
            <input className="input" placeholder="目标标题" value={title} onChange={(e) => setTitle(e.target.value)} />
            <textarea className="input" rows={2} placeholder="为什么设定这个目标？" value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <select className="input" style={{ flex: 1 }} value={gtype} onChange={(e) => setGtype(e.target.value)}>
                {GOAL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <select className="input" style={{ flex: 1 }} value={period} onChange={(e) => setPeriod(e.target.value)}>
                {["短期", "中期", "长期"].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginBottom: 4 }}>重要度：{importance}%</p>
              <input type="range" min={10} max={100} step={5} value={importance} onChange={(e) => setImportance(Number(e.target.value))} style={{ width: "100%" }} />
            </div>
            <button className="btn" onClick={create}>保存目标</button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {goals.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有目标——设定第一个目标，让 AI 帮你分析差距
          </div>
        )}
        {goals.map((g) => (
          <div key={g.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: "0.95rem", fontWeight: 600 }}>{g.title}</span>
                <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                  {GOAL_TYPES.find((t) => t.value === g.type)?.label || g.type}
                </span>
                <span className="badge" style={{
                  background: g.status === "achieved" ? "rgba(52,211,153,0.15)" : "rgba(251,191,36,0.15)",
                  color: g.status === "achieved" ? "#34D399" : "#FBBF24",
                }}>
                  {STATUS_LABEL[g.status] || g.status}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text4)" }}>重要度 {g.importance}% · {g.period || "未设周期"}</span>
                {g.status === "active" && (
                  <>
                    <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.72rem" }} onClick={() => analyze(g)} disabled={analyzing === g.id}>
                      {analyzing === g.id ? "分析中..." : "AI 差距分析"}
                    </button>
                    <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.72rem", color: "#34D399" }} onClick={async () => {
                      await api(`/api/mirror/goals/${g.id}/complete`, { method: "POST" });
                      load();
                    }}>
                      完成
                    </button>
                    <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.72rem", color: "#F87171" }} onClick={async () => {
                      if (confirm("确定删除这个目标吗？")) {
                        await api(`/api/mirror/goals/${g.id}/delete`, { method: "POST" });
                        load();
                      }
                    }}>
                      删除
                    </button>
                  </>
                )}
              </div>
            </div>
            {g.description && <p style={{ fontSize: "0.8rem", color: "var(--text3)", lineHeight: 1.6 }}>{g.description}</p>}
            {g.ai_gap_analysis && (
              <div style={{ marginTop: 10, padding: 12, borderRadius: 10, background: "var(--accent-bg2)", fontSize: "0.8rem", lineHeight: 1.7, whiteSpace: "pre-wrap", color: "var(--text2)" }}>
                {g.ai_gap_analysis}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
