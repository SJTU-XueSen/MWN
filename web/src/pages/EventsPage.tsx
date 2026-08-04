import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../auth";

const EVENT_TYPES = [
  { value: "project", label: "项目经历", icon: "📁" },
  { value: "competition", label: "比赛经历", icon: "🏆" },
  { value: "study", label: "学习经历", icon: "📖" },
  { value: "social", label: "社交经历", icon: "👥" },
  { value: "decision", label: "重要决定", icon: "🧭" },
  { value: "turning_point", label: "人生转折", icon: "🔀" },
  { value: "habit", label: "长期习惯", icon: "🔄" },
  { value: "failure", label: "失败经历", icon: "💪" },
  { value: "achievement", label: "成就突破", icon: "🌟" },
  { value: "relationship", label: "重要关系", icon: "💞" },
  { value: "emotion", label: "情绪波动", icon: "💭" },
];

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [etype, setEtype] = useState("project");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [saving, setSaving] = useState(false);

  const load = () => api("/api/mirror/events").then(setEvents).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    events.forEach((e) => (counts[e.type] = (counts[e.type] || 0) + 1));
    return counts;
  }, [events]);

  async function create() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await api("/api/mirror/events", {
        method: "POST",
        body: JSON.stringify({ title, description: desc, event_type: etype, occurred_at: date }),
      });
      setTitle("");
      setDesc("");
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  const typeMeta = (v: string) => EVENT_TYPES.find((t) => t.value === v) || { value: v, label: v, icon: "📌" };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>🗺 人生地图</h1>
        <button className="btn" onClick={() => setShowForm(!showForm)}>{showForm ? "取消" : "+ 记录事件"}</button>
      </div>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>你的人生节点——每次事件的 AI 分析都会影响数字人格</p>

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gap: 10 }}>
            <input className="input" placeholder="事件标题" value={title} onChange={(e) => setTitle(e.target.value)} />
            <textarea className="input" rows={3} placeholder="描述这段经历（AI 会分析情绪、兴趣与人格影响）" value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <select className="input" style={{ flex: 1, minWidth: 150 }} value={etype} onChange={(e) => setEtype(e.target.value)}>
                {EVENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
                ))}
              </select>
              <input className="input" type="date" style={{ flex: 1 }} value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <button className="btn" onClick={create} disabled={saving}>{saving ? "AI 分析中..." : "保存事件"}</button>
          </div>
        </div>
      )}

      {/* 类型统计 */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {Object.entries(typeCounts).map(([t, c]) => (
          <span key={t} className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
            {typeMeta(t).icon} {typeMeta(t).label} ×{c}
          </span>
        ))}
      </div>

      <div style={{ position: "relative", paddingLeft: 20 }}>
        <div style={{ position: "absolute", left: 5, top: 0, bottom: 0, width: 2, background: "var(--border)" }} />
        {events.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有人生事件——从第一件重要的事开始
          </div>
        )}
        {events.map((e) => (
          <Link key={e.id} to={`/events/${e.id}`} style={{ textDecoration: "none", display: "block", position: "relative", marginBottom: 14 }}>
            <span style={{ position: "absolute", left: -23, top: 22, width: 10, height: 10, borderRadius: "50%", background: "var(--accent2)" }} />
            <div className="card" style={{ padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                  {typeMeta(e.type).icon} {e.title}
                </span>
                <span style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{e.date}</span>
              </div>
              {e.description && <p style={{ fontSize: "0.82rem", color: "var(--text3)", lineHeight: 1.6 }}>{e.description.slice(0, 120)}</p>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
