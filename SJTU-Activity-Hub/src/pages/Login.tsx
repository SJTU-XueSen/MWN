import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn, LogOut, User } from "lucide-react";
import { useUserStore } from "@/hooks/useUserStore";

export default function LoginPage() {
  const { user, login, logout } = useUserStore();
  const navigate = useNavigate();

  const [nickname, setNickname] = useState("");
  const [realName, setRealName] = useState("");
  const [contact, setContact] = useState("");

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nickname.trim()) return;
    login({
      nickname: nickname.trim(),
      realName: realName.trim(),
      contact: contact.trim(),
    });
    navigate("/student-activity");
  };

  if (user) {
    return (
      <main className="page-shell">
        <section className="hero-panel">
          <div>
            <span className="hero-badge">已登录</span>
            <h1>个人信息</h1>
            <p>以下信息将在申报活动时自动填入主办人和联系方式。</p>
          </div>
        </section>

        <section style={{ marginTop: 20 }}>
          <div className="rec-card">
            <div className="rec-card__body">
              <div className="rec-card__meta" style={{ flexWrap: "wrap" }}>
                <span className="rec-meta-item">
                  <span className="rec-meta-label">昵称</span>
                  <strong>{user.nickname}</strong>
                </span>
                <span className="rec-meta-item">
                  <span className="rec-meta-label">真实姓名</span>
                  <strong>{user.realName || "未填写"}</strong>
                </span>
                <span className="rec-meta-item">
                  <span className="rec-meta-label">联系方式</span>
                  <strong>{user.contact || "未填写"}</strong>
                </span>
              </div>
            </div>
            <div className="rec-card__actions">
              <button className="pill confirm-button" type="button" onClick={() => { logout(); navigate("/login"); }}>
                <LogOut size={14} />
                退出登录
              </button>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <span className="hero-badge">身份登记</span>
          <h1>填写个人信息</h1>
          <p>输入你的信息用于活动申报。昵称将公开显示，真实姓名和联系方式在申报时自动填入。</p>
        </div>
      </section>

      <form className="memo-form" style={{ flexDirection: "column", marginTop: 20 }} onSubmit={handleLogin}>
        <div className="memo-form__fields">
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
            <User size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
            <input
              type="text"
              style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
              placeholder="昵称（必填，公开显示）"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
            <User size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
            <input
              type="text"
              style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
              placeholder="真实姓名"
              value={realName}
              onChange={(e) => setRealName(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
            <User size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
            <input
              type="text"
              style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
              placeholder="联系方式（微信/手机等）"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
            />
          </div>
        </div>
        <button type="submit" className="search-submit" disabled={!nickname.trim()} style={{ alignSelf: "flex-end" }}>
          <LogIn size={16} />
          确认
        </button>
      </form>
    </main>
  );
}
