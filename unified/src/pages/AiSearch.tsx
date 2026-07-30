import { useState } from "react";
import { Search } from "lucide-react";
import VoiceInput from "../components/VoiceInput";
export default function AiSearch() {
  const [q,setQ] = useState(""); const [results,setResults] = useState<any>(null);
  async function search() {
    const r = await fetch("/api/ai-search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:q})});
    setResults(await r.json());
  }
  return (<main style={{padding:"32px 40px",background:"var(--bg)",minHeight:"100vh"}}>
    <h1 style={{fontSize:"1.5rem",fontWeight:700,marginBottom:20}}>AI 检索</h1>
    <div style={{display:"flex",gap:8,marginBottom:20}}><VoiceInput onText={text => setQ(prev => prev + " " + text)} /><input className="input" value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search()} placeholder="搜索竞赛、活动..." style={{flex:1}} /><button className="btn" onClick={search} style={{whiteSpace:"nowrap",padding:"10px 24px"}}><Search size={15}/> 搜索</button></div>
    {results?.recommendations?.map((r:any)=>(<a key={r.id} href={r.url||"#"} target="_blank" className="card" style={{display:"block",marginBottom:8,textDecoration:"none"}}>
      <p style={{fontWeight:600}}>{r.title}</p><p style={{color:"#64748B",fontSize:"0.8rem",marginTop:4}}>{r.summary?.slice(0,150)}</p><span className="badge" style={{marginTop:8,background:"rgba(99,102,241,0.15)",color:"#8b5e3c"}}>{r.matchReason}</span>
    </a>))}
    {results && !results.recommendations?.length && <p style={{color:"#64748B",textAlign:"center",padding:20}}>未找到匹配结果</p>}
  </main>);
}
