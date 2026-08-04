import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../auth";

export default function JournalDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [record, setRecord] = useState<any>(null);

  useEffect(() => {
    api(`/api/mirror/journal/${id}`).then(setRecord).catch(() => {});
  }, [id]);

  if (!record) {
    return <div style={{ textAlign: "center", padding: 80, color: "var(--text4)" }}>加载中...</div>;
  }

  const analysis = record.ai_analysis || {};

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px" }}>
      <Link to="/journal" style={{ fontSize: "0.8rem", color: "var(--accent)", textDecoration: "none" }}>← 返回记录列表</Link>
      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text4)" }}>{record.date}</span>
          {record.mood && <span className="tag" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>{record.mood}</span>}
        </div>
        <p style={{ fontSize: "1rem", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{record.content}</p>
      </div>

      {analysis.engine && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>🪞 AI 分析</h3>
            <span className="badge" style={{ background: "var(--accent-bg)", color: "var(--accent)" }}>
              {analysis.engine === "deepseek" ? "DeepSeek" : "规则引擎"}
            </span>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <Section label="核心事件" text={analysis.event} />
            <Section label="情绪" text={`${analysis.emotion_detail || analysis.emotion || "中性"}`} />
            {(analysis.interest_fields || []).length > 0 && (
              <Section label="兴趣领域" text={(analysis.interest_fields || []).join("、")} />
            )}
            {(analysis.behavior_patterns || []).length > 0 && (
              <Section label="行为模式" text={(analysis.behavior_patterns || []).join("、")} />
            )}
            <Section label="长期影响" text={analysis.long_term_impact} />
            <Section label="真诚的肯定" text={analysis.encouragement} />
            {analysis.honest_reflection && <Section label="诚实反思" text={analysis.honest_reflection} accent />}
            <Section label="展望" text={analysis.outlook} />
          </div>
        </div>
      )}

      <button
        className="btn-ghost"
        style={{ marginTop: 16, color: "#F87171", borderColor: "rgba(248,113,113,0.3)" }}
        onClick={async () => {
          if (confirm("确定删除这条记录吗？")) {
            await api(`/api/mirror/journal/${id}`, { method: "DELETE" });
            nav("/journal");
          }
        }}
      >
        删除记录
      </button>
    </div>
  );
}

function Section({ label, text, accent }: { label: string; text?: string; accent?: boolean }) {
  if (!text) return null;
  return (
    <div>
      <p style={{ fontSize: "0.7rem", color: "var(--text4)", marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: "0.85rem", lineHeight: 1.7, color: accent ? "var(--accent)" : "var(--text2)" }}>{text}</p>
    </div>
  );
}
