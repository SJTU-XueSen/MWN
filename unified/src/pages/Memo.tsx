import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

export default function Memo() {
  const [memos, setMemos] = useState<any[]>([]);
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [deadline, setDeadline] = useState("");
  const [deadlineTime, setDeadlineTime] = useState("");

  useEffect(() => { fetchMemos(); }, []);

  function fetchMemos() { fetch("/api/memos").then(r => r.json()).then(d => setMemos(d?.items || [])); }

  async function create() {
    if (!title.trim()) return;
    const dl = deadline ? (deadlineTime ? deadline + "T" + deadlineTime : deadline + "T23:59") : "";
    await fetch("/api/memos", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, note, deadline: dl }),
    });
    setShow(false); setTitle(""); setNote(""); setDeadline(""); setDeadlineTime("");
    fetchMemos();
  }

  async function remove(id: string) { await fetch(`/api/memos/${id}`, { method: "DELETE" }); setMemos(memos.filter(m => m.id !== id)); }

  function fmtDate(d: string) {
    if (!d) return "";
    try { const dt = new Date(d); return dt.toLocaleDateString("zh-CN", { month: "short", day: "numeric" }) + (d.includes("T") && !d.endsWith("T23:59") ? " " + dt.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""); }
    catch { return d; }
  }

  return (
    <main style={{ padding: "32px 40px", background: "var(--bg)", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>备忘录</h1>
          <p style={{ color: "#64748B", fontSize: "0.85rem" }}>收藏感兴趣的活动和竞赛</p>
        </div>
        <button className="btn" onClick={() => setShow(!show)}><Plus size={15} /> 新建</button>
      </div>

      {show && (
        <div className="card" style={{ marginBottom: 20 }}>
          <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="备忘标题" style={{ marginBottom: 8 }} />
          <textarea className="input" rows={3} value={note} onChange={e => setNote(e.target.value)} placeholder="备注..." style={{ resize: "vertical", marginBottom: 8 }} />

          <div style={{ display: "flex", gap: 10, marginBottom: 8, alignItems: "center" }}>
            <span style={{ fontSize: "0.78rem", color: "#64748B", flexShrink: 0 }}>相关日期</span>
            <input type="date" className="input" value={deadline} onChange={e => setDeadline(e.target.value)} style={{ flex: 1 }} />
            <input type="time" className="input" value={deadlineTime} onChange={e => setDeadlineTime(e.target.value)} style={{ width: 130 }} />
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn" onClick={create}>保存</button>
            <button className="btn-ghost" onClick={() => setShow(false)}>取消</button>
          </div>
        </div>
      )}

      {memos.map(m => (
        <div key={m.id} className="card" style={{ marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ flex: 1 }}>
            <p style={{ fontWeight: 600 }}>{m.title}</p>
            {m.note && <p style={{ color: "#64748B", fontSize: "0.8rem", marginTop: 4 }}>{m.note}</p>}
            <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: "0.68rem", color: "#64748B" }}>
              {m.deadline && <span>📅 相关: {fmtDate(m.deadline)}</span>}
              {m.createdAt && <span>创建于 {fmtDate(m.createdAt)}</span>}
            </div>
          </div>
          <button onClick={() => remove(m.id)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", flexShrink: 0, marginLeft: 10 }}>
            <Trash2 size={14} />
          </button>
        </div>
      ))}

      {!memos.length && <p style={{ color: "#64748B", textAlign: "center", padding: 40 }}>暂无备忘</p>}
    </main>
  );
}
