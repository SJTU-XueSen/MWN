import { useEffect, useState } from "react";

const CATEGORIES: Record<string, { icon: string; label: string }> = {
  kaoyan: { icon: "📚", label: "考研深造" },
  job: { icon: "💼", label: "求职就业" },
  startup: { icon: "🚀", label: "创业经历" },
  cross: { icon: "🔀", label: "转行跨界" },
  campus: { icon: "🎓", label: "大学生活" },
  failure: { icon: "💪", label: "失败教训" },
  ai: { icon: "🤖", label: "AI" },
  coding: { icon: "💻", label: "编程" },
  research: { icon: "🔬", label: "科研" },
};

export default function ReferencesPage() {
  const [currentCat, setCurrentCat] = useState("kaoyan");
  const [results, setResults] = useState<any[]>([]);
  const [userContext, setUserContext] = useState("");

  const load = (category: string) => {
    setCurrentCat(category);
    fetch(`/api/mirror/references?category=${category}`)
      .then(r => r.json())
      .then(d => {
        setResults(Array.isArray(d) ? d : d.results || []);
        if (d.user_context) setUserContext(d.user_context);
      });
  };

  useEffect(() => { load("kaoyan"); }, []);

  function trackClick(item: any) {
    fetch("/track/ref-click", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "article", detail: { category: currentCat, title: item.title } }),
    }).catch(() => {});
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">人生参考</h2>
        <p className="#475569 text-sm mt-1">
          联网搜索真实大学生的人生经历，从中获取经验、了解不同人生选择的可能性
        </p>
        {userContext && (
          <p className="text-xs text-indigo-400 mt-1">
            <i className="fa-solid fa-bullseye mr-1"></i>
            根据你的专业和兴趣（{userContext}）精准推送
          </p>
        )}
        <p className="text-xs text-gray-600 mt-1">
          <i className="fa-solid fa-circle-info mr-1"></i>
          内容来自公开网络，点击标题可跳转原文。
        </p>
      </div>

      {/* 分类标签 */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {Object.entries(CATEGORIES).map(([key, cat]) => (
          <button
            key={key}
            onClick={() => load(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition ${
              currentCat === key
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                : "bg-white/5 text-gray-400 hover:bg-white/5 border border-white/5"
            }`}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {/* 搜索结果 */}
      {results.length > 0 ? (
        <div className="space-y-3">
          {results.map((item, i) => (
            <a
              key={i}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => trackClick(item)}
              className="card p-4 block no-underline group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm text-gray-200 group-hover:text-indigo-400 transition leading-snug">
                    {item.title}
                  </h4>
                  <p className="text-xs text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">
                    {(item.snippet || "").slice(0, 200)}
                  </p>
                </div>
                <span className="text-xs flex-shrink-0 mt-0.5">
                  <i className="fa-solid fa-arrow-up-right-from-square text-gray-600 group-hover:text-indigo-400 transition"></i>
                </span>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="tag bg-white/5 text-gray-500 text-xs">
                  {item.source_icon} {item.source_name}
                </span>
                <span className="text-xs text-gray-600 truncate max-w-[300px]">{item.url}</span>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-sm text-gray-400 mb-1">搜索中或暂无结果</p>
          <p className="text-xs text-gray-600">换个分类试试，或等待网络搜索完成</p>
        </div>
      )}

      {/* 底部说明 */}
      <div className="card p-4 mt-6 bg-white/3">
        <p className="text-xs text-gray-500 leading-relaxed">
          <i className="fa-solid fa-shield-halved mr-1 text-gray-400"></i>
          <strong>免责声明：</strong>以上内容来自搜索引擎公开结果，AI人生镜像不对其真实性、准确性负责。所有内容版权归原作者所有，点击标题可跳转至原始网页。
        </p>
      </div>
    </div>
  );
}
