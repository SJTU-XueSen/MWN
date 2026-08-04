import { useEffect, useState } from "react";
import {
  Briefcase,
  CalendarDays,
  FileText,
  Fingerprint,
  FlaskConical,
  Globe,
  Home,
  LogIn,
  Map,
  MessageCircle,
  PenLine,
  Search,
  Settings,
  StickyNote,
  Target,
  Telescope,
  User,
} from "lucide-react";
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import Journal from "./pages/Journal";
import JournalDetail from "./pages/JournalDetail";
import EventsPage from "./pages/EventsPage";
import EventDetail from "./pages/EventDetail";
import PersonaPage from "./pages/PersonaPage";
import GoalsPage from "./pages/GoalsPage";
import SimulationPage from "./pages/SimulationPage";
import SimulationDetail from "./pages/SimulationDetail";
import ProjectionPage from "./pages/ProjectionPage";
import FutureChatPage from "./pages/FutureChatPage";
import ReportsPage from "./pages/ReportsPage";
import ReportDetail from "./pages/ReportDetail";
import ExperiencePage from "./pages/ExperiencePage";
import ConnectionsPage from "./pages/ConnectionsPage";
import ChatPage from "./pages/ChatPage";
import WorkPage from "./pages/WorkPage";
import AiSearch from "./pages/AiSearch";
import Memo from "./pages/Memo";
import StudentActivity from "./pages/StudentActivity";
import SettingsPage from "./pages/SettingsPage";
import ReferencesPage from "./pages/ReferencesPage";
import ProfilePage from "./pages/ProfilePage";
import Login from "./pages/Login";
import NotificationBell from "./components/NotificationBell";

function Sidebar() {
  const { user } = useAuth();
  const loc = useLocation();
  const a = (p: string, exact?: boolean) =>
    exact ? loc.pathname === p : loc.pathname === p || loc.pathname.startsWith(p + "/");
  const s = (active: boolean): any => ({
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 12px",
    borderRadius: 8,
    color: active ? "var(--accent)" : "var(--text4)",
    textDecoration: "none",
    background: active ? "rgba(99,102,241,0.15)" : "transparent",
    marginBottom: 1,
    transition: "all 0.15s",
    fontSize: "0.84rem",
    fontWeight: active ? 600 : 400,
  });

  return (
    <aside
      style={{
        width: 220,
        minWidth: 220,
        height: "100vh",
        overflowY: "auto",
        background: "var(--sidebar-bg)",
        borderRight: "1px solid var(--sidebar-border)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 16px", borderBottom: "1px solid var(--sidebar-border)", textDecoration: "none" }}>
        <span style={{ fontSize: "1.5rem" }}>🪞</span>
        <div>
          <p style={{ fontWeight: 700, color: "var(--text)", margin: 0, fontSize: "0.9rem" }}>镜·界·联</p>
          <p style={{ fontSize: "0.6rem", color: "var(--text4)", margin: 0 }}>认识自己 · 走向世界 · 与他人共同创造</p>
        </div>
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
        <NavLink to="/connections/chat" style={s(a("/connections/chat"))}><MessageCircle size={15} />团队聊天</NavLink>
        <NavLink to="/connections/work" style={s(a("/connections/work"))}><Briefcase size={15} />工作台</NavLink>
        <Section label="🧰 更多" dim />
        <NavLink to="/ai-search" style={s(a("/ai-search"))}><Search size={15} />AI 检索</NavLink>
        <NavLink to="/memo" style={s(a("/memo"))}><StickyNote size={15} />备忘录</NavLink>
        <NavLink to="/references" style={s(a("/references"))}><Globe size={15} />人生参考</NavLink>
      </nav>
      <div style={{ padding: "12px 8px", borderTop: "1px solid var(--sidebar-border)" }}>
        {user && <NotificationBell />}
        <NavLink to="/settings" style={s(a("/settings"))}><Settings size={15} />设置</NavLink>
        <NavLink to="/profile" style={s(a("/profile"))}><User size={15} />{user?.real_name || user?.username || "登录"}</NavLink>
        {user && <LogoutButton />}
      </div>
    </aside>
  );
}

function LogoutButton() {
  const { logout } = useAuth();
  const nav = useNavigate();
  return (
    <button
      onClick={async () => {
        await fetch("/api/auth/logout", { method: "POST", credentials: "include" }).catch(() => {});
        logout();
        nav("/login");
      }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 12px",
        borderRadius: 8,
        border: "none",
        background: "transparent",
        color: "var(--text4)",
        cursor: "pointer",
        fontSize: "0.84rem",
        width: "100%",
        textAlign: "left",
      }}
    >
      <LogIn size={15} style={{ transform: "scaleX(-1)" }} />退出
    </button>
  );
}

function Section({ label, dim }: { label: string; dim?: boolean }) {
  return (
    <p style={{ fontSize: "0.6rem", fontWeight: 600, textTransform: "uppercase", color: "#64748B", padding: "14px 8px 2px", margin: 0, letterSpacing: "0.05em", opacity: dim ? 0.5 : 1 }}>
      {label}
    </p>
  );
}

function Protected({ children }: { children: any }) {
  const { user, ready } = useAuth();
  if (!ready) return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", color: "var(--text4)" }}>加载中...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function HomeOrLanding() {
  const { user, ready } = useAuth();
  if (!ready) return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", color: "var(--text4)" }}>加载中...</div>;
  return user ? <Dashboard /> : <Navigate to="/login" replace />;
}

function Tracker() {
  const loc = useLocation();
  useEffect(() => {
    fetch("/api/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: "page_view", detail: { path: loc.pathname } }),
      credentials: "include",
    }).catch(() => {});
  }, [loc.pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<AppShell />} />
      </Routes>
      <Tracker />
    </>
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
