import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../auth";

export default function SimulationDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [sim, setSim] = useState<any>(null);

  useEffect(() => {
    api(`/api/mirror/simulations/${id}`).then(setSim).catch(() => {});
  }, [id]);

  if (!sim) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  const paths = sim.paths || [];

  async function toGoal(idx: number) {
    await api(`/api/mirror/simulations/${id}/to-goal/${idx}`, { method: "POST" });
    nav("/goals");
  }

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/simulation" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>← 返回模拟列表</Link>

      <div style={{ marginTop: 16, marginBottom: 20 }}>
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700 }}>🔮 {sim.scenario === "further_study" ? "继续深造" : sim.scenario === "employment" ? "直接就业" : sim.scenario === "entrepreneurship" ? "创业探索" : "跨学科发展"}模拟</h1>
        {sim.question && <p style={{ color: "var(--text4)", fontSize: "0.85rem", marginTop: 4 }}>问题：{sim.question}</p>}
        <p style={{ color: "var(--text4)", fontSize: "0.75rem", marginTop: 4 }}>{sim.date}</p>
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        {paths.map((p: any, idx: number) => (
          <div key={idx} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 26, height: 26, borderRadius: "50%", background: "var(--accent-bg3)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem", fontWeight: 700 }}>
                  {idx + 1}
                </span>
                <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>{p.label}</h3>
              </div>
              <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                匹配度 {Math.round((p.confidence || 0) * 100)}%
              </span>
            </div>
            <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 8 }}>{p.path_type_hint}</p>
            <p style={{ fontSize: "0.88rem", lineHeight: 1.8, color: "var(--text2)", marginBottom: 12 }}>{p.description}</p>

            {p.persona_shift && (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                {Object.entries(p.persona_shift).map(([k, v]: any) => (
                  <span key={k} className="tag" style={{ background: "var(--surface2)", color: "var(--text3)" }}>{k} {v}</span>
                ))}
              </div>
            )}

            {(p.milestones || []).length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 4 }}>可能出现的人生节点</p>
                {p.milestones.map((m: string, i: number) => (
                  <p key={i} style={{ fontSize: "0.8rem", color: "var(--text3)", lineHeight: 1.7 }}>· {m}</p>
                ))}
              </div>
            )}

            {(p.gap_suggestions || []).length > 0 && (
              <div style={{ padding: 12, borderRadius: 10, background: "var(--accent-bg2)", marginBottom: 12 }}>
                <p style={{ fontSize: "0.72rem", color: "var(--accent)", marginBottom: 6 }}>90 天建议</p>
                {p.gap_suggestions.map((g: string, i: number) => (
                  <p key={i} style={{ fontSize: "0.8rem", color: "var(--text2)", lineHeight: 1.7 }}>{i + 1}. {g}</p>
                ))}
              </div>
            )}

            {p.grounding && (
              <p style={{ fontSize: "0.72rem", color: "var(--text4)", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
                📎 推导依据：{p.grounding}
              </p>
            )}

            <button className="btn-ghost" style={{ marginTop: 12, fontSize: "0.75rem" }} onClick={() => toGoal(idx)}>
              将此路径转为人生的一个目标 →
            </button>
          </div>
        ))}
      </div>

      {/* 与该路径的未来人格对话入口 */}
      {sim.futures && sim.futures.length > 0 && (
        <div className="card" style={{ marginTop: 16, textAlign: "center" }}>
          <p style={{ fontSize: "0.9rem", marginBottom: 12 }}>想和这些可能的你聊聊吗？</p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            {sim.futures.map((f: any) => (
              <Link key={f.id} to={`/future-chat`} state={{ fsId: f.id, label: f.label }} className="btn-ghost" style={{ textDecoration: "none", fontSize: "0.78rem" }}>
                和「{f.label}」对话
              </Link>
            ))}
          </div>
        </div>
      )}

      <button
        className="btn-ghost"
        style={{ marginTop: 16, color: "#F87171", borderColor: "rgba(248,113,113,0.3)" }}
        onClick={async () => {
          if (confirm("删除这次模拟？")) {
            await api(`/api/mirror/simulations/${id}`, { method: "DELETE" });
            nav("/simulation");
          }
        }}
      >
        删除模拟
      </button>
    </div>
  );
}
