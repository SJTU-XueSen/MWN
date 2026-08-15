import { useState } from 'react';
import { api } from '../api';

/**
 * AuthModal — 登录 / 注册（agent 独立认证, 数据与主站同库）
 */
export default function AuthModal({ onClose, onAuthed }) {
  const [mode, setMode] = useState('login');   // login | register
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (busy) return;
    setError('');
    if (!username.trim() || !password) { setError('请输入用户名和密码'); return; }
    if (mode === 'register' && (!email || !email.includes('@'))) { setError('请输入有效邮箱'); return; }
    setBusy(true);
    const body = mode === 'register'
      ? { username: username.trim(), password, email: email.trim() }
      : { username: username.trim(), password };
    const d = await api(`/api/auth/${mode}`, { method: 'POST', body: JSON.stringify(body) });
    setBusy(false);
    if (d.ok) { onAuthed?.(d.user); onClose(); }
    else setError(d.error || d.detail || '操作失败');
  };

  return (
    <div onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 1000,
               display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: 'var(--surface)', borderRadius: 14, width: '100%', maxWidth: 380, padding: '24px 28px',
                 boxShadow: '0 12px 40px rgba(0,0,0,.4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <div style={{ fontSize: 17, fontWeight: 700 }}>{mode === 'login' ? '登录' : '注册'}</div>
          <span onClick={onClose} style={{ cursor: 'pointer', color: 'var(--text4)', fontSize: 14 }}>✕</span>
        </div>
        <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
          {['login', 'register'].map(m => (
            <button key={m} onClick={() => { setMode(m); setError(''); }}
              style={{ flex: 1, padding: '7px 0', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                       border: mode === m ? '1px solid var(--accent-border2)' : '1px solid var(--border)',
                       background: mode === m ? 'var(--accent-bg)' : 'var(--surface)',
                       color: mode === m ? 'var(--accent)' : 'var(--text4)' }}>
              {m === 'login' ? '登录' : '注册'}
            </button>
          ))}
        </div>
        <input value={username} onChange={e => setUsername(e.target.value)} placeholder="用户名"
          style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--input-border)',
                   background: 'var(--input-bg)', color: 'var(--text)', fontSize: 14, outline: 'none',
                   marginBottom: 10, boxSizing: 'border-box' }} />
        {mode === 'register' && (
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="邮箱"
            style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--input-border)',
                     background: 'var(--input-bg)', color: 'var(--text)', fontSize: 14, outline: 'none',
                     marginBottom: 10, boxSizing: 'border-box' }} />
        )}
        <input value={password} onChange={e => setPassword(e.target.value)} type="password"
          placeholder="密码（≥8 字符）"
          onKeyDown={e => e.key === 'Enter' && submit()}
          style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--input-border)',
                   background: 'var(--input-bg)', color: 'var(--text)', fontSize: 14, outline: 'none',
                   marginBottom: 12, boxSizing: 'border-box' }} />
        {error && <div style={{ color: 'var(--danger)', fontSize: 12.5, marginBottom: 10 }}>{error}</div>}
        <button onClick={submit} disabled={busy}
          style={{ width: '100%', padding: '10px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
                   background: 'var(--btn-bg)', color: '#fff', fontSize: 14, opacity: busy ? 0.5 : 1 }}>
          {busy ? '处理中…' : (mode === 'login' ? '登录' : '注册并登录')}
        </button>
      </div>
    </div>
  );
}
