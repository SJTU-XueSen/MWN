import { useEffect, useState } from "react";
import EvidenceButton from "../components/EvidenceButton";
import { useNavigate, useParams } from "react-router-dom";

const EVENT_ICONS: Record<string, string> = {
  project: "📁", competition: "🏆", study: "📖", decision: "🧭",
  turning_point: "🔀", achievement: "🌟", failure: "💪", relationship: "💞",
  social: "👥", habit: "🔄", emotion: "💭",
};

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<any>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch(`/api/mirror/reports/${id}`).then(r => r.json()).then(setReport);
  }, [id]);

  async function deleteReport() {
    if (!confirm("确定删除这份报告吗？")) return;
    await fetch(`/api/mirror/reports/${id}`, { method: "DELETE" });
    nav("/reports");
  }

  if (!report) return null;

  const c = report.content || {};

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      {/* 返回 + 删除 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <a href="/reports" onClick={e => { e.preventDefault(); nav("/reports"); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </a>
          <h2 className="text-2xl font-bold">{report.title}</h2>
        </div>
        <button onClick={deleteReport} className="px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition border border-rose-500/20">
          <i className="fa-solid fa-trash mr-1"></i>删除
        </button>
      </div>

      {/* 报告元信息 */}
      <div className="card p-5 mb-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <i className="fa-solid fa-calendar"></i>
            <span>{report.period_start} — {report.period_end}</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <i className="fa-solid fa-clock"></i>
            <span>生成于 {report.date ? new Date(report.date).toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }) : ""}</span>
          </div>
          {c.engine === "deepseek" ? (
            <span className="tag bg-green-500/20 text-green-400"><i className="fa-solid fa-brain mr-1"></i>DeepSeek 深度分析</span>
          ) : (
            <span className="tag bg-amber-500/20 text-amber-400"><i className="fa-solid fa-gear mr-1"></i>规则引擎</span>
          )}
        </div>
      </div>

      {/* 核心摘要 */}
      {c.summary && (
        <div className="card p-6 mb-4 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
          <div className="flex items-start gap-3">
            <span className="text-2xl"></span>
            <div>
              <h3 className="font-semibold text-white mb-2">总体概览 <EvidenceButton query="总体概览" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h3>
              <p className="#475569 leading-relaxed">{c.summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* 情绪趋势 + 能力成长 双栏 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {c.emotional_trend && (
          <div className="card p-5">
            <h4 className="text-sm font-semibold text-gray-400 mb-3">情绪趋势 <EvidenceButton query="情绪趋势" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
            {c.emotional_trend.description && <p className="text-sm text-gray-400 mb-3">{c.emotional_trend.description}</p>}
            {(() => {
              const pos = c.emotional_trend.positive_pct || c.emotional_trend.positive || 0;
              const neg = c.emotional_trend.negative_pct || c.emotional_trend.negative || 0;
              return (
                <>
                  <div className="flex h-2 rounded-full overflow-hidden bg-white/5 mb-2">
                    <div className="bg-emerald-500" style={{ width: `${pos}%` }}></div>
                    <div className="bg-gray-600" style={{ width: `${100 - pos - neg}%` }}></div>
                    <div className="bg-rose-500" style={{ width: `${neg}%` }}></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span className="text-emerald-400">{pos}%</span>
                    <span></span>
                    <span className="text-rose-400">{neg}%</span>
                  </div>
                </>
              );
            })()}
          </div>
        )}

        {c.ability_growth && (
          <div className="card p-5">
            <h4 className="text-sm font-semibold text-gray-400 mb-3">能力成长 <EvidenceButton query="能力成长" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
            <div className="space-y-2">
              {(() => {
                const labels: Record<string, string> = { tech: "技术能力", creative: "创造力", social: "社交力", self_awareness: "自我认知" };
                return Object.entries(c.ability_growth as Record<string, number>).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-16">{labels[key] || key}</span>
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" style={{ width: `${val}%` }}></div>
                    </div>
                    <span className="text-xs text-gray-500 w-8 text-right">{val}</span>
                  </div>
                ));
              })()}
            </div>
          </div>
        )}
      </div>

      {/* 兴趣变化 */}
      {c.interest_changes && (
        <div className="card p-5 mb-4">
          <h4 className="text-sm font-semibold text-gray-400 mb-3">兴趣领域变化 <EvidenceButton query="兴趣领域变化" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
          <div className="space-y-3">
            {c.interest_changes.map((item: any, i: number) => (
              <div key={i}>
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/5">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-200 font-medium">{item.field}</span>
                    {item.trend && (
                      <span className={`tag text-xs ${
                        item.trend === "上升" ? "bg-emerald-500/20 text-emerald-400" :
                        item.trend === "下降" ? "bg-rose-500/20 text-rose-400" :
                        "bg-gray-500/20 text-gray-400"
                      }`}>{item.trend}</span>
                    )}
                  </div>
                  {item.count && <span className="text-xs text-gray-500">{item.count}条相关记录</span>}
                </div>
                {item.detail && <p className="text-xs text-gray-500 -mt-2 ml-2">{item.detail}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 关键事件分析 */}
      {(c.key_events_analysis || c.key_events) && (
        <div className="card p-5 mb-4">
          <h4 className="text-sm font-semibold text-gray-400 mb-3">关键事件 <EvidenceButton query="关键事件" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
          <div className="space-y-2">
            {(c.key_events_analysis || c.key_events).map((event: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-white/5">
                <span className="text-lg flex-shrink-0">{EVENT_ICONS[event.type] || "📌"}</span>
                <div>
                  <p className="text-sm text-gray-200">{event.title}</p>
                  {event.significance && <p className="text-xs text-gray-500 mt-1">{event.significance}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 人格变化 */}
      {c.personality_changes && (
        <div className="card p-5 mb-4">
          <h4 className="text-sm font-semibold text-gray-400 mb-2">人格变化 <EvidenceButton query="人格变化" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
          <p className="text-sm text-gray-400 leading-relaxed">{c.personality_changes}</p>
        </div>
      )}

      {/* 差距分析 + 建议 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {c.gap_analysis && (
          <div className="card p-5">
            <h4 className="text-sm font-semibold text-gray-400 mb-2">差距分析 <EvidenceButton query="差距分析" targetType="report" targetId={Number(id)} label="来源" size="xs" style={{ marginLeft: 6 }} /></h4>
            <p className="text-sm text-gray-400 leading-relaxed">{c.gap_analysis}</p>
          </div>
        )}

        {c.recommendation && (
          <div className="card p-5">
            <h4 className="text-sm font-semibold text-gray-400 mb-2">行动建议</h4>
            {typeof c.recommendation === "string" ? (
              <p className="text-sm text-gray-400 leading-relaxed whitespace-pre-wrap">{c.recommendation}</p>
            ) : (
              <div className="space-y-2">
                {c.recommendation.map((item: string, i: number) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="#8b5e3c text-xs mt-0.5">{i + 1}.</span>
                    <span className="text-sm text-gray-400">{item}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 鼓励 */}
      {c.encouragement && (
        <div className="card p-6 bg-gradient-to-br from-emerald-500/5 to-teal-500/5 border-emerald-500/10">
          <div className="flex items-start gap-3">
            <span className="text-2xl"></span>
            <div>
              <h4 className="font-semibold text-emerald-400 mb-2">写给现在的你</h4>
              <p className="#475569 leading-relaxed">{c.encouragement}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
