import { useEffect, useState } from "react";
import { api } from "../auth";

const CATEGORIES = [
  { key: "kaoyan", label: "考研深造", icon: "🎓" },
  { key: "job", label: "求职就业", icon: "💼" },
  { key: "startup", label: "创业经历", icon: "🚀" },
  { key: "cross", label: "转行跨界", icon: "🔀" },
  { key: "life", label: "大学生活", icon: "🏫" },
  { key: "failure", label: "失败教训", icon: "💪" },
];

export default function ReferencesPage() {
  const [category, setCategory] = useState("kaoyan");
  const [data, setData] = useState<any>(null);
  const [insight, setInsight] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setData(null);
    api(`/api/mirror/references`)
      .then((d) => setInsight(d.insight || ""))
      .catch(() => {});
    fetch(`/api/references?category=${category}`, { credentials: "include" })
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
    // 记录兴趣点击
    fetch("/api/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ event: "article_click", detail: { category } }),
    }).catch(() => {});
  }, [category]);

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>人生参考</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 16 }}>
        真实的他人经历——你的浏览会被记录为兴趣信号，参与人格聚合
      </p>
      {insight && <p style={{ fontSize: "0.78rem", color: "var(--accent)", marginBottom: 16 }}>{insight}</p>}

      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {CATEGORIES.map((c) => (
          <button
            key={c.key}
            className="badge"
            style={{
              cursor: "pointer",
              border: "1px solid",
              borderColor: category === c.key ? "var(--accent-border2)" : "var(--border)",
              background: category === c.key ? "var(--accent-bg3)" : "transparent",
              color: category === c.key ? "var(--accent)" : "var(--text4)",
              padding: "8px 16px",
            }}
            onClick={() => setCategory(c.key)}
          >
            {c.icon} {c.label}
          </button>
        ))}
      </div>

      {loading && <p style={{ color: "var(--text4)", fontSize: "0.8rem" }}>搜索真实经历中...</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {data?.items?.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            暂未搜索到相关内容，请稍后再试
          </div>
        )}
        {data?.items?.map((item: any, i: number) => (
          <a key={i} href={item.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
            <div className="card" style={{ padding: 14 }}>
              <p style={{ fontSize: "0.88rem", fontWeight: 600, marginBottom: 6 }}>{item.title}</p>
              <p style={{ fontSize: "0.78rem", color: "var(--text3)", lineHeight: 1.7 }}>{item.snippet}</p>
              <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 6 }}>{item.url}</p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
