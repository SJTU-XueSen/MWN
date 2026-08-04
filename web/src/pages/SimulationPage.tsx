import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const DIRECTIONS = [
  ["further_study", "🔬", "深度探索", "长期投入一个领域，追求知识积累与专业深度"],
  ["employment", "⚡", "现实创造", "将知识转化为产品和现实影响"],
  ["entrepreneurship", "🔥", "自主创造", "创造新的事业与可能性"],
  ["cross_discipline", "🔄", "跨界融合", "在多个领域之间建立独特的连接"],
] as const;

const SCENARIO_LABELS: Record<string, string> = {
  further_study: "深度探索",
  employment: "现实创造",
  entrepreneurship: "自主创造",
  cross_discipline: "跨界融合",
};

const SLIDERS = [
  ["探索程度", "exploration", "对未知领域的好奇和尝试意愿"],
  ["稳定偏好", "stability", "对确定性和可预测生活的偏好程度"],
  ["创造投入", "creativity", "将想法转化为行动和成果的驱动力"],
  ["社交网络", "social", "与外部世界建立连接和交流的倾向"],
  ["技术深耕", "tech_depth", "在特定技术领域持续深挖的意愿"],
] as const;

export default function SimulationPage() {
  const [sims, setSims] = useState<any[]>([]);
  const [view, setView] = useState<"list" | "create">("list");
  const [scenario, setScenario] = useState("further_study");
  const [question, setQuestion] = useState("");
  const [sliders, setSliders] = useState<Record<string, number>>({
    exploration: 50, stability: 50, creativity: 50, social: 50, tech_depth: 50,
  });
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const load = () =>
    fetch("/api/mirror/simulations")
      .then(r => r.json())
      .then(d => setSims(Array.isArray(d) ? d : d.simulations || []));
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const r = await fetch("/api/mirror/simulations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_type: scenario, question, ...sliders }),
    });
    if (r.ok) {
      const result = await r.json();
      setView("list");
      setQuestion("");
      load();
      if (result.id) nav(`/simulation/${result.id}`);
    }
    setLoading(false);
  }

  function sliderLabel(val: number) {
    return val <= 30 ? "较低" : val >= 70 ? "较高" : "适中";
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      {view === "list" ? (
        <>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold">人生模拟</h2>
              <p className="#475569 text-sm mt-1">AI 不会预测你的未来，而是基于你的经历生成"可能的自己"</p>
            </div>
            <button onClick={() => setView("create")} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold">
              <i className="fa-solid fa-flask mr-2"></i>创建人生实验
            </button>
          </div>

          {sims.length > 0 ? (
            <div className="space-y-4">
              {sims.map(s => {
                const firstPath = (s.paths || s.output_paths)?.[0];
                const scenarioVal = ((s.scenario || s.scenario_type || "") as string).toLowerCase();
                const label = firstPath?.label || SCENARIO_LABELS[scenarioVal] || scenarioVal;
                return (
                  <a
                    key={s.id}
                    href={`/simulation/${s.id}`}
                    onClick={e => { e.preventDefault(); nav(`/simulation/${s.id}`); }}
                    className="card p-5 block no-underline group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-semibold text-white group-hover:text-indigo-400 transition">
                            {label}
                          </h3>
                          <span className="tag bg-white/5 text-gray-400 text-xs">
                            {(s.paths || s.output_paths)?.length || 0}个可能的自己
                          </span>
                        </div>
                        {s.question && (
                          <p className="text-sm text-gray-400 mt-1">"{s.question?.slice(0, 100)}"</p>
                        )}
                        <p className="text-xs text-gray-600 mt-2">
                          {s.created_at ? new Date(s.created_at).toLocaleDateString("zh-CN") : ""}
                          {s.created_at ? ` ${new Date(s.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}` : ""}
                        </p>
                      </div>
                      <i className="fa-solid fa-chevron-right text-gray-600 group-hover:text-gray-400 transition"></i>
                    </div>
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="card p-16 text-center">
              <div className="text-6xl mb-5"></div>
              <h3 className="text-xl font-semibold text-gray-400 mb-2">发现未来的自己</h3>
              <p className="text-sm text-gray-500 mb-3 max-w-md mx-auto">
                AI 会从你的数字人格、ChromaDB 长期记忆和关键经历中，自动发现你可能的成长方向
              </p>
              <p className="text-xs text-gray-600 mb-8">建议先生成数字人格画像，镜像会更清晰</p>
              <div className="flex justify-center gap-4">
                <button onClick={() => setView("create")} className="btn text-white px-8 py-3 rounded-xl text-sm font-semibold inline-block">
                  <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>生成未来镜像
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-4">
                或者去 <a href="/persona" onClick={e => { e.preventDefault(); nav("/persona"); }} className="#8b5e3c hover:underline">先完善数字人格</a>，让镜像更准确
              </p>
            </div>
          )}
        </>
      ) : (
        /* 创建表单 */
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <a href="/simulation" onClick={e => { e.preventDefault(); setView("list"); }} className="text-gray-500 hover:text-gray-400 transition">
              <i className="fa-solid fa-arrow-left"></i>
            </a>
            <h2 className="text-2xl font-bold">创建人生实验</h2>
          </div>

          {/* 核心理念 */}
          <div className="card p-4 mb-5 bg-gradient-to-br from-indigo-500/3 to-purple-500/3 border-indigo-500/10">
            <p className="text-sm text-gray-400 leading-relaxed">
              <span className="#8b5e3c"></span>{" "}
              AI 不会预测你的未来，而是基于你的经历、记忆和价值倾向，生成几个可能成长出的未来自我，供你探索。
            </p>
          </div>

          <form onSubmit={create} className="card p-6 space-y-5">
            {/* 人生方向 */}
            <div>
              <label className="block text-sm text-gray-400 mb-3">人生方向 <span className="text-rose-400">*</span></label>
              <p className="text-xs text-gray-600 mb-3">选择一个你想探索的方向——不是选职业，是选你的人格朝哪个方向放大</p>
              <div className="grid grid-cols-2 gap-2">
                {DIRECTIONS.map(([did, icon, label, hint]) => (
                  <label
                    key={did}
                    className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                      scenario === did ? "border-indigo-400 bg-indigo-500/10" : "border-white/10 bg-white/3 hover:border-white/20"
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value={did}
                      checked={scenario === did}
                      onChange={() => setScenario(did)}
                      className="hidden"
                    />
                    <span className="text-xl flex-shrink-0 mt-0.5">{icon}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-200">{label}</p>
                      <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{hint}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* 问题 */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">你想探索什么？（可选）</label>
              <textarea
                className="input"
                rows={2}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                placeholder={"例如：如果我把好奇心驱动的探索坚持下去，5年后我会成为怎样的人？\n不填也可以——AI 会从你的数据中自动发现可能的方向"}
              />
            </div>

            {/* 人格变量 */}
            <div>
              <label className="block text-sm text-gray-400 mb-3">
                人格变量调节 <span className="text-xs text-gray-600">— 调整这些滑块来观察不同倾向下的未来变化</span>
              </label>
              <div className="space-y-3">
                {SLIDERS.map(([label, name, hint]) => (
                  <div key={name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="#475569">{label}</span>
                      <span className="text-gray-500">{sliderLabel(sliders[name] || 50)}</span>
                    </div>
                    <input
                      type="range"
                      name={name}
                      min={0}
                      max={100}
                      value={sliders[name] || 50}
                      step={10}
                      onChange={e => setSliders(prev => ({ ...prev, [name]: Number(e.target.value) }))}
                      className="w-full accent-indigo-500 h-1.5"
                    />
                    <p className="text-xs text-gray-600 mt-0.5">{hint}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 数据溯源 */}
            <div className="card p-4 bg-gradient-to-r from-indigo-500/5 to-purple-500/5 border-indigo-500/10">
              <p className="text-xs text-gray-400 mb-2 font-medium">AI 将基于以下真实数据生成未来镜像：</p>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div className="flex items-center gap-1.5"><span className="text-emerald-400"></span> 过去的人生记录</div>
                <div className="flex items-center gap-1.5"><span className="text-emerald-400"></span> 重要人生事件</div>
                <div className="flex items-center gap-1.5"><span className="text-emerald-400"></span> 当前数字人格画像</div>
                <div className="flex items-center gap-1.5"><span className="text-emerald-400"></span> 长期目标与兴趣</div>
                <div className="flex items-center gap-1.5 col-span-2"><span className="text-emerald-400"></span> ChromaDB 长期语义记忆</div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold" disabled={loading}>
                <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>{loading ? "生成中..." : "生成未来镜像"}
              </button>
              <button type="button" onClick={() => setView("list")} className="btn-ghost px-6 py-2.5 rounded-xl text-sm">
                取消
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
