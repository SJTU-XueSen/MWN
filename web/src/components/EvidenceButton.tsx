import { useState } from "react";

/** 「为什么」证据链按钮 — 点击弹出该结论的真实数据来源 */
export default function EvidenceButton({
  query,
  targetType,
  targetId,
  label = "为什么",
  size = "sm",
  style,
}: {
  query: string;
  targetType?: string;
  targetId?: number;
  label?: string;
  size?: "sm" | "xs";
  style?: React.CSSProperties;
}) {
  const [open, setOpen] = useState(false);
  const [evidence, setEvidence] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/mirror/evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ query, target_type: targetType, target_id: targetId }),
      });
      const data = await resp.json();
      setEvidence(data.evidence || []);
    } catch {
      setError("加载失败");
    } finally {
      setLoading(false);
    }
  }

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next) load();
  }

  return (
    <>
      <button
        onClick={(e) => {
          e.stopPropagation();
          toggle();
        }}
        style={{
          border: "1px solid var(--accent-border)",
          background: "var(--accent-bg)",
          color: "var(--accent)",
          borderRadius: 6,
          cursor: "pointer",
          fontSize: size === "sm" ? "0.68rem" : "0.62rem",
          padding: size === "sm" ? "3px 10px" : "2px 8px",
          ...style,
        }}
        title="展开这条结论的真实数据来源"
      >
        🔍 {label}
      </button>

      {open && (
        <div
          style={{ position: "fixed", inset: 0, zIndex: 300, background: "var(--overlay)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
          onClick={() => setOpen(false)}
        >
          <div
            className="card"
            style={{ maxWidth: 560, maxHeight: "80vh", overflowY: "auto", width: "100%" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>📎 证据链 — 为什么是这个结论</h3>
              <button onClick={() => setOpen(false)} style={{ border: "none", background: "none", fontSize: "1.2rem", cursor: "pointer", color: "var(--text4)" }}>×</button>
            </div>
            <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 12 }}>
              以下内容全部来自你的真实记录，无任何编造
            </p>

            {loading && <p style={{ fontSize: "0.8rem", color: "var(--text4)", textAlign: "center", padding: 20 }}>检索你的记忆库...</p>}
            {error && <p style={{ fontSize: "0.8rem", color: "#F87171" }}>{error}</p>}

            {!loading && !error && evidence && evidence.length === 0 && (
              <p style={{ fontSize: "0.8rem", color: "var(--text4)", textAlign: "center", padding: 24 }}>
                目前没有足够的数据支撑这条结论——继续记录后，证据会自然出现
              </p>
            )}

            {!loading && evidence && evidence.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {evidence.map((ev, i) => (
                  <div key={i} style={{ padding: "12px 14px", borderRadius: 10, background: "var(--surface2)", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span className="tag" style={{
                        background: ev.type === "memory" ? "var(--accent-bg)" : ev.type === "event" ? "rgba(52,211,153,0.15)" : "rgba(251,191,36,0.15)",
                        color: ev.type === "memory" ? "var(--accent)" : ev.type === "event" ? "#34D399" : "#FBBF24",
                      }}>
                        {ev.type === "memory" ? "💾 生命记忆" : ev.type === "event" ? "🗓 人生事件" : "📝 日常记录"}
                      </span>
                      <span style={{ fontSize: "0.66rem", color: "var(--text4)" }}>
                        {ev.date}
                        {ev.importance ? ` · 重要度 ${Math.round(ev.importance * 100)}%` : ""}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "var(--text2)", lineHeight: 1.7 }}>{ev.snippet}</p>
                    {ev.title && ev.type !== "memory" && (
                      <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 4 }}>{ev.title}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
