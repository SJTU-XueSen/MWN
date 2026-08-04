import { useState } from "react";
import { api } from "../auth";

export default function ProjectionPage() {
  const [years, setYears] = useState(10);
  const [projection, setProjection] = useState<any[] | null>(null);
  const [running, setRunning] = useState(false);
  const [reasoning, setReasoning] = useState("");

  async function run() {
    setRunning(true);
    setProjection(null);
    try {
      const res = await api("/api/mirror/projection", {
        method: "POST",
        body: JSON.stringify({ years }),
      });
      setProjection(res.projection || []);
      setReasoning("基于你的全部真实记忆、人格画像与目标推演");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>🔭 推演人生</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>
        无干预式推演——AI 基于你真实的过去，推演未来可能的人生走向。不是预言，是一种可能性
      </p>

      <div className="card" style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginBottom: 6 }}>推演年限：{years} 年</p>
          <input type="range" min={3} max={20} value={years} onChange={(e) => setYears(Number(e.target.value))} style={{ width: "100%" }} />
        </div>
        <button className="btn" onClick={run} disabled={running}>
          {running ? "推演中..." : "开始推演"}
        </button>
      </div>

      {running && (
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <p style={{ fontSize: "2rem", marginBottom: 12 }}>🔭</p>
          <p style={{ color: "var(--text3)" }}>AI 正在聚合你的记忆、人格与目标...</p>
        </div>
      )}

      {projection && (
        <>
          <p style={{ fontSize: "0.8rem", color: "var(--text4)", marginBottom: 16 }}>{reasoning}</p>
          <div style={{ position: "relative", paddingLeft: 24 }}>
            <div style={{ position: "absolute", left: 6, top: 0, bottom: 0, width: 2, background: "var(--border)" }} />
            {projection.map((node, i) => (
              <div key={i} style={{ position: "relative", marginBottom: 16 }}>
                <span style={{ position: "absolute", left: -24, top: 20, width: 10, height: 10, borderRadius: "50%", background: i % 4 === 0 ? "var(--accent)" : "var(--text4)" }} />
                <div className="card" style={{ padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span style={{ fontSize: "0.9rem", fontWeight: 700 }}>{node.year} 年 · {node.age} 岁</span>
                    {node.trait_shift && (
                      <div style={{ display: "flex", gap: 6 }}>
                        {Object.entries(node.trait_shift).map(([k, v]: any) => (
                          <span key={k} className="tag" style={{ background: "var(--surface2)", color: "var(--text3)" }}>{k}{v}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: "0.88rem", fontWeight: 600, marginBottom: 6 }}>{node.event}</p>
                  <p style={{ fontSize: "0.8rem", color: "var(--text3)", lineHeight: 1.7 }}>{node.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
