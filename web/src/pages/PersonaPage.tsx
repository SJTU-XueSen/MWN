import { useEffect, useState } from "react";
import { api } from "../auth";

export default function PersonaPage() {
  const [data, setData] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [viewVersion, setViewVersion] = useState<number | null>(null);

  const load = (version?: number) =>
    api(`/api/mirror/persona${version ? `?version=${version}` : ""}`).then(setData).catch(() => {});

  useEffect(() => {
    load();
  }, []);

  const persona = viewVersion ? (data?.current || null) : (data?.current || null);

  async function generate() {
    setGenerating(true);
    try {
      await api("/api/mirror/persona", { method: "POST" });
      await load();
    } finally {
      setGenerating(false);
    }
  }

  if (!data) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>🪞 数字人格</h1>
        <button className="btn" onClick={generate} disabled={generating}>
          {generating ? "AI 分析中..." : "重新生成"}
        </button>
      </div>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>
        五维画像完全由你的真实记录与事件推断——数据越多，画像越准确
      </p>

      {!persona ? (
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <p style={{ fontSize: "2.5rem", marginBottom: 12 }}>🪞</p>
          <p style={{ color: "var(--text3)", marginBottom: 16 }}>还没有人格画像——积累至少 3 条记录或事件后即可生成</p>
          <button className="btn" onClick={generate} disabled={generating}>立即生成</button>
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>{persona.persona_type}</h2>
                <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginTop: 2 }}>版本 v{persona.version} · {persona.date}</p>
              </div>
              <span className="badge" style={{ background: persona.confidence >= 0.5 ? "rgba(52,211,153,0.15)" : "rgba(251,191,36,0.15)", color: persona.confidence >= 0.5 ? "#34D399" : "#FBBF24" }}>
                置信度 {Math.round((persona.confidence || 0) * 100)}%
              </span>
            </div>
            {persona.summary && <p style={{ fontSize: "0.88rem", lineHeight: 1.8, color: "var(--text2)" }}>{persona.summary}</p>}
            {persona.confidence < 0.5 && (
              <p style={{ fontSize: "0.75rem", color: "#FBBF24", marginTop: 10 }}>
                ⚠ 当前样本较少，这只是你的一个可能侧面——继续记录会让人格画像更准确
              </p>
            )}
          </div>

          <div style={{ display: "grid", gap: 16 }}>
            <Dimension title="💪 能力画像" data={persona.ability} />
            <Dimension title="🎯 兴趣画像" data={persona.interest} />
            <Dimension title="💎 价值观" data={persona.value} />
            {persona.decision && (
              <div className="card">
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 8 }}>🧭 决策风格</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--accent)", marginBottom: 6 }}>{persona.decision.style}</p>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {(persona.decision.traits || []).map((t: string) => (
                    <span key={t} className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{t}</span>
                  ))}
                </div>
              </div>
            )}
            <Dimension title="🔁 行为模式" data={persona.behavior} />
          </div>
        </>
      )}

      {/* 版本历史 */}
      {data.history && data.history.length > 1 && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 10 }}>📜 版本历史</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.history.map((h: any) => (
              <div key={h.id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "0.8rem" }}>
                <span style={{ color: "var(--text3)" }}>v{h.version}</span>
                <span style={{ color: "var(--text4)" }}>{h.date}</span>
                <span style={{ color: "var(--text4)" }}>置信度 {Math.round((h.confidence || 0) * 100)}%</span>
                {h.is_current && <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>当前</span>}
                {!h.is_current && (
                  <button className="btn-ghost" style={{ padding: "2px 10px", fontSize: "0.7rem" }} onClick={() => load(h.id)}>
                    查看
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Dimension({ title, data }: { title: string; data?: Record<string, number> }) {
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div className="card">
      <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 12 }}>{title}</h3>
      {Object.entries(data).map(([k, v]: any) => (
        <div key={k} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ width: 90, fontSize: "0.78rem", color: "var(--text3)" }}>{k}</span>
          <div style={{ flex: 1, height: 7, background: "var(--input-bg)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ width: `${Math.min(100, v)}%`, height: "100%", background: "var(--bar-mid)", borderRadius: 4 }} />
          </div>
          <span style={{ width: 32, fontSize: "0.75rem", color: "var(--text4)", textAlign: "right" }}>{Math.round(v)}</span>
        </div>
      ))}
    </div>
  );
}
