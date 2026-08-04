import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../auth";
import VoiceInput from "../components/VoiceInput";

const MOODS = ["", "开心", "平静", "充实", "疲惫", "焦虑", "迷茫", "兴奋", "低落"];

export default function Journal() {
  const [records, setRecords] = useState<any[]>([]);
  const [content, setContent] = useState("");
  const [mood, setMood] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const load = () => api("/api/mirror/journal").then(setRecords).catch(() => {});

  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!content.trim()) {
      setErr("请写下今天发生了什么");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await api("/api/mirror/journal", {
        method: "POST",
        body: JSON.stringify({ content, mood }),
      });
      setContent("");
      setMood("");
      load();
    } catch (e: any) {
      setErr(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>📝 日常记录</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>每一笔记录，都是数字人格的数据来源</p>

      <div className="card" style={{ marginBottom: 24 }}>
        <textarea
          className="input"
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="今天发生了什么？有什么感受和思考？"
          style={{ resize: "vertical" }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
          <select className="input" style={{ width: 130 }} value={mood} onChange={(e) => setMood(e.target.value)}>
            {MOODS.map((m) => (
              <option key={m} value={m}>{m || "心情"}</option>
            ))}
          </select>
          <VoiceInput onText={(t) => setContent((c) => (c ? c + t : t))} />
          {err && <span style={{ color: "#F87171", fontSize: "0.75rem" }}>{err}</span>}
          <button className="btn" onClick={create} disabled={saving} style={{ marginLeft: "auto" }}>
            {saving ? "AI 分析中..." : "记录并分析"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {records.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有记录——写下第一条，开始积累属于你的人生数据
          </div>
        )}
        {records.map((r) => (
          <Link key={r.id} to={`/journal/${r.id}`} style={{ textDecoration: "none" }}>
            <div className="card" style={{ padding: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text4)" }}>{r.date}</span>
                {r.mood && <span className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{r.mood}</span>}
              </div>
              <p style={{ fontSize: "0.88rem", lineHeight: 1.7, color: "var(--text2)" }}>{r.content}</p>
              {r.ai_analysis?.honest_reflection && (
                <p style={{ fontSize: "0.75rem", color: "var(--text3)", marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                  🪞 {r.ai_analysis.honest_reflection}
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
