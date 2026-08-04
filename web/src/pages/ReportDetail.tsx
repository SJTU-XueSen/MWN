import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../auth";

export default function ReportDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    api(`/api/mirror/reports/${id}`).then(setReport).catch(() => {});
  }, [id]);

  if (!report) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  const c = report.content || {};

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/reports" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>← 返回报告列表</Link>

      <div className="card" style={{ marginTop: 16 }}>
        <h1 style={{ fontSize: "1.2rem", fontWeight: 700 }}>{report.title}</h1>
        <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginTop: 4 }}>{report.period_start} ~ {report.period_end} · 生成于 {report.date}</p>
        {c.summary && <p style={{ fontSize: "0.9rem", lineHeight: 1.8, color: "var(--text2)", marginTop: 14, whiteSpace: "pre-wrap" }}>{c.summary}</p>}
      </div>

      {c.mood_summary && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 8 }}>😌 情绪趋势</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text2)" }}>{c.mood_summary}</p>
        </div>
      )}

      {(c.interest_changes || []).length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 10 }}>🎯 兴趣变化</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {c.interest_changes.map((ic: any, i: number) => (
              <span key={i} className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
                {ic.field} ×{ic.count}
              </span>
            ))}
          </div>
        </div>
      )}

      {c.ability_growth && Object.keys(c.ability_growth).length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 10 }}>💪 能力成长</h3>
          {Object.entries(c.ability_growth).map(([k, v]: any) => (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ width: 90, fontSize: "0.78rem", color: "var(--text3)" }}>{k}</span>
              <div style={{ flex: 1, height: 6, background: "var(--input-bg)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${Math.min(100, v)}%`, height: "100%", background: "var(--bar-mid)", borderRadius: 3 }} />
              </div>
              <span style={{ width: 32, fontSize: "0.75rem", color: "var(--text4)", textAlign: "right" }}>{Math.round(v)}</span>
            </div>
          ))}
        </div>
      )}

      {(c.key_decisions || []).length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 10 }}>🧭 关键事件</h3>
          {c.key_decisions.map((d: any, i: number) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <p style={{ fontSize: "0.85rem", fontWeight: 600 }}>{d.title}</p>
              {d.insight && <p style={{ fontSize: "0.78rem", color: "var(--text3)" }}>{d.insight}</p>}
            </div>
          ))}
        </div>
      )}

      {c.personality_changes && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 8 }}>🪞 人格变化</h3>
          <p style={{ fontSize: "0.85rem", lineHeight: 1.7, color: "var(--text2)" }}>{c.personality_changes}</p>
        </div>
      )}

      {c.gap_analysis && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 8 }}>🎯 差距分析</h3>
          <p style={{ fontSize: "0.85rem", lineHeight: 1.7, color: "var(--text2)" }}>{c.gap_analysis}</p>
        </div>
      )}

      <button
        className="btn-ghost"
        style={{ marginTop: 16, color: "#F87171", borderColor: "rgba(248,113,113,0.3)" }}
        onClick={async () => {
          if (confirm("删除这份报告？")) {
            await api(`/api/mirror/reports/${id}`, { method: "DELETE" });
            nav("/reports");
          }
        }}
      >
        删除报告
      </button>
    </div>
  );
}
