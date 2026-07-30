import { useEffect, useState, useCallback } from "react";
import { RefreshCw, ChevronUp, ChevronDown } from "lucide-react";

const COLLAPSED_KEY = "collapsed_activities";

function getCollapsed(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(COLLAPSED_KEY) || "[]")); }
  catch { return new Set(); }
}
function saveCollapsed(ids: Set<string>) {
  localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...ids]));
}

export { getCollapsed }; // Dashboard 复用

export default function Activities() {
  const [data, setData] = useState<any>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(getCollapsed);
  const [hoverId, setHoverId] = useState<string | null>(null);

  function fetchData() { fetch("/api/activities?refresh=1").then(r => r.json()).then(setData); }
  useEffect(() => { fetchData(); }, []);

  const toggleCollapse = useCallback((id: string) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      saveCollapsed(next);
      return next;
    });
  }, []);

  const items = (data?.items || []) as any[];

  return (
    <main style={{ padding: "32px 40px", background: "var(--bg)", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>校园活动</h1>
          <p style={{ color: "#64748B", fontSize: "0.85rem" }}>SJTU 通知公告自动聚合</p>
        </div>
        <button className="btn-ghost" onClick={fetchData} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <RefreshCw size={14} /> 刷新
        </button>
      </div>

      {items.length === 0 && <p style={{ color: "#64748B", textAlign: "center", padding: 40 }}>暂无活动数据（确保 Express 3001 已启动）</p>}

      {items.map((a: any) => {
        const isCollapsed = collapsed.has(a.id);
        const isHovered = hoverId === a.id;
        return (
          <div
            key={a.id}
            className="card"
            style={{ marginBottom: 8, position: "relative", cursor: "default" }}
            onMouseEnter={() => setHoverId(a.id)}
            onMouseLeave={() => setHoverId(null)}
          >
            {/* 折叠/展开按钮 — hover 时显示 */}
            <button
              onClick={(e) => { e.preventDefault(); toggleCollapse(a.id); }}
              title={isCollapsed ? "展开" : "折叠"}
              style={{
                position: "absolute", right: 12, top: 12,
                width: 28, height: 28, borderRadius: "50%",
                border: "1px solid rgba(255,255,255,0.12)", cursor: "pointer",
                background: isHovered ? "rgba(0,0,0,0.06)" : "transparent",
                color: isHovered ? "#64748B" : "transparent",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.15s", zIndex: 2,
              }}
            >
              {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </button>

            {isCollapsed ? (
              /* 折叠态：只显示标题行 */
              <div style={{ paddingRight: 36 }}>
                <p style={{ fontWeight: 500, fontSize: "0.82rem", color: "#64748B" }}>{a.title}</p>
              </div>
            ) : (
              /* 展开态：完整内容 */
              <a href={a.url} target="_blank" style={{ display: "block", textDecoration: "none", color: "inherit", paddingRight: 36 }}>
                <p style={{ fontWeight: 600 }}>{a.title}</p>
                <p style={{ color: "#64748B", fontSize: "0.8rem", marginTop: 4 }}>{a.summary?.slice(0, 150)}</p>
                <div style={{ display: "flex", gap: 8, marginTop: 8, fontSize: "0.7rem", color: "#64748B" }}>
                  <span>{a.publishDate}</span>
                  {a.inferredEndDate && <span>截止: {a.inferredEndDate}</span>}
                </div>
              </a>
            )}
          </div>
        );
      })}
    </main>
  );
}
