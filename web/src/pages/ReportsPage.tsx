import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function defaultDates(): { start: string; end: string; title: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const s = fmt(start);
  const e = fmt(end);
  return { start: s, end: e, title: `成长报告 ${s} — ${e}` };
}

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [generating, setGenerating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const nav = useNavigate();

  const load = () => fetch("/api/mirror/reports").then(r => r.json()).then(d => setReports(Array.isArray(d) ? d : d.reports || []));
  useEffect(() => { load(); }, []);

  function openForm() {
    const d = defaultDates();
    setTitle(d.title);
    setPeriodStart(d.start);
    setPeriodEnd(d.end);
    setShowForm(true);
  }

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setGenerating(true);
    const r = await fetch("/api/mirror/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title || undefined, period_start: periodStart, period_end: periodEnd }),
    });
    if (r.ok) {
      setShowForm(false);
      load();
    }
    setGenerating(false);
  }

  // ── 生成表单（对照原版 reports/generate.html） ──
  if (showForm) {
    return (
      <div className="max-w-2xl mx-auto px-8 py-8">
        <div className="flex items-center gap-3 mb-6">
          <a href="/reports" onClick={e => { e.preventDefault(); setShowForm(false); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </a>
          <h2 className="text-2xl font-bold">生成成长报告</h2>
        </div>

        <form onSubmit={generate} className="card p-6 space-y-5">
          {/* 报告标题 */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">报告标题</label>
            <input
              type="text"
              className="input"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="例如：2026年7月成长总结"
            />
          </div>

          {/* 日期范围 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">起始日期</label>
              <input
                type="date"
                className="input"
                value={periodStart}
                onChange={e => setPeriodStart(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">结束日期</label>
              <input
                type="date"
                className="input"
                value={periodEnd}
                onChange={e => setPeriodEnd(e.target.value)}
              />
            </div>
          </div>

          {/* AI 分析范围 */}
          <div className="card p-4 bg-white/3">
            <div className="flex items-start gap-3">
              <span className="text-lg">🤖</span>
              <div>
                <p className="text-sm text-gray-400 font-medium">AI 会分析以下内容</p>
                <ul className="text-xs text-gray-500 mt-2 space-y-1">
                  <li>· 该时间段内的所有日常记录</li>
                  <li>· 重要人生事件</li>
                  <li>· 兴趣变化与行为模式</li>
                  <li>· 情绪趋势</li>
                  <li>· 成长建议与鼓励</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 按钮 */}
          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold" disabled={generating}>
              <i className={`fa-solid ${generating ? "fa-spinner animate-spin" : "fa-wand-magic-sparkles"} mr-2`}></i>
              {generating ? "生成中..." : "开始生成"}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-gray-200 transition border border-white/10">
              取消
            </button>
          </div>
        </form>
      </div>
    );
  }

  // ── 报告列表 ──
  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">成长报告</h2>
          <p className="#475569 text-sm mt-1">AI 基于你的人生数据，定期生成阶段性成长总结</p>
        </div>
        <button onClick={openForm} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold">
          <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>生成新报告
        </button>
      </div>

      {reports.length > 0 ? (
        <div className="space-y-4">
          {reports.map(r => (
            <a key={r.id} href={`/reports/${r.id}`} onClick={e => { e.preventDefault(); nav(`/reports/${r.id}`); }} className="card p-5 block no-underline group">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-white group-hover:text-indigo-400 transition">{r.title}</h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {r.period_start ? new Date(r.period_start).toLocaleDateString("zh-CN") : ""}
                    {" — "}
                    {r.period_end ? new Date(r.period_end).toLocaleDateString("zh-CN") : ""}
                    {r.date ? ` · 生成于 ${new Date(r.date).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })} ${new Date(r.date).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}` : ""}
                  </p>
                  {r.content?.summary && (
                    <p className="text-sm text-gray-400 mt-2 line-clamp-2">{r.content.summary.slice(0, 150)}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {r.content?.engine === "deepseek" ? (
                    <span className="tag bg-green-500/20 text-green-400 text-xs"><i className="fa-solid fa-brain mr-1"></i>DeepSeek</span>
                  ) : (
                    <span className="tag bg-amber-500/20 text-amber-400 text-xs"><i className="fa-solid fa-gear mr-1"></i>规则引擎</span>
                  )}
                  <i className="fa-solid fa-chevron-right text-gray-600 group-hover:text-gray-400 transition text-xs"></i>
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div className="card p-16 text-center">
          <div className="text-6xl mb-5">📊</div>
          <h3 className="text-xl font-semibold text-gray-400 mb-2">还没有成长报告</h3>
          <p className="text-sm text-gray-500 mb-8">积累一些日常记录和人生事件后，让 AI 帮你生成第一份成长报告</p>
          <button onClick={openForm} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold inline-block">
            生成第一份报告
          </button>
        </div>
      )}
    </div>
  );
}
