import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChevronRight, ExternalLink } from "lucide-react";

// ── 折叠活动（与 Activities 页共享 localStorage key） ──
const COLLAPSED_KEY = "collapsed_activities";
function getCollapsed(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(COLLAPSED_KEY) || "[]")); }
  catch { return new Set(); }
}
function saveCollapsed(ids: Set<string>) {
  localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...ids]));
}

// ── path_type → 未来倾向 & 诗意描述 ──
// ↑↑ = 核心强化方向  ↑ = 次要成长  ↓ = 可能弱化  → = 保持
const PATH_META: Record<string, { icon: string; tendencies: [string, string][]; poetic: string }> = {
  technical_creator: {
    icon: "🔬",
    tendencies: [["技术深度", "↑↑"], ["独立研究", "↑↑"], ["社交投入", "↓"]],
    poetic: "那个愿意花十年解决一个问题的人。",
  },
  knowledge_weaver: {
    icon: "🧭",
    tendencies: [["阅读广度", "↑↑"], ["知识整合", "↑↑"], ["表达输出", "↑"]],
    poetic: "那个把混乱知识变成清晰世界地图的人。",
  },
  deep_researcher: {
    icon: "🔮",
    tendencies: [["深度分析", "↑↑"], ["理论构建", "↑"], ["实践应用", "→"]],
    poetic: "那个在无人区点亮第一盏灯的人。",
  },
  social_connector: {
    icon: "🌐",
    tendencies: [["社交投入", "↑↑"], ["组织协调", "↑↑"], ["技术深度", "→"]],
    poetic: "那个让不同世界的人相遇并共同创造的人。",
  },
  creative_explorer: {
    icon: "🎨",
    tendencies: [["创造倾向", "↑↑"], ["跨界探索", "↑↑"], ["规范遵循", "↓"]],
    poetic: "那个打破边界、重新定义规则的人。",
  },
};
const FALLBACK_PATH_META = [
  { icon: "🔬", tendencies: [["技术深度", "↑↑"], ["独立研究", "↑"], ["长期专注", "↑"]], poetic: "那个愿意花多年时间，只为理解一个问题的人。" },
  { icon: "🧭", tendencies: [["阅读广度", "↑↑"], ["知识整合", "↑"], ["表达输出", "↑"]], poetic: "那个把分散知识连接成清晰地图的人。" },
  { icon: "🌐", tendencies: [["技术应用", "↑"], ["人文理解", "↑"], ["跨界协作", "↑↑"]], poetic: "那个让不同领域发生碰撞的人。" },
];

// ── 标签映射 ──
function signalLabel(key: string): string {
  const m: Record<string, string> = { "技术能力": "技术兴趣", "创造力": "创造倾向", "社交力": "社交投入", "自我认知": "自我认知", "执行力": "执行倾向", "领导力": "领导倾向", "学习能力": "学习兴趣", "表达能力": "表达倾向", "分析能力": "分析倾向", "组织能力": "组织倾向", "适应力": "适应倾向" };
  if (m[key]) return m[key];
  if (key.includes("能力")) return key.replace("能力", "倾向");
  if (key.includes("力") && !key.includes("倾")) return key.replace("力", "倾向");
  return key;
}

function stars(v: number): string {
  if (v >= 80) return "★★★★★"; if (v >= 60) return "★★★★"; if (v >= 40) return "★★★"; if (v >= 20) return "★★"; return "★";
}

function daysLeft(dateStr: string): string {
  if (!dateStr) return "";
  const days = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
  if (days < 0) return "已截止";
  if (days === 0) return "今天截止";
  if (days <= 7) return `${days} 天后截止`;
  return `${new Date(dateStr).toLocaleDateString("zh-CN", { month: "long", day: "numeric" })} 截止`;
}

// ── 从低分维度推导互补共同创造者 ──
function derivePartnerNeeds(abilities: [string, number][]) {
  const lowKeys = abilities.filter(([, v]) => v < 45).map(([k]) => k);
  const lowText = lowKeys.join("");
  const roles: { icon: string; name: string; desc: string }[] = [];

  if (lowText.includes("表达") || lowText.includes("社交")) {
    roles.push({ icon: "📡", name: "传播者", desc: "负责表达、演讲、社群——让想法被更多人看到" });
  }
  if (lowText.includes("技术") || lowText.includes("执行") || lowText.includes("实践")) {
    roles.push({ icon: "⚡", name: "执行者", desc: "负责项目管理、落地——把蓝图变成现实" });
  }
  if (lowText.includes("认知") || lowText.includes("反思") || lowText.includes("分析")) {
    roles.push({ icon: "🔍", name: "批判者", desc: "负责质疑、发现漏洞——让你看到盲区" });
  }
  if (lowText.includes("创造") || lowText.includes("艺术")) {
    roles.push({ icon: "💡", name: "灵感者", desc: "负责创意发散、打破常规——带来新鲜视角" });
  }
  // 共鸣者：不一定是功能互补，而是理解你的世界
  roles.push({ icon: "🫂", name: "共鸣者", desc: "理解你的世界、与你共享热情——让创造不再孤独" });
  // 前两个是功能互补角色 + 共鸣者始终在最后
  const functional = roles.slice(0, roles.length - 1); // exclude 共鸣者
  if (functional.length < 2) {
    if (!functional.find(r => r.name === "传播者")) functional.push({ icon: "📡", name: "传播者", desc: "负责表达、演讲、社群——让想法被更多人看到" });
    if (!functional.find(r => r.name === "执行者")) functional.push({ icon: "⚡", name: "执行者", desc: "负责项目管理、落地——把蓝图变成现实" });
  }
  const result = functional.slice(0, 2);
  result.push(roles[roles.length - 1]); // 共鸣者
  return result;
}

// ── 构建全部信号（兴趣 + 行为，不含推断能力） ──
function buildSignals(pf: any, dInterests: Record<string, number> | undefined): [string, number][] {
  const seen = new Set<string>();
  const out: [string, number][] = [];

  // 兴趣信号（来自真实追踪数据）
  const interestSrc = (pf?.interest && Object.keys(pf.interest).length > 0) ? pf.interest : (dInterests || {});
  for (const [k, v] of Object.entries(interestSrc as Record<string, number>)) {
    if (!seen.has(k)) { seen.add(k); out.push([k, v as number]); }
  }
  // 行为信号
  const behavior = pf?.behavior || {};
  for (const [k, v] of Object.entries(behavior as Record<string, number>)) {
    const key = k + "行为";
    if (!seen.has(key)) { seen.add(key); out.push([key, v as number]); }
  }
  return out.sort((a, b) => b[1] - a[1]);
}

export default function Dashboard() {
  const [d, setD] = useState<any>({});
  const [futures, setFutures] = useState<any[]>([]);
  const [personaFull, setPersonaFull] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [friends, setFriends] = useState<any[]>([]);
  const [myTeams, setMyTeams] = useState<any[]>([]);
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(getCollapsed);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const loc = useLocation();

  useEffect(() => {
    Promise.all([
      fetch("/api/mirror/dashboard").then(r => r.json()),
      fetch("/api/mirror/future-chats").then(r => r.json()).catch(() => []),
      fetch("/api/mirror/persona").then(r => r.json()).catch(() => null),
      fetch("/api/auth/me", { credentials: "include" }).then(r => r.json()).catch(() => null),
      fetch("/api/potential-friends").then(r => r.json()).then(d => setFriends(Array.isArray(d?.friends) ? d.friends : [])).catch(() => []),
      fetch("/api/my-teams").then(r => r.json()).then(d => setMyTeams(Array.isArray(d?.teams) ? d.teams : [])).catch(() => []),
    ]).then(([dash, futuresData, personaData, userData]) => {
      setD(dash);
      setFutures(Array.isArray(futuresData) ? futuresData : []);
      setPersonaFull(personaData);
      setUser(userData?.id ? userData : null);
    });
  }, [loc.key]);

  function toggleCollapse(id: string | number) {
    setCollapsedIds(prev => {
      const next = new Set(prev);
      const key = String(id);
      if (next.has(key)) next.delete(key); else next.add(key);
      saveCollapsed(next);
      return next;
    });
  }

  const s = d?.stats || {};
  const p = d?.persona;
  const pf = personaFull?.current;
  const name = user?.real_name || user?.username || "";
  const hasPersona = !!(pf || p);
  const personaData = pf || p;
  const personaType = personaData?.persona_type || "";
  const confidence = personaData?.confidence || 0;
  const confidencePct = Math.round(confidence * 100);

  // ── 信号（兴趣 + 行为观测） ──
  const signals = buildSignals(pf, d?.interests);
  const topSignalKeys = signals.slice(0, 2).map(([k]) => k);

  // ── 数据源计数 ──
  const recordCount = s.records || 0;
  const eventCount = s.events || 0;
  const exploreCount = Object.keys(d?.interests || {}).length;
  const goalCount = s.goals || 0;
  const totalData = Math.max(recordCount + eventCount + exploreCount + goalCount, 1);

  // ── 稳定度来源构成（按数据比例分配 confidence） ──
  const srcBreakdown = [
    { label: "日常记录", count: recordCount, pct: Math.round((recordCount / totalData) * confidencePct) },
    { label: "人生事件", count: eventCount, pct: Math.round((eventCount / totalData) * confidencePct) },
    { label: "目标选择", count: goalCount, pct: Math.round((goalCount / totalData) * confidencePct) },
    { label: "世界探索", count: exploreCount, pct: Math.round((exploreCount / totalData) * confidencePct) },
  ];

  // ── 倾向维度（ability_profile，用于活动匹配 & 伙伴推导） ──
  const abilityProfile: Record<string, number> = pf?.ability || p?.ability || {};
  const tendencies: [string, number][] = Object.entries(abilityProfile).sort((a, b) => b[1] - a[1]);
  const partnerNeeds = derivePartnerNeeds(tendencies);

  // ── 我与世界：组队活动 + SJTU 活动 ──
  const worldCompsAll = d?.competitions || [];
  const worldActsAll = d?.activities || [];
  const worldComps = worldCompsAll.filter((a: any) => !collapsedIds.has(String(a.id)));
  const worldActs = worldActsAll.filter((a: any) => !collapsedIds.has(String(a.id)));
  const collapsedCount = [...worldCompsAll, ...worldActsAll].filter((a: any) => collapsedIds.has(String(a.id))).length;

  // ── 目标→未来自我匹配 ──
  const goalFutureMatches = (d?.active_goals || []).map((g: any) => {
    const title = (g.title || "").toLowerCase();
    let match = futures[0];
    let score = 0;
    for (const f of futures) {
      const label = (f.label || "").toLowerCase();
      let s = 0;
      for (const ch of title) { if (label.includes(ch)) s++; }
      if (s > score) { score = s; match = f; }
    }
    return { goal: g, match: score > 1 ? match : null };
  });

  return (
    <main style={{ padding: "28px 40px 48px", minHeight: "100vh", maxWidth: 860, margin: "0 auto" }}>

      {/* ═══ Header ═══ */}
      <div style={{ textAlign: "center", marginBottom: 36 }}>
        <p style={{ fontSize: "0.7rem", color: "var(--text4)", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 4 }}>
          认识自己 · 走向世界 · 与他人共同创造
        </p>
        {name && <h1 style={{ fontSize: "1.35rem", fontWeight: 700, marginBottom: 4, color: "var(--text)" }}>{name}，这是你的镜像</h1>}
        <p style={{ fontSize: "0.8rem", color: "var(--text4)" }}>
          {hasPersona ? "所有内容来自你的真实经历——AI 只是把它重新组织，让你看清自己" : "记录你的第一段经历，AI 将开始为你构建镜像"}
        </p>
      </div>

      {/* ═══════ 1. 🪞 当前的我 ═══════ */}
      <section style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <span style={{ fontSize: "1rem" }}>🪞</span>
          <h2 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text)" }}>当前的我</h2>
        </div>

        {hasPersona ? (
          <div className="card" style={{ padding: "24px 28px", borderRadius: 16, background: "linear-gradient(135deg, var(--accent-bg), var(--accent-bg2))", border: "1px solid var(--accent-border)" }}>

            {/* ── 镜像观察 ── */}
            <div style={{ marginBottom: 16 }}>
              <span style={{ display: "inline-block", padding: "4px 14px", borderRadius: 6, fontSize: "0.8rem", fontWeight: 700, color: "var(--accent)", background: "var(--accent-bg3)", border: "1px solid var(--accent-border2)", marginBottom: 10 }}>🧬 {personaType}{confidence < 0.5 ? "倾向" : ""}</span>

              <p style={{ fontSize: "0.84rem", color: "var(--text)", lineHeight: 1.7, marginBottom: 4 }}>
                当前 AI 观察到：
                {topSignalKeys.length >= 2
                  ? <>你正在频繁靠近<span style={{ color: "var(--accent)", fontWeight: 600 }}>「{topSignalKeys[0]}」</span>和<span style={{ color: "var(--accent)", fontWeight: 600 }}>「{topSignalKeys[1]}」</span>的方向。</>
                  : <>你的行为数据正在积累中，一个更清晰的轮廓正在浮现。</>
                }
              </p>
              {confidence < 0.5 && (
                <p style={{ fontSize: "0.7rem", color: "var(--text4)", fontStyle: "italic" }}>但目前样本较少，这只是你的一个可能侧面。</p>
              )}
            </div>

            {/* ── 数字人格形成度 ── */}
            <div style={{ padding: "16px 20px", borderRadius: 12, background: "var(--accent-bg2)", border: "1px solid var(--accent-border)", marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text)" }}>🧬 数字人格形成度</span>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--accent)" }}>{confidencePct}%</span>
              </div>
              <div style={{ height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden", marginBottom: 6 }}>
                <div style={{ height: "100%", width: (confidencePct) + "%", background: "var(--bar-mid)", borderRadius: 3, transition: "width 0.8s" }} />
              </div>
              <p style={{ fontSize: "0.66rem", color: "var(--text4)", marginBottom: 12, fontStyle: "italic" }}>
                {confidence < 0.3 ? "照片像素还不足，但轮廓已经出现——记录更多，镜像更清晰。" : confidence < 0.6 ? "镜像正在成型——已有足够数据识别模式，继续积累会更加稳定。" : "镜像已较为清晰——AI 对你的理解正在趋于稳定。"}
              </p>

              <p style={{ fontSize: "0.62rem", color: "var(--text4)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>来源构成</p>
              {srcBreakdown.map(src => {
                const w = Math.min(100, src.pct) + "%";
                const barBg = src.count > 0 ? "var(--accent-bg3)" : "rgba(0,0,0,0.06)";
                const labelColor = src.count > 0 ? "var(--accent)" : "var(--text4)";
                const labelWeight = src.count > 0 ? 600 : 400;
                return (
                  <div key={src.label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
                    <span style={{ fontSize: "0.66rem", color: "var(--text4)", width: 56, flexShrink: 0, textAlign: "right" }}>{src.label}</span>
                    <div style={{ flex: 1, height: 4, background: "rgba(0,0,0,0.06)", borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: w, background: barBg, borderRadius: 2 }} />
                    </div>
                    <span style={{ fontSize: "0.62rem", color: labelColor, width: 28, textAlign: "right", fontWeight: labelWeight }}>{src.pct}%</span>
                  </div>
                );
              })}
              <p style={{ fontSize: "0.6rem", color: "var(--text4)", marginTop: 8 }}>
                基于 {recordCount} 条记录 · {eventCount} 个事件 · {exploreCount} 个探索领域 · {goalCount} 个目标
                {totalData <= 1 && "——记录更多，镜像更清晰"}
              </p>
            </div>

            {/* ── 当前信号 ── */}
            <div>
              <p style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--text4)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>当前信号</p>
              {signals.length > 0 ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 24px" }}>
                  {signals.slice(0, 8).map(([k, v]) => {
                    const w = Math.min(100, v || 0) + "%";
                    const bg = v >= 70 ? "var(--bar-high)" : v >= 40 ? "var(--bar-mid)" : "var(--bar-low)";
                    return (
                      <div key={k} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: "0.68rem", color: "var(--text4)", width: 72, flexShrink: 0, textAlign: "right", whiteSpace: "nowrap" }}>{signalLabel(k)}</span>
                        <div style={{ flex: 1, height: 5, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: w, background: bg, borderRadius: 3, transition: "width 0.6s" }} />
                        </div>
                        <span style={{ fontSize: "0.65rem", color: "var(--accent)", width: 26, fontWeight: 600, textAlign: "right" }}>{v}%</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p style={{ fontSize: "0.72rem", color: "var(--text4)" }}>信号积累中——记录更多经历后出现</p>
              )}
              <p style={{ fontSize: "0.6rem", color: "var(--text4)", marginTop: 8 }}>
                这些是 AI 从你的记录、事件、浏览行为中提取的信号强度。兴趣 ≠ 能力，行为 ≠ 性格。
              </p>
            </div>

            <p style={{ fontSize: "0.62rem", color: "var(--text4)", textAlign: "center", marginTop: 14 }}>
              这不是标签，而是当前版本的你。随着你记录、选择、参与，镜像将持续变化。
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 8 }}>
              <a href="/persona" style={{ fontSize: "0.7rem", color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>完整画像 <ChevronRight size={11} /></a>
              <span style={{ color: "var(--text4)" }}>·</span>
              <a href="/simulation" style={{ fontSize: "0.7rem", color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>探索可能的我 <ChevronRight size={11} /></a>
            </div>
          </div>
        ) : (
          <div style={{ padding: "32px 24px", borderRadius: 16, textAlign: "center", background: "linear-gradient(135deg, var(--accent-bg2), rgba(0,0,0,0.02))", border: "1px solid var(--accent-border)" }}>
            <p style={{ fontSize: "2.4rem", marginBottom: 10 }}>🪞</p>
            <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text2)", marginBottom: 4 }}>镜像尚未形成</p>
            <p style={{ fontSize: "0.76rem", color: "var(--text4)", marginBottom: 14 }}>记录人生经历后，AI 将从你的行为模式中构建属于你的人格镜像</p>
            <a href="/journal" style={{ display: "inline-block", padding: "8px 20px", borderRadius: 8, fontSize: "0.82rem", background: "rgba(99,102,241,0.2)", color: "var(--accent)", textDecoration: "none", border: "1px solid rgba(99,102,241,0.25)" }}>开始记录 →</a>
          </div>
        )}
      </section>

      {hasPersona && <FlowArrow />}

      {/* ═══════ 2. 🌱 可能的我 ═══════ */}
      <section style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: "1rem" }}>🌱</span>
          <h2 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text)" }}>可能的我</h2>
        </div>
        <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginBottom: 14, lineHeight: 1.5 }}>
          不是预测未来。而是：如果你继续沿着某些方向积累，你可能逐渐成长出的版本。
        </p>

        {futures.length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
            {futures.slice(0, 3).map((f: any, idx: number) => {
              const meta = PATH_META[f.path_type] || FALLBACK_PATH_META[idx % FALLBACK_PATH_META.length];
              const pct = Math.round((f.confidence || 0.7) * 100);
              return (
                <a key={f.id} href="/future-chat" style={{ display: "block", padding: "16px 18px", borderRadius: 12, textDecoration: "none", color: "inherit", background: "rgba(0,0,0,0.02)", border: "1px solid rgba(0,0,0,0.06)", transition: "all 0.2s" }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(139,92,246,0.35)"; e.currentTarget.style.background = "rgba(139,92,246,0.05)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(0,0,0,0.06)"; e.currentTarget.style.background = "rgba(0,0,0,0.02)"; }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                    <p style={{ fontSize: "1.3rem", margin: 0 }}>{meta.icon}</p>
                    <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--accent2)" }}>{pct}%</span>
                  </div>
                  <p style={{ fontSize: "0.88rem", fontWeight: 700, marginBottom: 8, color: "var(--text)" }}>{f.label}</p>

                  {/* 未来倾向 — 用 ↑↑ / ↑ / ↓ / → 表示强弱 */}
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
                    {meta.tendencies.map(([dim, arrow]) => (
                      <span key={dim} style={{
                        padding: "2px 8px", borderRadius: 4, fontSize: "0.62rem",
                        background: arrow.includes("↑") ? "rgba(16,185,129,0.08)" : arrow === "↓" ? "rgba(239,68,68,0.05)" : "rgba(0,0,0,0.03)",
                        color: arrow.includes("↑") ? "#34D399" : arrow === "↓" ? "#F87171" : "#64748B",
                        fontWeight: arrow === "↑↑" ? 700 : 400,
                      }}>{dim} {arrow}</span>
                    ))}
                  </div>

                  <p style={{ fontSize: "0.68rem", color: "var(--text4)", lineHeight: 1.5, fontStyle: "italic" }}>
                    你可能成为{meta.poetic}
                  </p>
                </a>
              );
            })}
          </div>
        ) : hasPersona ? (
          <div style={{ padding: "20px", borderRadius: 12, textAlign: "center", background: "rgba(0,0,0,0.02)", border: "1px solid rgba(0,0,0,0.04)" }}>
            <p style={{ fontSize: "0.78rem", color: "var(--text4)" }}>积累更多经历后，AI 将为你推演可能的未来版本。<a href="/simulation" style={{ color: "var(--accent)", marginLeft: 6 }}>开始人生模拟 →</a></p>
          </div>
        ) : null}
      </section>

      {hasPersona && <FlowArrow />}

      {/* ═══════ 3. 🗺 我与世界 ═══════ */}
      <section style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: "1rem" }}>🗺</span>
          <h2 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text)" }}>我与世界</h2>
          {hasPersona && <span style={{ fontSize: "0.68rem", color: "var(--text4)" }}>— 世界回应你的镜像</span>}
        </div>
        <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginBottom: 14, lineHeight: 1.5 }}>
          这些活动与你的画像产生共鸣——不是"你该参加的"，而是可能自然吸引你的。
        </p>

        {worldComps.length + worldActs.length > 0 || collapsedCount > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {collapsedCount > 0 && (
              <button
                onClick={() => { const all = new Set<string>(); saveCollapsed(all); setCollapsedIds(all); }}
                style={{ alignSelf: "flex-start", padding: "4px 12px", borderRadius: 8, fontSize: "0.68rem", cursor: "pointer", background: "var(--surface2)", color: "var(--text4)", border: "1px solid var(--border)" }}
              >
                ↺ 展开已折叠的 {collapsedCount} 条活动
              </button>
            )}

            {/* ── 组队活动（可加入战队共同创造） ── */}
            {worldComps.length > 0 && (
              <>
                <p style={{ fontSize: "0.68rem", fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 4 }}>
                  🏳️ 组队活动
                </p>
                {worldComps.map((c: any, i: number) => {
                  // 详细适配度：去模板化维度子集（与 SJTU 活动一致）
                  const offset = i * 2;
                  const rotatedTendencies = [...tendencies.slice(offset, offset + 3), ...tendencies.slice(0, Math.max(0, 3 - Math.max(0, tendencies.length - offset)))];
                  const dims = rotatedTendencies.length >= 2 ? rotatedTendencies.slice(0, 3) : tendencies.slice(0, 3);
                  const hasDims = dims.length >= 2;
                  return (
                    <div key={c.id} style={{ position: "relative" }}
                      onMouseEnter={() => setHoverId(String(c.id))}
                      onMouseLeave={() => setHoverId(null)}
                    >
                      <a href="/connections"
                        style={{ display: "block", padding: "14px 18px", borderRadius: 10, textDecoration: "none", color: "inherit", background: "rgba(139,92,246,0.03)", border: "1px solid rgba(139,92,246,0.12)", transition: "all 0.15s" }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(139,92,246,0.3)"; }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(139,92,246,0.12)"; }}
                      >
                        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                          <span style={{ fontSize: "1rem", flexShrink: 0 }}>{c.match_score >= 60 ? "🔥" : "🎯"}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <p style={{ fontSize: "0.84rem", fontWeight: 600, marginBottom: 4, color: "var(--text)" }}>
                              {c.title}
                              <span style={{ marginLeft: 8, fontSize: "0.62rem", color: "var(--text4)", fontWeight: 400 }}>{c.category} · {c.level}</span>
                            </p>
                            <div style={{ display: "flex", gap: 10, fontSize: "0.68rem", color: "var(--text4)", flexWrap: "wrap", marginBottom: hasDims || c.match_reason ? 8 : 0 }}>
                              <span style={{ color: "var(--accent)", fontWeight: 600 }}>匹配度 {c.match_score}%</span>
                              {c.registration_deadline && <span>⏰ {daysLeft(c.registration_deadline)}</span>}
                              <span>{c.team_count} 支战队</span>
                              {c.max_team_size && <span>最多 {c.max_team_size} 人</span>}
                              {c.credit_info && <span>💎 {c.credit_info}</span>}
                            </div>
                            {(hasDims || c.match_reason) && (
                              <div style={{ padding: "8px 12px", borderRadius: 6, background: "rgba(139,92,246,0.05)", border: "1px solid rgba(139,92,246,0.1)" }}>
                                {hasDims && (
                                  <>
                                    <p style={{ fontSize: "0.62rem", color: "var(--text4)", marginBottom: 4 }}>可能帮助你成长的维度</p>
                                    {dims.map(([k, v]) => (
                                      <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                                        <span style={{ fontSize: "0.64rem", color: "var(--text4)", width: 56, textAlign: "right", flexShrink: 0 }}>{signalLabel(k)}</span>
                                        <span style={{ fontSize: "0.68rem", color: "#34D399", letterSpacing: "0.05em" }}>{stars(v)}</span>
                                      </div>
                                    ))}
                                    <p style={{ fontSize: "0.64rem", color: "var(--text4)", lineHeight: 1.4, marginTop: 4 }}>
                                      💡 活动不匹配现在的你，而是匹配你可能成长的方向——你的{signalLabel(dims[0][0])}和{signalLabel(dims[1][0])}在这里有发挥空间。
                                    </p>
                                  </>
                                )}
                                {c.match_reason && (
                                  <p style={{ fontSize: "0.64rem", color: "var(--text3)", lineHeight: 1.5 }}>💡 {c.match_reason}</p>
                                )}
                              </div>
                            )}
                          </div>
                          <ExternalLink size={12} color="#475569" style={{ flexShrink: 0, marginTop: 3 }} />
                        </div>
                      </a>
                      <button
                        onClick={() => toggleCollapse(c.id)}
                        title="折叠"
                        style={{ position: "absolute", top: 8, right: 8, border: "none", background: "var(--surface2)", color: "var(--text4)", cursor: "pointer", width: 22, height: 22, borderRadius: 6, fontSize: "0.7rem", opacity: hoverId === String(c.id) ? 1 : 0, transition: "opacity 0.15s" }}
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </>
            )}

            {/* ── SJTU 校园通知 ── */}
            {worldActs.length > 0 && (
              <>
                <p style={{ fontSize: "0.68rem", fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 4 }}>
                  📅 SJTU 校园通知
                </p>
                {worldActs.map((a: any, i: number) => {
                  const offset = i * 2;
                  const rotatedTendencies = [...tendencies.slice(offset, offset + 3), ...tendencies.slice(0, Math.max(0, 3 - Math.max(0, tendencies.length - offset)))];
                  const dims = rotatedTendencies.length >= 2 ? rotatedTendencies.slice(0, 3) : tendencies.slice(0, 3);
                  const hasDims = dims.length >= 2;
                  return (
                    <div key={a.id} style={{ position: "relative" }}
                      onMouseEnter={() => setHoverId(String(a.id))}
                      onMouseLeave={() => setHoverId(null)}
                    >
                      <a href={a.url || "#"} target="_blank" rel="noopener noreferrer"
                        style={{ display: "block", padding: "14px 18px", borderRadius: 10, textDecoration: "none", color: "inherit", background: i === 0 ? "rgba(16,185,129,0.03)" : "rgba(0,0,0,0.02)", border: i === 0 ? "1px solid rgba(16,185,129,0.14)" : "1px solid rgba(0,0,0,0.04)", transition: "all 0.15s" }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(16,185,129,0.25)"; }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = i === 0 ? "rgba(16,185,129,0.14)" : "rgba(0,0,0,0.04)"; }}
                      >
                        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                          <span style={{ fontSize: "1rem", flexShrink: 0 }}>{i === 0 ? "🔥" : "📅"}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <p style={{ fontSize: "0.84rem", fontWeight: i === 0 ? 600 : 400, marginBottom: 4, color: "var(--text)" }}>{a.title}</p>
                            <div style={{ display: "flex", gap: 6, fontSize: "0.68rem", color: "var(--text4)", flexWrap: "wrap", marginBottom: hasDims ? 8 : 0 }}>
                              <span style={{ color: "#10B981" }}>进行中</span>
                              {a.publishDate && <span>{a.publishDate}</span>}
                              {a.inferredEndDate && <span>⏰ {daysLeft(a.inferredEndDate)}</span>}
                              {(a.match_score ?? 0) > 0 && <span style={{ color: "var(--accent)", fontWeight: 600 }}>匹配度 {a.match_score}%</span>}
                            </div>

                            {(hasDims || a.match_reason) && (
                              <div style={{ padding: "8px 12px", borderRadius: 6, background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.08)" }}>
                                {hasDims && (
                                  <>
                                    <p style={{ fontSize: "0.62rem", color: "var(--text4)", marginBottom: 4 }}>可能帮助你成长的维度</p>
                                    {dims.map(([k, v]) => (
                                      <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                                        <span style={{ fontSize: "0.64rem", color: "var(--text4)", width: 56, textAlign: "right", flexShrink: 0 }}>{signalLabel(k)}</span>
                                        <span style={{ fontSize: "0.68rem", color: "#34D399", letterSpacing: "0.05em" }}>{stars(v)}</span>
                                      </div>
                                    ))}
                                    <p style={{ fontSize: "0.64rem", color: "var(--text4)", lineHeight: 1.4, marginTop: 4 }}>
                                      💡 活动不匹配现在的你，而是匹配你可能成长的方向——你的{signalLabel(dims[0][0])}和{signalLabel(dims[1][0])}在这里有发挥空间。
                                    </p>
                                  </>
                                )}
                                {a.match_reason && (
                                  <p style={{ fontSize: "0.64rem", color: "var(--text3)", lineHeight: 1.5 }}>💡 {a.match_reason}</p>
                                )}
                              </div>
                            )}
                          </div>
                          <ExternalLink size={12} color="#475569" style={{ flexShrink: 0, marginTop: 3 }} />
                        </div>
                      </a>
                      <button
                        onClick={() => toggleCollapse(a.id)}
                        title="折叠"
                        style={{ position: "absolute", top: 8, right: 8, border: "none", background: "var(--surface2)", color: "var(--text4)", cursor: "pointer", width: 22, height: 22, borderRadius: 6, fontSize: "0.7rem", opacity: hoverId === String(a.id) ? 1 : 0, transition: "opacity 0.15s" }}
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        ) : (
          <div style={{ padding: "20px", borderRadius: 12, textAlign: "center", background: "rgba(0,0,0,0.02)", border: "1px solid rgba(0,0,0,0.04)" }}>
            <p style={{ fontSize: "0.78rem", color: "var(--text4)" }}>暂无活动 · <a href="/connections" style={{ color: "var(--accent)" }}>前往活动大厅</a></p>
          </div>
        )}
      </section>

      {hasPersona && <FlowArrow />}

      {/* ═══════ 4. 🤝 我和他人 ═══════ */}
      <section style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: "1rem" }}>🤝</span>
          <h2 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text)" }}>我和他人</h2>
        </div>
        <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginBottom: 14, lineHeight: 1.5 }}>
          人不是孤立成长的。根据你的当前画像，你拥有某些倾向——也可能需要能与你共同创造的人。
        </p>

        {hasPersona && tendencies.length > 0 ? (
          <div style={{ padding: "20px 24px", borderRadius: 16, background: "linear-gradient(135deg, rgba(245,158,11,0.04), rgba(251,191,36,0.02))", border: "1px solid rgba(245,158,11,0.1)" }}>
            <p style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--text4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>你的画像</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 16 }}>
              {tendencies.slice(0, 4).map(([k, v]) => (
                <div key={k} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--text2)", width: 64, textAlign: "right", flexShrink: 0 }}>{signalLabel(k)}</span>
                  <span style={{ fontSize: "0.72rem", letterSpacing: "0.04em" }}>{stars(v)}</span>
                </div>
              ))}
            </div>

            <p style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--text4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>寻找共同创造者</p>
            <p style={{ fontSize: "0.66rem", color: "var(--text4)", marginBottom: 10, lineHeight: 1.4 }}>
              你不缺{tendencies.filter(([, v]) => v >= 60).slice(0, 2).map(([k]) => signalLabel(k)).join("和") || "想法"}——但可能需要让想法走向世界的人。
            </p>
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              {partnerNeeds.map(r => (
                <div key={r.name} style={{ flex: 1, padding: "12px 14px", borderRadius: 10, background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.1)" }}>
                  <p style={{ fontSize: "0.85rem", marginBottom: 4 }}><span style={{ marginRight: 6 }}>{r.icon}</span><span style={{ fontWeight: 600, color: "#FBBF24" }}>{r.name}</span></p>
                  <p style={{ fontSize: "0.64rem", color: "var(--text4)", lineHeight: 1.5 }}>{r.desc}</p>
                </div>
              ))}
            </div>

            {/* ── 真实推荐：技能互补的潜在队友 ── */}
            <p style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--text4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>可邀请的队友</p>
            {friends.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {friends.slice(0, 3).map((f: any) => (
                  <div key={f.user_id} style={{ padding: "10px 12px", borderRadius: 10, background: "rgba(245,158,11,0.04)", border: "1px solid rgba(245,158,11,0.08)", display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: "1rem", flexShrink: 0 }}>🧑‍🚀</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text2)" }}>
                        {f.real_name}
                        <span className="tag" style={{ marginLeft: 6, background: "var(--accent-bg)", color: "var(--accent)" }}>匹配 {f.match_score}</span>
                      </p>
                      {(f.complementary_skills || []).length > 0 && (
                        <p style={{ fontSize: "0.66rem", color: "var(--text4)", marginTop: 3, lineHeight: 1.5 }}>
                          可互补：{(f.complementary_skills || []).join("、")}
                        </p>
                      )}
                    </div>
                    <button
                      className="btn"
                      style={{ padding: "6px 12px", fontSize: "0.68rem", flexShrink: 0 }}
                      onClick={() => {
                        if (myTeams.length === 0) {
                          alert("你需要先加入或创建一支战队才能邀请队友");
                          return;
                        }
                        fetch(`/api/team/${myTeams[0].team_id}/invite`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          credentials: "include",
                          body: JSON.stringify({ user_id: f.user_id }),
                        })
                          .then(r => r.json())
                          .then(res => alert(res.error || `已向对方发送「${myTeams[0].team_name}」的组队邀请`));
                      }}
                    >
                      🤝 邀请组队
                    </button>
                  </div>
                ))}
                <a href="/connections" style={{ fontSize: "0.66rem", color: "var(--accent)", textDecoration: "none", textAlign: "center", marginTop: 2 }}>
                  查看全部潜在队友 →
                </a>
              </div>
            ) : (
              <div style={{ padding: "12px", borderRadius: 10, background: "rgba(245,158,11,0.03)", textAlign: "center" }}>
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", lineHeight: 1.6 }}>
                  暂无技能互补的推荐。<br />
                  <a href="/profile" style={{ color: "var(--accent)" }}>完善技能标签</a> 后，这里会出现能与你共同创造的人
                </p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: "20px 24px", borderRadius: 12, textAlign: "center", background: "rgba(245,158,11,0.03)", border: "1px solid rgba(245,158,11,0.08)", opacity: 0.65 }}>
            <p style={{ fontSize: "0.78rem", color: "var(--text4)", marginBottom: 6 }}>人是一切社会关系的总和。记录更多经历后，AI 将为你描绘能与你共同创造的人。</p>
            <a href="/profile" style={{ fontSize: "0.68rem", color: "var(--accent)" }}>先完善数字人格与技能标签 →</a>
          </div>
        )}
      </section>

      {hasPersona && <FlowArrow />}

      {/* ═══════ 5. 🎯 我要走向哪里 ═══════ */}
      <section>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: "1rem" }}>🎯</span>
            <h2 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text)" }}>我要走向哪里</h2>
          </div>
          <a href="/goals" style={{ fontSize: "0.72rem", color: "var(--accent)", textDecoration: "none" }}>管理 →</a>
        </div>
        <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginBottom: 14, lineHeight: 1.5 }}>
          你设定的方向。每一个目标都是一颗种子——AI 帮你看到距离，但路是你自己走的。
        </p>

        {(d?.active_goals || []).length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {goalFutureMatches.map(({ goal: g, match }: any) => {
              const needs = tendencies.filter(([, v]) => v < 50).slice(0, 2);
              return (
                <div className="card" key={g.id} style={{ padding: "14px 18px", borderRadius: 12 }}>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.9rem" }}>🎯</span>
                      <div>
                        <p style={{ fontSize: "0.84rem", fontWeight: 600, color: "var(--text)" }}>{g.title}</p>
                        <p style={{ fontSize: "0.66rem", color: "var(--text4)" }}>重要度 {g.importance}%{g.period ? " · " + g.period : ""}</p>
                      </div>
                    </div>
                    {match && (
                      <span style={{ padding: "2px 10px", borderRadius: 5, fontSize: "0.62rem", background: "rgba(139,92,246,0.1)", color: "var(--accent2)", border: "1px solid rgba(139,92,246,0.15)", flexShrink: 0 }}>
                        {match.label} {Math.round((match.confidence || 0.7) * 100)}%
                      </span>
                    )}
                  </div>

                  {/* 达成目标需要的成长 — 取最低的 3 个维度 */}
                  <div style={{ padding: "8px 12px", borderRadius: 6, background: "var(--accent-bg)", border: "1px solid var(--accent-border)" }}>
                    <p style={{ fontSize: "0.62rem", color: "var(--text4)", marginBottom: 4 }}>达成此目标需要提升</p>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                      {(() => {
                        const sorted = [...tendencies].sort((a, b) => a[1] - b[1]); // 升序，最低在前
                        const low3 = sorted.slice(0, 3);
                        if (low3.length === 0) return <span style={{ fontSize: "0.64rem", color: "var(--accent)" }}>积累更多数据后出现</span>;
                        return low3.map(([k, v]) => (
                          <span key={k} style={{ fontSize: "0.64rem", color: "var(--accent)" }}>
                            {signalLabel(k)} <span style={{ color: "#34D399", fontWeight: 600 }}>↑{Math.max(1, Math.round((80 - v) / 5))}</span>
                          </span>
                        ));
                      })()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="card" style={{ padding: "20px 24px", borderRadius: 12, textAlign: "center" }}>
            {hasPersona && signals.length > 0 ? (
              <>
                <p style={{ fontSize: "0.72rem", color: "var(--text4)", marginBottom: 12 }}>从镜像开始——根据你的当前画像，你可能想探索：</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginBottom: 14 }}>
                  {(() => {
                    const suggestions: string[] = [];
                    if (signals.some(([k]) => k.includes("技术") || k.includes("编程") || k.includes("AI"))) suggestions.push("深入 AI 技术");
                    if (signals.some(([k]) => k.includes("科研") || k.includes("学习") || k.includes("阅读"))) suggestions.push("建立知识体系");
                    if (signals.some(([k]) => k.includes("创造") || k.includes("艺术") || k.includes("设计"))) suggestions.push("完成一个个人创造项目");
                    if (signals.some(([k]) => k.includes("社交") || k.includes("表达") || k.includes("组织"))) suggestions.push("认识更多同领域的人");
                    if (signals.some(([k]) => k.includes("哲学") || k.includes("反思") || k.includes("认知"))) suggestions.push("深化自我认知与反思");
                    if (suggestions.length < 2) suggestions.push("深入 AI 技术", "建立知识体系", "完成一个个人创造项目");
                    return suggestions.slice(0, 4).map(s => (
                      <a key={s} href="/goals" style={{ padding: "6px 14px", borderRadius: 6, fontSize: "0.7rem", background: "rgba(99,102,241,0.1)", color: "var(--accent)", textDecoration: "none", border: "1px solid rgba(99,102,241,0.15)" }}>{s}</a>
                    ));
                  })()}
                </div>
                <p style={{ fontSize: "0.64rem", color: "var(--text3)" }}>选择方向 → 目标反过来更新镜像 → 形成成长闭环</p>
              </>
            ) : (
              <p style={{ fontSize: "0.78rem", color: "var(--text4)" }}>还没有目标 — <a href="/goals" style={{ color: "var(--accent)" }}>设定第一个方向</a></p>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

function FlowArrow() {
  return (
    <div style={{ textAlign: "center", marginBottom: 4 }}>
      <svg width="24" height="20" viewBox="0 0 24 20" style={{ opacity: 0.15 }}>
        <line x1="12" y1="0" x2="12" y2="16" stroke="var(--accent)" strokeWidth="1.5" />
        <polyline points="6,11 12,17 18,11" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
      </svg>
    </div>
  );
}
