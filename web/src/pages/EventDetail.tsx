import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../auth";

export default function EventDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [event, setEvent] = useState<any>(null);

  useEffect(() => {
    api(`/api/mirror/events/${id}`).then(setEvent).catch(() => {});
  }, [id]);

  if (!event) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/events" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>← 返回人生地图</Link>

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: "1.6rem" }}>{event.display_icon}</span>
          <h1 style={{ fontSize: "1.2rem", fontWeight: 700, flex: 1 }}>{event.title}</h1>
          <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{event.display_label}</span>
        </div>
        <p style={{ fontSize: "0.8rem", color: "var(--text4)", marginBottom: 12 }}>{event.date}</p>
        {event.description && <p style={{ fontSize: "0.9rem", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{event.description}</p>}
      </div>

      {event.ai_impact && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 10 }}>🪞 AI 影响分析</h3>
          <p style={{ fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text2)" }}>{event.ai_impact}</p>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        {event.persona_delta && Object.keys(event.persona_delta).length > 0 && (
          <div className="card">
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 10 }}>人格影响</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {Object.entries(event.persona_delta).map(([k, v]: any) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                  <span style={{ color: "var(--text3)" }}>{k}</span>
                  <span style={{ color: v > 0 ? "#34D399" : v < 0 ? "#F87171" : "var(--text4)" }}>{v > 0 ? `+${v}` : v}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {(event.interest_tags || []).length > 0 && (
          <div className="card">
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 10 }}>兴趣标签</h3>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {event.interest_tags.map((t: string) => (
                <span key={t} className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{t}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {event.memory && (
        <div className="card" style={{ marginTop: 16, background: "var(--accent-bg2)" }}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 8 }}>💾 提炼的生命记忆</h3>
          <p style={{ fontSize: "0.85rem", lineHeight: 1.7, color: "var(--text2)" }}>{event.memory.memory_content}</p>
          <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginTop: 6 }}>重要度 {(event.memory.importance_score * 100).toFixed(0)}% — 已存入长期记忆库</p>
        </div>
      )}

      <button
        className="btn-ghost"
        style={{ marginTop: 16, color: "#F87171", borderColor: "rgba(248,113,113,0.3)" }}
        onClick={async () => {
          if (confirm("确定删除这个事件吗？")) {
            await api(`/api/mirror/events/${id}`, { method: "DELETE" });
            nav("/events");
          }
        }}
      >
        删除事件
      </button>
    </div>
  );
}
