import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

function getIcon(label: string): string {
  if (label.includes("创造")) return "🔧";
  if (label.includes("思考") || label.includes("真理") || label.includes("探索")) return "🔬";
  if (label.includes("开拓") || label.includes("创业")) return "🚀";
  if (label.includes("连接")) return "🌐";
  return "🪞";
}

export default function FutureChatPage() {
  const [futureSelves, setFutureSelves] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch("/api/mirror/future-chats").then(r => r.json()).then(d => setFutureSelves(Array.isArray(d) ? d : d.future_selves || []));
  }, []);

  useEffect(() => {
    if (selected) {
      fetch(`/api/mirror/future-chats/${selected.id}/messages`).then(r => r.json()).then(setMessages);
    }
  }, [selected]);

  useEffect(() => {
    if (chatAreaRef.current) chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || !selected || sending) return;
    setSending(true);
    const msg = input.trim();
    setInput("");

    try {
      const r = await fetch(`/api/mirror/future-chats/${selected.id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: msg }),
      });
      if (r.ok) {
        const d = await r.json();
        const newMsgs: any[] = [];
        if (d.user) newMsgs.push({ ...d.user, created_at: new Date().toISOString() });
        if (d.assistant) newMsgs.push({ ...d.assistant, created_at: new Date().toISOString() });
        setMessages(prev => [...prev, ...newMsgs]);
      }
    } catch (e) {
      console.error(e);
    }
    setSending(false);
  }

  function clearChat() {
    if (!confirm("清除所有对话记录？") || !selected) return;
    fetch(`/api/mirror/future-chats/${selected.id}/clear`, { method: "POST" }).then(() => setMessages([]));
  }

  // List View
  if (!selected) {
    return (
      <div className="max-w-3xl mx-auto px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold">与未来的自己对话</h2>
          <p className="#475569 text-sm mt-1">选择一个你生成过的未来人格，与ta进行对话</p>
        </div>

        {futureSelves.length > 0 ? (
          <div className="space-y-3">
            {futureSelves.map(fs => (
              <div key={fs.id} onClick={() => setSelected(fs)} className="card p-5 block no-underline group cursor-pointer">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-2xl flex-shrink-0">
                      {getIcon(fs.persona_label || fs.label || "")}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white group-hover:text-indigo-400 transition">{fs.persona_label || fs.label}</h3>
                      <p className="text-xs text-gray-500 mt-1">
                        {fs.target_year}年 · 置信度{Math.round((fs.confidence || 0) * 100)}%
                        {fs.basis_summary && <span className="text-gray-600 ml-2">{fs.basis_summary.slice(0, 60)}</span>}
                      </p>
                    </div>
                  </div>
                  <i className="fa-solid fa-comment-dots text-gray-600 group-hover:text-indigo-400 transition text-lg"></i>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-16 text-center">
            <div className="text-6xl mb-5">💬</div>
            <h3 className="text-xl font-semibold text-gray-400 mb-2">还没有未来人格</h3>
            <p className="text-sm text-gray-500 mb-8">先进行一次人生模拟，生成未来人格后就能对话了</p>
            <button onClick={() => nav("/simulation")} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold inline-block">
              开始人生模拟 →
            </button>
          </div>
        )}
      </div>
    );
  }

  // Chat View
  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto px-8">
      {/* 顶部 */}
      <div className="py-4 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => { setSelected(null); setMessages([]); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </button>
          <div>
            <h3 className="font-semibold text-white text-sm">{selected.persona_label || selected.label}</h3>
            <p className="text-xs text-gray-500">
              <span className="#8b5e3c">{selected.target_year}年</span>
              的版本 · 跨越 {selected.target_year ? selected.target_year - 2026 : 5} 年
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="tag bg-white/5 text-gray-500 text-xs">置信度 {Math.round((selected.confidence || 0) * 100)}%</span>
          <button onClick={clearChat} className="text-xs text-gray-600 hover:text-rose-400 transition px-2 py-1">清除</button>
        </div>
      </div>

      {/* 对话区域 */}
      <div ref={chatAreaRef} className="flex-1 overflow-y-auto py-6 space-y-5">
        {messages.length > 0 ? (
          messages.map(msg => (
            msg.role === "user" ? (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[75%] p-3.5 rounded-2xl rounded-br-md bg-indigo-500/20 border border-indigo-500/20">
                  <p className="text-xs text-indigo-400 mb-1">2026年的你</p>
                  <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs text-gray-600 mt-1 text-right">
                    {msg.created_at ? new Date(msg.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}
                  </p>
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-sm flex-shrink-0 mt-1">🪞</div>
                <div className="max-w-[75%] p-3.5 rounded-2xl rounded-bl-md bg-white/5 border border-white/10">
                  <p className="text-xs text-gray-500 mb-1">{selected.persona_label || selected.label} · {selected.target_year}年</p>
                  <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs text-gray-600 mt-1">
                    {msg.created_at ? new Date(msg.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}
                  </p>
                </div>
              </div>
            )
          ))
        ) : (
          <div className="text-center py-12">
            <div className="text-5xl mb-4">🪞</div>
            <p className="#475569 text-sm mb-1">这是你和"{selected.persona_label || selected.label}"的对话空间</p>
            <p className="text-gray-600 text-xs">你可以问ta关于未来的选择、困惑，或者只是聊聊</p>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="py-4 border-t border-white/5 flex-shrink-0">
        <div className="flex gap-3">
          <input
            className="input flex-1"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="向未来的自己提问..."
            autoFocus
            autoComplete="off"
          />
          <button onClick={sendMessage} disabled={sending || !input.trim()} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex-shrink-0">
            <i className="fa-solid fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  );
}
