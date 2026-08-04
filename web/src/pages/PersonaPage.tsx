import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import EvidenceButton from "../components/EvidenceButton";

const INTEREST_ICONS: Record<string, string> = {
  "AI": "🤖", "编程": "💻", "科研": "🔬", "设计": "🎨", "写作": "✍️",
  "音乐": "🎵", "体育": "⚽", "创业": "🚀", "教育": "📚", "社会": "🌍",
  "游戏": "🎮", "哲学": "💭", "心理学": "🧠", "经济": "📈", "政治": "🏛️",
};

export default function PersonaPage() {
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [generating, setGenerating] = useState(false);
  const [compareSel, setCompareSel] = useState<number[]>([]);
  const [compareData, setCompareData] = useState<any>(null);
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const versionId = searchParams.get("version");

  const load = () => {
    const url = versionId ? `/api/mirror/persona?version=${versionId}` : "/api/mirror/persona";
    fetch(url).then(r => r.json()).then((d) => {
      setData(d);
      if (d.history) setHistory(d.history);
    });
  };
  useEffect(() => { load(); }, [versionId]);

  async function generate() {
    setGenerating(true);
    const r = await fetch("/api/mirror/persona", { method: "POST" });
    if (r.ok) { window.location.href = "/persona"; }
    else { setGenerating(false); }
  }

  const persona = data?.current || data;
  if (!persona && !data) return null;

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">数字人格</h2>
          <p className="#475569 text-sm mt-1">AI 从你的人生数据中提炼的个性画像</p>
        </div>
        <button onClick={generate} disabled={generating} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold">
          <i className={`fa-solid ${generating ? "fa-spinner animate-spin" : "fa-arrows-rotate"} mr-2`}></i>
          {persona ? "更新画像" : "生成画像"}
        </button>
      </div>

      {persona ? (
        <>
          {persona.is_current === false && (
            <div className="card p-3 mb-4 bg-amber-500/10 border border-amber-500/20 text-center">
              <p className="text-sm text-amber-400">
                <i className="fa-solid fa-clock-rotate-left mr-2"></i>
                正在查看历史版本 v{persona.version}
                {persona.generated_at ? `（${new Date(persona.generated_at).toLocaleDateString("zh-CN")}）` : ""}
                <a href="/persona" onClick={e => { e.preventDefault(); nav("/persona"); }} className="#8b5e3c hover:underline ml-2">
                  返回当前版本 →
                </a>
              </p>
            </div>
          )}

          {/* 人格类型 + 置信度 */}
          <div className="card p-6 mb-5 bg-gradient-to-br from-indigo-500/8 to-purple-500/8 border-indigo-500/20 text-center">
            <div className="text-5xl mb-3"></div>
            <h3 className="text-2xl font-bold text-white">{persona.persona_type || "探索中"}</h3>
            <p className="#475569 mt-2 max-w-lg mx-auto">{persona.persona_summary || persona.summary}</p>
            <div style={{ marginTop: 10, display: "flex", justifyContent: "center", gap: 8 }}>
              <EvidenceButton query={`${persona.persona_type || ""} ${persona.persona_summary || ""}`} targetType="persona" targetId={persona.id} label="为什么得出这个人格" />
            </div>
            <div className="flex items-center justify-center gap-4 mt-4">
              <span className="tag bg-white/5 text-gray-400 text-xs">
                v{persona.version} · 置信度 {Math.round((persona.confidence || 0) * 100)}%
              </span>
              {persona.trigger_event && (
                <span className="tag bg-white/5 text-gray-400 text-xs">{persona.trigger_event}</span>
              )}
            </div>
          </div>

          {/* 五维人格评分总览 */}
          <div className="card p-5 mb-5">
            <h4 className="text-sm font-semibold text-gray-400 mb-4 text-center">五维人格评分</h4>
            <div className="grid grid-cols-5 gap-3 text-center">
              {[
                { label: "能力", icon: "💪", data: persona.ability_profile || persona.ability || {}, color: "from-indigo-500 to-purple-500" },
                { label: "兴趣", icon: "🎯", data: persona.interest_profile || persona.interest || {}, color: "from-emerald-500 to-teal-500" },
                { label: "价值观", icon: "💎", data: persona.value_profile || persona.value || {}, color: "from-amber-500 to-orange-500" },
                { label: "决策", icon: "🧭", data: persona.decision_style || persona.decision || {}, color: "from-rose-500 to-pink-500" },
                { label: "行为", icon: "🔄", data: persona.behavior_profile || persona.behavior || {}, color: "from-cyan-500 to-blue-500" },
              ].map((dim, i) => {
                // 决策风格是文本结构（style/traits），特殊渲染
                if (dim.label === "决策") {
                  const ds = persona.decision_style || persona.decision || {};
                  const styleText = ds.style || "";
                  const traits: string[] = Array.isArray(ds.traits) ? ds.traits : [];
                  return (
                    <div key={dim.label} className="p-3 rounded-xl bg-white/5">
                      <div className="text-lg mb-1">{dim.icon}</div>
                      <div className="text-xs text-gray-500 mb-1">{dim.label}</div>
                      <div className="text-xs font-semibold text-gray-300 leading-snug" style={{ minHeight: 28 }}>
                        {styleText || (traits[0] || "数据积累中")}
                      </div>
                      {traits.length > 0 && (
                        <div className="mt-1.5 text-[0.6rem] text-gray-500 leading-relaxed">{traits.slice(0, 2).join(" · ")}</div>
                      )}
                    </div>
                  );
                }
                const vals = dim.data && typeof dim.data === 'object' && !Array.isArray(dim.data)
                  ? (Object.values(dim.data) as any[]).filter((v: any) => typeof v === 'number') as number[]
                  : [];
                const avg = vals.length > 0 ? Math.round(vals.reduce((a:number,b:number)=>a+b,0) / vals.length) : 0;
                return (
                  <div key={dim.label} className="p-3 rounded-xl bg-white/5">
                    <div className="text-lg mb-1">{dim.icon}</div>
                    <div className="text-xs text-gray-500 mb-1">{dim.label}</div>
                    <div className={`text-2xl font-bold ${avg > 0 ? `bg-gradient-to-r ${dim.color} bg-clip-text text-transparent` : 'text-gray-500'}`}>
                      {avg > 0 ? avg : '-'}
                    </div>
                    {avg > 0 && (
                      <div className="h-1.5 mt-2 bg-white/10 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full bg-gradient-to-r ${dim.color}`} style={{width:`${avg}%`}} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-5">
            {/* 能力画像 */}
            {(persona.ability_profile || persona.ability) && Object.keys(persona.ability_profile || persona.ability || {}).length > 0 && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span></span> 能力画像
                  <span style={{ marginLeft: "auto" }}>
                    <EvidenceButton query={(Object.keys(persona.ability_profile || persona.ability || {}).join(" ")) + " " + (persona.persona_type || "")} targetType="persona" targetId={persona.id} label="为什么" size="xs" />
                  </span>
                </h4>
                <div className="space-y-3">
                  {Object.entries((persona.ability_profile || persona.ability || {}) as Record<string, number>).map(([key, val]) => (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="#475569">{key}</span>
                        <span className="text-gray-500">{val}</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all"
                          style={{ width: `${val}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 兴趣画像 */}
            {(persona.interest_profile || persona.interest) && Object.keys(persona.interest_profile || persona.interest || {}).length > 0 && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span></span> 兴趣画像
                  <span style={{ marginLeft: "auto" }}>
                    <EvidenceButton query={(Object.keys(persona.interest_profile || persona.interest || {}).join(" ")) + " " + (persona.persona_type || "")} targetType="persona" targetId={persona.id} label="为什么" size="xs" />
                  </span>
                </h4>
                <div className="space-y-3">
                  {Object.entries((persona.interest_profile || persona.interest || {}) as Record<string, number>).map(([key, val]) => (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="#475569">{INTEREST_ICONS[key] || "📌"} {key}</span>
                        <span className="text-gray-500">{val}</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all"
                          style={{ width: `${val}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 价值观画像 */}
            {(persona.value_profile || persona.value) && Object.keys(persona.value_profile || persona.value || {}).length > 0 && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span></span> 价值观画像
                  <span style={{ marginLeft: "auto" }}>
                    <EvidenceButton query={(Object.keys(persona.value_profile || persona.value || {}).join(" ")) + " " + (persona.persona_type || "")} targetType="persona" targetId={persona.id} label="为什么" size="xs" />
                  </span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries((persona.value_profile || persona.value || {}) as Record<string, number>).map(([key, val]) => (
                    <div key={key} className="p-3 rounded-xl bg-white/5 flex-1 min-w-[80px] text-center">
                      <div className="text-lg font-bold text-white">{val}</div>
                      <div className="text-xs text-gray-500 mt-1">{key}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 决策风格 */}
            {(persona.decision_style || persona.decision) && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span></span> 决策风格
                  <span style={{ marginLeft: "auto" }}>
                    <EvidenceButton query={(Object.keys(persona.decision_style?.traits || persona.decision?.traits || {}).join(" ")) + " " + (persona.persona_type || "")} targetType="persona" targetId={persona.id} label="为什么" size="xs" />
                  </span>
                </h4>
                {(persona.decision_style || persona.decision).style && (
                  <p className="text-lg font-semibold text-white mb-2">{(persona.decision_style || persona.decision).style}</p>
                )}
                {(persona.decision_style || persona.decision).traits && (
                  <div className="flex flex-wrap gap-2">
                    {(persona.decision_style || persona.decision).traits.map((trait: string, i: number) => (
                      <span key={i} className="tag bg-purple-500/20 text-indigo-400">{trait}</span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 行为模式 */}
            {(persona.behavior_profile || persona.behavior) && Object.keys(persona.behavior_profile || persona.behavior || {}).length > 0 && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span></span> 行为模式
                  <span style={{ marginLeft: "auto" }}>
                    <EvidenceButton query={(Object.keys(persona.behavior_profile || persona.behavior || {}).join(" ")) + " " + (persona.persona_type || "")} targetType="persona" targetId={persona.id} label="为什么" size="xs" />
                  </span>
                </h4>
                <div className="space-y-3">
                  {Object.entries((persona.behavior_profile || persona.behavior || {}) as Record<string, number>).map(([key, val]) => (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="#475569">{key}</span>
                        <span className="text-gray-500">{val}</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all"
                          style={{ width: `${Math.min(val, 100)}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 版本历史 */}
            {history && history.length > 1 && (
              <div className="card p-5 col-span-2">
                <h4 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                  <span></span> 画像版本历史
                  <span className="text-xs text-gray-600 ml-1">选择两个版本可对比成长变化</span>
                </h4>
                <div className="flex items-center gap-2 overflow-x-auto pb-2">
                  {history.map((ver: any) => (
                    <div
                      key={ver.id}
                      className={`flex-shrink-0 p-3 rounded-xl text-center min-w-[100px] no-underline transition cursor-pointer ${
                        compareSel.includes(ver.id)
                          ? "bg-emerald-500/15 border border-emerald-500/30"
                          : ver.id === persona.id ? "bg-indigo-500/15 border border-indigo-500/30" : "bg-white/5 hover:bg-white/5"
                      }`}
                      onClick={() => {
                        setCompareSel(prev => {
                          if (prev.includes(ver.id)) return prev.filter(x => x !== ver.id);
                          if (prev.length >= 2) return [prev[1], ver.id];
                          return [...prev, ver.id];
                        });
                      }}
                      title="点击选择对比"
                    >
                      <div className={`text-xs font-bold ${compareSel.includes(ver.id) ? "text-emerald-400" : ver.id === persona.id ? "#8b5e3c" : "text-gray-500"}`}>
                        v{ver.version}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {ver.generated_at ? new Date(ver.generated_at).toLocaleDateString("zh-CN") : ""}
                      </div>
                      <div className="text-xs text-gray-600 mt-0.5">
                        {Math.round((ver.confidence || 0) * 100)}%
                      </div>
                    </div>
                  ))}
                </div>

                {compareSel.length === 2 && (
                  <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
                    <button
                      className="btn"
                      style={{ padding: "6px 16px", fontSize: "0.75rem" }}
                      onClick={async () => {
                        const [a, b] = compareSel;
                        const resp = await fetch(`/api/mirror/persona/compare?v1=${a}&v2=${b}`, { credentials: "include" });
                        setCompareData(await resp.json());
                      }}
                    >
                      对比这两个版本
                    </button>
                    <button className="btn-ghost" style={{ padding: "6px 16px", fontSize: "0.75rem" }} onClick={() => { setCompareSel([]); setCompareData(null); }}>
                      取消
                    </button>
                  </div>
                )}

                {compareData && compareData.diff && (
                  <div style={{ marginTop: 16, padding: 14, borderRadius: 12, background: "var(--accent-bg2)", border: "1px solid var(--accent-border)" }}>
                    <p style={{ fontSize: "0.8rem", fontWeight: 700, marginBottom: 8 }}>v{compareData.older.version}（{Math.round((compareData.older.confidence || 0) * 100)}%）→ v{compareData.newer.version}（{Math.round((compareData.newer.confidence || 0) * 100)}%）
                    </p>
                    {compareData.diff.length === 0 && (
                      <p style={{ fontSize: "0.75rem", color: "var(--text4)" }}>五维画像无明显变化——数据仍在积累中</p>
                    )}
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {compareData.diff.map((d: any, i: number) => (
                        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem" }}>
                          <span style={{ color: "var(--text3)", width: 80 }}>{d.dimension}</span>
                          <span style={{ color: "var(--text4)" }}>{d.from}</span>
                          <span style={{ color: "var(--text4)" }}>→</span>
                          <span style={{ color: "var(--text2)", fontWeight: 600 }}>{d.to}</span>
                          <span style={{ color: d.delta > 0 ? "#34D399" : "#F87171", fontWeight: 700 }}>
                            {d.delta > 0 ? `+${d.delta}` : d.delta}
                          </span>
                        </div>
                      ))}
                    </div>
                    {compareData.new_data && compareData.new_data.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 6 }}>是什么数据带来了这些变化：</p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                          {compareData.new_data.map((nd: any, i: number) => (
                            <span key={i} className="tag" style={{
                              background: nd.type === "event" ? "rgba(52,211,153,0.15)" : "var(--surface2)",
                              color: nd.type === "event" ? "#34D399" : "var(--text3)",
                            }}>
                              {nd.type === "event" ? "🗓 " : "📝 "}{nd.title.slice(0, 24)}{nd.title.length > 24 ? "…" : ""} · {nd.date}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        /* 空状态 —— 还没有画像 */
        <div className="card p-16 text-center">
          <div className="text-6xl mb-5"></div>
          <h3 className="text-xl font-semibold text-gray-400 mb-2">尚未生成数字人格</h3>
          <p className="text-sm text-gray-500 mb-3">
            AI 需要积累了足够的人生数据后，才能为你生成准确的数字人格画像
          </p>
          <p className="text-sm text-gray-500 mb-8">
            当前建议至少：
            <span className="#8b5e3c">5条日常记录</span> +
            <span className="#8b5e3c">3个重要事件</span>
          </p>
          <button onClick={generate} disabled={generating} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold">
            <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>立即生成
          </button>
        </div>
      )}
    </div>
  );
}
