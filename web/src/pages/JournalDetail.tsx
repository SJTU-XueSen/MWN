import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

export default function JournalDetail() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<any>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch(`/api/mirror/journal/${id}`).then(r => r.json()).then(setRecord);
  }, [id]);

  async function deleteRecord() {
    if (!confirm("确定删除这条记录吗？此操作不可恢复。")) return;
    await fetch(`/api/mirror/journal/${id}`, { method: "DELETE" });
    nav("/journal");
  }

  if (!record) return null;
  const analysis = record.ai_analysis;

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <a href="/journal" onClick={e => { e.preventDefault(); nav("/journal"); }} className="text-gray-500 hover:text-gray-400 transition">
            <i className="fa-solid fa-arrow-left"></i>
          </a>
          <h2 className="text-2xl font-bold">记录详情</h2>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:bg-white/5 transition border border-white/10">
            <i className="fa-solid fa-pen mr-1"></i>编辑
          </button>
          <button onClick={deleteRecord} className="px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition border border-rose-500/20">
            <i className="fa-solid fa-trash mr-1"></i>删除
          </button>
        </div>
      </div>

      {/* 原文 */}
      <div className="card p-6 mb-4">
        <div className="flex items-center gap-3 mb-3">
          {record.mood && (
            <span className="text-sm text-gray-400 italic">心情：{record.mood}</span>
          )}
          <span className="text-xs text-gray-500">{record.record_date || record.date || ""}</span>
        </div>
        <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">{record.content}</p>
      </div>

      {/* AI 分析结果 */}
      {analysis ? (
        <div className="card p-6 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl"></span>
            <h3 className="font-semibold text-white">AI 分析结果</h3>
            {analysis.engine === "deepseek" ? (
              <span className="tag bg-green-500/20 text-green-400 text-xs ml-1"><i className="fa-solid fa-brain mr-1"></i>DeepSeek</span>
            ) : analysis.engine === "rule_based" ? (
              <span className="tag bg-amber-500/20 text-amber-400 text-xs ml-1"><i className="fa-solid fa-gear mr-1"></i>规则引擎</span>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {analysis.event && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">核心事件</p>
                <p className="text-sm text-gray-200">{analysis.event}</p>
              </div>
            )}

            {analysis.emotion && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">情绪倾向</p>
                <p className="text-sm">
                  {analysis.emotion === "positive" ? <span className="text-emerald-400">积极</span>
                    : analysis.emotion === "negative" ? <span className="text-rose-400">消极</span>
                    : <span className="#475569">中性</span>}
                </p>
                {analysis.emotion_detail && (
                  <p className="text-xs text-gray-400 mt-1 italic">"{analysis.emotion_detail}"</p>
                )}
              </div>
            )}

            {analysis.interest_fields && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">关联兴趣</p>
                <div className="flex flex-wrap gap-1">
                  {analysis.interest_fields.map((f: string, i: number) => (
                    <span key={i} className="tag bg-emerald-500/20 text-emerald-400">{f}</span>
                  ))}
                </div>
              </div>
            )}

            {analysis.behavior_patterns && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">行为模式</p>
                <div className="flex flex-wrap gap-1">
                  {analysis.behavior_patterns.map((p: string, i: number) => (
                    <span key={i} className="tag bg-purple-500/20 text-indigo-400">{p}</span>
                  ))}
                </div>
              </div>
            )}

            {analysis.knowledge_domains && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">专业知识</p>
                <div className="flex flex-wrap gap-1">
                  {analysis.knowledge_domains.map((d: string, i: number) => (
                    <span key={i} className="tag bg-cyan-500/20 text-cyan-400">{d}</span>
                  ))}
                </div>
              </div>
            )}

            {analysis.persona_delta && (
              <div className="p-3 rounded-xl bg-white/5">
                <p className="text-xs text-gray-500 mb-1">人格影响</p>
                <div className="space-y-1">
                  {Object.entries(analysis.persona_delta as Record<string, number>).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 w-16 truncate">{key}</span>
                      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${val >= 0 ? "bg-gradient-to-r from-indigo-500 to-purple-500" : "bg-gradient-to-r from-rose-500 to-orange-500"}`}
                          style={{ width: `${Math.min(Math.abs(val) * 10, 100)}%` }}
                        ></div>
                      </div>
                      <span className={`text-xs ${val >= 0 ? "text-emerald-400" : "text-rose-400"} w-8 text-right`}>
                        {val > 0 ? "+" : ""}{val}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {analysis.long_term_impact && (
            <div className="p-3 rounded-xl bg-white/5 mt-3">
              <p className="text-xs text-gray-500 mb-1">长期影响</p>
              <p className="text-sm text-gray-400">{analysis.long_term_impact}</p>
            </div>
          )}

          {analysis.search_insight && (
            <div className="p-3 rounded-xl bg-amber-500/5 mt-3 border border-amber-500/10">
              <p className="text-xs text-amber-400 mb-1">联网搜索洞察</p>
              <p className="text-sm text-gray-400">{analysis.search_insight}</p>
            </div>
          )}

          {(analysis.encouragement || analysis.outlook) && (
            <div className="grid grid-cols-2 gap-4 mt-3">
              {analysis.encouragement && (
                <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                  <p className="text-xs text-emerald-400 mb-1">鼓励</p>
                  <p className="text-sm text-gray-200 leading-relaxed">{analysis.encouragement}</p>
                </div>
              )}
              {analysis.outlook && (
                <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10">
                  <p className="text-xs text-indigo-400 mb-1">展望</p>
                  <p className="text-sm text-gray-200 leading-relaxed">{analysis.outlook}</p>
                </div>
              )}
            </div>
          )}

          {analysis.honest_reflection && (
            <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/10 mt-3">
              <p className="text-xs text-rose-400 mb-1">诚实的反思</p>
              <p className="text-sm text-gray-200 leading-relaxed">{analysis.honest_reflection}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="card p-6 text-center">
          <p className="text-sm text-gray-500">AI 分析尚未生成</p>
        </div>
      )}
    </div>
  );
}
