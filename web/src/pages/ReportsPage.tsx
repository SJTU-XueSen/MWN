import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../auth";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [days, setDays] = useState(30);
  const [title, setTitle] = useState("");
  const [generating, setGenerating] = useState(false);

  const load = () => api("/api/mirror/reports").then(setReports).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function generate() {
    setGenerating(true);
    try {
      await api("/api/mirror/reports", {
        method: "POST",
        body: JSON.stringify({ days, title }),
      });
      setTitle("");
      load();
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>📊 成长报告</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>AI 定期总结你的成长轨迹——完全基于你的真实数据</p>

      <div className="card" style={{ marginBottom: 24, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <input className="input" style={{ flex: 1, minWidth: 200 }} placeholder="报告标题（可选）" value={title} onChange={(e) => setTitle(e.target.value)} />
        <select className="input" style={{ width: 130 }} value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 30, 60, 90].map((d) => (
            <option key={d} value={d}>近 {d} 天</option>
          ))}
        </select>
        <button className="btn" onClick={generate} disabled={generating}>
          {generating ? "AI 分析中..." : "生成报告"}
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {reports.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有成长报告——积累一段时间的记录后生成
          </div>
        )}
        {reports.map((r) => (
          <Link key={r.id} to={`/reports/${r.id}`} style={{ textDecoration: "none" }}>
            <div className="card" style={{ padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ fontSize: "0.9rem", fontWeight: 600 }}>{r.title}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginTop: 3 }}>{r.period_start} ~ {r.period_end}</p>
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{r.date}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
