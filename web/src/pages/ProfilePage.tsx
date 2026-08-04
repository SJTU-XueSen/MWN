import { useEffect, useState } from "react";
import { api } from "../auth";

const SKILL_OPTIONS = [
  "编程", "算法", "数据分析", "UI设计", "前端开发", "后端开发",
  "文案写作", "PPT制作", "演讲汇报", "调研访谈", "视频剪辑",
  "3D建模", "项目管理", "测试", "文档编写", "Python", "C++",
  "Java", "JavaScript", "MATLAB", "嵌入式", "硬件设计", "机器学习",
  "人工智能", "深度学习", "数学", "英语", "财务分析", "路演",
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api("/api/auth/me").then(setProfile).catch(() => {});
    api("/api/mirror/settings")
      .then((d) => {
        setSettings(d);
        setSkills(d.skill_tags || []);
      })
      .catch(() => {});
  }, []);

  async function saveSkills() {
    await api("/api/profile", { method: "POST", body: JSON.stringify({ skill_tags: skills }) });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!profile) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px" }}>
      <div className="card" style={{ textAlign: "center", marginBottom: 16 }}>
        <p style={{ fontSize: "3rem", marginBottom: 8 }}>🪞</p>
        <h1 style={{ fontSize: "1.3rem", fontWeight: 700 }}>{settings?.real_name || profile.real_name || profile.username}</h1>
        <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginTop: 4 }}>@{profile.username} · {settings?.email || profile.email}</p>
        {settings?.university && <p style={{ color: "var(--text4)", fontSize: "0.78rem", marginTop: 4 }}>{settings.university} · {settings.major} · {settings.grade}</p>}
        {settings?.bio && <p style={{ color: "var(--text3)", fontSize: "0.82rem", marginTop: 8 }}>{settings.bio}</p>}
        <p style={{ color: "var(--text4)", fontSize: "0.7rem", marginTop: 8 }}>加入于 {settings?.created_at} · 共 {settings?.total ?? 0} 条数据</p>
      </div>

      <div className="card">
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 4 }}>🛠 技能标签</h3>
        <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 12 }}>
          用于潜在队友匹配与任务技能评估（点击切换）
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
          {SKILL_OPTIONS.map((s) => {
            const active = skills.includes(s);
            return (
              <button
                key={s}
                onClick={() => setSkills(active ? skills.filter((x) => x !== s) : [...skills, s])}
                className="tag"
                style={{
                  cursor: "pointer",
                  border: "1px solid",
                  borderColor: active ? "var(--accent-border2)" : "var(--border)",
                  background: active ? "var(--accent-bg3)" : "var(--surface2)",
                  color: active ? "var(--accent)" : "var(--text3)",
                }}
              >
                {s}
              </button>
            );
          })}
        </div>
        {saved && <p style={{ color: "#34D399", fontSize: "0.8rem", marginBottom: 8 }}>✓ 已保存</p>}
        <button className="btn" onClick={saveSkills}>保存技能标签</button>
      </div>
    </div>
  );
}
