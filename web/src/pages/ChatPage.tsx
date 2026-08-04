import { useEffect, useRef, useState } from "react";
import { api } from "../auth";

export default function ChatPage() {
  const [chatType, setChatType] = useState<"group" | "team">("group");
  const [messages, setMessages] = useState<any[]>([]);
  const [friends, setFriends] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [aiInput, setAiInput] = useState("");
  const [aiReply, setAiReply] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [myId, setMyId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadMessages = () =>
    api(`/api/chat/messages/${chatType}`).then((d) => setMessages(d.messages || [])).catch(() => {});

  useEffect(() => {
    api("/api/auth/me").then((u) => setMyId(u.id)).catch(() => {});
    api("/api/potential-friends").then((d) => setFriends(d.friends || [])).catch(() => {});
  }, []);

  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatType]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiReply]);

  async function send() {
    if (!input.trim()) return;
    const content = input;
    setInput("");
    try {
      await api("/api/chat/send", {
        method: "POST",
        body: JSON.stringify({ content, chat_type: chatType }),
      });
    } catch {
      setInput(content);
      return;
    }
    loadMessages();
  }

  async function aiChat() {
    if (!aiInput.trim() || aiLoading) return;
    setAiLoading(true);
    setAiReply("");
    try {
      const dsKey = localStorage.getItem("deepseek_api_key") || "";
      const res = await api("/api/deepseek/chat", {
        method: "POST",
        body: JSON.stringify({ messages: [{ role: "user", content: aiInput }], api_key: dsKey }),
      });
      setAiReply(res.reply || res.error || "请求失败");
    } catch (e: any) {
      setAiReply(e.message || "请求失败");
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px", display: "grid", gridTemplateColumns: "1fr 280px", gap: 20 }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <h1 style={{ fontSize: "1.3rem", fontWeight: 700 }}>💬 团队聊天</h1>
          {(["group", "team"] as const).map((t) => (
            <button key={t} className="badge" style={{
              cursor: "pointer",
              border: "1px solid",
              borderColor: chatType === t ? "var(--accent-border2)" : "var(--border)",
              background: chatType === t ? "var(--accent-bg3)" : "transparent",
              color: chatType === t ? "var(--accent)" : "var(--text4)",
              padding: "6px 14px",
            }} onClick={() => setChatType(t)}>
              {t === "group" ? "组内聊天" : "团队频道"}
            </button>
          ))}
        </div>

        <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: "55vh", padding: 0, overflow: "hidden" }}>
          <div style={{ flex: 1, padding: 18, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
            {messages.length === 0 && (
              <p style={{ color: "var(--text4)", fontSize: "0.78rem", textAlign: "center", marginTop: 40 }}>
                还没有消息——加入战队后即可聊天
              </p>
            )}
            {messages.map((m) => (
              <div key={m.id} style={{ display: "flex", justifyContent: m.user_id === myId ? "flex-end" : "flex-start" }}>
                <div style={{ maxWidth: "75%" }}>
                  {m.user_id !== myId && <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginBottom: 3 }}>{m.user_name}</p>}
                  <div style={{
                    padding: "9px 13px",
                    borderRadius: 12,
                    fontSize: "0.84rem",
                    lineHeight: 1.7,
                    background: m.user_id === myId ? "var(--btn-grad)" : "var(--surface2)",
                    color: m.user_id === myId ? "#fff" : "var(--text2)",
                    border: m.user_id === myId ? "none" : "1px solid var(--border)",
                  }}>
                    {m.image_url && <img src={m.image_url} alt="" style={{ maxWidth: 180, borderRadius: 8, marginBottom: 6, display: "block" }} />}
                    {m.content && <p>{m.content}</p>}
                    <p style={{ fontSize: "0.6rem", opacity: 0.7, marginTop: 4, textAlign: "right" }}>{m.created_at}</p>
                  </div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div style={{ padding: "12px 18px", borderTop: "1px solid var(--border)", display: "flex", gap: 10 }}>
            <input className="input" placeholder="输入消息..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
            <button className="btn" onClick={send}>发送</button>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* AI 助手 */}
        <div className="card">
          <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 8 }}>🤖 DeepSeek 协作助手</h3>
          <textarea className="input" rows={3} placeholder="问团队相关的问题..." value={aiInput} onChange={(e) => setAiInput(e.target.value)} />
          <button className="btn" style={{ width: "100%", marginTop: 8 }} onClick={aiChat} disabled={aiLoading}>
            {aiLoading ? "思考中..." : "提问"}
          </button>
          {aiReply && (
            <div style={{ marginTop: 10, padding: 10, borderRadius: 10, background: "var(--accent-bg2)", fontSize: "0.78rem", lineHeight: 1.7, whiteSpace: "pre-wrap", color: "var(--text2)" }}>
              {aiReply}
            </div>
          )}
          <p style={{ fontSize: "0.65rem", color: "var(--text4)", marginTop: 8 }}>
            提示：可在设置中填入自己的 DeepSeek API Key
          </p>
        </div>

        {/* 潜在队友 */}
        <div className="card">
          <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 10 }}>👥 潜在队友</h3>
          {friends.length === 0 && <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>暂无推荐</p>}
          {friends.map((f) => (
            <div key={f.user_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.82rem", fontWeight: 600 }}>{f.real_name}</span>
              <span className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{f.match_score}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
