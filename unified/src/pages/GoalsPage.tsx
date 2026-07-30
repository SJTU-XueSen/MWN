import { useEffect, useState } from "react";

const GOAL_TYPE_ICON: Record<string, string> = {
  career: "💼", study: "📚", skill: "🔧", lifestyle: "🌱", relationship: "💞",
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [goalType, setGoalType] = useState("study");
  const [importance, setImportance] = useState(50);
  const [period, setPeriod] = useState("");
  const [loading, setLoading] = useState(false);

  const load = () => fetch("/api/mirror/goals").then(r => r.json()).then((d) => setGoals(Array.isArray(d) ? d : d.goals || []));
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    const r = await fetch("/api/mirror/goals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description: desc, goal_type: goalType, importance, target_period: period }),
    });
    if (r.ok) {
      setShowForm(false);
      setTitle("");
      setDesc("");
      setGoalType("study");
      setImportance(50);
      setPeriod("");
      load();
    }
    setLoading(false);
  }

  async function doAction(url: string, confirmMsg?: string) {
    if (confirmMsg && !confirm(confirmMsg)) return;
    await fetch(url, { method: "POST" });
    load();
  }

  const activeGoals = goals.filter(g => g.status !== "achieved" && g.status !== "done");
  const achievedGoals = goals.filter(g => g.status === "achieved" || g.status === "done");

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">人生目标</h2>
          <p className="#475569 text-sm mt-1">设定方向，追踪进展</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold">
          <i className="fa-solid fa-plus mr-2"></i>添加目标
        </button>
      </div>

      {/* 创建表单 */}
      {showForm && (
        <div className="card p-6 mb-6">
          <form onSubmit={create} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">目标标题 <span className="text-rose-400">*</span></label>
              <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="你想实现什么？" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">描述</label>
              <textarea className="input" rows={3} value={desc} onChange={e => setDesc(e.target.value)} placeholder="具体描述这个目标..." />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">目标类型</label>
                <select className="input" value={goalType} onChange={e => setGoalType(e.target.value)}>
                  {Object.entries(GOAL_TYPE_ICON).map(([k, icon]) => (
                    <option key={k} value={k}>{icon} {k}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">目标周期</label>
                <input className="input" value={period} onChange={e => setPeriod(e.target.value)} placeholder="如：1年" />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">重要度：{importance}%</label>
              <input type="range" min={10} max={100} step={10} value={importance} onChange={e => setImportance(Number(e.target.value))}
                className="w-full accent-indigo-500 h-1.5" />
            </div>
            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold" disabled={loading}>
                {loading ? "保存中..." : "添加目标"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-ghost px-6 py-2.5 rounded-xl text-sm">
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 活跃目标 */}
      <div className="mb-8">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          进行中 <span className="#8b5e3c">({activeGoals.length})</span>
        </h3>

        {activeGoals.length > 0 ? (
          <div className="space-y-3">
            {activeGoals.map(goal => (
              <div key={goal.id} className="card p-5 group">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="text-2xl flex-shrink-0">
                      {GOAL_TYPE_ICON[goal.goal_type] || "🎯"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-semibold text-white">{goal.title}</h4>
                        {goal.target_period && (
                          <span className="tag bg-cyan-500/20 text-cyan-400 text-xs">{goal.target_period}</span>
                        )}
                      </div>
                      {goal.description && (
                        <p className="text-sm text-gray-400 mt-1.5 line-clamp-2">{goal.description}</p>
                      )}
                      {goal.ai_gap_analysis && (
                        <div className="mt-2 p-2 rounded-lg bg-indigo-500/5 border border-indigo-500/10">
                          <p className="text-xs text-indigo-400 mb-1">🤖 AI 差距分析</p>
                          <p className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">
                            {(goal.ai_gap_analysis || "").slice(0, 300)}
                          </p>
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {goal.target_year > 0 && (
                          <span><i className="fa-solid fa-calendar-check mr-1"></i>{goal.target_year}年</span>
                        )}
                        <span>重要度 {goal.importance}%</span>
                      </div>
                    </div>
                  </div>
                  {/* 操作 */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition flex-shrink-0">
                    <button onClick={() => doAction(`/api/mirror/goals/${goal.id}/analyze`)}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-xs text-indigo-400 hover:bg-indigo-500/10"
                      title="AI分析差距"><i className="fa-solid fa-brain"></i></button>
                    <button
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-xs text-gray-400 hover:text-white hover:bg-white/5"
                      title="编辑"><i className="fa-solid fa-pen"></i></button>
                    <button onClick={() => doAction(`/api/mirror/goals/${goal.id}/complete`)}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-xs text-emerald-400 hover:bg-emerald-500/10"
                      title="完成"><i className="fa-solid fa-check"></i></button>
                    <button onClick={() => doAction(`/api/mirror/goals/${goal.id}/delete`, "删除这个目标？")}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-xs text-gray-500 hover:text-rose-400 hover:bg-rose-500/10"
                      title="删除"><i className="fa-solid fa-xmark"></i></button>
                  </div>
                </div>
                {/* 重要度进度条 */}
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-xs text-gray-600 w-12">重要度</span>
                  <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                      style={{ width: `${goal.importance || 50}%` }}></div>
                  </div>
                  <span className="text-xs text-gray-500 w-8 text-right">{goal.importance || 50}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-10 text-center">
            <p className="text-sm text-gray-500">还没有目标，<button onClick={() => setShowForm(true)} className="#8b5e3c hover:underline">设定第一个</button></p>
          </div>
        )}
      </div>

      {/* 已完成目标 */}
      {achievedGoals.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            已完成 <span className="text-emerald-400">({achievedGoals.length})</span>
          </h3>
          <div className="space-y-2">
            {achievedGoals.map(goal => (
              <div key={goal.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/3 opacity-60 group">
                <span className="text-lg flex-shrink-0">
                  {GOAL_TYPE_ICON[goal.goal_type] || "🎯"}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-400 line-through truncate">{goal.title}</p>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => doAction(`/api/mirror/goals/${goal.id}/reactivate`)}
                    title="重新激活"
                    className="w-5 h-5 rounded-full flex items-center justify-center text-xs text-amber-400 hover:bg-amber-500/10">↩</button>
                  <button onClick={() => doAction(`/api/mirror/goals/${goal.id}/delete`, "永久删除？")}
                    title="删除"
                    className="w-5 h-5 rounded-full flex items-center justify-center text-xs text-gray-500 hover:text-rose-400">×</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
