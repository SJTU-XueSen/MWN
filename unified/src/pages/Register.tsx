import { useState } from "react";
import { useNavigate } from "react-router-dom";
export default function Register() {
  const [u,setU]=useState("");const [e,setE]=useState("");const [p,setP]=useState("");const [cp,setCp]=useState("");
  const [n,setN]=useState("");const [err,setErr]=useState("");const nav=useNavigate();
  async function reg(){
    if(p!==cp){setErr("两次密码不一致");return;}
    if(p.length<6){setErr("密码至少6位");return;}
    try {
      const fd=new URLSearchParams({username:u,email:e,password:p,confirm_password:cp,real_name:n,agree_terms:"1"});
      const r=await fetch("/auth/register",{method:"POST",body:fd,credentials:"include"});
      if(r.redirected||r.ok){nav("/");return;}
      const t=await r.text();
      if(t.includes("已存在")){setErr("用户名或邮箱已被注册");return;}
      if(t.includes("不一致")){setErr("两次密码不一致");return;}
      setErr("注册失败，请检查信息");
    }catch{setErr("网络错误");}
  }
  return (<main style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh",background:"var(--bg)"}}>
    <div className="card" style={{width:400,padding:32}}>
      <div style={{textAlign:"center",marginBottom:24}}><p style={{fontSize:"2.5rem"}}>🪞</p><h1 style={{fontSize:"1.3rem",fontWeight:700}}>注册 镜·界·联</h1></div>
      {err && <p style={{color:"#F87171",fontSize:"0.8rem",marginBottom:12,textAlign:"center"}}>{err}</p>}
      <input className="input" value={u} onChange={e=>setU(e.target.value)} placeholder="用户名" style={{marginBottom:8}} />
      <input className="input" value={n} onChange={e=>setN(e.target.value)} placeholder="真实姓名" style={{marginBottom:8}} />
      <input className="input" value={e} onChange={e=>setE(e.target.value)} placeholder="邮箱" style={{marginBottom:8}} />
      <input className="input" type="password" value={p} onChange={e=>setP(e.target.value)} placeholder="密码（至少6位）" style={{marginBottom:8}} />
      <input className="input" type="password" value={cp} onChange={e=>setCp(e.target.value)} placeholder="确认密码" style={{marginBottom:16}} />
      <label style={{display:"flex",alignItems:"center",gap:8,marginBottom:16,fontSize:"0.75rem",color:"#64748B"}}>
        <input type="checkbox" defaultChecked style={{accentColor:"#6366F1"}} />已阅读并同意用户协议和隐私政策
      </label>
      <button className="btn" onClick={reg} style={{width:"100%"}}>注册</button>
      <p style={{textAlign:"center",marginTop:16,fontSize:"0.8rem",color:"#64748B"}}>已有账户？<a href="/login" style={{color:"#8b5e3c"}}>登录</a></p>
    </div>
  </main>);
}
