import { useState } from "react";
import { BrowserRouter as Router, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { Bell, CalendarDays, Home, LogIn, Search, StickyNote, User } from "lucide-react";
import HomePage from "@/pages/Home";
import CompetitionSearch from "@/pages/CompetitionSearch";
import MemoPage from "@/pages/Memo";
import StudentActivityPage from "@/pages/StudentActivity";
import LoginPage from "@/pages/Login";
import { useUserStore } from "@/hooks/useUserStore";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useUserStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const user = useUserStore((s) => s.user);

  return (
    <nav className="app-nav">
      <div className="app-nav__inner">
        <a className="app-nav__brand" href="/">
          交大活动通
        </a>
        <button
          className="app-nav__toggle"
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="切换菜单"
        >
          <span className={menuOpen ? "toggle-bar toggle-bar--open" : "toggle-bar"} />
        </button>
        <ul className={`app-nav__links ${menuOpen ? "app-nav__links--open" : ""}`}>
          <li>
            <NavLink
              to="/"
              end
              className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              onClick={() => setMenuOpen(false)}
            >
              <Home size={16} />
              活动聚合
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/competition-search"
              className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              onClick={() => setMenuOpen(false)}
            >
              <Search size={16} />
              AI 检索
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/memo"
              className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              onClick={() => setMenuOpen(false)}
            >
              <StickyNote size={16} />
              备忘录
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/student-activity"
              className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              onClick={() => setMenuOpen(false)}
            >
              <CalendarDays size={16} />
              学生活动
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/login"
              className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              onClick={() => setMenuOpen(false)}
              style={user ? { gap: 6 } : undefined}
            >
              {user ? (
                <>
                  <User size={14} />
                  <span style={{ maxWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {user.nickname}
                  </span>
                </>
              ) : (
                <>
                  <LogIn size={16} />
                  登录
                </>
              )}
            </NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <Router>
      <NavBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
        <Route path="/competition-search" element={<ProtectedRoute><CompetitionSearch /></ProtectedRoute>} />
        <Route path="/memo" element={<ProtectedRoute><MemoPage /></ProtectedRoute>} />
        <Route path="/student-activity" element={<ProtectedRoute><StudentActivityPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
