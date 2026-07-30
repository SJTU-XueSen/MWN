import { useState } from "react";

export default function ProjectionPage() {
  const [projection, setProjection] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [years, setYears] = useState(10);

  async function generate() {
    setLoading(true);
    const r = await fetch("/api/mirror/projection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ years }),
    });
    if (r.ok) {
      const d = await r.json();
      setProjection(d.projection || []);
    }
    setLoading(false);
  }

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">推演人生</h2>
        <p className="text-gray-400 text-sm mt-1">不干预，不选择——AI 基于你的全部记忆和人格，推演未来可能的人生轨迹</p>
      </div>

      {projection.length === 0 && !loading && (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4">🔮</div>
          <p className="text-gray-400 mb-2">看看如果没有主动干预，未来可能如何展开</p>
          <p className="text-xs text-gray-600 mb-6">AI 会读取你的全部长期记忆、人格画像和活跃目标进行推演</p>
          <div className="flex items-center justify-center gap-3">
            <select className="input text-sm py-2 w-20" value={years} onChange={e => setYears(Number(e.target.value))}>
              {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}年</option>)}
            </select>
            <button onClick={generate} className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold">
              <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>开始推演
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div className="card p-12 text-center">
          <div className="w-10 h-10 border-3 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">AI 正在基于你的全部记忆推演未来...</p>
          <p className="text-xs text-gray-600 mt-2">这可能需要 30-60 秒</p>
        </div>
      )}

      {projection.length > 0 && (
        <>
          <div className="flex items-center gap-2 mb-6">
            <button onClick={() => setProjection([])} className="text-gray-500 hover:text-gray-400 transition text-sm">
              <i className="fa-solid fa-arrow-left mr-1"></i>重新推演
            </button>
            <span className="text-gray-600 text-xs ml-auto">{projection.length} 个人生节点</span>
          </div>

          {/* 时间线 */}
          <div className="relative pl-8 border-l-2 border-indigo-500/20 space-y-6">
            {projection.map((node: any, i: number) => {
              const colors = ["bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500"];
              const color = colors[i % colors.length];

              return (
                <div key={i} className="relative">
                  {/* 时间点 */}
                  <div className={`absolute -left-[29px] top-0 w-4 h-4 rounded-full border-2 border-white/10 ${color}`} />

                  {/* 年份标签 */}
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-xs font-bold ${color === "bg-indigo-500" ? "text-indigo-400" : color === "bg-emerald-500" ? "text-emerald-400" : color === "bg-amber-500" ? "text-amber-400" : "text-rose-400"}`}>
                      {node.year}年
                    </span>
                    <span className="text-xs text-gray-500">{node.age}岁</span>
                  </div>

                  {/* 卡片 */}
                  <div className="card p-4 bg-gradient-to-r from-white/3 to-transparent">
                    <h4 className="font-semibold text-white mb-2">{node.event}</h4>
                    {node.detail && <p className="text-sm text-gray-400 leading-relaxed">{node.detail}</p>}

                    {/* 人格变化 */}
                    {node.trait_shift && Object.keys(node.trait_shift).length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {Object.entries(node.trait_shift).map(([k, v]: any) => (
                          <span key={k} className={`tag text-xs ${
                            String(v).includes("↑") ? "bg-emerald-500/15 text-emerald-400" :
                            String(v).includes("↓") ? "bg-rose-500/15 text-rose-400" :
                            "bg-amber-500/15 text-amber-400"
                          }`}>{k} {v}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 底部提示 */}
          <div className="text-center mt-8">
            <p className="text-xs text-gray-600 leading-relaxed">
              🪞 这不是预言，而是基于你过去所有经历的推演。<br />
              真实的人生中，你的每一个选择都在改写未来的可能性。<br />
              这个推演的假设是：你保持当前的倾向和模式，不主动改变。
            </p>
          </div>
        </>
      )}
    </div>
  );
}
