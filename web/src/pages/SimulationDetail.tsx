import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import EvidenceButton from "../components/EvidenceButton";

const SCENARIO_ICONS: Record<string, string> = {
  further_study: "📚", employment: "💼", entrepreneurship: "🚀", cross_discipline: "🔄",
};
const SCENARIO_LABELS: Record<string, string> = {
  further_study: "深度探索", employment: "现实创造", entrepreneurship: "自主创造", cross_discipline: "跨界融合",
};
const PATH_COLORS = [
  { dot: "bg-indigo-500", border: "border-indigo-500/20", from: "from-indigo-500/5", bar: "bg-indigo-500", btn: "bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30" },
  { dot: "bg-emerald-500", border: "border-emerald-500/20", from: "from-emerald-500/5", bar: "bg-emerald-500", btn: "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30" },
  { dot: "bg-amber-500", border: "border-amber-500/20", from: "from-amber-500/5", bar: "bg-amber-500", btn: "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30" },
];

export default function SimulationDetail() {
  const { id } = useParams<{ id: string }>();
  const [sim, setSim] = useState<any>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch(`/api/mirror/simulations/${id}`).then(r => r.json()).then(setSim);
  }, [id]);

  async function deleteSim() {
    if (!confirm("删除这次模拟？")) return;
    await fetch(`/api/mirror/simulations/${id}`, { method: "DELETE" });
    nav("/simulation");
  }

  async function setAsGoal(pathIdx: number) {
    await fetch(`/api/mirror/simulations/${id}/to-goal/${pathIdx}`, { method: "POST" });
    nav("/goals");
  }

  if (!sim) return null;

  const scenarioType = typeof sim.scenario_type === "object" ? sim.scenario_type?.value : (sim.scenario_type || sim.scenario || "");
  const paths = sim.paths || sim.output_paths || [];

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <a href="/simulation" onClick={e => { e.preventDefault(); nav("/simulation"); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </a>
          <h2 className="text-2xl font-bold">可能的自己</h2>
        </div>
        <button onClick={deleteSim} className="px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition border border-rose-500/20">
          <i className="fa-solid fa-trash mr-1"></i>删除
        </button>
      </div>

      <div className="card p-5 mb-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-2xl">{SCENARIO_ICONS[scenarioType] || "🔄"}</span>
          <div>
            <h3 className="font-semibold text-white">{SCENARIO_LABELS[scenarioType] || scenarioType}</h3>
            {sim.question && sim.question.length > 5 && <p className="text-sm text-gray-400 mt-1">"{sim.question}"</p>}
          </div>
          <span className="text-xs text-gray-500 ml-auto">{sim.created_at ? new Date(sim.created_at).toLocaleDateString("zh-CN") + " " + new Date(sim.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}</span>
        </div>
      </div>

      <div className="mb-5 text-center">
        <p className="text-sm text-gray-500"><span className="#475569"></span> 这些未来版本并不是预测的命运，而是基于你过去的经历、行为习惯和价值倾向生成的<strong className="#475569">"可能的自己"</strong>。未来不会被决定，但你可以提前观察不同选择下可能成长出的自己。</p>
      </div>

      {paths.length > 0 ? (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {paths.map((path: any, idx: number) => {
            const c = PATH_COLORS[idx] || PATH_COLORS[2];
            return (
              <div key={idx} className={`card p-5 bg-gradient-to-b ${c.from} to-transparent ${c.border}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-3 h-3 rounded-full flex-shrink-0 ${c.dot}`}></span>
                  <h4 className="font-bold text-white text-sm">{path.label}</h4>
                </div>
                {path.path_type_hint && <p className="text-xs text-gray-500 mb-3 ml-5">{path.path_type_hint}</p>}

                <p className="text-sm text-gray-400 leading-relaxed mb-4">{path.description}</p>

                {/* 人格倾向变化 —— 兼容 persona_shift / personality_traits / ability_growth 三种字段 */}
                {(() => {
                  // 尝试多个可能的字段名
                  const rawShift = path.persona_shift || path.personality_traits || path.ability_growth;
                  if (!rawShift) return null;
                  const shifts: [string, string, string][] = [];
                  const colorOf = (v: number | string) => {
                    const n = typeof v === 'number' ? v : parseFloat(String(v));
                    if (!isNaN(n)) return n > 0 ? 'green' : n < 0 ? 'red' : 'yellow';
                    const s = String(v);
                    if (s.includes('↑') || s.startsWith('+')) return 'green';
                    if (s.includes('↓') || s.startsWith('-')) return 'red';
                    return 'yellow';
                  };
                  if (typeof rawShift === 'object' && !Array.isArray(rawShift)) {
                    for (const [k, v] of Object.entries(rawShift as Record<string, any>)) {
                      // 箭头可能在 key 里（如 "专注深度 ↑"）或 value 里
                      let dim = k;
                      let display = String(v);
                      const arrowInKey = k.match(/[↑↓]/);
                      if (arrowInKey) {
                        dim = k.replace(/[↑↓]/g, '').trim();
                        display = arrowInKey[0];
                      }
                      const numVal = parseFloat(display);
                      if (!isNaN(numVal)) {
                        shifts.push([dim, (numVal > 0 ? '+' : '') + numVal, colorOf(numVal)]);
                      } else {
                        shifts.push([dim, display, colorOf(display)]);
                      }
                    }
                  }
                  if (!shifts.length) return null;
                  const label = path.persona_shift ? '人格倾向变化' : path.personality_traits ? '人格倾向' : '能力成长';
                  return (
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">{label}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {shifts.map(([dim, display, color]) => (
                        <span key={dim} className={`tag text-xs ${
                          color === 'green' ? 'bg-emerald-500/15 text-emerald-400' :
                          color === 'red' ? 'bg-rose-500/15 text-rose-400' :
                          'bg-amber-500/15 text-amber-400'
                        }`}>{dim} {display}</span>
                      ))}
                    </div>
                  </div>
                  );
                })()}

                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500">未来人格匹配度</span>
                    <span className="text-xs text-gray-500">{Math.round((path.confidence || 0) * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.bar}`} style={{ width: `${Math.round((path.confidence || 0.5) * 100)}%` }}></div>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">根据你的长期记忆、兴趣倾向和行为模式生成</p>
                </div>

                {path.milestones && (
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">可能出现的人生节点</p>
                    <div className="space-y-2">
                      {path.milestones.map((ms: string, i: number) => (
                        <div key={i} className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-white/30 mt-1.5 flex-shrink-0"></span><span className="text-xs text-gray-400">{ms}</span></div>
                      ))}
                    </div>
                  </div>
                )}

                {path.turning_points && (
                  <div className="mb-4 p-3 rounded-xl bg-amber-500/5 border border-amber-500/10">
                    <p className="text-xs text-amber-400 mb-2">可能的成长课题</p>
                    <div className="space-y-1.5">
                      {path.turning_points.map((tp: string, i: number) => (
                        <div key={i} className="flex items-start gap-2"><span className="text-xs text-amber-400/60">~</span><span className="text-xs text-gray-400">{tp}</span></div>
                      ))}
                    </div>
                  </div>
                )}

                {path.grounding && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2">
                      <p className="text-xs text-gray-600 italic">{path.grounding}</p>
                      <EvidenceButton query={`${path.label || ""} ${path.grounding}`} targetType="simulation" targetId={Number(id)} label="查看证据" size="xs" style={{ flexShrink: 0 }} />
                    </div>
                  </div>
                )}

                {(() => {
                  const future = sim.futures?.[idx];
                  if (future) {
                    return (
                      <button onClick={() => nav(`/experience/${future.id}`)} className="block w-full text-center py-2.5 rounded-xl text-sm font-semibold bg-purple-500/15 text-indigo-400 hover:bg-purple-500/25 transition mb-2">
                        <i className="fa-solid fa-gamepad mr-2"></i>详细体验这段人生
                      </button>
                    );
                  }
                  return null;
                })()}

                <button onClick={() => nav("/future-chat")} className={`block w-full text-center py-2.5 rounded-xl text-sm font-semibold ${c.btn} transition`}>
                  <i className="fa-solid fa-comment-dots mr-2"></i>与这个版本的自己对话
                </button>

                <button onClick={() => setAsGoal(idx)} className="w-full py-2 rounded-xl text-xs font-medium text-emerald-400 hover:text-emerald-300 border border-emerald-500/20 hover:border-emerald-500/40 transition bg-transparent mt-2">
                  <i className="fa-solid fa-bullseye mr-1"></i>一键设为目标
                </button>

                <div className="mt-3 p-3 rounded-xl bg-white/5">
                  <p className="text-xs text-gray-500 mb-2">↩ 回到现在：90天可以做什么</p>
                  <div className="space-y-1 text-xs text-gray-400">
                    {path.gap_suggestions ? path.gap_suggestions.map((s: string, i: number) => (
                      <div key={i} className="flex items-start gap-2"><span className="#8b5e3c mt-0.5">{i + 1}.</span><span>{s}</span></div>
                    )) : <span className="text-gray-600">基于当前兴趣在核心领域建立持续的学习习惯</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card p-10 text-center"><p className="text-sm text-gray-500">模拟结果生成中或数据异常</p></div>
      )}

      <div className="flex items-center gap-4 text-sm justify-center mt-6">
        <a href="/simulation" onClick={e => { e.preventDefault(); nav("/simulation"); }} className="#8b5e3c hover:underline"><i className="fa-solid fa-plus mr-1"></i>新建模拟</a>
        <span className="text-gray-600">·</span>
        <a href="/persona" onClick={e => { e.preventDefault(); nav("/persona"); }} className="#8b5e3c hover:underline"><i className="fa-solid fa-fingerprint mr-1"></i>查看数字人格</a>
        <span className="text-gray-600">·</span>
        <a href="/goals" onClick={e => { e.preventDefault(); nav("/goals"); }} className="#8b5e3c hover:underline"><i className="fa-solid fa-bullseye mr-1"></i>管理人生目标</a>
      </div>
    </div>
  );
}
