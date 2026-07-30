import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

const EVENT_TYPE_CONFIG: Record<string, { icon: string; label: string }> = {
  project: { icon: "📁", label: "项目经历" },
  competition: { icon: "🏆", label: "比赛经历" },
  achievement: { icon: "🌟", label: "成就突破" },
  study: { icon: "📖", label: "学习经历" },
  habit: { icon: "🔄", label: "长期习惯" },
  social: { icon: "👥", label: "社交经历" },
  relationship: { icon: "💞", label: "重要关系" },
  decision: { icon: "🧭", label: "重要决定" },
  turning_point: { icon: "🔀", label: "人生转折" },
  failure: { icon: "💪", label: "成长经历" },
  emotion: { icon: "💭", label: "情感经历" },
};

function getTagClass(etype: string): string {
  if (["project", "competition", "achievement"].includes(etype))
    return "tag bg-indigo-500/20 text-indigo-400";
  if (["study", "habit"].includes(etype))
    return "tag bg-emerald-500/20 text-emerald-400";
  if (["social", "relationship"].includes(etype))
    return "tag bg-amber-500/20 text-amber-400";
  if (["decision", "turning_point"].includes(etype))
    return "tag bg-purple-500/20 text-indigo-400";
  if (["failure", "emotion"].includes(etype))
    return "tag bg-rose-500/20 text-rose-400";
  return "tag bg-gray-500/20 text-gray-400";
}

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<any>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch(`/api/mirror/events/${id}`).then(r => r.json()).then(setEvent);
  }, [id]);

  async function deleteEvent() {
    if (!confirm(`确定删除「${event?.title}」吗？此操作不可恢复。`)) return;
    await fetch(`/api/mirror/events/${id}`, { method: "DELETE" });
    nav("/events");
  }

  if (!event) return null;

  const evTypeValue = typeof event.event_type === "object" ? event.event_type?.value : (event.event_type || event.type || "other");
  const display = EVENT_TYPE_CONFIG[evTypeValue] || { icon: "📌", label: evTypeValue };
  const dateStr = event.occurred_at || event.date || "";
  // LifeEvent 没有 ai_analysis JSON 字段，分析数据分散在独立列中
  const analysis: any = {
    emotion_detail: "",
    behavior_patterns: [],
    knowledge_domains: event.interest_tags || [],
    long_term_impact: event.ai_impact || "",
    encouragement: "",
    outlook: "",
    honest_reflection: "",
    search_insight: "",
  };

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      {/* 返回导航 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <a href="/events" onClick={e => { e.preventDefault(); nav("/events"); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </a>
          <h2 className="text-2xl font-bold">事件详情</h2>
        </div>
        <button
          onClick={deleteEvent}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition border border-rose-500/20"
        >
          <i className="fa-solid fa-trash mr-1"></i>删除
        </button>
      </div>

      {/* 事件主卡片 */}
      <div className="card p-6 mb-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">{display.icon}</span>
          <div>
            <span className={getTagClass(evTypeValue)}>{display.label}</span>
            <span className="text-xs text-gray-500 ml-2">
              {dateStr ? new Date(dateStr).toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" }) : ""}
            </span>
          </div>
        </div>

        <h3 className="text-xl font-bold text-white mb-3">{event.title}</h3>

        {event.description ? (
          <p className="#475569 leading-relaxed whitespace-pre-wrap">{event.description}</p>
        ) : (
          <p className="text-sm text-gray-500 italic">暂无详细描述</p>
        )}
      </div>

      {/* AI 分析面板 */}
      <div className="card p-6 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
        <div className="flex items-center gap-2 mb-5">
          <span className="text-xl">🤖</span>
          <h3 className="font-semibold text-white">AI 分析结果</h3>
          <span className="text-xs text-gray-500 ml-2">自动生成</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* 情绪倾向 */}
          <div className="p-4 rounded-xl bg-white/5">
            <p className="text-xs text-gray-500 mb-2">情绪倾向</p>
            <p className="text-lg">
              {event.emotion?.value === "positive" || event.emotion === "positive" ? (
                <span className="text-emerald-400">😊 积极</span>
              ) : event.emotion?.value === "negative" || event.emotion === "negative" ? (
                <span className="text-rose-400">😔 消极</span>
              ) : (
                <span className="#475569">😐 中性</span>
              )}
            </p>
            {analysis?.emotion_detail && (
              <p className="text-xs text-gray-400 mt-1 italic">"{analysis.emotion_detail}"</p>
            )}
          </div>

          {/* 行为模式 */}
          {analysis?.behavior_patterns && (
            <div className="p-4 rounded-xl bg-white/5">
              <p className="text-xs text-gray-500 mb-2">行为模式</p>
              <div className="flex flex-wrap gap-1">
                {analysis.behavior_patterns.map((p: string, i: number) => (
                  <span key={i} className="tag bg-purple-500/20 text-indigo-400">{p}</span>
                ))}
              </div>
            </div>
          )}

          {/* 兴趣领域 */}
          <div className="p-4 rounded-xl bg-white/5">
            <p className="text-xs text-gray-500 mb-2">关联兴趣</p>
            {event.interest_tags && event.interest_tags.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {event.interest_tags.map((tag: string, i: number) => (
                  <span key={i} className="tag bg-emerald-500/20 text-emerald-400">{tag}</span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">未检测到特定兴趣领域</p>
            )}
          </div>

          {/* 专业知识 */}
          {analysis?.knowledge_domains && (
            <div className="p-4 rounded-xl bg-white/5">
              <p className="text-xs text-gray-500 mb-2">专业知识</p>
              <div className="flex flex-wrap gap-1">
                {analysis.knowledge_domains.map((d: string, i: number) => (
                  <span key={i} className="tag bg-cyan-500/20 text-cyan-400">{d}</span>
                ))}
              </div>
            </div>
          )}

          {/* 人格维度影响 */}
          <div className="p-4 rounded-xl bg-white/5">
            <p className="text-xs text-gray-500 mb-2">人格维度影响</p>
            {event.persona_delta && Object.keys(event.persona_delta).length > 0 ? (
              <div className="space-y-1.5">
                {Object.entries(event.persona_delta as Record<string, number>).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-20 truncate">{key}</span>
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${val > 0 ? "bg-gradient-to-r from-indigo-500 to-purple-500" : "bg-gradient-to-r from-rose-500 to-orange-500"}`}
                        style={{ width: `${Math.min(Math.abs(val) * 10, 100)}%` }}
                      ></div>
                    </div>
                    <span className={`text-xs ${val >= 0 ? "text-emerald-400" : "text-rose-400"} w-8 text-right`}>
                      {val > 0 ? "+" : ""}{val}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">暂无显著人格维度影响</p>
            )}
          </div>

          {/* 事件重要性 */}
          <div className="p-4 rounded-xl bg-white/5">
            <p className="text-xs text-gray-500 mb-2">事件重要性</p>
            {event.memory ? (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full"
                      style={{ width: `${(event.memory.importance_score || 0.5) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-400">
                    {Math.round((event.memory.importance_score || 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">此事件已存入长期记忆</p>
              </>
            ) : (
              <p className="text-sm text-gray-500">此事件对人格影响较低</p>
            )}
          </div>
        </div>

        {/* AI 影响分析（合并长期影响） */}
        {event.ai_impact && (
          <div className="p-4 rounded-xl bg-white/5 mt-4">
            <p className="text-xs text-gray-500 mb-2">AI 影响分析</p>
            <p className="text-sm text-gray-400 leading-relaxed">{event.ai_impact}</p>
          </div>
        )}

        {/* 鼓励 + 展望 */}
        {(analysis?.encouragement || analysis?.outlook) && (
          <div className="grid grid-cols-2 gap-4 mt-3">
            {analysis.encouragement && (
              <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                <p className="text-xs text-emerald-400 mb-1">💚 鼓励</p>
                <p className="text-sm text-gray-200 leading-relaxed">{analysis.encouragement}</p>
              </div>
            )}
            {analysis.outlook && (
              <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10">
                <p className="text-xs text-indigo-400 mb-1">🔭 展望</p>
                <p className="text-sm text-gray-200 leading-relaxed">{analysis.outlook}</p>
              </div>
            )}
          </div>
        )}

        {/* 诚实反思 */}
        {analysis?.honest_reflection && (
          <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/10 mt-3">
            <p className="text-xs text-rose-400 mb-1">🪞 诚实的反思</p>
            <p className="text-sm text-gray-200 leading-relaxed">{analysis.honest_reflection}</p>
          </div>
        )}
      </div>

      {/* 关联记忆 */}
      {event.memory && (
        <div className="card p-5 mt-4 bg-white/3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm">🧠</span>
            <h4 className="text-sm font-semibold text-gray-400">关联生命记忆</h4>
          </div>
          <p className="text-sm text-gray-400">{event.memory.memory_content}</p>
        </div>
      )}
    </div>
  );
}
