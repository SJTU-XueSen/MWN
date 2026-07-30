import { BrowserRouter, Routes, Route, NavLink, useLocation, Navigate } from "react-router-dom";
import { Home, PenLine, Fingerprint, FlaskConical, MessageCircle, CalendarDays, Search, StickyNote, User, LogIn, Settings, Target, FileText, Globe, PlusSquare, Map, Telescope, Briefcase } from "lucide-react";
import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import Activities from "./pages/Activities";
import AiSearch from "./pages/AiSearch";
import Memo from "./pages/Memo";
import StudentActivity from "./pages/StudentActivity";
import Login from "./pages/Login";
import RegisterPage from "./pages/Register";
import Journal from "./pages/Journal";
import JournalDetail from "./pages/JournalDetail";
import EventsPage from "./pages/EventsPage";
import EventDetail from "./pages/EventDetail";
import PersonaPage from "./pages/PersonaPage";
import GoalsPage from "./pages/GoalsPage";
import SimulationPage from "./pages/SimulationPage";
import SimulationDetail from "./pages/SimulationDetail";
import FutureChatPage from "./pages/FutureChatPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import ReferencesPage from "./pages/ReferencesPage";
import ProfilePage from "./pages/ProfilePage";
import ExperiencePage from "./pages/ExperiencePage";
import ReportDetail from "./pages/ReportDetail";
import ConnectionsPage from "./pages/ConnectionsPage";
import WorkPage from "./pages/WorkPage";
import ChatPage from "./pages/ChatPage";
import ProjectionPage from "./pages/ProjectionPage";

let _userCache: any = null;
function useAuth() {
  const [user, setUser] = useState<any>(undefined);
  useEffect(() => {
    async function check() {
      // 快速路径：从 cookie 直接读（mirror_uid 不是 httponly）
      const muid = document.cookie.split("; ").find(c => c.startsWith("mirror_uid="))?.split("=")[1];
      if (muid) {
        const uname = document.cookie.split("; ").find(c => c.startsWith("mirror_username="))?.split("=")[1] || "";
        const u = { id: parseInt(muid), username: decodeURIComponent(uname), real_name: decodeURIComponent(uname) };
        _userCache = u; setUser(u);
        // 后台验证
        fetch("/api/auth/me", { credentials: "include" }).then(r => r.json()).then(d => {
          if (d && d.id) { _userCache = d; setUser(d); }
        }).catch(() => {});
        return;
      }
      // 慢路径：fetch 验证
      for (let i = 0; i < 3; i++) {
        const d = await fetch("/api/auth/me", { credentials: "include" }).then(r => r.json()).catch(() => null);
        if (d && d.id) { const u = d; _userCache = u; setUser(u); return; }
        await new Promise(r => setTimeout(r, 500));
      }
      setUser(null);
    }
    check();
  }, []);
  return user;
}

function Sidebar() {
  const user = useAuth(); const loc = useLocation();
  const a = (p: string, exact?: boolean) => exact ? loc.pathname === p : (loc.pathname === p || loc.pathname.startsWith(p + "/"));
  const s = (active: boolean): any => ({ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8, color: active ? "var(--accent)" : "var(--text4)", textDecoration: "none", background: active ? "rgba(99,102,241,0.15)" : "transparent", marginBottom: 1, transition: "all 0.15s", fontSize: "0.84rem", fontWeight: active ? 600 : 400 });

  return (
    <aside style={{ width: 220, minWidth: 220, height: "100vh", overflowY: "auto", background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)", display: "flex", flexDirection: "column" }}>
      <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 16px", borderBottom: "1px solid var(--sidebar-border)", textDecoration: "none" }}>
        <span style={{ fontSize: "1.5rem" }}>🪞</span><div><p style={{ fontWeight: 700, color: "var(--text)", margin: 0, fontSize: "0.9rem" }}>镜·界·联</p><p style={{ fontSize: "0.6rem", color: "var(--text4)", margin: 0 }}>认识自己 · 走向世界 · 与他人共同创造</p></div>
      </a>
      <nav style={{ flex: 1, padding: "12px 8px", overflowY: "auto" }}>
        <NavLink to="/" end style={s(a("/"))}><Home size={15} />首页</NavLink>
        <Section label="🪞 认识自己" />
        <NavLink to="/journal" style={s(a("/journal"))}><PenLine size={15} />日常记录</NavLink>
        <NavLink to="/events" style={s(a("/events"))}><Map size={15} />人生地图</NavLink>
        <NavLink to="/persona" style={s(a("/persona"))}><Fingerprint size={15} />数字人格</NavLink>
        <NavLink to="/simulation" style={s(a("/simulation"))}><FlaskConical size={15} />人生模拟</NavLink>
        <NavLink to="/projection" style={s(a("/projection"))}><Telescope size={15} />推演人生</NavLink>
        <NavLink to="/future-chat" style={s(a("/future-chat"))}><MessageCircle size={15} />未来对话</NavLink>
        <NavLink to="/goals" style={s(a("/goals"))}><Target size={15} />人生目标</NavLink>
        <NavLink to="/reports" style={s(a("/reports"))}><FileText size={15} />成长报告</NavLink>
        <Section label="🌏 走向世界" />
        <NavLink to="/connections" end style={s(a("/connections", true))}><CalendarDays size={15} />活动大厅</NavLink>
        <NavLink to="/ai-search" style={s(a("/ai-search"))}><Search size={15} />AI 检索</NavLink>
        <NavLink to="/memo" style={s(a("/memo"))}><StickyNote size={15} />备忘录</NavLink>
        <NavLink to="/references" style={s(a("/references"))}><Globe size={15} />人生参考</NavLink>
        <Section label="🤝 与他人连接" />
        <NavLink to="/connections/chat" style={s(a("/connections/chat"))}><MessageCircle size={15} />聊天</NavLink>
        <NavLink to="/connections/work" style={s(a("/connections/work"))}><Briefcase size={15} />工作台</NavLink>
      </nav>
      <div style={{ padding: "12px 8px", borderTop: "1px solid var(--sidebar-border)" }}>
        <NavLink to="/settings" style={s(a("/settings"))}><Settings size={15} />设置</NavLink>
        <NavLink to="/profile" style={s(a("/profile"))}><User size={15} />{user ? (user.real_name || user.username) : "登录"}</NavLink>
        {user && <a href="http://127.0.0.1:5000/auth/logout" style={s(false)} onClick={() => { _userCache = null; }}><LogIn size={15} style={{ transform: "scaleX(-1)" }} />退出</a>}
      </div>
    </aside>
  );
}
function Section({ label, dim }: { label: string; dim?: boolean }) {
  return <p style={{ fontSize: "0.6rem", fontWeight: 600, textTransform: "uppercase", color: "#64748B", padding: "14px 8px 2px", margin: 0, letterSpacing: "0.05em", opacity: dim ? 0.4 : 1 }}>{label}</p>;
}

function Protected({ children }: { children: any }) { const user = useAuth(); if (user === undefined) return null; if (user === null) return <Navigate to="/login" replace />; return children; }

let _prevPath = "";
function trackEvent(event: string, detail?: any) {
  fetch("/api/track", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event, detail, timestamp: new Date().toISOString() }) }).catch(() => {});
}
function Tracker() {
  const loc = useLocation();
  useEffect(() => {
    const prev = _prevPath;
    _prevPath = loc.pathname;
    trackEvent("page_view", { path: loc.pathname, referrer: prev || "direct" });
  }, [loc.pathname]);
  // 全局点击追踪：带有 data-track 属性的元素自动上报
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const el = (e.target as HTMLElement).closest?.("[data-track]") as HTMLElement | null;
      if (el) {
        const action = el.dataset.track;
        const label = el.dataset.trackLabel || el.textContent?.trim().slice(0, 60) || "";
        trackEvent("click", { action, label, path: location.pathname });
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);
  return null;
}

function LoadingOverlay() {
  useEffect(() => {
    const origFetch = window.fetch;
    let active = 0;
    window.fetch = (...args: any[]) => {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request).url || '';
      const init = args[1] as RequestInit | undefined;
      const method = (init?.method || 'GET').toUpperCase();
      // 只有写操作（非 GET/HEAD）才显示 loading 遮罩
      if (method === 'GET' || method === 'HEAD') return origFetch(...args);
      const isAI = url.includes('/api/mirror/') || url.includes('/simulation') || url.includes('/api/ai-search');
      if (!isAI) return origFetch(...args);
      active++;
      const el = document.getElementById('global-loading');
      if (el) el.style.display = 'flex';
      const result = origFetch(...args);
      result.finally(() => { active--; if (active <= 0 && el) el.style.display = 'none'; });
      return result;
    };
    return () => { window.fetch = origFetch; };
  }, []);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<AppShell />} />
      </Routes>
      <Tracker />
      <LoadingOverlay />
      <div id="global-loading" style={{ display: "none", position: "fixed", inset: 0, zIndex: 9999, background: "var(--overlay)", backdropFilter: "blur(4px)", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 40, height: 40, border: "3px solid var(--border)", borderTopColor: "var(--accent2)", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ color: "var(--text)", fontSize: "0.9rem" }}>AI 正在分析中...</p>
          <p style={{ color: "var(--text4)", fontSize: "0.75rem", marginTop: 4 }}>请勿关闭页面</p>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </BrowserRouter>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    try { const v = localStorage.getItem("theme"); return v === null ? true : v === "dark"; } catch { return true; }
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {}
  }, [dark]);
  return (
    <button onClick={() => setDark(!dark)}
      style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8, border: "none", background: "transparent", color: "var(--text4)", cursor: "pointer", fontSize: "0.82rem", width: "100%", textAlign: "left" }}>
      {dark ? <><span>☀️</span> 浅色模式</> : <><span>🌙</span> 深色模式</>}
    </button>
  );
}

function AppShell() {
  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg)", overflow: "hidden" }}>
      <Sidebar />
      <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <Routes>
          <Route path="/" element={<HomeOrLanding />} />
          <Route path="/journal" element={<Protected><Journal /></Protected>} />
          <Route path="/journal/:id" element={<Protected><JournalDetail /></Protected>} />
          <Route path="/events" element={<Protected><EventsPage /></Protected>} />
          <Route path="/events/:id" element={<Protected><EventDetail /></Protected>} />
          <Route path="/persona" element={<Protected><PersonaPage /></Protected>} />
          <Route path="/simulation" element={<Protected><SimulationPage /></Protected>} />
          <Route path="/simulation/:id" element={<Protected><SimulationDetail /></Protected>} />
          <Route path="/projection" element={<Protected><ProjectionPage /></Protected>} />
          <Route path="/future-chat" element={<Protected><FutureChatPage /></Protected>} />
          <Route path="/goals" element={<Protected><GoalsPage /></Protected>} />
          <Route path="/reports" element={<Protected><ReportsPage /></Protected>} />
          <Route path="/reports/:id" element={<Protected><ReportDetail /></Protected>} />
          <Route path="/experience/:fsId" element={<Protected><ExperiencePage /></Protected>} />
          <Route path="/connections" element={<Protected><ConnectionsPage /></Protected>} />
          <Route path="/connections/chat" element={<Protected><ChatPage /></Protected>} />
          <Route path="/connections/work" element={<Protected><WorkPage /></Protected>} />
          <Route path="/activities" element={<Protected><Activities /></Protected>} />
          <Route path="/ai-search" element={<Protected><AiSearch /></Protected>} />
          <Route path="/memo" element={<Protected><Memo /></Protected>} />
          <Route path="/student-activity" element={<Protected><StudentActivity /></Protected>} />
          <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
          <Route path="/references" element={<Protected><ReferencesPage /></Protected>} />
          <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
        </Routes>
      </div>
    </div>
  );
}

function HomeOrLanding() {
  const user = useAuth();
  if (user === undefined) return <div style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh",color:"var(--text4)"}}>加载中...</div>;
  return user ? <Dashboard /> : <Navigate to="/login" replace />;
}
