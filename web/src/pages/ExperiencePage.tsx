import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../auth";

export default function ExperiencePage() {
  const { fsId } = useParams();
  const [session, setSession] = useState<any>(null);
  const [scene, setScene] = useState<any>(null);
  const [lastResult, setLastResult] = useState<any>(null);
  const [customChoice, setCustomChoice] = useState("");
  const [playing, setPlaying] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api(`/api/mirror/experience/start/${fsId}`, { method: "POST" })
      .then((res) => {
        setSession({ session_id: res.session_id, current_year: res.current_year, current_age: res.current_age });
        setScene(res.scene);
      })
      .catch(() => {});
  }, [fsId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [scene, lastResult]);

  async function choose(idx: number) {
    if (!session || playing) return;
    setPlaying(true);
    try {
      const res = await api(`/api/mirror/experience/play/${session.session_id}`, {
        method: "POST",
        body: JSON.stringify({ choice: idx, custom_choice: customChoice }),
      });
      setLastResult(res.last_result);
      setScene(res.scene);
      setSession((s: any) => ({ ...s, ...res.session }));
      setCustomChoice("");
    } finally {
      setPlaying(false);
    }
  }

  if (!scene) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>正在进入人生体验...</div>;
  }

  const traits = scene.current_traits || {};

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/future-chat" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>← 返回对话列表</Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, marginBottom: 20 }}>
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700 }}>人生体验</h1>
        <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
          {session?.current_year} 年 · {session?.current_age} 岁
        </span>
      </div>

      {/* 人格状态 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 10 }}>当前人格状态</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 8 }}>
          {Object.entries(traits).map(([k, v]: any) => (
            <div key={k}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", marginBottom: 3 }}>
                <span style={{ color: "var(--text3)" }}>{k}</span>
                <span style={{ color: "var(--text4)" }}>{v}</span>
              </div>
              <div style={{ height: 5, background: "var(--input-bg)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${v}%`, height: "100%", background: "var(--bar-mid)", borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {lastResult && (
        <div className="card" style={{ marginBottom: 16, borderColor: "var(--accent-border2)", background: "var(--accent-bg2)" }}>
          <p style={{ fontSize: "0.78rem", color: "var(--text4)", marginBottom: 6 }}>你的选择（{lastResult.year} 年）</p>
          <p style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 6 }}>{lastResult.choice}</p>
          <p style={{ fontSize: "0.8rem", color: "var(--text3)" }}>获得：{lastResult.gain} · 放下：{lastResult.cost}</p>
          {lastResult.trait_deltas && Object.keys(lastResult.trait_deltas).length > 0 && (
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              {Object.entries(lastResult.trait_deltas).map(([k, v]: any) => (
                <span key={k} className="tag" style={{ background: "var(--surface2)", color: v > 0 ? "#34D399" : "#F87171" }}>
                  {k} {v > 0 ? `+${v}` : v}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <p style={{ fontSize: "0.95rem", lineHeight: 1.9, color: "var(--text2)", whiteSpace: "pre-wrap" }}>{scene.narrative}</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {(scene.choices || []).map((c: any, i: number) => (
          <button
            key={i}
            onClick={() => choose(i)}
            disabled={playing}
            className="card"
            style={{
              cursor: "pointer",
              textAlign: "left",
              padding: "14px 18px",
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "var(--input-bg)",
              transition: "border-color .2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent-border2)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
          >
            <p style={{ fontSize: "0.9rem", fontWeight: 600 }}>{c.text}</p>
            <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginTop: 6 }}>{c.gain} · 🌙 {c.cost}</p>
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <input className="input" placeholder="或者自由选择一条路..." value={customChoice} onChange={(e) => setCustomChoice(e.target.value)} />
        <button className="btn-ghost" onClick={() => choose(-1)} disabled={playing || !customChoice.trim()}>
          自由选择
        </button>
      </div>

      <div ref={bottomRef} />
    </div>
  );
}
