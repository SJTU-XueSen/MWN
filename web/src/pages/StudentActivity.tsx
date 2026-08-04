import { useEffect, useState } from "react";
import { Plus, Trash2, MapPin, Clock, User as UserIcon } from "lucide-react";

export default function StudentActivity() {
  const [items, setItems] = useState<any[]>([]);
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState(""); const [desc, setDesc] = useState("");
  const [date, setDate] = useState(""); const [location, setLocation] = useState("");
  const [org, setOrg] = useState(""); const [contact, setContact] = useState("");

  useEffect(() => { fetch("/api/student-activities").then(r => r.json()).then(setItems); }, []);

  async function submit() {
    if (!title.trim()) return;
    await fetch("/api/student-activities", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, description: desc, date, location, organizer: org, contact, status: "pending" }) });
    setShow(false); setTitle(""); setDesc(""); setDate(""); setLocation(""); setOrg(""); setContact("");
    fetch("/api/student-activities").then(r => r.json()).then(setItems);
  }

  async function remove(id: string) {
    await fetch(`/api/student-activities/${id}`, { method: "DELETE" });
    setItems(items.filter(i => i.id !== id));
  }

  return (
    <main style={{ padding: "32px 40px", background: "var(--bg)", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div><h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>学生活动</h1><p style={{ color: "#64748B", fontSize: "0.85rem" }}>发布和浏览同学自发组织的活动</p></div>
        <button className="btn" onClick={() => setShow(!show)}><Plus size={15} /> 发布活动</button>
      </div>
      {show && (
        <div className="card" style={{ marginBottom: 20 }}>
          <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="活动标题" style={{ marginBottom: 8 }} />
          <textarea className="input" rows={3} value={desc} onChange={e => setDesc(e.target.value)} placeholder="活动描述" style={{ marginBottom: 8, resize: "vertical" }} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
            <input className="input" value={date} onChange={e => setDate(e.target.value)} placeholder="时间（如2026-08-01 14:00）" />
            <input className="input" value={location} onChange={e => setLocation(e.target.value)} placeholder="地点" />
            <input className="input" value={org} onChange={e => setOrg(e.target.value)} placeholder="组织者" />
            <input className="input" value={contact} onChange={e => setContact(e.target.value)} placeholder="联系方式" />
          </div>
          <div style={{ display: "flex", gap: 8 }}><button className="btn" onClick={submit}>发布</button><button className="btn-ghost" onClick={() => setShow(false)}>取消</button></div>
        </div>
      )}
      {items.map((a: any) => (
        <div key={a.id} className="card" style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <p style={{ fontWeight: 600 }}>{a.title}</p>
              <p style={{ color: "#64748B", fontSize: "0.8rem", marginTop: 4 }}>{a.description?.slice(0, 120)}</p>
              <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: "0.7rem", color: "#64748B", flexWrap: "wrap" }}>
                {a.date && <span><Clock size={10} /> {a.date}</span>}
                {a.location && <span><MapPin size={10} /> {a.location}</span>}
                {a.organizer && <span><UserIcon size={10} /> {a.organizer}</span>}
              </div>
            </div>
            <button onClick={() => remove(a.id)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}><Trash2 size={14} /></button>
          </div>
        </div>
      ))}
      {!items.length && <p style={{ color: "#64748B", textAlign: "center", padding: 40 }}>暂无学生活动，发布第一个吧</p>}
    </main>
  );
}
