import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

export default function ExperiencePage() {
  const { fsId } = useParams<{ fsId: string }>();
  const nav = useNavigate();
  const [session, setSession] = useState<any>(null);
  const [scene, setScene] = useState<any>(null);
  const [lastResult, setLastResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [customChoice, setCustomChoice] = useState("");
  const [choosing, setChoosing] = useState(false);

  useEffect(() => {
    startExperience();
  }, [fsId]);

  async function startExperience() {
    setLoading(true);
    const r = await fetch(`/api/mirror/experience/start/${fsId}`, { method: "POST" });
    if (r.ok) {
      const d = await r.json();
      setSession(d);
      setScene(d.scene);
    }
    setLoading(false);
  }

  async function makeChoice(choiceIdx: number, custom?: string) {
    setChoosing(true);
    const r = await fetch(`/api/mirror/experience/play/${session.session_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choice: choiceIdx, custom_choice: custom || "" }),
    });
    if (r.ok) {
      const d = await r.json();
      setLastResult(d.last_result);
      setScene(d.scene);
      setSession((prev: any) => ({ ...prev, ...d.session }));
    }
    setChoosing(false);
    setCustomChoice("");
  }

  async function restart() {
    if (!confirm("重新开始？当前进度将丢失。")) return;
    setLastResult(null);
    setScene(null);
    startExperience();
  }

  if (loading) return null;

  const traits = session?.traits || {};
  const stableKeys = ["专注度", "独立性", "探索欲", "社交需求", "抗挫力"];
  const growingKeys = ["技术能力", "表达能力", "管理能力", "行动力"];
  const lifeState = session?.life_state || {};

  return (
    <div className="max-w-2xl mx-auto px-8 py-8">
      {/* 顶栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">人生体验</h2>
          <p className="text-xs text-gray-500 mt-1">
            {session?.current_year}年 · {session?.current_age}岁 · 种子 #{session?.random_seed}
          </p>
        </div>
        <button onClick={restart} className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-gray-200 border border-white/10 transition">
          <i className="fa-solid fa-rotate-right mr-1"></i>重新开始
        </button>
      </div>

      {/* 人格权重 */}
      <div className="card p-3 mb-4 bg-white/3">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="text-gray-500">当前状态</span>
          {Object.entries(traits).filter(([k]) => !k.startsWith("_")).map(([k, v]: any) => (
            <span key={k} className="tag bg-white/5 text-gray-400">{k} {v}</span>
          ))}
        </div>
      </div>

      {/* 上一次选择的结果 */}
      {lastResult && (
        <div className="card p-4 mb-4 bg-amber-500/5 border border-amber-500/10">
          <p className="text-xs text-amber-400 mb-1">你的选择</p>
          <p className="text-sm text-gray-400">{lastResult.chosen}</p>
          <p className="text-xs text-gray-400 mt-2">{lastResult.outcome}</p>
          {lastResult.trait_changes && (
            <div className="flex gap-1 mt-2">
              {Object.entries(lastResult.trait_changes as Record<string, number>).map(([k, v]) => (
                <span key={k} className={`tag text-xs ${v > 0 ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}`}>
                  {k} {v > 0 ? "+" : ""}{v}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 状态面板 */}
      {scene?.current_traits && (
        <div className="card p-3 mb-4 bg-white/3">
          <p className="text-xs text-gray-500 mb-2">{session?.current_year}年 · {session?.current_age}岁</p>
          {Object.keys(lifeState).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {Object.entries(lifeState).map(([k, v]: any) => (
                <span key={k} className="tag text-xs bg-amber-500/10 text-amber-400">{k}: {v}</span>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-600 mb-1">人格倾向</p>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {Object.entries(scene.current_traits || {}).filter(([k]: any) => stableKeys.includes(k)).map(([k, v]: any) => {
              const delta = scene.trait_deltas?.[k] || 0;
              return (
                <span key={k} className={`tag text-xs ${delta > 0 ? "bg-emerald-500/10 text-emerald-400" : delta < 0 ? "bg-rose-500/10 text-rose-400" : "bg-white/5 text-gray-400"}`}>
                  {k} {v}{delta !== 0 ? (delta > 0 ? " ↑" : " ↓") : ""}
                </span>
              );
            })}
          </div>
          <p className="text-xs text-gray-600 mb-1">成长能力</p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(scene.current_traits || {}).filter(([k]: any) => growingKeys.includes(k)).map(([k, v]: any) => {
              const delta = scene.trait_deltas?.[k] || 0;
              return (
                <span key={k} className={`tag text-xs ${delta > 0 ? "bg-emerald-500/10 text-emerald-400" : delta < 0 ? "bg-rose-500/10 text-rose-400" : "bg-white/5 text-gray-400"}`}>
                  {k} {v}{delta !== 0 ? (delta > 0 ? " ↑" : " ↓") : ""}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* 当前场景 */}
      {scene ? (
        <>
          <div className="card p-6 mb-5 bg-gradient-to-br from-indigo-500/3 to-purple-500/3 border-indigo-500/10">
            <p className="text-gray-200 leading-relaxed text-sm">{scene.narrative}</p>
          </div>

          {/* 选择 */}
          {scene.choices && scene.choices.length > 0 && (
            <div className="space-y-3 mb-6">
              {scene.choices.map((c: any, i: number) => (
                <button
                  key={i}
                  onClick={() => makeChoice(i)}
                  disabled={choosing}
                  className="w-full text-left p-4 rounded-xl border border-white/10 bg-white/3 hover:bg-white/8 hover:border-white/20 transition cursor-pointer group"
                >
                  <p className="text-sm text-gray-200 group-hover:text-white transition mb-2">{c.text}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {c.gain && <div><span className="text-emerald-400">✓ {c.gain}</span></div>}
                    {c.cost && <div><span className="text-rose-400">✗ {c.cost}</span></div>}
                  </div>
                  {c.hint && <p className="text-xs text-gray-600 mt-2">{c.hint}</p>}
                </button>
              ))}

              {/* 开放式选择 */}
              <div className="p-4 rounded-xl border border-dashed border-purple-500/20 bg-purple-500/3 hover:border-purple-500/40 transition">
                <p className="text-xs text-indigo-400 mb-2">✧ 或者，你想做什么？</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="input flex-1 text-xs py-2"
                    value={customChoice}
                    onChange={e => setCustomChoice(e.target.value)}
                    placeholder="写下你自己的选择..."
                  />
                  <button
                    onClick={() => customChoice.trim() && makeChoice(-1, customChoice.trim())}
                    disabled={choosing || !customChoice.trim()}
                    className="btn text-white px-4 py-2 rounded-lg text-xs font-semibold flex-shrink-0"
                  >
                    确定
                  </button>
                </div>
                <p className="text-xs text-gray-600 mt-2">你的人格权重仍然会影响结果，但选择本身是自由的</p>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card p-12 text-center">
          <p className="text-sm text-gray-500">体验数据加载中...</p>
        </div>
      )}

      {/* 底部理念 */}
      <div className="text-center mt-6">
        <p className="text-xs text-gray-500 leading-relaxed">
          🪞 人生模拟不是预测未来，而是探索可能性。<br />
          你的选择、习惯和价值倾向决定了某些趋势。<br />
          但随机事件、环境变化和偶然相遇，也会共同塑造人生。<br />
          <span className="text-gray-600">种子 #{session?.random_seed} · 每一次模拟都是独立不可再现的人生</span>
        </p>
      </div>
    </div>
  );
}
