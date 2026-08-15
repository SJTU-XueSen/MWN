import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api';
import AuthModal from './AuthModal';
import UserCenterModal from './UserCenterModal';
import RecordDetailModal from './RecordDetailModal';

/**
 * AgentSidebar — 智能体广场（PhiAgent 同款视觉, 单全能 agent）
 * 独立认证: 注册/登录同库, session 与主站互通
 */
const AGENT = { key: 'mentor', name: '镜界导师', subtitle: '全能成长伙伴', tagline: '记录 / 看见 / 预见 / 共创' };

const RECORD_TABS = [['journal', '日记'], ['events', '事件'], ['goals', '目标']];   // 记忆为后台数据, 不显式展示

export default function AgentSidebar({ onAuthed, onQuery }) {
  const [user, setUser] = useState(null);
  const [checked, setChecked] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showCenter, setShowCenter] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem('agent_theme') === 'dark');
  const [recTab, setRecTab] = useState('journal');
  const [records, setRecords] = useState(null);   // null=未加载 / [] = 空
  const [recQ, setRecQ] = useState('');           // 记录搜索词
  const [hoverId, setHoverId] = useState(null);   // 悬停记录 id（显示删除按钮）
  const [detail, setDetail] = useState(null);     // {type, id} 打开的详情弹窗

  // 登录后加载当前 tab 的记录（搜索词变化时重新加载）
  useEffect(() => {
    if (!user) { setRecords(null); return; }
    setRecords(null);
    const timer = setTimeout(() => {
      fetch(`/api/agent/records?type=${recTab}&limit=100&q=${encodeURIComponent(recQ)}`, { credentials: 'include' })
        .then(r => r.json())
        .then(d => setRecords(d.records || []))
        .catch(() => setRecords([]));
    }, recQ ? 300 : 0);   // 搜索防抖
    return () => clearTimeout(timer);
  }, [user, recTab, recQ]);

  const deleteRecord = async (id) => {
    if (!confirm('确定删除这条记录？将从数据库连同记忆、向量一并清除，不可恢复。')) return;
    const d = await api(`/api/agent/records?type=${recTab}&id=${id}`, { method: 'DELETE' });
    if (d.ok) {
      setRecords(prev => (prev || []).filter(r => r.id !== id));
    }
  };

  // 目标标注完成（仅 goals tab）
  const markGoal = async (id, status) => {
    const d = await api('/api/agent/records', {
      method: 'PUT',
      body: JSON.stringify({ type: 'goals', id, status }),
    });
    if (d.ok) {
      setRecords(prev => (prev || []).map(r => r.id === id ? { ...r, status } : r));
    }
  };

  const STATUS_LABEL = { active: '进行中', achieved: '已完成', abandoned: '已放弃' };

  useEffect(() => {
    api('/api/agent/me').then(d => {
      if (d.username) setUser(d);
      setChecked(true);
    }).catch(() => setChecked(true));
  }, []);

  // 主题初始化（切换入口在用户中心）
  useEffect(() => { document.body.classList.toggle('dark-mode', dark); }, [dark]);

  const logout = async () => {
    await api('/api/auth/logout', { method: 'POST', body: '{}' });
    setUser(null);
    onAuthed?.();
  };

  return (
    <div style={{
      width: 216, flexShrink: 0, borderRight: '1px solid var(--border)',
      background: 'var(--bg)', display: 'flex', flexDirection: 'column', height: '100vh',
      position: 'sticky', top: 0, overflowY: 'auto',
    }}>
      <div style={{ padding: '18px 16px 10px', fontSize: 13, fontWeight: 700, letterSpacing: '1px', color: 'var(--text-dim)' }}>
        智能体广场
      </div>

      {/* 单 agent 卡片（PhiAgent 卡片式） */}
      <div style={{
        margin: '4px 10px', padding: '10px 12px', borderRadius: 10,
        border: '1px solid #d4d4d8', background: 'var(--soft)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--accent)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 15, color: 'var(--card-bg)' }}>
            {AGENT.name[0]}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{AGENT.name}</div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 1, lineHeight: 1.4,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {AGENT.subtitle}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.4 }}>
          {AGENT.tagline}
        </div>
      </div>

      {/* 我的记录（查询面板） */}
      {user && (
        <div style={{ marginTop: 8, borderTop: '1px solid var(--border)', padding: '10px 12px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '1px', color: 'var(--text-dim)', marginBottom: 6 }}>
            我的记录
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
            {RECORD_TABS.map(([k, label]) => (
              <button key={k} onClick={() => { setRecTab(k); setRecQ(''); }}
                style={{ flex: 1, padding: '4px 0', borderRadius: 6, cursor: 'pointer', fontSize: 11,
                         border: recTab === k ? '1px solid #d4d4d8' : '1px solid transparent',
                         background: recTab === k ? 'var(--soft)' : 'transparent',
                         color: recTab === k ? 'var(--text)' : 'var(--text-dim)' }}>
                {label}
              </button>
            ))}
          </div>
          <input value={recQ} onChange={e => setRecQ(e.target.value)}
            placeholder="搜索记录…"
            style={{ width: '100%', padding: '5px 9px', borderRadius: 6, marginBottom: 6, fontSize: 11,
                     border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text)',
                     outline: 'none', boxSizing: 'border-box' }} />
          <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
            {records === null ? (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: '6px 2px' }}>加载中…</div>
            ) : records.length === 0 ? (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: '6px 2px' }}>
                {recQ ? '无匹配记录' : '暂无记录'}
              </div>
            ) : records.map((r, i) => (
              <div key={i} onClick={() => setDetail({ type: recTab, id: r.id })}
                title="点击查看 AI 分析"
                onMouseEnter={() => setHoverId(String(r.id))}
                onMouseLeave={() => setHoverId(null)}
                style={{ position: 'relative', padding: '5px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 11,
                         background: hoverId === String(r.id) ? 'var(--soft)' : 'var(--card-bg)',
                         border: '1px solid var(--border)', color: 'var(--text-dim)', lineHeight: 1.4,
                         transition: 'background .15s' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 1, paddingRight: 18 }}>
                  {r.date}
                  {r.status ? ` · ${STATUS_LABEL[r.status] || r.status}` : ''}
                  {r.status === 'achieved' && <span style={{ color: '#5F8A6E', fontWeight: 700 }}> ✓</span>}
                  {r.importance ? ` · 重要 ${r.importance}` : ''}
                </div>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                              color: r.status === 'achieved' ? 'var(--text-dim)' : 'var(--text)',
                              textDecoration: r.status === 'achieved' ? 'line-through' : 'none' }}>
                  {r.title || r.content}
                </div>
                {hoverId === String(r.id) && (
                  <div style={{ position: 'absolute', top: 3, right: 3, display: 'flex', gap: 3 }}>
                    {recTab === 'goals' && r.status !== 'achieved' && (
                      <button onClick={e => { e.stopPropagation(); markGoal(r.id, 'achieved'); }}
                        title="标注完成"
                        style={{ width: 20, height: 20, borderRadius: 5,
                                 border: '1px solid rgba(95,138,110,.5)', background: 'var(--card-bg)', color: '#5F8A6E',
                                 cursor: 'pointer', fontSize: 11, lineHeight: 1, display: 'flex',
                                 alignItems: 'center', justifyContent: 'center' }}>
                        ✓
                      </button>
                    )}
                    <button onClick={e => { e.stopPropagation(); deleteRecord(r.id); }}
                      title="删除这条记录"
                      style={{ width: 20, height: 20, borderRadius: 5,
                               border: '1px solid #d8a0a0', background: 'var(--card-bg)', color: '#c0392b',
                               cursor: 'pointer', fontSize: 11, lineHeight: 1, display: 'flex',
                               alignItems: 'center', justifyContent: 'center' }}>
                      🗑
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 'auto', padding: '10px 12px', borderTop: '1px solid var(--border)' }}>
        {checked && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div onClick={() => setShowCenter(true)} title="用户中心"
              style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, cursor: 'pointer', minWidth: 0 }}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'var(--accent)', color: 'var(--bg)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, flexShrink: 0 }}>
                {user.username[0]}
              </div>
              <span style={{ fontSize: 13, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                {user.username}
              </span>
            </div>
            <button onClick={logout} title="退出"
              style={{ fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer', padding: '3px 8px',
                       borderRadius: 6, border: '1px solid var(--border)', background: 'var(--card-bg)' }}>
              退出
            </button>
          </div>
        ) : (
          <button onClick={() => setShowAuth(true)}
            style={{ width: '100%', padding: '8px 0', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                     border: 'none', background: 'var(--accent)', color: 'var(--bg)' }}>
            登录 / 注册
          </button>
        )}
        <div style={{ padding: '8px 4px 2px', fontSize: 10.5, color: 'var(--text-dim)', lineHeight: 1.5,
                      display: 'flex', justifyContent: 'space-between' }}>
          <span>独立账号 · 数据同主站</span>
          <a href="http://localhost:5000" target="_blank" rel="noreferrer"
            style={{ color: 'var(--text-dim)', textDecoration: 'underline' }}>主站</a>
        </div>
      </div>
      {showAuth && createPortal(
        <AuthModal onClose={() => setShowAuth(false)}
          onAuthed={(u) => { setUser(u); onAuthed?.(); }} />, document.body)}
      {showCenter && createPortal(
        <UserCenterModal onClose={() => setShowCenter(false)}
          onLogout={() => { setUser(null); onAuthed?.(); }} />, document.body)}
      {detail && createPortal(
        <RecordDetailModal type={detail.type} id={detail.id}
          onClose={() => setDetail(null)} />, document.body)}
    </div>
  );
}
