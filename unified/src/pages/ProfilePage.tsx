import { useEffect, useState } from "react";

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ real_name: "", university: "", major: "", grade: "", bio: "" });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me").then(r => r.json()).then(auth => {
      if (!auth?.id) return;
      fetch("/api/mirror/settings").then(r => r.json()).then(d => {
        setUser({ ...auth, ...d });
        setForm({ real_name: d.real_name || "", university: d.university || "", major: d.major || "", grade: d.grade || "", bio: d.bio || "" });
      });
    });
  }, []);

  async function save() {
    await fetch("/api/mirror/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setUser((prev: any) => ({ ...prev, ...form }));
    setEditing(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!user) return null;

  const fields = [
    { key: "real_name", label: "真实姓名" },
    { key: "university", label: "学校" },
    { key: "major", label: "专业" },
    { key: "grade", label: "年级" },
  ];

  return (
    <div className="max-w-2xl mx-auto px-8 py-8">
      <h2 className="text-2xl font-bold mb-6">个人资料</h2>

      <div className="card p-6 mb-4">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-indigo-500/15 flex items-center justify-center text-2xl font-bold text-indigo-400 mx-auto mb-3">
            {(user.real_name || user.username)?.[0]?.toUpperCase() || "U"}
          </div>
          <h3 className="text-lg font-bold text-white">{user.real_name || user.username}</h3>
          <p className="text-sm text-gray-500">@{user.username}</p>
        </div>

        <div className="border-t border-white/5 pt-4 space-y-3">
          <FieldRow label="用户名" value={user.username} />
          {fields.map(f => (
            <FieldRow key={f.key} label={f.label} value={user[f.key] || "未设置"}>
              {editing && <input className="input text-sm py-1 px-2 w-40 text-right" value={form[f.key as keyof typeof form]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />}
            </FieldRow>
          ))}
          <div className="flex justify-between items-start py-2">
            <span className="text-sm text-gray-400">个人简介</span>
            {editing ? (
              <textarea className="input text-sm py-1 px-2 w-60" rows={3} value={form.bio} onChange={e => setForm({ ...form, bio: e.target.value })} placeholder="介绍一下自己..." />
            ) : (
              <span className="text-sm text-gray-200 text-right max-w-[60%]">{user.bio || "未设置"}</span>
            )}
          </div>
          <FieldRow label="注册时间" value={user.created_at || "未知"} />
        </div>

        <div className="mt-4 flex gap-2">
          {editing ? (
            <>
              <button onClick={save} className="btn text-white px-4 py-2 rounded-lg text-sm">保存</button>
              <button onClick={() => { setEditing(false); setForm({ real_name: user.real_name || "", university: user.university || "", major: user.major || "", grade: user.grade || "", bio: user.bio || "" }); }}
                className="px-4 py-2 rounded-lg text-sm text-gray-400 border border-white/10">取消</button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="px-4 py-2 rounded-lg text-sm text-gray-400 border border-white/10 hover:text-white hover:border-white/20 transition">
              <i className="fa-solid fa-pen mr-1"></i>编辑
            </button>
          )}
          {saved && <span className="text-xs text-emerald-400 py-2">已保存 ✓</span>}
        </div>
      </div>
    </div>
  );
}

function FieldRow({ label, value, children }: { label: string; value?: string; children?: any }) {
  return (
    <div className="flex justify-between items-center py-2">
      <span className="text-sm text-gray-400">{label}</span>
      {children || <span className="text-sm text-gray-200">{value || "未设置"}</span>}
    </div>
  );
}
