import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const INTEREST_ICONS: Record<string, string> = {
  "AI": "🤖", "编程": "💻", "科研": "🔬", "设计": "🎨", "写作": "✍️",
  "音乐": "🎵", "体育": "⚽", "创业": "🚀", "教育": "📚", "社会": "🌍",
  "游戏": "🎮", "哲学": "💭", "心理学": "🧠", "经济": "📈", "政治": "🏛️",
};

export default function PersonaPage() {
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [generating, setGenerating] = useState(false);
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
    if (r.ok) {
      await new Promise(r => setTimeout(r, 3000));
      load();
    }
    setGenerating(false);
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
            <div className="text-5xl mb-3">🧬</div>
            <h3 className="text-2xl font-bold text-white">{persona.persona_type || "探索中"}</h3>
            <p className="#475569 mt-2 max-w-lg mx-auto">{persona.persona_summary || persona.summary}</p>
            <div className="flex items-center justify-center gap-4 mt-4">
              <span className="tag bg-white/5 text-gray-400 text-xs">
                v{persona.version} · 置信度 {Math.round((persona.confidence || 0) * 100)}%
              </span>
              {persona.trigger_event && (
                <span className="tag bg-white/5 text-gray-400 text-xs">{persona.trigger_event}</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-5">
            {/* 能力画像 */}
            {(persona.ability_profile || persona.ability) && Object.keys(persona.ability_profile || persona.ability || {}).length > 0 && (
              <div className="card p-5">
                <h4 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
                  <span>💪</span> 能力画像
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
                  <span>🎯</span> 兴趣画像
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
                  <span>💎</span> 价值观画像
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
                  <span>🧭</span> 决策风格
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
                  <span>🔄</span> 行为模式
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
                  <span>📜</span> 画像版本历史
                </h4>
                <div className="flex items-center gap-2 overflow-x-auto pb-2">
                  {history.map((ver: any) => (
                    <a
                      key={ver.id}
                      href={`/persona?version=${ver.id}`}
                      onClick={e => { e.preventDefault(); nav(`/persona?version=${ver.id}`); }}
                      className={`flex-shrink-0 p-3 rounded-xl text-center min-w-[100px] no-underline hover:scale-105 transition ${
                        ver.id === persona.id ? "bg-indigo-500/15 border border-indigo-500/30" : "bg-white/5 hover:bg-white/5"
                      }`}
                    >
                      <div className={`text-xs font-bold ${ver.id === persona.id ? "#8b5e3c" : "text-gray-500"}`}>
                        v{ver.version}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {ver.generated_at ? new Date(ver.generated_at).toLocaleDateString("zh-CN") : ""}
                      </div>
                      <div className="text-xs text-gray-600 mt-0.5">
                        {Math.round((ver.confidence || 0) * 100)}%
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        /* 空状态 —— 还没有画像 */
        <div className="card p-16 text-center">
          <div className="text-6xl mb-5">🧬</div>
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
