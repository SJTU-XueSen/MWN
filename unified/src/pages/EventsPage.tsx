import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import VoiceInput from "../components/VoiceInput";

const EVENT_TYPE_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  project: { icon: "📁", label: "项目经历", color: "indigo" },
  competition: { icon: "🏆", label: "比赛经历", color: "indigo" },
  achievement: { icon: "🌟", label: "成就突破", color: "indigo" },
  study: { icon: "📖", label: "学习经历", color: "emerald" },
  habit: { icon: "🔄", label: "长期习惯", color: "emerald" },
  social: { icon: "👥", label: "社交经历", color: "amber" },
  relationship: { icon: "💞", label: "重要关系", color: "amber" },
  decision: { icon: "🧭", label: "重要决定", color: "purple" },
  turning_point: { icon: "🔀", label: "人生转折", color: "purple" },
  failure: { icon: "💪", label: "成长经历", color: "rose" },
  emotion: { icon: "💭", label: "情感经历", color: "rose" },
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

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [etype, setEtype] = useState("study");
  const [edate, setEdate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const load = () =>
    fetch("/api/mirror/events")
      .then(r => r.json())
      .then((data: any) => setEvents(Array.isArray(data) ? data : data.events || []));
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    const r = await fetch("/api/mirror/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        description: desc,
        event_type: etype,
        occurred_at: edate,
      }),
    });
    if (r.ok) {
      setShowForm(false);
      setTitle("");
      setDesc("");
      setEtype("study");
      setEdate(new Date().toISOString().slice(0, 10));
      load();
    }
    setLoading(false);
  }

  const total = events.length;
  const typeCounts: Record<string, number> = {};
  events.forEach(ev => {
    const t = ev.event_type || ev.type || "other";
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  });

  // Group by month
  const grouped: Record<string, any[]> = {};
  events.forEach(ev => {
    const dateStr = ev.occurred_at || ev.date || "";
    const period = dateStr ? dateStr.slice(0, 7) : "未知";
    if (!grouped[period]) grouped[period] = [];
    grouped[period].push(ev);
  });

  return (
    <div className="max-w-5xl mx-auto px-8 py-8">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">人生地图</h2>
          <p className="#475569 text-sm mt-1">记录你人生中的重要事件，AI 会帮你发现成长轨迹</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold"
        >
          <i className="fa-solid fa-plus mr-2"></i>记录事件
        </button>
      </div>

      {/* 创建表单 */}
      {showForm ? (
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-gray-400 transition"><i className="fa-solid fa-arrow-left"></i></button>
            <h2 className="text-2xl font-bold">记录人生事件</h2>
          </div>
          <form onSubmit={create} className="card p-6 space-y-5">
            <div>
              <label className="block text-sm text-gray-400 mb-2">事件标题 <span className="text-rose-400">*</span></label>
              <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="例如：第一次参加全国大学生电子设计竞赛" required autoFocus maxLength={200} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-3">事件类型 <span className="text-rose-400">*</span></label>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(EVENT_TYPE_CONFIG).map(([k, cfg]) => (
                  <label key={k} className={`flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition ${etype === k ? "border-indigo-400 bg-indigo-500/10" : "border-white/10 bg-white/3 hover:border-white/20"}`}>
                    <input type="radio" name="event_type" value={k} checked={etype === k} onChange={() => setEtype(k)} className="hidden" />
                    <span className="text-lg flex-shrink-0">{cfg.icon}</span>
                    <span className="text-xs text-gray-200">{cfg.label}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">详细描述</label>
              <div className="relative">
                <textarea className="input" rows={6} value={desc} onChange={e => setDesc(e.target.value)} placeholder={`描述事件的经过、你的感受和收获。\n\n例如：大三和同学组队参加电赛...`} />
                <div className="absolute bottom-2 right-2"><VoiceInput onText={text => setDesc(prev => prev + text)} /></div>
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">发生日期</label>
              <input type="date" className="input" value={edate} onChange={e => setEdate(e.target.value)} />
            </div>
            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold" disabled={loading}>
                <i className="fa-solid fa-check mr-2"></i>{loading ? "保存中..." : "保存事件"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-gray-200 transition border border-white/10">取消</button>
            </div>
          </form>
          <div className="card p-5 mt-4 bg-white/3">
            <p className="text-xs text-gray-500"><i className="fa-solid fa-lightbulb text-amber-400 mr-1"></i><strong>人生事件 vs 日常记录：</strong>日常记录是「今天发生了什么」，人生事件是「什么塑造了今天的我」—— 项目、比赛、重要决定、转折点都属于人生事件。</p>
          </div>
        </div>
      ) : (
      <>

      {/* 统计条 */}
      <div className="card p-4 mb-6 flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          <span className="text-sm text-gray-400">
            共 <strong className="#10213c">{total}</strong> 个人生事件
          </span>
        </div>
        {Object.keys(typeCounts).length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {Object.entries(typeCounts).map(([etypeKey, count]) => {
              const cfg = EVENT_TYPE_CONFIG[etypeKey] || { icon: "📌", label: etypeKey, color: "gray" };
              return (
                <span key={etypeKey} className="tag bg-white/5 text-gray-400">
                  {cfg.icon} {cfg.label} ×{count}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {events.length > 0 ? (
        /* 时间线 */
        <div className="relative">
          {/* 中心线 */}
          <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-white/8 ml-[1px]"></div>

          <div className="space-y-0">
            {Object.entries(grouped).map(([period, periodEvents]) => (
              <div key={period}>
                {/* 月份分隔 */}
                <div className="flex items-center gap-4 py-3 first:pt-0">
                  <div className="w-10 flex-shrink-0 flex justify-center relative z-10">
                    <div className="w-3 h-3 rounded-full bg-indigo-500 border-2 border-[var(--bg)]"></div>
                  </div>
                  <h3 className="text-base font-bold text-gray-400">
                    {period.length === 7
                      ? `${period.slice(0, 4)}年${parseInt(period.slice(5, 7))}月`
                      : period}
                  </h3>
                </div>

                {/* 事件卡片 */}
                {periodEvents.map((event: any) => {
                  const evType = event.event_type || event.type || "other";
                  const evTypeValue = typeof evType === "object" ? evType.value || "other" : evType;
                  const cfg = EVENT_TYPE_CONFIG[evTypeValue] || { icon: "📌", label: evTypeValue, color: "gray" };
                  const dateStr = event.occurred_at || event.date || "";
                  const emotionVal = event.emotion;
                  const emotionStr = typeof emotionVal === "object" ? emotionVal.value : emotionVal;

                  return (
                    <a
                      key={event.id}
                      href={`/events/${event.id}`}
                      onClick={e => { e.preventDefault(); nav(`/events/${event.id}`); }}
                      className="flex items-start gap-4 py-2.5 group no-underline"
                    >
                      <div className="w-10 flex-shrink-0 flex justify-center relative z-10 pt-0.5">
                        <span className="text-lg">{cfg.icon}</span>
                      </div>
                      <div className="flex-1 card p-4 group-hover:border-white/20 transition-all min-w-0">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-semibold text-gray-200 group-hover:text-white transition truncate">
                              {event.title}
                            </h4>
                            {event.description && (
                              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                                {(event.description || "").slice(0, 150)}
                                {(event.description || "").length > 150 ? "..." : ""}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {emotionStr && (
                              <span className="text-sm">
                                {emotionStr === "positive" ? "😊" : emotionStr === "negative" ? "😔" : "😐"}
                              </span>
                            )}
                            <i className="fa-solid fa-chevron-right text-gray-600 group-hover:text-gray-400 transition text-xs"></i>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className={getTagClass(evTypeValue)}>{cfg.label}</span>
                          {event.interest_tags &&
                            event.interest_tags.slice(0, 3).map((tag: string, i: number) => (
                              <span key={i} className="tag bg-emerald-500/20 text-emerald-400">
                                {tag}
                              </span>
                            ))}
                          <span className="text-xs text-gray-600">
                            {dateStr ? `${new Date(dateStr).getMonth() + 1}月${new Date(dateStr).getDate()}日` : ""}
                          </span>
                        </div>
                      </div>
                    </a>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* 空状态 */
        <div className="card p-16 text-center">
          <div className="text-6xl mb-5">🗺️</div>
          <h3 className="text-xl font-semibold text-gray-400 mb-2">这里是你的人生地图</h3>
          <p className="text-sm text-gray-500 mb-2">记录重要的项目、比赛、决定、转折点……</p>
          <p className="text-sm text-gray-500 mb-8">每一次记录，都是人生轨迹上的一个标记</p>
          <div className="flex justify-center gap-4">
            <button
              onClick={() => setShowForm(true)}
              className="btn text-white px-6 py-2.5 rounded-xl text-sm font-semibold inline-block"
            >
              <i className="fa-solid fa-plus mr-2"></i>记录第一个事件
            </button>
            <button
              onClick={() => nav("/journal")}
              className="px-6 py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:text-gray-200 transition border border-white/10 inline-block"
            >
              <i className="fa-solid fa-pen mr-2"></i>写日常记录
            </button>
          </div>
        </div>
      )}

      {/* 底部快捷入口 */}
      <div className="mt-6 flex items-center gap-3 text-sm text-gray-500">
        <span>快速跳转：</span>
        <a href="/journal" onClick={e => { e.preventDefault(); nav("/journal"); }} className="#8b5e3c hover:underline">
          📝 日常记录
        </a>
        <span>·</span>
        <a href="/persona" onClick={e => { e.preventDefault(); nav("/persona"); }} className="#8b5e3c hover:underline">
          🧬 数字人格
        </a>
      </div>
      </>
    )}
    </div>
  );
}
