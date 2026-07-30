import { Fingerprint, Globe, Users } from "lucide-react";
export default function Landing() {
  return (
    <main style={{background:"var(--bg)",minHeight:"100vh",color:"var(--text)"}}>
      <section style={{textAlign:"center",padding:"100px 24px 60px"}}>
        <h1 style={{fontSize:"2.8rem",fontWeight:800,letterSpacing:"-0.02em",marginBottom:16}}>🪞 镜·界·联</h1>
        <p style={{fontSize:"1.2rem",color:"#64748B",maxWidth:560,margin:"0 auto 12px",lineHeight:1.6}}>从自我出发，在世界中探索，在关系中成为自己</p>
        <p style={{fontSize:"0.9rem",color:"#64748B",maxWidth:480,margin:"0 auto 40px"}}>以 AI 人格模型为核心的大学生成长平台——认识自己、发现机会、连接伙伴</p>
        <div style={{display:"flex",gap:12,justifyContent:"center"}}>
          <a href="/login" style={{background:"linear-gradient(135deg,#6366F1,#8B5CF6)",color:"#fff",textDecoration:"none",fontSize:"1rem",padding:"14px 32px",borderRadius:12,fontWeight:600}}>开始使用</a>
          <a href="/activities" style={{color:"#64748B",textDecoration:"none",fontSize:"1rem",padding:"14px 32px",borderRadius:12,border:"1px solid rgba(255,255,255,0.15)"}}>浏览活动</a>
        </div>
      </section>
      <section style={{maxWidth:900,margin:"0 auto",padding:"60px 24px",display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(250px,1fr))",gap:24}}>
        {[{icon:<Fingerprint size={36}/>,title:"认识自己",desc:"我是谁？我会成为谁？",sub:"AI 数字人格画像 · 人生模拟 · 未来对话"},{icon:<Globe size={36}/>,title:"探索世界",desc:"我可以做什么？",sub:"校园活动聚合 · AI 智能检索 · 个性化推荐"},{icon:<Users size={36}/>,title:"连接伙伴",desc:"和谁一起创造？",sub:"AI 人格互补匹配 · 团队协作 · 即将上线",dim:true}].map((m,i)=>(
          <div key={i} className="card" style={{textAlign:"center",padding:36,opacity:m.dim?0.4:1}}>
            <div style={{color:"#8b5e3c",marginBottom:16}}>{m.icon}</div>
            <h3 style={{marginBottom:8,fontSize:"1.1rem"}}>{m.title}</h3>
            <p style={{color:"#64748B",fontSize:"0.9rem",marginBottom:4}}>{m.desc}</p>
            <p style={{color:"#64748B",fontSize:"0.8rem"}}>{m.sub}</p>
          </div>
        ))}
      </section>
      <footer style={{textAlign:"center",padding:"40px 24px",color:"#64748B",fontSize:"0.8rem"}}>镜·界·联 — 青年成长生态系统</footer>
    </main>
  );
}
