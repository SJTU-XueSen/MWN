import { useEffect, useState } from "react";
import { api } from "../auth";

interface Memo {
  id: string;
  title: string;
  note: string;
  deadline: string;
  createdAt: string;
}

export default function Memo() {
  const [memos, setMemos] = useState<Memo[]>([]);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [deadline, setDeadline] = useState("");

  const load = () => api("/api/memos").then((d) => setMemos(d.items || [])).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!title.trim()) return;
    await api("/api/memos", {
      method: "POST",
      body: JSON.stringify({ title, content: note, deadline }),
    });
    setTitle("");
    setNote("");
    setDeadline("");
    load();
  }

  const sorted = [...memos].sort((a, b) => (a.deadline || "9999").localeCompare(b.deadline || "9999"));

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>📌 备忘录</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>记住重要的事——持久化存储，重启不丢失</p>

      <div className="card" style={{ marginBottom: 20 }}>
        <input className="input" placeholder="标题" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea className="input" style={{ marginTop: 8 }} rows={2} placeholder="内容" value={note} onChange={(e) => setNote(e.target.value)} />
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <input className="input" type="datetime-local" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          <button className="btn" onClick={create}>添加</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
        {sorted.length === 0 && (
          <div className="card" style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有备忘——添加第一条
          </div>
        )}
        {sorted.map((m) => {
          const expired = m.deadline && new Date(m.deadline) < new Date();
          return (
            <div key={m.id} className="card" style={{ position: "relative" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <p style={{ fontSize: "0.9rem", fontWeight: 700 }}>{m.title}</p>
                <button
                  style={{ border: "none", background: "none", cursor: "pointer", color: "var(--text4)" }}
                  onClick={async () => {
                    await api(`/api/memos/${m.id}`, { method: "DELETE" });
                    load();
                  }}
                >
                  🗑
                </button>
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text3)", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{m.note}</p>
              {m.deadline && (
                <p style={{ fontSize: "0.7rem", marginTop: 8, color: expired ? "#F87171" : "var(--accent)" }}>
                  ⏰ {new Date(m.deadline).toLocaleString("zh-CN")}{expired ? "（已过期）" : ""}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
