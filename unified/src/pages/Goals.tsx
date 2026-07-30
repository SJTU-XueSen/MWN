import { useEffect, useState } from "react";
export default function Goals() {
  const [goals,setGoals] = useState<any[]>([]);
  useEffect(()=>{fetch("/api/mirror/goals").then(r=>r.json()).then(setGoals);},[]);
  return (<main style={{padding:"32px 40px",background:"var(--bg)",minHeight:"100vh"}}><h1 style={{fontSize:"1.5rem",fontWeight:700,marginBottom:20}}>人生目标</h1>
    {goals.map(g=>(<div key={g.id} className="card" style={{marginBottom:8}}><div style={{display:"flex",justifyContent:"space-between"}}>
      <div><p style={{fontWeight:600}}>{g.title}</p><p style={{color:"#64748B",fontSize:"0.8rem",marginTop:4}}>{g.description?.slice(0,100)}</p>
        <div style={{display:"flex",gap:8,marginTop:8}}><span className="badge" style={{background:"rgba(99,102,241,0.15)",color:"#8b5e3c"}}>{g.period||"长期"}</span><span className="badge" style={{background:"rgba(0,0,0,0.04)",color:"#64748B"}}>重要度 {g.importance}%</span>{g.target_year&&<span className="badge" style={{background:"rgba(0,0,0,0.04)",color:"#64748B"}}>{g.target_year}年</span>}{g.status==="achieved"&&<span className="badge" style={{background:"rgba(16,185,129,0.15)",color:"#10B981"}}>已完成</span>}</div></div>
    </div></div>))}
    {!goals.length && <p style={{color:"#64748B",textAlign:"center",padding:40}}>还没有目标</p>}
  </main>);
}
