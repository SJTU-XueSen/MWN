import { useEffect, useState } from "react";
export default function Persona() {
  const [d,setD] = useState<any>(null);
  useEffect(()=>{fetch("/api/mirror/persona").then(r=>r.json()).then(setD);},[]);
  const p = d?.current;
  return (<main style={{padding:"32px 40px",background:"var(--bg)",minHeight:"100vh"}}>
    <h1 style={{fontSize:"1.5rem",fontWeight:700,marginBottom:24}}>数字人格</h1>
    {p ? <div>
      <div className="card" style={{textAlign:"center",padding:40,marginBottom:24,background:"linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.08))",borderColor:"rgba(99,102,241,0.2)"}}>
        <p style={{fontSize:"3rem",marginBottom:8}}>🧬</p>
        <h2 style={{fontSize:"1.5rem",margin:0}}>{p.persona_type}</h2>
        <p style={{color:"#64748B",maxWidth:500,margin:"12px auto"}}>{p.summary}</p>
        <span className="badge" style={{background:"rgba(0,0,0,0.04)",color:"#64748B"}}>v{p.version} · 置信度 {Math.round(p.confidence*100)}%</span>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(250px,1fr))",gap:16}}>
        {Object.entries({ability:"能力画像",interest:"兴趣画像",value:"价值观",decision:"决策风格",behavior:"行为模式"}).map(([k,label])=>(
          <div key={k} className="card"><h3 style={{fontSize:"0.85rem",color:"#64748B",marginBottom:12}}>{label}</h3>
            {p[k] && typeof p[k]==='object' ? Object.entries(p[k]).map(([kk,vv]:any)=>(
              <div key={kk} style={{display:"flex",justifyContent:"space-between",fontSize:"0.82rem",marginBottom:6}}><span style={{color:"#64748B"}}>{kk}</span><span>{typeof vv==='number'?vv:String(vv)}</span></div>
            )) : <p style={{color:"#64748B",fontSize:"0.8rem"}}>暂无数据</p>}
          </div>
        ))}
      </div>
    </div> : <div style={{textAlign:"center",padding:60,color:"#64748B"}}><p style={{fontSize:"3rem"}}>🧬</p><p>还没有数字人格画像</p></div>}
  </main>);
}
