import { useState } from "react";
import { api } from "../auth";

export default function AiSearch() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api("/api/ai-search", {
        method: "POST",
        body: JSON.stringify({ query }),
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  const recs = result?.recommendations || [];

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>🔍 AI 检索</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>
        DeepSeek 语义匹配——描述你感兴趣的方向，AI 推荐校园活动与知名竞赛
      </p>

      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <input
          className="input"
          placeholder="例如：我想参加机器人方向的比赛，对嵌入式感兴趣"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn" onClick={search} disabled={loading}>{loading ? "AI 匹配中..." : "检索"}</button>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <p style={{ fontSize: "2rem", marginBottom: 12 }}>🤖</p>
          <p style={{ color: "var(--text3)" }}>AI 正在分析你的兴趣与活动匹配度...</p>
        </div>
      )}

      {result && !result.success && <p style={{ color: "#F87171", fontSize: "0.85rem" }}>{result.error}</p>}

      {recs.length > 0 && (
        <>
          <p style={{ fontSize: "0.78rem", color: "var(--text4)", whiteSpace: "pre-wrap", marginBottom: 14 }}>{result.reasoning}</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
            {recs.map((r: any, i: number) => (
              <div key={i} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span className="badge" style={{ background: r.source === "campus" ? "var(--accent-bg)" : "rgba(52,211,153,0.15)", color: r.source === "campus" ? "var(--accent)" : "#34D399" }}>
                    {r.source === "campus" ? "校园活动" : "知名竞赛"}
                  </span>
                  {r.inferredEndDate && <span style={{ fontSize: "0.7rem", color: "var(--text4)" }}>截止 {r.inferredEndDate}</span>}
                </div>
                <p style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 6 }}>{r.title}</p>
                <p style={{ fontSize: "0.78rem", color: "var(--text3)", lineHeight: 1.6, marginBottom: 8 }}>{r.summary}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--accent)" }}>🎯 {r.matchReason}</p>
                {r.url && (
                  <a href={r.url} target="_blank" rel="noreferrer" style={{ fontSize: "0.72rem", color: "var(--text4)", display: "block", marginTop: 6 }}>
                    查看详情 →
                  </a>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
