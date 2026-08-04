import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../auth";
import VoiceInput from "../components/VoiceInput";

export default function FutureChatPage() {
  const location = useLocation();
  const [futures, setFutures] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(
    (location.state as any)?.fsId ? { id: (location.state as any).fsId, label: (location.state as any).label } : null
  );
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api("/api/mirror/future-chats").then(setFutures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selected) {
      api(`/api/mirror/future-chats/${selected.id}/messages`).then(setMessages).catch(() => {});
    }
  }, [selected?.id]);

  async function send() {
    if (!input.trim() || !selected || sending) return;
    setSending(true);
    const content = input;
    setInput("");
    try {
      const res = await api(`/api/mirror/future-chats/${selected.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMessages((prev) => [
        ...prev,
        { role: "user", content, time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) },
        ...(res.assistant ? [{ role: "assistant", content: res.assistant.content, time: res.assistant.time }] : []),
      ]);
    } finally {
      setSending(false);
    }
  }

  async function clearChat() {
    if (!selected || !confirm("确定清空这段对话吗？")) return;
    await api(`/api/mirror/future-chats/${selected.id}/clear`, { method: "POST" });
    setMessages([]);
  }

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px", display: "grid", gridTemplateColumns: "240px 1fr", gap: 20, minHeight: "70vh" }}>
      <div>
        <h1 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 12 }}>未来对话</h1>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {futures.length === 0 && (
            <p style={{ fontSize: "0.78rem", color: "var(--text4)", lineHeight: 1.7 }}>
              还没有未来人格——先到<a href="/simulation" style={{ color: "var(--accent)" }}>人生模拟</a>生成一条路径
            </p>
          )}
          {futures.map((f) => (
            <button
              key={f.id}
              onClick={() => setSelected(f)}
              style={{
                padding: "12px 14px",
                borderRadius: 10,
                border: "1px solid",
                cursor: "pointer",
                textAlign: "left",
                background: selected?.id === f.id ? "var(--accent-bg3)" : "var(--input-bg)",
                borderColor: selected?.id === f.id ? "var(--accent-border2)" : "var(--border)",
              }}
            >
              <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text2)" }}>{f.label}</p>
              <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 3 }}>{f.target_year} 年 · 置信度 {Math.round((f.confidence || 0) * 100)}%</p>
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: "60vh", padding: 0, overflow: "hidden" }}>
        {!selected ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, color: "var(--text4)", fontSize: "0.85rem" }}>
            选择一个未来人格开始对话
          </div>
        ) : (
          <>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ fontWeight: 700, fontSize: "0.9rem" }}>{selected.label}</p>
                {selected.basis && <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 2 }}>{selected.basis}</p>}
              </div>
              <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: "0.7rem" }} onClick={clearChat}>清空</button>
            </div>

            <div style={{ flex: 1, padding: 18, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
              {messages.length === 0 && (
                <p style={{ color: "var(--text4)", fontSize: "0.78rem", textAlign: "center", marginTop: 40 }}>
                  开始对话——这个「可能的你」记得你的真实经历
                </p>
              )}
              {messages.map((m, i) => (
                <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                  <div
                    style={{
                      maxWidth: "75%",
                      padding: "10px 14px",
                      borderRadius: 12,
                      fontSize: "0.84rem",
                      lineHeight: 1.7,
                      background: m.role === "user" ? "var(--btn-grad)" : "var(--surface2)",
                      color: m.role === "user" ? "#fff" : "var(--text2)",
                      border: m.role === "user" ? "none" : "1px solid var(--border)",
                    }}
                  >
                    <p>{m.content}</p>
                    <p style={{ fontSize: "0.62rem", opacity: 0.7, marginTop: 6, textAlign: "right" }}>{m.time}</p>
                  </div>
                </div>
              ))}
              {sending && <p style={{ color: "var(--text4)", fontSize: "0.75rem", textAlign: "center" }}>未来的你正在思考...</p>}
            </div>

            <div style={{ padding: "12px 18px", borderTop: "1px solid var(--border)", display: "flex", gap: 10 }}>
              <VoiceInput onText={(t) => setInput((v) => v + t)} />
              <input
                className="input"
                placeholder="对未来的你说点什么..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
              />
              <button className="btn" onClick={send} disabled={sending}>发送</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
