import { useEffect, useState } from "react";

const STAT_ITEMS = [
  ["records", "📝", "日常记录"],
  ["events", "📌", "人生事件"],
  ["memories", "🧠", "长期记忆"],
  ["personas", "🧬", "人格画像版本"],
  ["goals", "🎯", "人生目标"],
  ["interests", "📈", "兴趣数据点"],
  ["simulations", "🔮", "人生模拟"],
  ["future_selves", "🪞", "未来人格"],
  ["chat_messages", "💬", "对话消息"],
  ["reports", "📊", "成长报告"],
];

export default function SettingsPage() {
  const [stats, setStats] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetch("/api/mirror/settings").then(r => r.json()).then(d => {
      setStats(d.stats || {});
      setTotal(d.total || Object.values(d.stats || {}).reduce((a: number, b: number) => (a as number) + (b as number), 0) as number);
    });
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      <h2 className="text-2xl font-bold mb-2">设置</h2>
      <div className="card p-5 mb-5">
        <h3 className="font-semibold text-white mb-3">🎨 主题</h3>
        <ThemeSwitch />
      </div>
      <HotwordsSection />
      <h3 className="text-lg font-semibold text-white mb-2 mt-6">隐私与数据</h3>
      <p className="#475569 text-sm mb-6">你的数据完全属于你。随时导出或删除。</p>
      <div className="card p-5 mb-5">
        <h3 className="font-semibold text-white mb-3">📊 数据存储概览</h3>
        <p className="text-sm text-gray-400 mb-4">以下是 AI人生镜像中存储的与你相关的所有数据：</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          {STAT_ITEMS.map(([key, icon, label]) => (
            <div key={key} className="flex items-center justify-between p-2.5 rounded-lg bg-white/5">
              <span className="#475569">{icon} {label}</span>
              <span className="#10213c font-semibold text-xs">{stats[key] || 0}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t border-white/5 flex justify-between text-sm">
          <span className="#475569">总计</span>
          <span className="#10213c font-bold">{total} 条数据</span>
        </div>
      </div>
      <div className="card p-5 mb-5">
        <h3 className="font-semibold text-white mb-3">🔒 数据存储说明</h3>
        <div className="space-y-3 text-sm text-gray-400">
          <div className="flex items-start gap-3"><span className="text-lg flex-shrink-0">💾</span><div><p className="#475569 font-medium">SQLite 本地数据库</p><p className="text-xs text-gray-500 mt-0.5">结构化数据存储在本地 SQLite 中。</p></div></div>
          <div className="flex items-start gap-3"><span className="text-lg flex-shrink-0">🧬</span><div><p className="#475569 font-medium">ChromaDB 向量数据库</p><p className="text-xs text-gray-500 mt-0.5">语义记忆以向量形式存储。</p></div></div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <a href="/settings/export" onClick={e => { e.preventDefault(); window.location.href = "/settings/export"; }} className="card p-5 block no-underline hover:border-indigo-500/30 transition group">
          <div className="flex items-start gap-3"><span className="text-2xl">📥</span><div><h4 className="font-semibold text-white group-hover:text-indigo-400 transition">导出全部数据</h4><p className="text-xs text-gray-500 mt-1">下载 JSON 格式的完整数据备份</p></div></div>
        </a>
        <a href="/settings/delete-account" onClick={e => { e.preventDefault(); window.location.href = "/settings/delete-account"; }} className="card p-5 block no-underline hover:border-rose-500/30 transition group">
          <div className="flex items-start gap-3"><span className="text-2xl">⚠️</span><div><h4 className="font-semibold text-rose-400">删除账户</h4><p className="text-xs text-gray-500 mt-1">永久删除账户及所有关联数据</p></div></div>
        </a>
      </div>
    </div>
  );
}

function ThemeSwitch() {
  const [dark, setDark] = useState(() => { try { const v = localStorage.getItem("theme"); return v === null ? true : v === "dark"; } catch { return true; } });
  useEffect(() => { document.documentElement.setAttribute("data-theme", dark ? "dark" : "light"); try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {} }, [dark]);
  return (
    <div className="flex items-center gap-3">
      <button onClick={() => setDark(true)} className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${dark ? "btn text-white" : "bg-white/5 text-gray-500"}`}>🌙 深色</button>
      <button onClick={() => setDark(false)} className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${!dark ? "btn text-white" : "bg-white/5 text-gray-500"}`}>☀️ 浅色</button>
    </div>
  );
}

function HotwordsSection() {
  const [hotwords, setHotwords] = useState<string[]>([]);
  const [input, setInput] = useState("");
  useEffect(() => { fetch("/api/mirror/stt/hotwords").then(r => r.json()).then(d => { if (d.ok) setHotwords(d.hotwords || []); }); }, []);
  async function add() { const w = input.trim(); if (!w || hotwords.includes(w)) return; const words = [...hotwords, w]; await fetch("/api/mirror/stt/hotwords", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ words }) }); setHotwords(words); setInput(""); }
  async function remove(w: string) { const words = hotwords.filter(h => h !== w); await fetch("/api/mirror/stt/hotwords", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ words }) }); setHotwords(words); }
  return (
    <div className="card p-5 mb-5">
      <h3 className="font-semibold text-white mb-3">🎙️ 语音识别热词</h3>
      <p className="text-xs text-gray-500 mb-3">添加专有名词提升 FunASR 识别准确率</p>
      <div className="flex gap-2 mb-3">
        <input className="input text-sm py-2 flex-1" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && add()} placeholder="输入热词..." />
        <button onClick={add} className="btn text-white px-4 py-2 rounded-lg text-sm">添加</button>
      </div>
      {hotwords.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">{hotwords.map(w => (<span key={w} className="tag bg-indigo-500/15 text-indigo-400 flex items-center gap-1 cursor-pointer" onClick={() => remove(w)}>{w} <span className="text-xs opacity-50">×</span></span>))}</div>
      ) : <p className="text-xs text-gray-600">暂无热词</p>}
    </div>
  );
}
