import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../auth";

const SCENARIOS = [
  { value: "further_study", label: "继续深造", icon: "🎓", desc: "在学术方向上持续深耕" },
  { value: "employment", label: "直接就业", icon: "💼", desc: "走向真实的工作场景" },
  { value: "entrepreneurship", label: "创业探索", icon: "🚀", desc: "把想法变成现实" },
  { value: "cross_discipline", label: "跨学科发展", icon: "🔀", desc: "在不同领域间建立连接" },
];

export default function SimulationPage() {
  const [sims, setSims] = useState<any[]>([]);
  const [scenario, setScenario] = useState("further_study");
  const [question, setQuestion] = useState("");
  const [running, setRunning] = useState(false);

  const load = () => api("/api/mirror/simulations").then(setSims).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function run() {
    setRunning(true);
    try {
      const res = await api("/api/mirror/simulations", {
        method: "POST",
        body: JSON.stringify({ scenario_type: scenario, question }),
      });
      window.location.href = `/simulation/${res.id}`;
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: 4 }}>🔮 人生模拟</h1>
      <p style={{ color: "var(--text4)", fontSize: "0.8rem", marginBottom: 20 }}>
        基于你的真实记忆与人格，推演 3 条可能的未来路径——不是预测，是可能性
      </p>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginBottom: 14 }}>
          {SCENARIOS.map((s) => (
            <button
              key={s.value}
              onClick={() => setScenario(s.value)}
              style={{
                padding: "14px 10px",
                borderRadius: 12,
                border: "1px solid",
                cursor: "pointer",
                background: scenario === s.value ? "var(--accent-bg3)" : "var(--input-bg)",
                borderColor: scenario === s.value ? "var(--accent-border2)" : "var(--border)",
                textAlign: "center",
              }}
            >
              <p style={{ fontSize: "1.3rem", marginBottom: 4 }}>{s.icon}</p>
              <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text2)" }}>{s.label}</p>
              <p style={{ fontSize: "0.68rem", color: "var(--text4)", marginTop: 4 }}>{s.desc}</p>
            </button>
          ))}
        </div>
        <input
          className="input"
          placeholder="你想带着什么问题进入模拟？（可选）"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="btn" style={{ marginTop: 12, width: "100%" }} onClick={run} disabled={running}>
          {running ? "AI 正在推演 3 条未来路径..." : "开始模拟"}
        </button>
      </div>

      <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 12 }}>📚 历史模拟</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sims.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 36, color: "var(--text4)", fontSize: "0.85rem" }}>
            还没有模拟记录——生成第一条未来路径
          </div>
        )}
        {sims.map((s) => (
          <Link key={s.id} to={`/simulation/${s.id}`} style={{ textDecoration: "none" }}>
            <div className="card" style={{ padding: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <p style={{ fontSize: "0.88rem", fontWeight: 600 }}>
                  {SCENARIOS.find((x) => x.value === s.scenario)?.icon} {SCENARIOS.find((x) => x.value === s.scenario)?.label || s.scenario}
                </p>
                {s.question && <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginTop: 2 }}>{s.question}</p>}
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: "0.72rem", color: "var(--text4)" }}>{s.date}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--accent)" }}>{s.paths?.length || 0} 条路径</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
