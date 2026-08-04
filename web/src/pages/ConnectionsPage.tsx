import { useEffect, useState } from "react";
import { api } from "../auth";

const STATUS_MAP: Record<string, string> = {
  recruiting: "招募中",
  full: "已满员",
  closed: "已关闭",
};

export default function ConnectionsPage() {
  const [tab, setTab] = useState<"activities" | "competitions" | "sjtu" | "pending" | "friends">("activities");
  const [competitions, setCompetitions] = useState<any[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);
  const [sjtuItems, setSjtuItems] = useState<any[]>([]);
  const [pending, setPending] = useState<any[]>([]);
  const [friends, setFriends] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [filterCat, setFilterCat] = useState("");
  const [filterLevel, setFilterLevel] = useState("");
  const [search, setSearch] = useState("");
  const [msg, setMsg] = useState("");
  const [scraping, setScraping] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [myTeams, setMyTeams] = useState<any[]>([]);
  const [inviting, setInviting] = useState<number | null>(null);

  // 发布表单
  const [cTitle, setCTitle] = useState("");
  const [cCat, setCCat] = useState("");
  const [cLevel, setCLevel] = useState("");
  const [cDesc, setCDesc] = useState("");
  const [cOrg, setCOrg] = useState("");
  const [cMax, setCMax] = useState("5");
  const [cDeadline, setCDeadline] = useState("");
  const [cCredit, setCCredit] = useState("");
  const [cTags, setCTags] = useState("");

  // 组队表单
  const [teamName, setTeamName] = useState("");
  const [teamSlogan, setTeamSlogan] = useState("");
  const [teamDesc, setTeamDesc] = useState("");

  const loadCompetitions = () =>
    api(`/api/competitions?category=${filterCat}&level=${filterLevel}&search=${encodeURIComponent(search)}&kind=${tab === "competitions" ? "competition" : "activity"}`)
      .then((d) => {
        setCompetitions(d.activities || []);
        setCategories(d.categories || []);
        setLevels(d.levels || []);
      })
      .catch(() => {});

  const loadSjtu = () =>
    api("/api/activities")
      .then((d) => setSjtuItems(d.items || []))
      .catch(() => {});

  const loadPending = () =>
    api("/api/pending-activities").then((d) => setPending(d.activities || [])).catch(() => {});

  const loadFriends = () =>
    api("/api/potential-friends").then((d) => setFriends(d.friends || [])).catch(() => {});

  useEffect(() => {
    loadCompetitions();
    loadSjtu();
    loadFriends();
    api("/api/my-teams").then((d) => setMyTeams(d.teams || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterCat, filterLevel, search]);

  useEffect(() => {
    if (tab === "pending") loadPending();
  }, [tab]);

  async function openDetail(id: number) {
    const d = await api(`/api/competitions/${id}`);
    setDetail(d);
    setShowCreate(false);
  }

  async function joinTeam(teamId: number) {
    const res = await api(`/api/teams/${teamId}/join`, { method: "POST" });
    setMsg(res.error || res.message || "已加入");
    openDetail(detail.id);
  }

  async function createCompetition() {
    const res = await api("/api/competition/create", {
      method: "POST",
      body: JSON.stringify({
        title: cTitle, category: cCat, level: cLevel, description: cDesc, organizer: cOrg,
        max_team_size: cMax, min_team_size: "1", registration_deadline: cDeadline || null,
        credit_info: cCredit, tags: cTags,
      }),
    });
    setMsg(res.error || res.message || "提交成功");
    if (!res.error) {
      setShowCreate(false);
      setCTitle("");
      loadPending();
    }
  }

  async function createTeam() {
    const res = await api("/api/team/create", {
      method: "POST",
      body: JSON.stringify({ competition_id: detail.id, team_name: teamName, slogan: teamSlogan, description: teamDesc }),
    });
    setMsg(res.error || `战队「${res.name}」创建成功`);
    if (!res.error) {
      setTeamName("");
      openDetail(detail.id);
    }
  }

  async function inviteFriend(userId: number) {
    if (myTeams.length === 0) {
      setMsg("你需要先加入或创建一支战队才能邀请队友");
      return;
    }
    setInviting(userId);
    try {
      const res = await api(`/api/team/${myTeams[0].team_id}/invite`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      });
      setMsg(res.error || `已向对方发送「${myTeams[0].team_name}」的组队邀请`);
    } finally {
      setInviting(null);
    }
  }

  async function triggerScrape() {
    setScraping(true);
    setMsg("正在爬取 SJTU 活动源...");
    try {
      const res = await api("/api/scrape/trigger", { method: "POST" });
      const s = res.stats || {};
      setMsg(`爬取完成：扫描 ${s.raw || 0} 条，新增 ${s.new || 0} 条`);
      loadSjtu();
      loadCompetitions();
    } finally {
      setScraping(false);
    }
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>活动大厅</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-ghost" onClick={triggerScrape} disabled={scraping}>
            <i className="fa-solid fa-rotate" /> {scraping ? "爬取中..." : "爬取 SJTU 活动"}
          </button>
          <button className="btn" onClick={() => setShowCreate(!showCreate)}>+ 发布活动</button>
        </div>
      </div>
      {msg && (
        <div style={{ padding: "10px 16px", borderRadius: 10, background: "var(--accent-bg2)", color: "var(--accent)", fontSize: "0.8rem", marginBottom: 16 }}>
          {msg}
        </div>
      )}

      {/* 发布活动表单 */}
      {showCreate && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 12 }}>发布活动（提交后需审核）</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <input className="input" placeholder="活动名称 *" value={cTitle} onChange={(e) => setCTitle(e.target.value)} />
            <input className="input" placeholder="主办方" value={cOrg} onChange={(e) => setCOrg(e.target.value)} />
            <input className="input" placeholder="分类（如 创新创业）" value={cCat} onChange={(e) => setCCat(e.target.value)} />
            <input className="input" placeholder="级别（校级/市级/国家级）" value={cLevel} onChange={(e) => setCLevel(e.target.value)} />
            <input className="input" type="date" value={cDeadline} onChange={(e) => setCDeadline(e.target.value)} />
            <input className="input" placeholder="最大组队人数" value={cMax} onChange={(e) => setCMax(e.target.value)} />
            <input className="input" placeholder="学分信息" value={cCredit} onChange={(e) => setCCredit(e.target.value)} />
            <input className="input" placeholder="标签（逗号分隔）" value={cTags} onChange={(e) => setCTags(e.target.value)} />
          </div>
          <textarea className="input" style={{ marginTop: 10 }} rows={2} placeholder="活动描述" value={cDesc} onChange={(e) => setCDesc(e.target.value)} />
          <button className="btn" style={{ marginTop: 10 }} onClick={createCompetition}>提交审核</button>
        </div>
      )}

      {/* Tab */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {([
          ["activities", "组队活动"],
          ["competitions", "🏆 竞赛信息"],
          ["sjtu", "SJTU 通知"],
          ["pending", "待审核"],
          ["friends", "潜在队友"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className="badge"
            style={{
              cursor: "pointer",
              border: "1px solid",
              borderColor: tab === k ? "var(--accent-border2)" : "var(--border)",
              background: tab === k ? "var(--accent-bg3)" : "transparent",
              color: tab === k ? "var(--accent)" : "var(--text4)",
              padding: "8px 16px",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "activities" && (
        <>
          <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
            <input className="input" style={{ flex: 1, minWidth: 180 }} placeholder="搜索活动..." value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="input" style={{ width: 130 }} value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
              <option value="">全部分类</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select className="input" style={{ width: 130 }} value={filterLevel} onChange={(e) => setFilterLevel(e.target.value)}>
              <option value="">全部级别</option>
              {levels.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
            {competitions.length === 0 && (
              <div className="card" style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
                {tab === "competitions"
                  ? "暂无竞赛信息——点击右上角「爬取 SJTU 活动」自动抓取 6 个站点并 AI 筛选竞赛"
                  : "暂无活动——发布第一个，或触发爬虫获取 SJTU 通知"}
              </div>
            )}
            {competitions.map((c) => (
              <div key={c.id} className="card" style={{ display: "flex", flexDirection: "column", cursor: "pointer" }} onClick={() => openDetail(c.id)}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
                  <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{c.category || "未分类"}</span>
                  <span className="badge" style={{ background: "var(--surface2)", color: "var(--text4)" }}>{c.level || "校级"}</span>
                  {tab === "competitions" && (
                    <>
                      <span className="badge" style={{ background: "rgba(52,211,153,0.15)", color: "#34D399" }}>
                        AI 识别 {(c.ai_confidence * 100).toFixed(0)}%
                      </span>
                      {c.source_site && <span className="badge" style={{ background: "var(--surface2)", color: "var(--text4)" }}>{c.source_site.slice(0, 12)}</span>}
                    </>
                  )}
                </div>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 6 }}>{c.title}</h3>
                <p style={{ fontSize: "0.78rem", color: "var(--text3)", lineHeight: 1.6, flex: 1 }}>{c.description}</p>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10, fontSize: "0.72rem", color: "var(--text4)" }}>
                  <span>{tab === "competitions" ? "查看详情并组队" : `${c.team_count} 支战队`}</span>
                  {c.registration_deadline && <span>截止 {c.registration_deadline}</span>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "sjtu" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {sjtuItems.length === 0 && (
            <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
              暂无 SJTU 通知——点击右上角「爬取 SJTU 活动」
            </div>
          )}
          {sjtuItems.map((item) => (
            <a key={item.id} href={item.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
              <div className="card" style={{ padding: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <p style={{ fontSize: "0.88rem", fontWeight: 600 }}>{item.title}</p>
                  <span style={{ fontSize: "0.72rem", color: "var(--text4)", whiteSpace: "nowrap", marginLeft: 10 }}>{item.publishDate}</span>
                </div>
                <p style={{ fontSize: "0.78rem", color: "var(--text3)", lineHeight: 1.6 }}>{item.summary}</p>
                {item.inferredEndDate && (
                  <p style={{ fontSize: "0.7rem", color: "var(--accent)", marginTop: 6 }}>截止 {item.inferredEndDate} {item.matchedKeywords?.length ? `· ${item.matchedKeywords.slice(0, 3).join("/")}` : ""}</p>
                )}
              </div>
            </a>
          ))}
        </div>
      )}

      {tab === "pending" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {pending.length === 0 && (
            <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>没有待审核的活动</div>
          )}
          {pending.map((p) => (
            <div key={p.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <p style={{ fontSize: "0.9rem", fontWeight: 600 }}>{p.title}</p>
                  <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginTop: 2 }}>{p.publisher_name} · {p.category} · {p.level}</p>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn" style={{ padding: "6px 16px", fontSize: "0.75rem" }} onClick={async () => {
                    await api(`/api/competition/${p.id}/approve`, { method: "POST" });
                    loadPending();
                  }}>通过</button>
                  <button className="btn-ghost" style={{ padding: "6px 16px", fontSize: "0.75rem", color: "#F87171" }} onClick={async () => {
                    await api(`/api/competition/${p.id}/reject`, { method: "POST" });
                    loadPending();
                  }}>拒绝</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "friends" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
          {friends.length === 0 && (
            <div className="card" style={{ gridColumn: "1/-1", textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
              暂无推荐——完善技能标签后，系统会推荐技能互补的队友（设置 → 技能标签）
            </div>
          )}
          {friends.map((f) => (
            <div key={f.user_id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <p style={{ fontSize: "0.9rem", fontWeight: 700 }}>{f.real_name}</p>
                <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>匹配 {f.match_score}</span>
              </div>
              {(f.complementary_skills || []).length > 0 && (
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 6 }}>
                  可互补：{(f.complementary_skills || []).join("、")}
                </p>
              )}
              {(f.shared_skills || []).length > 0 && (
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 8 }}>共同技能：{(f.shared_skills || []).join("、")}</p>
              )}
              <button
                className="btn"
                style={{ padding: "6px 14px", fontSize: "0.72rem", width: "100%" }}
                disabled={inviting === f.user_id}
                onClick={() => inviteFriend(f.user_id)}
              >
                {inviting === f.user_id ? "发送中..." : myTeams.length === 0 ? "先创建战队后邀请" : "🤝 邀请组队"}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 活动详情 */}
      {detail && (
        <div style={{ position: "fixed", inset: 0, zIndex: 90, background: "var(--overlay)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }} onClick={() => setDetail(null)}>
          <div className="card" style={{ maxWidth: 640, maxHeight: "85vh", overflow: "auto", width: "100%" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>{detail.title}</h2>
              <button onClick={() => setDetail(null)} style={{ border: "none", background: "none", fontSize: "1.3rem", cursor: "pointer", color: "var(--text4)" }}>×</button>
            </div>
            <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
              <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{detail.category || "未分类"}</span>
              <span className="badge" style={{ background: "var(--surface2)", color: "var(--text4)" }}>{detail.level || "校级"}</span>
              {detail.organizer && <span className="badge" style={{ background: "var(--surface2)", color: "var(--text4)" }}>{detail.organizer}</span>}
            </div>
            <p style={{ fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text2)", whiteSpace: "pre-wrap", marginBottom: 10 }}>{detail.description}</p>
            {detail.credit_info && <p style={{ fontSize: "0.78rem", color: "var(--accent)", marginBottom: 8 }}>{detail.credit_info}</p>}
            {detail.registration_deadline && <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginBottom: 8 }}>报名截止：{detail.registration_deadline}</p>}

            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, margin: "14px 0 8px" }}>战队列表（{detail.teams?.length || 0}）</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {detail.teams?.map((t: any) => (
                <div key={t.id} style={{ padding: 12, borderRadius: 10, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ fontSize: "0.85rem", fontWeight: 600 }}>{t.name} <span className="tag" style={{ background: "var(--surface2)", color: "var(--text4)" }}>{STATUS_MAP[t.status] || t.status}</span></p>
                    <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginTop: 2 }}>队长：{t.leader_name} · {t.member_count} 人</p>
                  </div>
                  {t.status === "recruiting" && detail.my_team?.id !== t.id && (
                    <button className="btn" style={{ padding: "6px 14px", fontSize: "0.75rem" }} onClick={() => joinTeam(t.id)}>加入</button>
                  )}
                  {detail.my_team?.id === t.id && (
                    <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>我的战队（{detail.my_team.role === "leader" ? "队长" : "成员"}）</span>
                  )}
                </div>
              ))}
            </div>

            {!detail.my_team && detail.status === "active" && (
              <div style={{ marginTop: 14, padding: 14, borderRadius: 10, border: "1px dashed var(--accent-border2)", background: "var(--accent-bg2)" }}>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 8 }}>创建你的战队</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <input className="input" placeholder="战队名称 *" value={teamName} onChange={(e) => setTeamName(e.target.value)} />
                  <input className="input" placeholder="口号（可选）" value={teamSlogan} onChange={(e) => setTeamSlogan(e.target.value)} />
                  <input className="input" placeholder="战队简介（可选）" value={teamDesc} onChange={(e) => setTeamDesc(e.target.value)} />
                  <button className="btn" onClick={createTeam}>创建战队</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
