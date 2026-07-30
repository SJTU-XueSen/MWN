import { useState } from "react";
import { useNavigate } from "react-router-dom";

const LEGAL = {
  terms: {
    title: "用户协议",
    content: `欢迎使用镜·界·联（以下简称"本平台"）。

一、服务说明
本平台是一个面向大学生的 AI 成长辅助系统，提供人格分析、人生模拟、活动推荐与组队协作服务。所有 AI 分析结果仅供参考，不构成职业建议、心理诊断或人生决策依据。

二、用户责任
1. 您承诺提供真实、准确的个人信息。
2. 您对在本平台发布的所有内容（包括记录、事件、聊天消息）负责。
3. 不得利用本平台从事违法违规活动。

三、数据与隐私
1. 您的人生数据（日记、事件、人格画像）归您个人所有。
2. 您可以随时查看、修改、删除自己的数据。
3. 本平台不会向第三方出售或分享您的个人数据。`,
  },
  privacy: {
    title: "隐私政策",
    content: `一、我们收集什么
1. 账户信息：用户名、真实姓名（用于团队协作展示）。
2. 人生数据：您主动记录的日记、事件、目标。
3. 行为数据：浏览活动、点击记录等，用于兴趣追踪。
4. AI 分析结果：人格画像、模拟路径、成长报告。

二、数据存储
1. 所有数据存储在本地 SQLite 数据库和 ChromaDB 向量库中。
2. 密码使用 bcrypt 哈希，不可逆。
3. AI 分析通过 DeepSeek/智谱 API 进行，传输内容不含个人身份信息。

三、您的权利
1. 访问权：随时查看您的所有数据。
2. 删除权：随时删除任何记录、事件或账户。
3. 数据可携权：可申请导出所有数据。`,
  },
  disclaimer: {
    title: "免责声明",
    content: `一、AI 分析说明
本平台的数字人格画像、人生模拟、成长报告等均由 AI 自动生成，其准确性取决于您提供的数据质量和数量。AI 不是预言家——它只是在您的真实数据上进行模式识别和趋势推演。

二、不构成专业建议
本平台的内容不构成：
- 职业规划建议
- 心理健康诊断或治疗
- 学术或法律建议

如需专业指导，请咨询相关领域的专业人士。

三、模拟局限性
人生模拟的结果不是对未来的预测。人的成长受到大量无法建模的因素影响：社会变化、偶然机遇、个人选择——AI 只能基于您的过去，推演一种可能性的方向。`,
  },
};

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [realName, setRealName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [legalDoc, setLegalDoc] = useState<string | null>(null);
  const nav = useNavigate();

  function handleLogin(e: React.FormEvent) {
    // 传统表单提交——绕过 fetch CORS/代理问题
    const form = e.target as HTMLFormElement;
    if (!username.trim() || !password) { setErr("请填写用户名和密码"); e.preventDefault(); return; }
    setLoading(true); setErr("");
    // 让表单正常提交，Mirror 302 → / → React 接管
  }

  function handleRegister(e: React.FormEvent) {
    if (!username.trim() || !realName.trim()) { setErr("请填写用户名和姓名"); e.preventDefault(); return; }
    if (password.length < 6) { setErr("密码至少6位"); e.preventDefault(); return; }
    if (password !== confirmPwd) { setErr("两次密码不一致"); e.preventDefault(); return; }
    if (!agreed) { setErr("请阅读并同意用户协议和隐私政策"); e.preventDefault(); return; }
    setLoading(true); setErr("");
    // 让表单正常提交，Mirror 302 → / → React 接管
  }

  return (
    <main style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      {/* 法律文档弹窗 */}
      {legalDoc && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => setLegalDoc(null)}>
          <div className="card" style={{ maxWidth: 560, maxHeight: "80vh", overflow: "auto", padding: 28 }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontWeight: 700 }}>{(LEGAL as any)[legalDoc]?.title}</h3>
              <button onClick={() => setLegalDoc(null)} style={{ border: "none", background: "none", cursor: "pointer", fontSize: "1.2rem", color: "var(--text4)" }}>×</button>
            </div>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.82rem", lineHeight: 1.7, color: "var(--text3)", fontFamily: "inherit" }}>
              {(LEGAL as any)[legalDoc]?.content}
            </pre>
          </div>
        </div>
      )}

      <div className="card" style={{ width: 400, padding: 32 }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <p style={{ fontSize: "2.5rem", marginBottom: 4 }}>🪞</p>
          <h1 style={{ fontSize: "1.3rem", fontWeight: 700 }}>镜·界·联</h1>
          <p style={{ fontSize: "0.75rem", color: "var(--text4)", marginTop: 4 }}>认识自己 · 走向世界 · 与他人共同创造</p>
        </div>

        {/* 模式切换 */}
        <div style={{ display: "flex", marginBottom: 20, borderRadius: 10, overflow: "hidden", border: "1px solid var(--border)" }}>
          <button onClick={() => { setMode("login"); setErr(""); }}
            style={{ flex: 1, padding: "10px 0", border: "none", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem",
              background: mode === "login" ? "var(--accent-bg3)" : "transparent", color: mode === "login" ? "var(--accent)" : "var(--text4)" }}>
            登录
          </button>
          <button onClick={() => { setMode("register"); setErr(""); }}
            style={{ flex: 1, padding: "10px 0", border: "none", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem",
              background: mode === "register" ? "var(--accent-bg3)" : "transparent", color: mode === "register" ? "var(--accent)" : "var(--text4)" }}>
            注册
          </button>
        </div>

        {err && <p style={{ color: "#F87171", fontSize: "0.8rem", marginBottom: 12, textAlign: "center" }}>{err}</p>}

        <form action={mode === "login" ? "/auth/login" : "/auth/register"} method="POST" onSubmit={mode === "login" ? handleLogin : handleRegister} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <input className="input" value={username} onChange={e => setUsername(e.target.value)} placeholder="用户名" />

          {mode === "register" && (
            <input className="input" value={realName} onChange={e => setRealName(e.target.value)} placeholder="真实姓名（团队协作时显示）" />
          )}

          <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)}
            placeholder={mode === "login" ? "密码" : "密码（至少6位）"} />

          {mode === "register" && (
            <input className="input" type="password" value={confirmPwd} onChange={e => setConfirmPwd(e.target.value)} placeholder="确认密码" />
          )}

          {mode === "register" && (
            <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: "0.75rem", color: "var(--text4)", cursor: "pointer", marginTop: 4 }}>
              <input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} style={{ marginTop: 2, flexShrink: 0 }} />
              <span>
                我已阅读并同意
                <span style={{ color: "var(--accent)", cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("terms")}>《用户协议》</span>、
                <span style={{ color: "var(--accent)", cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("privacy")}>《隐私政策》</span>和
                <span style={{ color: "var(--accent)", cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("disclaimer")}>《免责声明》</span>
              </span>
            </label>
          )}

          <button type="submit" className="btn text-white" disabled={loading} style={{ width: "100%", marginTop: 8 }}>
            {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
          </button>
        </form>

        {/* 法律链接（登录模式也可见） */}
        <div style={{ textAlign: "center", marginTop: 16, fontSize: "0.7rem", color: "var(--text4)" }}>
          <span style={{ cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("terms")}>用户协议</span>
          {" · "}
          <span style={{ cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("privacy")}>隐私政策</span>
          {" · "}
          <span style={{ cursor: "pointer", textDecoration: "underline" }} onClick={() => setLegalDoc("disclaimer")}>免责声明</span>
        </div>
      </div>
    </main>
  );
}
