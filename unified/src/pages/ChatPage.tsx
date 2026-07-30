import { useEffect, useState, useRef } from "react";
import VoiceInput from "../components/VoiceInput";

export default function ChatPage() {
  // ── 潜在好友 ──
  const [friends, setFriends] = useState<any[]>([]);

  // ── 聊天 ──
  const [chatType, setChatType] = useState<"group" | "team">("group");
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [showChat, setShowChat] = useState(true);
  const chatRef = useRef<HTMLDivElement>(null);

  // ── DeepSeek ──
  const [dsMessages, setDsMessages] = useState<{ role: string; content: string }[]>([]);
  const [dsInput, setDsInput] = useState("");
  const [dsKey, setDsKey] = useState(() => { try { return localStorage.getItem("deepseek_api_key") || ""; } catch { return ""; } });

  useEffect(() => { loadFriends(); loadChatMessages("group"); }, []);

  async function loadFriends() {
    try {
      const r = await fetch("/nexus/api/potential-friends");
      if (r.ok) { const d = await r.json(); setFriends(d.friends || []); }
    } catch {}
  }

  async function loadChatMessages(type: string) {
    try {
      const r = await fetch(`/nexus/api/chat/messages/${type}`);
      if (r.ok) { const d = await r.json(); setChatMessages(d.messages || []); }
    } catch {}
  }

  async function sendChat() {
    if (!chatInput.trim()) return;
    const content = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { id: Date.now(), content, user_name: "我", is_mine: true, created_at: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) }]);
    try {
      await fetch("/nexus/api/chat/send", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content, chat_type: chatType }) });
      await new Promise(r => setTimeout(r, 500));
      loadChatMessages(chatType);
    } catch {}
  }

  async function sendDeepseek() {
    const msg = dsInput.trim();
    if (!msg) return;
    if (msg.startsWith("sk-") && !msg.includes(" ")) { localStorage.setItem("deepseek_api_key", msg); setDsKey(msg); setDsInput(""); return; }
    if (!dsKey) { setDsMessages(prev => [...prev, { role: "bot", content: "请先粘贴你的 DeepSeek API Key（以 sk- 开头）。" }]); return; }
    setDsMessages(prev => [...prev, { role: "user", content: msg }]);
    setDsInput("");
    try {
      const r = await fetch("/nexus/api/deepseek/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: dsMessages.concat([{ role: "user", content: msg }]).map(m => ({ role: m.role === "bot" ? "assistant" : "user", content: m.content })), api_key: dsKey }),
      });
      const d = await r.json();
      setDsMessages(prev => [...prev, { role: "bot", content: d.reply || d.error || "请求失败" }]);
    } catch {}
  }

  useEffect(() => { chatRef.current?.scrollTo(0, chatRef.current.scrollHeight); }, [chatMessages]);

  return (
    <div className="max-w-5xl mx-auto px-8 py-8">
      <h2 className="text-2xl font-bold mb-6">💬 聊天与连接</h2>

      <div className="grid gap-6" style={{ gridTemplateColumns: "300px 1fr 280px" }}>
        {/* 左侧：DeepSeek 助手 */}
        <div className="card flex flex-col" style={{ maxHeight: 520 }}>
          <div className="p-2 px-3 flex items-center gap-2 border-b border-gray-100 flex-shrink-0 bg-amber-50 rounded-t-xl">
            <span>🤖</span><span className="text-xs font-semibold text-gray-700">DeepSeek 助手</span>
            <button onClick={() => { setDsMessages([]); localStorage.removeItem("deepseek_api_key"); setDsKey(""); }} className="ml-auto text-xs text-gray-400 hover:text-gray-600">清空</button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2" style={{ minHeight: 200 }}>
            {dsMessages.length === 0 && <p className="text-xs text-gray-400 p-2">粘贴 API Key 发送，然后直接提问。</p>}
            {dsMessages.map((m, i) => (
              <div key={i} className={`text-xs ${m.role === "user" ? "text-right" : ""}`}>
                <span className={`inline-block px-3 py-2 rounded-xl max-w-[85%] ${m.role === "user" ? "bg-indigo-500 text-white rounded-br-sm" : "bg-gray-100 text-gray-700 rounded-bl-sm"}`}>{m.content}</span>
              </div>
            ))}
          </div>
          <div className="p-2 border-t border-gray-100 flex gap-2 flex-shrink-0">
            <input className="input text-xs py-1.5 flex-1" value={dsInput} onChange={e => setDsInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendDeepseek()} placeholder="输入问题或 API Key..." />
            <button onClick={sendDeepseek} className="w-7 h-7 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center flex-shrink-0">↑</button>
          </div>
        </div>

        {/* 中间：聊天频道 */}
        <div>
          <div className="card p-4" style={{ minHeight: 400, display: "flex", flexDirection: "column" }}>
            <div className="flex items-center gap-3 mb-3 flex-shrink-0">
              <span className="text-sm font-semibold text-gray-500">聊天频道</span>
              <div className="flex gap-2">
                <button onClick={() => { setChatType("group"); loadChatMessages("group"); setShowChat(true); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${chatType==="group"?"bg-indigo-500 text-white":"bg-white/5 text-gray-500"}`}>
                  👥 组内
                </button>
                <button onClick={() => { setChatType("team"); loadChatMessages("team"); setShowChat(true); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${chatType==="team"?"bg-amber-500 text-white":"bg-white/5 text-gray-500"}`}>
                  🏠 团队
                </button>
              </div>
            </div>

            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto space-y-3 mb-3" ref={chatRef} style={{ minHeight: 260 }}>
              {chatMessages.length === 0 && (
                <p className="text-center text-gray-400 text-sm py-12">暂无消息。加入团队后即可聊天。</p>
              )}
              {chatMessages.map(m => (
                <div key={m.id} className={`flex gap-2 text-sm ${m.is_mine ? "flex-row-reverse" : ""}`}>
                  <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs flex-shrink-0">{m.user_name?.[0] || "?"}</div>
                  <div className={`px-3 py-2 rounded-xl max-w-[70%] ${m.is_mine ? "bg-indigo-500 text-white rounded-br-sm" : "bg-white/5 text-gray-800 rounded-bl-sm"}`}>
                    {m.content}
                    <div className={`text-[10px] mt-0.5 ${m.is_mine ? "text-indigo-200" : "text-gray-400"}`}>{m.user_name} · {m.created_at}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* 输入框 */}
            <div className="flex gap-2 flex-shrink-0">
              <VoiceInput onText={text => { setChatInput(prev => prev + text); }} />
              <input className="input text-sm py-2 flex-1" value={chatInput} onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendChat()} placeholder="输入消息..." />
              <button onClick={sendChat} className="btn text-white px-4 py-2 rounded-lg text-sm">发送</button>
            </div>
          </div>
        </div>

        {/* 右侧：潜在好友 */}
        <div>
          {friends.length > 0 ? (
            <div className="card p-4">
              <h3 className="text-sm font-semibold text-gray-500 mb-3">🔗 潜在队友</h3>
              <div className="space-y-2">
                {friends.slice(0, 8).map((f: any) => (
                  <div key={f.user_id} className="p-3 rounded-xl bg-gradient-to-r from-amber-500/5 to-yellow-500/5 border border-amber-500/8">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center text-white font-semibold text-xs">{f.real_name?.[0]}</div>
                      <span className="text-sm font-semibold">{f.real_name}</span>
                      <span className="text-xs text-amber-500 font-semibold ml-auto">{f.match_score}分</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mb-1">
                      {f.skill_tags?.slice(0, 3).map((t: string, i: number) => (
                        <span key={i} className="tag bg-amber-500/10 text-amber-600 text-xs">{t}</span>
                      ))}
                    </div>
                    {f.complementary_skills?.length > 0 && (
                      <p className="text-xs text-emerald-600">互补：{f.complementary_skills.slice(0, 2).join("、")}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card p-6 text-center">
              <p className="text-gray-400 text-sm">暂无推荐</p>
              <p className="text-xs text-gray-500 mt-1">加入团队后自动匹配</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
