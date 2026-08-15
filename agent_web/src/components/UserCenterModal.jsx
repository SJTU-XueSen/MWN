import { useEffect, useState } from 'react';
import { api } from '../api';

/**
 * UserCenterModal — Manus 式用户中心（PhiAgent 同款四区）
 * 通用（主题/通知）/ 账户（资料/改密/注销）/ 个性化（昵称/专业/学校/简介/技能）/ 数据（记录删除管理）
 */
export default function UserCenterModal({ onClose, onLogout }) {
  const [section, setSection] = useState('secGeneral');
  const [profile, setProfile] = useState({});
  const [notice, setNotice] = useState('');
  const [dark, setDark] = useState(() => document.body.classList.contains('dark-mode'));
  const [notifEnabled, setNotifEnabled] = useState(false);

  useEffect(() => {
    api('/api/agent/me').then(d => d.username && setProfile(d));
    setNotifEnabled(Notification?.permission === 'granted');
  }, []);

  const flash = (msg) => { setNotice(msg); setTimeout(() => setNotice(''), 2500); };

  const toggleTheme = (v) => {
    const next = v === 'dark';
    setDark(next);
    document.body.classList.toggle('dark-mode', next);
    localStorage.setItem('agent_theme', next ? 'dark' : 'light');
  };

  const saveProfile = async () => {
    const d = await api('/api/agent/profile', {
      method: 'PUT',
      body: JSON.stringify({
        real_name: profile.real_name || null, major: profile.major || null,
        university: profile.university || null, bio: profile.bio || null,
        skill_tags: profile.skill_tags || null,
      }),
    });
    flash(d.ok ? '已保存' : (d.error || '保存失败'));
  };

  const changePassword = async () => {
    const oldP = prompt('输入当前密码');
    if (!oldP) return;
    const newP = prompt('输入新密码（≥8 字符）');
    if (!newP || newP.length < 8) { flash('新密码至少 8 字符'); return; }
    const d = await api('/api/agent/change-password', {
      method: 'POST', body: JSON.stringify({ old_password: oldP, new_password: newP }),
    });
    flash(d.ok ? '密码已更新' : (d.error || '修改失败'));
  };

  const deleteRecords = async (type, label) => {
    if (!confirm(`确定删除全部${label}？将从数据库连同记忆、向量一并清除，不可恢复。`)) return;
    const d = await api(`/api/agent/records?type=${type}&all=1`, { method: 'DELETE' });
    flash(d.ok ? `已删除 ${d.deleted ?? 0} 条${label}` : (d.error || '删除失败'));
  };

  const clearChat = async () => {
    if (!confirm('确定清空全部对话历史？')) return;
    const d = await api('/api/agent/chat/clear', { method: 'DELETE' });
    flash(d.ok ? '对话历史已清空' : '清除失败');
    window.location.reload();
  };

  const deleteAccount = async () => {
    if (!confirm('确定删除账户及全部数据（日记/事件/目标/记忆/向量/对话）？此操作不可撤销！')) return;
    const d = await api('/api/agent/account', { method: 'DELETE' });
    if (d.ok) { onLogout?.(); window.location.reload(); }
    else flash(d.error || '删除失败');
  };

  const requestNotif = async () => {
    if (!('Notification' in window)) { flash('浏览器不支持通知'); return; }
    const perm = await Notification.requestPermission();
    setNotifEnabled(perm === 'granted');
    flash(perm === 'granted' ? '通知已开启' : '通知被拒绝');
  };

  const SECTIONS = [['secGeneral', '通用'], ['secAccount', '账户'], ['secPersonal', '个性化'], ['secData', '数据']];
  const inputStyle = { width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border)',
                       fontSize: 13, outline: 'none', marginBottom: 10, boxSizing: 'border-box',
                       background: 'var(--card-bg)', color: 'var(--text)' };
  const btnStyle = { padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border)', cursor: 'pointer',
                     fontSize: 13, background: 'var(--accent)', color: 'var(--bg)' };

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.35)', zIndex: 1300,
                                   display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: 'var(--bg)', borderRadius: 16, width: '100%', maxWidth: 940, height: '84vh',
                 display: 'flex', overflow: 'hidden', boxShadow: '0 24px 80px rgba(0,0,0,.28)' }}>
        {/* 左导航 */}
        <div style={{ width: 190, flexShrink: 0, borderRight: '1px solid var(--border)', padding: '24px 14px',
                      display: 'flex', flexDirection: 'column', gap: 3 }}>
          <div style={{ padding: '0 12px 16px', fontSize: 15, fontWeight: 700 }}>设置</div>
          {SECTIONS.map(([k, label]) => (
            <button key={k} onClick={() => setSection(k)}
              style={{ textAlign: 'left', padding: '11px 14px', borderRadius: 9, cursor: 'pointer', fontSize: 13.5,
                       border: 'none', background: section === k ? 'var(--soft)' : 'transparent',
                       color: section === k ? 'var(--text)' : 'var(--text-dim)', fontWeight: section === k ? 600 : 400 }}>
              {label}
            </button>
          ))}
          <div style={{ marginTop: 'auto' }}>
            <button onClick={onClose} style={{ width: '100%', padding: '10px 0', borderRadius: 9, cursor: 'pointer',
                                               fontSize: 13, border: 'none', color: 'var(--text-dim)', background: 'transparent' }}>
              ← 返回
            </button>
          </div>
        </div>
        {/* 内容区 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 40px' }}>
          {notice && <div style={{ marginBottom: 10, padding: '7px 12px', borderRadius: 8, fontSize: 12,
                                  background: '#f0f7f0', border: '1px solid #cde5cd', color: '#2c662d' }}>{notice}</div>}

          {section === 'secGeneral' && (
            <>
              <h3 style={{ fontSize: 15, margin: '0 0 6px' }}>外观</h3>
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 10 }}>主题</div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 22 }}>
                {[['light', '浅色'], ['dark', '深色']].map(([v, label]) => (
                  <button key={v} onClick={() => toggleTheme(v)}
                    style={{ padding: '7px 18px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                             border: (v === 'dark') === dark ? '1px solid var(--accent)' : '1px solid var(--border)',
                             background: (v === 'dark') === dark ? 'var(--soft)' : 'var(--bg)',
                             color: (v === 'dark') === dark ? 'var(--text)' : 'var(--text-dim)' }}>
                    {label}
                  </button>
                ))}
              </div>
              <h3 style={{ fontSize: 15, margin: '0 0 6px' }}>通知</h3>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13 }}>回答完成通知</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>回答完成时收到浏览器通知</div>
                </div>
                <button onClick={requestNotif}
                  style={{ width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
                           background: notifEnabled ? 'var(--accent)' : 'var(--border)', position: 'relative' }}>
                  <span style={{ position: 'absolute', top: 3, left: notifEnabled ? 24 : 3, width: 18, height: 18,
                                 borderRadius: '50%', background: 'var(--card-bg)', transition: 'left .15s' }} />
                </button>
              </div>
            </>
          )}

          {section === 'secAccount' && (
            <>
              <h3 style={{ fontSize: 15, margin: '0 0 14px' }}>账户</h3>
              <Row label="用户名"><b>{profile.username}</b></Row>
              <Row label="邮箱">{profile.email || '—'}</Row>
              <Row label="会话">登录后跨设备同步</Row>
              <div style={{ marginTop: 18, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button onClick={changePassword} style={btnStyle}>更新密码</button>
                <button onClick={deleteAccount}
                  style={{ padding: '6px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                           border: '1px solid #d8a0a0', background: 'var(--card-bg)', color: '#c0392b' }}>
                  删除账户
                </button>
              </div>
            </>
          )}

          {section === 'secPersonal' && (
            <>
              <h3 style={{ fontSize: 15, margin: '0 0 14px' }}>个性化（Agent 据此定制回答）</h3>
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 4 }}>昵称</div>
              <input value={profile.real_name || ''} onChange={e => setProfile({ ...profile, real_name: e.target.value })}
                placeholder="你的昵称" style={inputStyle} />
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 4 }}>专业</div>
              <input value={profile.major || ''} onChange={e => setProfile({ ...profile, major: e.target.value })}
                placeholder="如: 人工智能" style={inputStyle} />
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 4 }}>学校</div>
              <input value={profile.university || ''} onChange={e => setProfile({ ...profile, university: e.target.value })}
                placeholder="如: 上海交通大学" style={inputStyle} />
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 4 }}>简介</div>
              <textarea value={profile.bio || ''} onChange={e => setProfile({ ...profile, bio: e.target.value })}
                placeholder="兴趣、背景、关注的问题…" rows={3} style={inputStyle} />
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 4 }}>技能标签（逗号分隔）</div>
              <input value={(profile.skill_tags || []).join(', ')}
                onChange={e => setProfile({ ...profile, skill_tags: e.target.value.split(/[,，]/).map(s => s.trim()).filter(Boolean) })}
                placeholder="Python, 算法, 机器人" style={inputStyle} />
              <button onClick={saveProfile} style={btnStyle}>保存</button>
            </>
          )}

          {section === 'secData' && (
            <>
              <h3 style={{ fontSize: 15, margin: '0 0 14px' }}>数据管理</h3>
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 10 }}>
                删除将从数据库彻底清除（含提炼的记忆与向量，不可恢复）
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                {[['journal', '日记'], ['events', '事件'], ['goals', '目标'], ['memories', '记忆'], ['all', '全部记录']].map(([t, label]) => (
                  <div key={t} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                       padding: '9px 12px', borderRadius: 8, border: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13 }}>删除{label}</span>
                    <button onClick={() => deleteRecords(t, label)}
                      style={{ padding: '5px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                               border: '1px solid #d8a0a0', background: 'var(--card-bg)', color: '#c0392b' }}>
                      清除
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                           padding: '9px 12px', borderRadius: 8, border: '1px solid var(--border)' }}>
                <span style={{ fontSize: 13 }}>清空对话历史</span>
                <button onClick={clearChat}
                  style={{ padding: '5px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                           border: '1px solid #d8a0a0', background: 'var(--card-bg)', color: '#c0392b' }}>
                  清除
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--border)',
                  fontSize: 13 }}>
      <span style={{ color: 'var(--text-dim)' }}>{label}</span>
      <span>{children}</span>
    </div>
  );
}
