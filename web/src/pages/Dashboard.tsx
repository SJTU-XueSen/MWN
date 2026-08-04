import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, useAuth } from "../auth";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api("/api/mirror/dashboard").then(setData).catch(() => {});
  }, []);

  if (!data) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "80vh", color: "var(--text4)" }}>
        加载中...
      </div>
    );
  }

  const stats = data.stats || {};
  const persona = data.persona;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 4 }}>
        你好，{user?.real_name || user?.username} 👋
      </h1>
      <p style={{ color: "var(--text4)", fontSize: "0.85rem", marginBottom: 24 }}>{data.insight}</p>

      {/* 数据统计 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "连续记录", value: stats.streak || 0, unit: "天" },
          { label: "日常记录", value: stats.record_count || 0, unit: "条" },
          { label: "人生事件", value: stats.event_count || 0, unit: "个" },
          { label: "活跃目标", value: stats.goal_count || 0, unit: "个" },
          { label: "本周新增", value: stats.this_week || 0, unit: "条" },
        ].map((s) => (
          <div key={s.label} className="card" style={{ textAlign: "center", padding: "16px 8px" }}>
            <p style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--accent)" }}>
              {s.value}
              <span style={{ fontSize: "0.8rem", color: "var(--text4)", fontWeight: 400 }}> {s.unit}</span>
            </p>
            <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* 数字人格 */}
      {persona ? (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>🪞 数字人格 v{persona.version}</h3>
            <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
              置信度 {Math.round((persona.confidence || 0) * 100)}%
            </span>
          </div>
          <p style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 8 }}>{persona.persona_type}</p>
          {Object.entries(persona.ability || {}).map(([k, v]: any) => (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ width: 80, fontSize: "0.75rem", color: "var(--text3)" }}>{k}</span>
              <div style={{ flex: 1, height: 6, background: "var(--input-bg)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${v}%`, height: "100%", background: "var(--bar-mid)", borderRadius: 3 }} />
              </div>
              <span style={{ width: 30, fontSize: "0.75rem", color: "var(--text4)", textAlign: "right" }}>{v}</span>
            </div>
          ))}
          <Link to="/persona" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>查看完整画像 →</Link>
        </div>
      ) : (
        <div className="card" style={{ marginBottom: 24, textAlign: "center", padding: 32 }}>
          <p style={{ fontSize: "2rem", marginBottom: 8 }}>🪞</p>
          <p style={{ color: "var(--text3)", marginBottom: 12 }}>还没有数字人格画像——积累 3 条记录后自动生成</p>
          <Link to="/journal" className="btn" style={{ textDecoration: "none" }}>开始记录</Link>
        </div>
      )}

      {/* 近期事件 */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 12 }}>🗓 近期事件</h3>
        {(data.recent_events || []).length === 0 ? (
          <p style={{ color: "var(--text4)", fontSize: "0.8rem" }}>还没有事件记录</p>
        ) : (
          data.recent_events.map((e: any) => (
            <div key={e.id} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text4)", minWidth: 70 }}>{e.date}</span>
              <div>
                <p style={{ fontSize: "0.85rem", fontWeight: 600 }}>{e.title}</p>
                <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{e.ai_impact}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 活动预览 */}
      {(data.activities || []).length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 12 }}>🎯 校园活动</h3>
          {data.activities.map((a: any) => (
            <a key={a.id} href={a.url} target="_blank" rel="noreferrer" style={{ display: "block", padding: "8px 0", borderBottom: "1px solid var(--border)", textDecoration: "none" }}>
              <p style={{ fontSize: "0.85rem", fontWeight: 600 }}>{a.title}</p>
              <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{a.summary}</p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
