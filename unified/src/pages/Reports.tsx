import { useEffect, useState } from "react";
export default function Reports() {
  const [reports,setReports] = useState<any[]>([]);
  useEffect(()=>{fetch("/api/mirror/reports").then(r=>r.json()).then(setReports);},[]);
  return (<main style={{padding:"32px 40px",background:"var(--bg)",minHeight:"100vh"}}><h1 style={{fontSize:"1.5rem",fontWeight:700,marginBottom:20}}>成长报告</h1>
    {reports.map(r=>(<div key={r.id} className="card" style={{marginBottom:8}}><p style={{fontWeight:600}}>{r.title}</p><p style={{color:"#64748B",fontSize:"0.8rem",marginTop:4}}>{r.period_start} — {r.period_end}</p><p style={{color:"#64748B",fontSize:"0.8rem",marginTop:4}}>{r.content?.summary?.slice(0,150)}</p></div>))}
    {!reports.length && <p style={{color:"#64748B",textAlign:"center",padding:40}}>还没有成长报告</p>}
  </main>);
}
