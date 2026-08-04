import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";

interface Notif {
  id: number;
  title: string;
  message: string;
  read: boolean;
  meta: Record<string, any>;
  createdAt: string;
}

/** 通知铃铛 — 显示未读数，支持组队邀请接受/拒绝 */
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notif[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const load = () =>
    fetch("/api/notifications", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setItems(Array.isArray(d) ? d : []))
      .catch(() => {});

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000); // 30s 轮询
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("mousedown", onClick);
    };
  }, []);

  const unread = items.filter((n) => !n.read).length;

  async function act(n: Notif, action: "accept" | "decline" | "read") {
    setBusy(n.id);
    setMsg("");
    try {
      const resp = await fetch(`/api/notifications/${n.id}/${action}`, {
        method: "POST",
        credentials: "include",
      });
      const data = await resp.json();
      if (!resp.ok) setMsg(data.error || "操作失败");
      else if (action === "accept") setMsg("✅ 已加入战队");
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
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
        <Bell size={15} />
        通知
        {unread > 0 && (
          <span style={{
            marginLeft: "auto",
            minWidth: 18,
            height: 18,
            borderRadius: 9,
            background: "var(--btn-grad)",
            color: "#fff",
            fontSize: "0.62rem",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 5px",
          }}>
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            left: 8,
            bottom: "100%",
            width: 320,
            maxHeight: 360,
            overflowY: "auto",
            background: "var(--sidebar-bg)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            boxShadow: "0 12px 40px rgba(0,0,0,0.4)",
            zIndex: 200,
            padding: 10,
          }}
        >
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text2)", padding: "6px 8px", marginBottom: 4 }}>
            通知
          </p>
          {msg && <p style={{ fontSize: "0.72rem", color: "#34D399", padding: "4px 8px" }}>{msg}</p>}
          {items.length === 0 && (
            <p style={{ fontSize: "0.75rem", color: "var(--text4)", padding: "12px 8px", textAlign: "center" }}>暂无通知</p>
          )}
          {items.map((n) => (
            <div key={n.id} style={{ padding: "10px 8px", borderRadius: 8, background: n.read ? "transparent" : "var(--accent-bg)", marginBottom: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                <span style={{ fontSize: "0.74rem", fontWeight: 600, color: "var(--text2)" }}>{n.title}</span>
                <span style={{ fontSize: "0.6rem", color: "var(--text4)" }}>
                  {n.createdAt ? new Date(n.createdAt).toLocaleDateString("zh-CN") : ""}
                </span>
              </div>
              <p style={{ fontSize: "0.7rem", color: "var(--text3)", lineHeight: 1.5, marginBottom: 6 }}>{n.message}</p>
              {n.meta?.team_id && !n.read ? (
                <div style={{ display: "flex", gap: 6 }}>
                  <button className="btn" style={{ padding: "4px 12px", fontSize: "0.68rem" }} disabled={busy === n.id} onClick={() => act(n, "accept")}>
                    接受邀请
                  </button>
                  <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.68rem", color: "#F87171" }} disabled={busy === n.id} onClick={() => act(n, "decline")}>
                    拒绝
                  </button>
                </div>
              ) : (
                !n.read && (
                  <button className="btn-ghost" style={{ padding: "3px 10px", fontSize: "0.65rem" }} onClick={() => act(n, "read")}>
                    标记已读
                  </button>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
