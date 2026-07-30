import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const CAT_ICONS: Record<string, string> = {
  "社会实践": "🤝", "文体活动": "🎭", "学术活动": "📚", "志愿服务": "💚", "社团活动": "🎯", "其他": "📋",
  "技术": "💻", "创新": "💡", "创业": "🚀", "设计": "🎨", "体育": "⚽", "竞赛": "🏆", "综合": "📋",
};
const STATUS_MAP: Record<string, string> = {
  recruiting: "招募中", full: "已满员", closed: "已关闭",
};
const STATUS_CLASS: Record<string, string> = {
  recruiting: "tag bg-emerald-500/20 text-emerald-400",
  full: "tag bg-amber-500/20 text-amber-400",
  closed: "tag bg-gray-500/20 text-gray-400",
};

const CATEGORIES = ["社会实践", "文体活动", "学术活动", "志愿服务", "社团活动", "其他"];
const LEVELS = ["国家级", "省市级", "校级", "院级"];

export default function ConnectionsPage() {
  const nav = useNavigate();
  const [view, setView] = useState<"list" | "detail" | "create" | "pending">("list");
  const [activities, setActivities] = useState<any[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);
  const [filter, setFilter] = useState({ category: "", level: "", search: "" });
  const [detail, setDetail] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);
  const [friends, setFriends] = useState<any[]>([]);
  const [sjtuItems, setSjtuItems] = useState<any[]>([]);
  const [sourceFilter, setSourceFilter] = useState<"all"|"team"|"sjtu">("all");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadActivities(); loadSjtu(); loadFriends(); }, []);

  async function loadActivities(cat = "", lev = "", srch = "") {
    setLoading(true);
    const p = new URLSearchParams();
    if (cat) p.set("category", cat);
    if (lev) p.set("level", lev);
    if (srch) p.set("search", srch);
    const r = await fetch(`/nexus/api/competitions?${p}`);
    if (r.ok) {
      const d = await r.json();
      setActivities(d.activities || []);
      setCategories(d.categories || []);
      setLevels(d.levels || []);
    }
    const r2 = await fetch("/nexus/api/pending-activities");
    if (r2.ok) { const d = await r2.json(); setPending(d.activities || []); }
    setLoading(false);
  }

  async function loadSjtu() {
    try {
      const r = await fetch("/api/activities");
      if (r.ok) { const d = await r.json(); setSjtuItems(d.items || []); }
    } catch {}
  }

  async function loadFriends() {
    const r = await fetch("/nexus/api/potential-friends");
    if (r.ok) { const d = await r.json(); setFriends(d.friends || []); }
  }

  async function showDetail(id: string) {
    setLoading(true);
    const r = await fetch(`/nexus/api/competitions/${id}`);
    if (r.ok) { setDetail(await r.json()); setView("detail"); }
    setLoading(false);
  }

  async function joinTeam(teamId: string) {
    const r = await fetch(`/nexus/api/teams/${teamId}/join`, { method: "POST" });
    const d = await r.json();
    setMessage(d.error || d.message || "");
    if (d.ok && detail) showDetail(detail.id);
    setTimeout(() => setMessage(""), 4000);
  }

  async function createActivity(e: React.FormEvent) {
    e.preventDefault();
    const form = new FormData(e.target as HTMLFormElement);
    const body: any = {};
    for (const [k, v] of form.entries()) body[k] = v;
    body.max_team_size = parseInt(body.max_team_size || "5");
    body.min_team_size = parseInt(body.min_team_size || "1");
    const r = await fetch("/nexus/api/competition/create", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (d.ok) { setMessage(d.message); setView("list"); loadActivities(); }
    else setMessage(d.error || "创建失败");
    setTimeout(() => setMessage(""), 4000);
  }

  async function createTeam(e: React.FormEvent) {
    e.preventDefault();
    const form = new FormData(e.target as HTMLFormElement);
    const body: any = { competition_id: detail?.id };
    for (const [k, v] of form.entries()) body[k] = v;
    const r = await fetch("/nexus/api/team/create", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (d.ok) {
      setMessage(`战队「${d.name}」创建成功！`);
      showDetail(detail.id);
    } else setMessage(d.error || "创建失败");
    setTimeout(() => setMessage(""), 4000);
  }

  async function doScrape() {
    setMessage("爬虫已触发，请稍后刷新...");
    await fetch("/nexus/api/scrape/trigger", { method: "POST" });
    setTimeout(() => { loadActivities(); setMessage(""); }, 5000);
  }

  async function approve(id: string) {
    await fetch(`/nexus/api/competition/${id}/approve`, { method: "POST" });
    loadActivities();
  }
  async function reject(id: string) {
    await fetch(`/nexus/api/competition/${id}/reject`, { method: "POST" });
    loadActivities();
  }

  // ── 活动大厅列表 ──
  if (view === "list") {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        {message && <div className={`card p-3 mb-4 text-center text-sm ${message.includes("成功") || message.includes("已提交") ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border border-rose-500/20 text-rose-400"}`}>{message}</div>}

        {/* 顶栏 */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-2xl font-bold">活动大厅</h2>
          <div className="flex gap-2">
            <button onClick={doScrape} className="px-4 py-2 rounded-xl text-sm font-semibold bg-white/5 border border-white/10 text-gray-400 hover:border-white/20 transition">
              <i className="fa-solid fa-robot mr-2"></i>爬取活动
            </button>
            <button onClick={() => { if (pending.length > 0) { setView("pending"); } else { setMessage("暂无待审核活动"); setTimeout(() => setMessage(""), 3000); } }}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-white/5 border border-white/10 text-gray-400 hover:border-white/20 transition">
              <i className="fa-solid fa-clock mr-2"></i>待审核{pending.length > 0 ? ` (${pending.length})` : ""}
            </button>
            <button onClick={() => setView("create")} className="btn text-white px-5 py-2 rounded-xl text-sm font-semibold">
              <i className="fa-solid fa-plus mr-2"></i>发布活动
            </button>
            <button onClick={() => nav("/connections/work")} className="px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/25 transition">
              <i className="fa-solid fa-briefcase mr-2"></i>工作台
            </button>
          </div>
        </div>

        {/* 筛选栏 */}
        <div className="card p-4 mb-5">
          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex-1 min-w-[160px]">
              <label className="block text-xs text-gray-500 mb-1">搜索</label>
              <input type="text" value={filter.search} onChange={e => setFilter(f => ({ ...f, search: e.target.value }))}
                onKeyDown={e => e.key === "Enter" && loadActivities(filter.category, filter.level, filter.search)}
                placeholder="搜索活动..." className="input text-sm py-2 px-3 rounded-lg bg-white/5 border border-white/10 text-gray-400 w-full" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">分类</label>
              <select value={filter.category} onChange={e => { setFilter(f => ({ ...f, category: e.target.value })); loadActivities(e.target.value, filter.level, filter.search); }}
                className="input text-sm py-2 px-3 rounded-lg bg-white/5 border border-white/10 text-gray-400">
                <option value="">全部分类</option>
                {(categories.length > 0 ? categories : CATEGORIES).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">级别</label>
              <select value={filter.level} onChange={e => { setFilter(f => ({ ...f, level: e.target.value })); loadActivities(filter.category, e.target.value, filter.search); }}
                className="input text-sm py-2 px-3 rounded-lg bg-white/5 border border-white/10 text-gray-400">
                <option value="">全部级别</option>
                {(levels.length > 0 ? levels : LEVELS).map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* 潜在好友 */}
        {friends.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">🔗 潜在队友</h3>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {friends.slice(0, 6).map(f => (
                <div key={f.user_id} className="card p-4 flex-shrink-0 min-w-[200px] bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-semibold text-xs">{f.real_name?.[0]}</div>
                    <span className="text-sm font-semibold text-white">{f.real_name}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {f.skill_tags?.slice(0, 3).map((t: string, i: number) => (
                      <span key={i} className="tag bg-indigo-500/15 text-indigo-400 text-xs">{t}</span>
                    ))}
                  </div>
                  {f.complementary_skills?.length > 0 && (
                    <p className="text-xs text-emerald-400">互补：{f.complementary_skills.slice(0, 2).join("、")}</p>
                  )}
                  {f.shared_skills?.length > 0 && (
                    <p className="text-xs text-gray-500">共同：{f.shared_skills.slice(0, 2).join("、")}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 来源筛选标签 */}
        <div className="flex gap-2 mb-4">
          {(["all","team","sjtu"] as const).map(t => (
            <button key={t} onClick={() => setSourceFilter(t)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${sourceFilter===t?"bg-indigo-500 text-white":"bg-white/5 text-gray-500 hover:bg-black/10"}`}>
              {t==="all"?`全部 (${activities.length+sjtuItems.length})`:t==="team"?`🔵 组队 (${activities.length})`:`🟢 SJTU通知 (${sjtuItems.length})`}
            </button>
          ))}
        </div>

        {/* ═══ 组队活动卡片 ═══ */}
        {(sourceFilter==="all"||sourceFilter==="team") && activities.length > 0 && (
          <div className="grid gap-4 mb-6" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
            {activities.map(a => (
              <div key={"t-"+a.id} className="card p-5 cursor-pointer hover:border-indigo-500/30 transition group" onClick={() => showDetail(a.id)}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="tag bg-blue-500/15 text-blue-400 text-xs">🔵 组队</span>
                  <span className="text-xl">{CAT_ICONS[a.category] || "📌"}</span>
                  <span className="tag bg-indigo-500/15 text-indigo-400 text-xs">{a.level || "未分类"}</span>
                </div>
                <h3 className="font-semibold text-white group-hover:text-indigo-400 transition mb-1">{a.title}</h3>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-2 flex-wrap">
                  {a.category && <span className="tag bg-white/5 text-gray-400">{a.category}</span>}
                  <span>👥 {a.min_team_size}-{a.max_team_size}人</span>
                  {a.registration_deadline && <span>⏰ {a.registration_deadline}截止</span>}
                  {a.team_count > 0 && <span className="text-emerald-400">{a.team_count}个战队</span>}
                </div>
                {a.description && <p className="text-sm text-gray-400 line-clamp-2 mb-3">{a.description}</p>}
                <div className="flex items-center justify-between text-xs mt-auto">
                  <span className="text-gray-600">{a.publisher_name || "用户发布"}</span>
                  <span className="text-indigo-400 group-hover:underline">查看详情 →</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ═══ SJTU 通知卡片（保留原始展开/折叠设计） ═══ */}
        {(sourceFilter==="all"||sourceFilter==="sjtu") && sjtuItems.length > 0 && (
          <div>
            {sourceFilter==="all" && <h3 className="text-sm font-semibold text-gray-400 mb-3 mt-2">🟢 SJTU 通知公告</h3>}
            {sjtuItems.map((a: any) => (
              <SJTUCard key={"s-"+a.id} item={a} />
            ))}
          </div>
        )}

        {/* 空状态 */}
        {activities.length === 0 && sjtuItems.length === 0 && (
          <div className="card p-16 text-center">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-400 mb-2">暂无活动</p>
            <p className="text-xs text-gray-600 mb-6">点击「爬取活动」获取 SJTU 最新活动，或「发布活动」创建新活动</p>
            <div className="flex gap-3 justify-center">
              <button onClick={doScrape} className="px-5 py-2.5 rounded-xl text-sm bg-white/5 border border-white/10 text-gray-400 hover:border-white/20 transition">
                <i className="fa-solid fa-robot mr-2"></i>爬取活动
              </button>
              <button onClick={() => setView("create")} className="btn text-white px-5 py-2.5 rounded-xl text-sm font-semibold">
                <i className="fa-solid fa-plus mr-2"></i>发布活动
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── 活动详情 ──
  if (view === "detail" && detail) {
    return (
      <div className="max-w-5xl mx-auto px-8 py-8">
        <button onClick={() => { setDetail(null); setView("list"); }} className="text-gray-500 hover:text-gray-400 transition mb-4 inline-flex items-center gap-2">
          <i className="fa-solid fa-arrow-left"></i> 返回活动大厅
        </button>

        {message && <div className={`card p-3 mb-4 text-center text-sm ${message.includes("成功") ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border border-rose-500/20 text-rose-400"}`}>{message}</div>}

        <div className="grid gap-5" style={{ gridTemplateColumns: "1fr 360px" }}>
          {/* 左侧：活动详情 */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{CAT_ICONS[detail.category] || "📌"}</span>
              <div>
                <h2 className="text-xl font-bold text-white">{detail.title}</h2>
                <div className="flex items-center gap-2 mt-1 text-xs">
                  {detail.category && <span className="tag bg-indigo-500/20 text-indigo-400">{detail.category}</span>}
                  {detail.level && <span className="tag bg-purple-500/20 text-indigo-400">{detail.level}</span>}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm mb-4">
              <div className="flex justify-between p-2 rounded bg-white/5"><span className="text-gray-500">组队人数</span><span className="#475569">{detail.min_team_size}-{detail.max_team_size} 人</span></div>
              <div className="flex justify-between p-2 rounded bg-white/5"><span className="text-gray-500">截止日期</span><span className="#475569">{detail.registration_deadline || "待定"}</span></div>
              <div className="flex justify-between p-2 rounded bg-white/5"><span className="text-gray-500">主办单位</span><span className="#475569">{detail.organizer || "—"}</span></div>
              <div className="flex justify-between p-2 rounded bg-white/5"><span className="text-gray-500">发布者</span><span className="#475569">{detail.publisher_type === "scraped" ? "🤖 AI 爬取" : `👤 ${detail.publisher_name || "用户"}`}</span></div>
            </div>

            {detail.description && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-gray-400 mb-2">活动描述</h4>
                <p className="text-sm text-gray-400 whitespace-pre-line">{detail.description}</p>
              </div>
            )}
            {detail.credit_info && (
              <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/10 text-xs text-amber-400">🎓 {detail.credit_info}</div>
            )}
            {detail.tags && detail.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {detail.tags.map((tag: string, i: number) => (
                  <span key={i} className="tag bg-indigo-500/10 text-indigo-400 text-xs">{tag}</span>
                ))}
              </div>
            )}
          </div>

          {/* 右侧：战队列表 + 操作 */}
          <div>
            <div className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-gray-400">已有团队（{detail.teams?.length || 0}）</h4>
              </div>
              {detail.my_team ? (
                <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10 mb-3">
                  <p className="text-xs text-emerald-400">你已加入 <span className="font-semibold">{detail.my_team.name}</span></p>
                  <button onClick={() => nav("/connections/work")} className="btn text-white w-full mt-2 py-2 rounded-lg text-xs font-semibold">
                    <i className="fa-solid fa-briefcase mr-1"></i>进入工作台
                  </button>
                </div>
              ) : (
                <CreateTeamForm detail={detail} onCreated={(msg: string) => { setMessage(msg); showDetail(detail.id); }} />
              )}

              {detail.teams && detail.teams.length > 0 ? (
                <div className="space-y-2">
                  {detail.teams.map((t: any) => (
                    <div key={t.id} className="p-3 rounded-xl bg-white/5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-white">{t.name}</span>
                        <span className={STATUS_CLASS[t.status] || "tag bg-gray-500/20 text-gray-400"}>{STATUS_MAP[t.status] || t.status}</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        队长 {t.leader_name} · {t.member_count}/{detail.max_team_size}人
                      </div>
                      <div className="flex gap-2 mt-2">
                        {t.status === "recruiting" && !detail.my_team && (
                          <button onClick={() => joinTeam(t.id)} className="btn text-white px-4 py-1.5 rounded-lg text-xs font-semibold">
                            <i className="fa-solid fa-user-plus mr-1"></i>加入
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : !detail.my_team && (
                <p className="text-xs text-gray-500 text-center py-4">还没有团队，快来创建第一个！</p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── 创建活动表单 ──
  if (view === "create") {
    return (
      <div className="max-w-2xl mx-auto px-8 py-8">
        <div className="flex items-center gap-3 mb-6">
          <a href="#" onClick={e => { e.preventDefault(); setView("list"); }} className="text-gray-500 hover:text-gray-400 transition"><i className="fa-solid fa-arrow-left"></i></a>
          <h2 className="text-2xl font-bold">创建新活动</h2>
        </div>

        <form onSubmit={createActivity} className="card p-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">活动名称 *</label>
            <input type="text" name="title" className="input" placeholder="请输入活动名称" required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">活动分类</label>
              <select name="category" className="input">
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">活动级别</label>
              <select name="level" className="input">
                {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">主办单位</label>
              <input type="text" name="organizer" className="input" placeholder="如：校团委、学生会" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">报名截止日期</label>
              <input type="date" name="registration_deadline" className="input" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">组队人数上限</label>
              <input type="number" name="max_team_size" className="input" defaultValue={5} min={1} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">组队人数下限</label>
              <input type="number" name="min_team_size" className="input" defaultValue={1} min={1} />
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">学分信息</label>
            <input type="text" name="credit_info" className="input" placeholder='例如"可获2学分"' />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">标签</label>
            <input type="text" name="tags" className="input" placeholder="用逗号分隔，例如：志愿者,文化节,校园" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">活动描述</label>
            <textarea name="description" className="input" rows={5} placeholder="请详细描述活动内容、要求等" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn text-white px-8 py-2.5 rounded-xl text-sm font-semibold"><i className="fa-solid fa-paper-plane mr-2"></i>提交申请</button>
            <button type="button" onClick={() => setView("list")} className="px-6 py-2.5 rounded-xl text-sm text-gray-400 hover:text-gray-200 border border-white/10 transition">取消</button>
          </div>
        </form>
        <p className="text-center text-xs text-gray-600 mt-4">提交后需等待审核通过，才能在大厅展示。</p>
      </div>
    );
  }

  // ── 待审核 ──
  if (view === "pending") {
    return (
      <div className="max-w-4xl mx-auto px-8 py-8">
        <button onClick={() => setView("list")} className="text-gray-500 hover:text-gray-400 transition mb-4 inline-flex items-center gap-2">
          <i className="fa-solid fa-arrow-left"></i> 返回活动大厅
        </button>
        <h2 className="text-xl font-bold mb-4">⏳ 待审核活动</h2>
        {pending.length > 0 ? (
          <div className="space-y-3">
            {pending.map(a => (
              <div key={a.id} className="card p-5 bg-amber-500/3 border border-amber-500/10">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-white">{a.title}</h3>
                    <div className="flex gap-2 mt-1 text-xs text-gray-500">
                      <span>{a.category}</span><span>{a.level}</span>
                      <span>by {a.publisher_name}</span>
                    </div>
                    <p className="text-sm text-gray-400 mt-2">{a.description?.slice(0, 150)}</p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button onClick={() => approve(a.id)} className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 text-xs font-semibold hover:bg-emerald-500/30 transition">
                      ✓ 通过
                    </button>
                    <button onClick={() => reject(a.id)} className="px-4 py-2 rounded-lg bg-rose-500/20 text-rose-400 text-xs font-semibold hover:bg-rose-500/30 transition">
                      ✕ 拒绝
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-12 text-center"><p className="text-gray-500">暂无待审核活动</p></div>
        )}
      </div>
    );
  }

  return null;
}

// ── SJTU 通知卡片（保留原始 Activities 页面的展开/折叠设计） ──
function SJTUCard({ item }: { item: any }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ marginBottom: 8, position: "relative" }}>
      <button onClick={() => setOpen(!open)}
        title={open ? "折叠" : "展开"}
        style={{ position: "absolute", right: 12, top: 12, width: 28, height: 28, borderRadius: "50%",
          border: "1px solid var(--border)", cursor: "pointer", background: "transparent",
          color: "var(--text4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2 }}>
        {open ? "▲" : "▼"}
      </button>
      {open ? (
        <div style={{ paddingRight: 36 }}>
          <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
            <p style={{ fontWeight: 600, color: "var(--text)" }}>{item.title}</p>
            <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginTop: 4 }}>{item.summary?.slice(0, 200)}</p>
            <div style={{ display: "flex", gap: 8, marginTop: 8, fontSize: "0.7rem", color: "var(--text4)" }}>
              <span>📅 {item.publishDate}</span>
              {item.inferredEndDate && <span>⏰ 截止: {item.inferredEndDate}</span>}
              {item.matchedKeywords && <span className="tag bg-white/5 text-gray-400">{item.matchedKeywords?.slice(0,3).join(" ")}</span>}
            </div>
            <div style={{ marginTop: 6 }}>
              <span className="text-indigo-400 text-xs hover:underline">查看原网站 ↗</span>
            </div>
          </a>
        </div>
      ) : (
        <div style={{ paddingRight: 36 }}>
          <p style={{ fontWeight: 500, fontSize: "0.82rem", color: "var(--text4)" }}>{item.title}</p>
        </div>
      )}
    </div>
  );
}

// ── 创建战队表单组件 ──
function CreateTeamForm({ detail, onCreated }: { detail: any; onCreated: (msg: string) => void }) {
  const [show, setShow] = useState(false);
  const [name, setName] = useState("");
  const [slogan, setSlogan] = useState("");
  const [desc, setDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setErr("战队名称不能为空"); return; }
    setLoading(true); setErr("");
    const r = await fetch("/nexus/api/team/create", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ competition_id: detail.id, team_name: name.trim(), slogan: slogan.trim(), description: desc.trim() }),
    });
    const d = await r.json();
    if (d.ok) {
      onCreated(`战队「${d.name}」创建成功！`);
      setShow(false); setName(""); setSlogan(""); setDesc("");
    } else {
      setErr(d.error || "创建失败");
    }
    setLoading(false);
  }

  if (!show) {
    return (
      <button onClick={() => setShow(true)} className="btn text-white w-full py-2.5 rounded-xl text-sm font-semibold mb-3">
        <i className="fa-solid fa-plus mr-2"></i>新建团队
      </button>
    );
  }

  return (
    <div className="card p-5 mb-3 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
      <h4 className="text-sm font-semibold text-white mb-3">创建团队</h4>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">团队名称 *</label>
          <input className="input text-sm py-2" value={name} onChange={e => setName(e.target.value)} placeholder="给你的团队起个名字" autoFocus />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">团队口号（选填）</label>
          <input className="input text-sm py-2" value={slogan} onChange={e => setSlogan(e.target.value)} placeholder="一句响亮的口号" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">团队描述（选填）</label>
          <textarea className="input text-sm py-2" rows={3} value={desc} onChange={e => setDesc(e.target.value)} placeholder="欢迎语、招募要求等" />
        </div>
        {err && <p className="text-xs text-rose-400">{err}</p>}
        <div className="flex gap-2">
          <button type="submit" disabled={loading} className="btn text-white px-4 py-2 rounded-lg text-sm">{loading ? "创建中..." : "创建"}</button>
          <button type="button" onClick={() => { setShow(false); setErr(""); }} className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 border border-white/10">取消</button>
        </div>
      </form>
    </div>
  );
}
