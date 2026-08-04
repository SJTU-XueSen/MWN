import { useEffect, useState } from "react";
import { api } from "../auth";

export default function SettingsPage() {
  const [data, setData] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [saved, setSaved] = useState(false);
  const [dsKey, setDsKey] = useState("");
  const [sttHotwords, setSttHotwords] = useState("");

  const load = () =>
    api("/api/mirror/settings").then((d) => {
      setData(d);
      setForm({
        real_name: d.real_name || "",
        email: d.email || "",
        university: d.university || "",
        major: d.major || "",
        grade: d.grade || "",
        bio: d.bio || "",
      });
    }).catch(() => {});

  useEffect(() => {
    load();
    setDsKey(localStorage.getItem("deepseek_api_key") || "");
    api("/api/mirror/stt/hotwords").then((d) => setSttHotwords((d.hotwords || []).join(", "))).catch(() => {});
  }, []);

  async function save() {
    await api("/api/mirror/settings", { method: "POST", body: JSON.stringify(form) });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function saveDsKey() {
    localStorage.setItem("deepseek_api_key", dsKey.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function saveHotwords() {
    await api("/api/mirror/stt/hotwords", {
      method: "POST",
      body: JSON.stringify({ words: sttHotwords.split(/[,，]/).map((w) => w.trim()).filter(Boolean) }),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function exportData() {
    const res = await api("/api/mirror/settings/export");
    const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `mwn-data-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  }

  if (!data) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 20 }}>⚙️ 设置</h1>
      {saved && <p style={{ color: "#34D399", fontSize: "0.8rem", marginBottom: 10 }}>✓ 已保存</p>}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 12 }}>个人信息</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <input className="input" placeholder="真实姓名" value={form.real_name} onChange={(e) => setForm({ ...form, real_name: e.target.value })} />
          <input className="input" placeholder="邮箱" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="input" placeholder="学校" value={form.university} onChange={(e) => setForm({ ...form, university: e.target.value })} />
          <input className="input" placeholder="专业" value={form.major} onChange={(e) => setForm({ ...form, major: e.target.value })} />
          <input className="input" placeholder="年级" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
          <input className="input" placeholder="个人简介" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
        </div>
        <button className="btn" style={{ marginTop: 12 }} onClick={save}>保存</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 12 }}>🤖 DeepSeek API Key（团队助手用）</h3>
        <input className="input" type="password" placeholder="sk-..." value={dsKey} onChange={(e) => setDsKey(e.target.value)} />
        <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 6 }}>
          可选——不填则使用系统配置的 Key
        </p>
        <button className="btn" style={{ marginTop: 10 }} onClick={saveDsKey}>保存 Key</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 12 }}>🎤 语音识别热词</h3>
        <input className="input" placeholder="逗号分隔，如：强化学习,机器人" value={sttHotwords} onChange={(e) => setSttHotwords(e.target.value)} />
        <button className="btn" style={{ marginTop: 10 }} onClick={saveHotwords}>保存热词</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 10 }}>📊 数据概况</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 8 }}>
          {Object.entries(data.stats || {}).map(([k, v]: any) => (
            <div key={k} style={{ padding: "10px", borderRadius: 10, background: "var(--surface2)", textAlign: "center" }}>
              <p style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--accent)" }}>{v}</p>
              <p style={{ fontSize: "0.65rem", color: "var(--text4)" }}>{k}</p>
            </div>
          ))}
        </div>
        <button className="btn-ghost" style={{ marginTop: 12 }} onClick={exportData}>导出全部数据（JSON）</button>
      </div>

      <div className="card">
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 8, color: "#F87171" }}>危险区</h3>
        <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginBottom: 10 }}>
          注销账户将永久删除你的全部记录、事件、记忆与人格数据
        </p>
        <button
          className="btn-ghost"
          style={{ color: "#F87171", borderColor: "rgba(248,113,113,0.3)" }}
          onClick={async () => {
            if (confirm("确定注销账户吗？此操作不可恢复！")) {
              await api("/api/mirror/settings/delete-account", { method: "POST" });
              window.location.href = "/login";
            }
          }}
        >
          注销账户
        </button>
      </div>
    </div>
  );
}
