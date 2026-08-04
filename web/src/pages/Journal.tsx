import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import VoiceInput from "../components/VoiceInput";

export default function Journal() {
  const [records, setRecords] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [content, setContent] = useState("");
  const [mood, setMood] = useState("");
  const [recordDate, setRecordDate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const nav = useNavigate();

  const load = (kw?: string) =>
    fetch(`/api/mirror/journal${kw ? `?search=${encodeURIComponent(kw)}` : ""}`)
      .then(r => r.json())
      .then((d) => setRecords(Array.isArray(d) ? d : []));
  useEffect(() => { load(); }, []);

  function startEdit(r: any) {
    setEditingId(r.id);
    setContent(r.content || "");
    setMood(r.mood || "");
    setRecordDate(r.date?.slice(0, 10) || new Date().toISOString().slice(0, 10));
    setShowForm(false);
  }

  async function saveEdit() {
    if (!content.trim() || !editingId) return;
    setLoading(true);
    const r = await fetch(`/api/mirror/journal/${editingId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mood, record_date: recordDate }),
    });
    if (r.ok) { setEditingId(null); setContent(""); setMood(""); load(); }
    setLoading(false);
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setLoading(true);
    const r = await fetch("/api/mirror/journal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mood, record_date: recordDate }),
    });
    if (r.ok) { setShowForm(false); setContent(""); setMood(""); setRecordDate(new Date().toISOString().slice(0, 16)); load(); }
    setLoading(false);
  }

  async function deleteRecord(id: number) {
    if (!confirm("删除这条记录？")) return;
    await fetch(`/api/mirror/journal/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">日常人生记录</h2>
          <p className="#475569 text-sm mt-1">记录每一天的经历、心情和思考，AI 会帮你发现其中的成长轨迹</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="input"
            style={{ width: 220 }}
            placeholder="检索日记…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(search.trim())}
          />
          <button onClick={() => load(search.trim())} className="btn-ghost" style={{ padding: "8px 16px" }}>检索</button>
        </div>
      </div>
      {search && (
        <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginBottom: 12 }}>
          检索「{search}」：{records.length} 条结果
          <button onClick={() => { setSearch(""); load(); }} style={{ marginLeft: 10, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", fontSize: "0.72rem" }}>清除</button>
        </p>
      )}

      {showForm ? (
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-gray-400 transition"><i className="fa-solid fa-arrow-left"></i></button>
            <h2 className="text-2xl font-bold">记录今天的经历</h2>
          </div>
          <div className="card p-6">
            <form onSubmit={create} className="space-y-5">
              <div>
                <label className="block text-sm text-gray-400 mb-2">今天发生了什么？心情如何？在想什么？</label>
                <div className="relative">
                  <textarea className="input" rows={8} value={content} onChange={e => setContent(e.target.value)} placeholder="例如：今天第一次参加机器人比赛..." required autoFocus />
                  <div className="absolute bottom-2 right-2"><VoiceInput onText={text => setContent(prev => prev + text)} /></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">今天的心情</label>
                  <input type="text" className="input" value={mood} onChange={e => setMood(e.target.value)} placeholder="自由描述你的心情，比如：既紧张又兴奋、有点累但充实..." />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">日期</label>
                  <input type="date" className="input" value={recordDate} onChange={e => setRecordDate(e.target.value)} />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold" disabled={loading}>
                  <i className="fa-solid fa-paper-plane mr-2"></i>{loading ? "保存中..." : "保存记录"}
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-gray-200 transition border border-white/10">
                  取消
                </button>
              </div>
            </form>
          </div>
          <div className="card p-5 mt-4 bg-white/3">
            <p className="text-xs text-gray-500"><i className="fa-solid fa-lightbulb text-amber-400 mr-1"></i><strong>提示：</strong>越详细、越真实的记录，AI 越能准确地理解你。不用担心格式，想到什么写什么。</p>
          </div>
        </div>
      ) : records.length > 0 ? (
        <div className="space-y-6">
          {(() => {
            // 按月分组（records 按日期倒序，分组自然倒序）
            const groups: { month: string; items: any[] }[] = [];
            for (const r of records) {
              const month = (r.record_date || r.date || "").slice(0, 7);
              const last = groups[groups.length - 1];
              if (last && last.month === month) last.items.push(r);
              else groups.push({ month, items: [r] });
            }
            return groups.map((g) => (
              <div key={g.month}>
                <p style={{
                  fontSize: "0.68rem", fontWeight: 600, letterSpacing: "0.08em",
                  textTransform: "uppercase", color: "var(--text4)",
                  margin: "0 0 8px 4px",
                }}>
                  {g.month} · {g.items.length} 篇
                </p>
                <div className="space-y-3">
                  {g.items.map((r) => (
                    <div key={r.id} className="card p-4 block group relative">
              <a
                href={`/journal/${r.id}`}
                className="no-underline flex-1"
                onClick={e => { e.preventDefault(); nav(`/journal/${r.id}`); }}
              >
                <div className="flex items-start gap-3">
                  <div className="text-lg flex-shrink-0 mt-1 w-8 text-center text-gray-500">
                    <i className="fa-solid fa-feather-pointed"></i>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 line-clamp-2 group-hover:text-white transition">
                      {r.content?.slice(0, 200)}{(r.content?.length || 0) > 200 ? "..." : ""}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      {r.mood && (
                        <span className="text-xs text-gray-400 italic">「{r.mood}」</span>
                      )}
                      <span className="text-xs text-gray-500">{r.record_date || r.date || ""}</span>
                      {r.tags && r.tags.map((tag: string, i: number) => (
                        <span key={i} className="tag bg-indigo-500/20 text-indigo-400">{tag}</span>
                      ))}
                      {r.ai_analysis?.interest_fields && r.ai_analysis.interest_fields.slice(0, 3).map((f: string, i: number) => (
                        <span key={i} className="tag bg-emerald-500/20 text-emerald-400">{f}</span>
                      ))}
                    </div>
                  </div>
                  <i className="fa-solid fa-chevron-right text-gray-600 group-hover:text-gray-400 transition flex-shrink-0 mt-2"></i>
                </div>
              </a>
                      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition">
                        <button onClick={(e) => { e.stopPropagation(); startEdit(r); }}
                          className="w-6 h-6 rounded-full flex items-center justify-center text-xs text-gray-600 hover:text-indigo-400 hover:bg-indigo-500/10 transition"
                          title="编辑"><i className="fa-solid fa-pen"></i></button>
                        <button onClick={(e) => { e.stopPropagation(); deleteRecord(r.id); }}
                          className="w-6 h-6 rounded-full flex items-center justify-center text-xs text-gray-600 hover:text-rose-400 hover:bg-rose-500/10 transition"
                          title="删除"><i className="fa-solid fa-xmark"></i></button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ));
          })()}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-400 mb-2">还没有人生记录</h3>
          <p className="text-sm text-gray-500 mb-6">写下你今天经历了什么、心情如何、在想什么</p>
          <button onClick={() => setShowForm(true)} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold inline-block">
            开始记录
          </button>
        </div>
      )}
    </div>
  );
}
