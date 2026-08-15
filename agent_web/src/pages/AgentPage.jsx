import { useState, useRef, useEffect } from 'react';
import Icon from '../components/Icon';
import { renderMarkdown } from '../utils/markdown';

/**
 * AgentPage — 智能体对话页（PhiAgent 同款视觉）
 * Claude Code 风格: 思考流（折叠联动）→ 工具卡片（调用中→完成）→ 回答打字机 → 建议按钮
 * SSE 协议与 PhiAgent 一致: status/thought_stream/thought/tool_start/tool/token/done/error
 */

/* 工具图标 + 能力分组（工具不暴露为技术名词, 而是"能力"） */
const TOOL_META = {
  memory_search: { icon: 'icon-search', group: '🧠 记忆', label: '回忆你的经历' },
  current_persona: { icon: 'icon-brain', group: '🪞 洞察', label: '看清人格画像' },
  recent_events: { icon: 'icon-calendar', group: '🪞 洞察', label: '回顾人生事件' },
  recent_journals: { icon: 'icon-clipboard', group: '🪞 洞察', label: '翻阅日记记录' },
  life_goals: { icon: 'icon-target', group: '🪞 洞察', label: '查看人生目标' },
  interest_tracks: { icon: 'icon-calc', group: '🪞 洞察', label: '追踪兴趣变化' },
  future_paths: { icon: 'icon-sparkles', group: '🌌 推演', label: '已有未来路径' },
  growth_report: { icon: 'icon-scroll', group: '🪞 洞察', label: '成长报告' },
  evidence_chain: { icon: 'icon-link', group: '🪞 洞察', label: '证据链' },
  future_simulation: { icon: 'icon-rocket', group: '🌌 推演', label: '推演另一条时间线' },
  activity_search: { icon: 'icon-search', group: '🌍 连接', label: '匹配机会' },
  web_search: { icon: 'icon-sun', group: '🌍 连接', label: '联网检索' },
  team_context: { icon: 'icon-handshake', group: '🌍 连接', label: '战队实况' },
  ancient_wisdom: { icon: 'icon-scroll', group: '📜 古语', label: '古语回响' },
  record_entry: { icon: 'icon-writing', group: '✍️ 记录', label: '记录经历' },
  create_goal: { icon: 'icon-target', group: '✍️ 记录', label: '设定目标' },
  update_goal: { icon: 'icon-refresh', group: '✍️ 记录', label: '更新目标' },
  regenerate_persona: { icon: 'icon-brain', group: '🪞 洞察', label: '刷新画像' },
  create_task: { icon: 'icon-clipboard', group: '✍️ 记录', label: '拆解任务' },
  future_chat: { icon: 'icon-sparkles', group: '🌌 推演', label: '与未来的我对话' },
};

/* ── 工具调用卡片（PhiAgent 同款: 序号 + PNG 图标 + 展开） ── */
/* 联网类工具结果 → 可点击直链列表 */
function parseResultLinks(resultSummary) {
  try {
    const d = JSON.parse(resultSummary);
    const arr = d.results || d.recommendations || [];
    return arr.filter(r => r && (r.url || r.link)).map(r => ({
      title: r.title || r.name || '',
      url: r.url || r.link || '',
      snippet: r.snippet || r.description || r.reason || '',
    }));
  } catch { return []; }
}

function ToolCard({ tc, index }) {
  const [open, setOpen] = useState(false);
  const meta = TOOL_META[tc.name] || { icon: 'icon-cog', label: tc.name };
  const links = (tc.name === 'web_search' || tc.name === 'activity_search') ? parseResultLinks(tc.result_summary) : [];
  return (
    <div style={{ margin: '4px 0' }}>
      {tc.thought && (
        <div style={{ fontSize: 12.5, color: 'var(--text-dim)', fontStyle: 'italic',
                      padding: '2px 4px 4px', lineHeight: 1.6 }}>
          {tc.thought}
        </div>
      )}
      <div style={{ border: '1px solid var(--border)', borderRadius: 8,
                    background: 'var(--card-bg)', overflow: 'hidden' }}>
        <div onClick={() => setOpen(!open)}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                   cursor: 'pointer', userSelect: 'none' }}>
          <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'monospace', minWidth: 22 }}>
            {String(index + 1).padStart(2, '0')}
          </span>
          <Icon name={meta.icon} size={16} />
          <span style={{ fontSize: 10.5, color: 'var(--text-dim)', background: 'var(--soft)',
                         padding: '2px 6px', borderRadius: 5, flexShrink: 0 }}>
            {meta.group}
          </span>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{meta.label}</span>
          <span style={{ flex: 1 }} />
          <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'monospace' }}>
            {Object.values(tc.args || {}).filter(v => typeof v === 'string').join(' ').slice(0, 40) || '—'}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-dim)', transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}>▶</span>
        </div>
        {open && (
          <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)', fontSize: 12 }}>
            <div style={{ color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'monospace' }}>
              {JSON.stringify(tc.args, null, 2)}
            </div>
            {links.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {links.map((l, i) => (
                  <div key={i} style={{ padding: '6px 9px', borderRadius: 7, background: 'var(--soft)',
                                        border: '1px solid var(--border)' }}>
                    <a href={l.url} target="_blank" rel="noreferrer"
                      style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--accent)',
                               textDecoration: 'underline', display: 'block', marginBottom: 2 }}>
                      {l.title || l.url}
                    </a>
                    {l.snippet && (
                      <div style={{ fontSize: 11.5, color: 'var(--text-dim)', lineHeight: 1.5 }}>
                        {l.snippet}
                      </div>
                    )}
                    <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 2,
                                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      🔗 {l.url}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim)', whiteSpace: 'pre-wrap', maxHeight: 160, overflow: 'auto' }}>
                {tc.result_summary}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── 对话页签 ── */
function ChatTab({ agent = 'mentor', questions = [], pendingQuery, onQueryConsumed }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [thoughtsOpen, setThoughtsOpen] = useState(true);
  const [notLoggedIn, setNotLoggedIn] = useState(false);
  const [mirror, setMirror] = useState(null);      // 今日镜像（主动观察）
  const [mirrorAnswer, setMirrorAnswer] = useState('');
  const bottomRef = useRef(null);
  const abortRef = useRef(null);
  const inputRef = useRef(null);

  // 登录后: 拉取对话历史（刷新恢复）+ 今日镜像（主动观察）
  useEffect(() => {
    fetch('/api/agent/me', { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (!d.username) return;
        fetch(`/api/agent/chat/history?agent=${agent}&limit=50`, { credentials: 'include' })
          .then(r => r.json())
          .then(h => {
            if (h.history?.length) {
              setMessages(h.history.map(m => ({ role: m.role, content: m.content })));
            }
          }).catch(() => {});
        fetch('/api/agent/daily_mirror', { credentials: 'include' })
          .then(r => r.json())
          .then(m => m.observations && setMirror(m))
          .catch(() => {});
      }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 侧边栏"我的记录"点击 → 自动发送查询
  useEffect(() => {
    if (pendingQuery) {
      send(pendingQuery);
      onQueryConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingQuery]);

  // 每日一问: 用户回答 → 自动记录
  const submitMirrorAnswer = () => {
    const a = mirrorAnswer.trim();
    if (!a || loading) return;
    setMirrorAnswer('');
    send(`（今日一问）${mirror.daily_question}\n我的回答：${a}`);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    const nodes = document.querySelectorAll('.mermaid:not([data-processed])');
    if (nodes.length) {
      import('mermaid').then((mod) => {
        const mermaid = mod.default || mod;
        mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
        return mermaid.run({ nodes });
      }).catch(() => {});
    }
  }, [messages, loading]);

  const send = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || loading) return;
    setInput('');
    const history = messages.slice(-20).map(m => ({ role: m.role, content: m.content }));
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    setNotLoggedIn(false);
    // 持久化用户消息（刷新恢复用）
    fetch('/api/agent/chat/save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
      body: JSON.stringify({ agent, role: 'user', content: text }),
    }).catch(() => {});
    const controller = new AbortController();
    abortRef.current = controller;
    const msgId = Date.now();
    let finalContent = '';
    setMessages(prev => [...prev, { role: 'assistant', content: '', events: [], msgId, streaming: true }]);
    try {
      const resp = await fetch('/api/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history, agent }),
        credentials: 'include',
        signal: controller.signal,
      });
      if (resp.status === 401) {
        setNotLoggedIn(true);
        setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, content: '请先在主站登录后刷新本页', streaming: false } : m));
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      const handleEvent = (evt) => {
        if (evt.type === 'status') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, status: evt.content } : m));
        } else if (evt.type === 'thought') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, curThought: null,
            events: [...m.events, { t: 'thought', text: evt.content }],
          } : m));
        } else if (evt.type === 'thought_stream') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, curThought: (m.curThought || '') + evt.content } : m));
        } else if (evt.type === 'tool_start') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, curThought: null,
            events: [...m.events,
                     ...(m.curThought ? [{ t: 'thought', text: m.curThought }] : []),
                     { t: 'tool_start', name: evt.name }],
          } : m));
        } else if (evt.type === 'tool') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, curThought: null,
            events: m.events.map(ev =>
              ev.t === 'tool_start' && ev.name === evt.name ? { t: 'tool', tc: { name: evt.name, args: evt.args, result_summary: evt.result, thought: evt.thought } } : ev),
          } : m));
        } else if (evt.type === 'token') {
          finalContent += evt.content;
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, content: m.content + evt.content,
            events: m.curThought ? [...m.events, { t: 'thought', text: m.curThought }] : m.events,
            curThought: null,
          } : m));
        } else if (evt.type === 'done') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, reasoningSummary: evt.reasoning_summary || null,
            suggestions: evt.suggestions || [],
            safety: evt.safety || null,
            content: evt.safety === 'blocked' && evt.safety_reply ? evt.safety_reply : m.content,
            events: m.curThought ? [...m.events, { t: 'thought', text: m.curThought }] : m.events,
            curThought: null, streaming: false,
          } : m));
        } else if (evt.type === 'error') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, content: evt.content, streaming: false } : m));
        }
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const raw = buf.slice(0, idx); buf = buf.slice(idx + 2);
          if (!raw.startsWith('data: ')) continue;
          try { handleEvent(JSON.parse(raw.slice(6))); } catch (e) { /* 忽略坏事件 */ }
        }
      }
      setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, streaming: false } : m));
    } catch (e) {
      if (e.name === 'AbortError') {
        setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, streaming: false } : m));
      } else {
        setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, content: `请求失败: ${e.message}`, streaming: false } : m));
      }
    }
    abortRef.current = null;
    setLoading(false);
    // 持久化回答（刷新恢复用）
    if (finalContent) {
      fetch('/api/agent/chat/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ agent, role: 'assistant', content: finalContent }),
      }).catch(() => {});
    }
  };

  const stopGenerating = () => abortRef.current?.abort();

  const cleanContent = (text) => (text || '')
    .replace(/<tool_calls>[\s\S]*?<\/tool_calls>/g, '')
    .replace(/<invoke name="[^"]+">[\s\S]*?<\/invoke>/g, '')
    .replace(/\{TOOL:[\s\S]*?\}/g, '');

  const renderContent = (m) => {
    if (m.role === 'user') return <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{m.content}</div>;
    return (
      <div>
        {m.reasoningSummary && (
          <div style={{ marginBottom: 10, padding: '8px 12px', borderRadius: 8,
                        background: 'var(--soft)', border: '1px solid var(--border)', fontSize: 12.5 }}>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5, letterSpacing: '.5px' }}>
              ✦ 推理摘要
            </div>
            {m.reasoningSummary.split('\n').filter(Boolean).map((s, i) => (
              <div key={i} style={{ margin: '2px 0', lineHeight: 1.6, color: 'var(--text-dim)' }}>{s}</div>
            ))}
          </div>
        )}
        {m.safety === 'warning' && (
          <div style={{ marginBottom: 10, padding: '8px 12px', borderRadius: 8, fontSize: 12,
                        background: '#fdf6e3', border: '1px solid #e8d9a0', color: '#8a6d1a' }}>
            ⚠ 该回答涉及敏感内容，请以批判性思考对待。
          </div>
        )}
        {m.events?.map((ev, i) => ev.t === 'thought' ? (
          <details key={i} open={thoughtsOpen}
            onClick={(e) => { e.preventDefault(); setThoughtsOpen(!thoughtsOpen); }}
            style={{ margin: '4px 0', fontSize: 12.5 }}>
            <summary style={{ color: 'var(--text-dim)', cursor: 'pointer', fontStyle: 'italic',
                              borderLeft: '2px solid var(--border)', paddingLeft: 10,
                              padding: '2px 0', userSelect: 'none' }}>
              {thoughtsOpen ? '▾ 思考过程' : '▸ 思考过程'}
            </summary>
            <div style={{ fontSize: 12.5, color: 'var(--text-dim)', fontStyle: 'italic',
                          padding: '4px 2px', margin: '2px 0', lineHeight: 1.7,
                          borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
              {renderMarkdown(cleanContent(ev.text))}
            </div>
          </details>
        ) : ev.t === 'tool_start' ? (
          <div key={i} style={{ margin: '6px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                          border: '1px solid var(--border)', borderRadius: 8, background: 'var(--card-bg)',
                          fontSize: 13, color: 'var(--text-dim)' }}>
              <span style={{ width: 13, height: 13, borderRadius: '50%', border: '2px solid var(--border)',
                             borderTopColor: 'var(--accent)', animation: 'spin 0.8s linear infinite' }} />
              {(TOOL_META[ev.name]?.group || '') && TOOL_META[ev.name].group + ' · '}
              {TOOL_META[ev.name]?.label || ev.name}…
            </div>
          </div>
        ) : (
          <div key={i} style={{ margin: '6px 0' }}>
            <ToolCard tc={ev.tc} index={i} />
          </div>
        ))}
        {m.streaming && !m.curThought && !m.content && !m.events?.length && m.status && (
          <div style={{ fontSize: 12.5, color: 'var(--text-dim)', fontStyle: 'italic',
                        padding: '4px 2px', marginBottom: 6, lineHeight: 1.7, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 13, height: 13, borderRadius: '50%', border: '2px solid var(--border)',
                           borderTopColor: 'var(--accent)', animation: 'spin 0.8s linear infinite' }} />
            {m.status}…
          </div>
        )}
        {m.curThought && (
          <div style={{ fontSize: 12.5, color: 'var(--text-dim)', fontStyle: 'italic',
                        padding: '4px 2px', marginBottom: 6, lineHeight: 1.7,
                        borderLeft: '2px solid var(--border)', paddingLeft: 10, whiteSpace: 'pre-wrap' }}>
            {renderMarkdown(cleanContent(m.curThought))}
            <span style={{ display: 'inline-block', width: 6, height: 14, marginLeft: 3,
                           background: 'var(--accent)', animation: 'pulse 1s infinite', verticalAlign: 'middle' }} />
          </div>
        )}
        <div style={{ lineHeight: 1.8, fontSize: 14 }}>
          {renderMarkdown(cleanContent(m.content))}
          {m.streaming && !m.curThought && m.content && (
            <span style={{ display: 'inline-block', width: 6, height: 14, marginLeft: 3,
                           background: 'var(--accent)', animation: 'pulse 1s infinite', verticalAlign: 'middle' }} />
          )}
        </div>
        {m.suggestions?.length > 0 && !m.streaming && (
          <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>可继续探索</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {m.suggestions.map((s, i) => (
                <button key={i} onClick={() => send(s)}
                  style={{ textAlign: 'left', padding: '7px 12px', borderRadius: 8, cursor: 'pointer',
                           background: 'var(--soft)', border: '1px solid var(--border)', fontSize: 13,
                           color: 'var(--text)', transition: 'background .15s' }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {notLoggedIn && (
          <div style={{ margin: '20px auto', padding: '14px 20px', borderRadius: 10, fontSize: 13,
                        background: 'var(--soft)', border: '1px solid var(--border)' }}>
            未登录。请先在<a href="http://localhost:5000" target="_blank" rel="noreferrer"
              style={{ color: 'var(--accent)' }}>主站登录</a>，然后刷新本页即可使用智能体。
          </div>
        )}

        {/* 🪞 今日镜像（主动观察） */}
        {mirror && (
          <div style={{ padding: '18px 20px', borderRadius: 14, border: '1px solid var(--border)',
                        background: 'var(--card-bg)', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Icon name="icon-brain" size={18} />
              <span style={{ fontSize: 14, fontWeight: 700 }}>今日镜像</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {mirror.name ? `${mirror.name}，` : ''}过去 7 天 · {mirror.stats?.journals_7d ?? 0} 条记录 · {mirror.stats?.events_7d ?? 0} 个事件
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 10 }}>
              {mirror.observations?.map((o, i) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
                  {i === 0 ? '📚 ' : i === 1 ? '⚡ ' : '🔍 '}{o}
                </div>
              ))}
            </div>
            {mirror.suggestion && (
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', padding: '8px 12px', borderRadius: 8,
                            background: 'var(--soft)', marginBottom: 10, lineHeight: 1.6 }}>
                💡 今天：{mirror.suggestion}
              </div>
            )}
            <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 6, lineHeight: 1.6 }}>
              🎯 每日一问：{mirror.daily_question}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <input value={mirrorAnswer} onChange={e => setMirrorAnswer(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && submitMirrorAnswer()}
                placeholder="回答它（会自动记录为今天的经历）"
                style={{ flex: 1, padding: '7px 12px', borderRadius: 18, border: '1px solid var(--border)',
                         background: 'var(--soft)', fontSize: 13, outline: 'none', color: 'var(--text)' }} />
              <button onClick={submitMirrorAnswer} disabled={!mirrorAnswer.trim()}
                style={{ padding: '7px 16px', borderRadius: 18, cursor: 'pointer', fontSize: 13,
                         border: 'none', background: 'var(--accent)', color: 'var(--bg)',
                         opacity: !mirrorAnswer.trim() ? 0.4 : 1 }}>
                记录
              </button>
            </div>
          </div>
        )}

        {/* 🌱 三入口（人生入口: 镜 → 界 → 联） */}
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '20px 0 8px', fontSize: 14 }}>
            <div style={{ fontSize: 15, color: 'var(--text-dim)', marginBottom: 16 }}>
              🪞 今天，你想看看什么？
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              {[
                { icon: '🌱', title: '看见自己', sub: '最近的我，好像变了吗？',
                  q: '帮我看看最近的我有什么变化？结合我的记录、事件和人格画像。' },
                { icon: '🌌', title: '看见未来', sub: '如果继续这样走，会成为怎样的人？',
                  q: '如果继续这样走下去，我会成为怎样的人？帮我推演并给出当下可行的步骤。' },
                { icon: '🌍', title: '连接世界', sub: '世界上有什么正在回应现在的我？',
                  q: '世界上有哪些机会正在回应现在的我？结合我的画像推荐活动、比赛或伙伴。' },
              ].map((e, i) => (
                <button key={i} onClick={() => send(e.q)}
                  style={{ width: 190, padding: '16px 14px', borderRadius: 12, cursor: 'pointer',
                           border: '1px solid var(--border)', background: 'var(--card-bg)',
                           transition: 'all .15s', textAlign: 'center' }}
                  onMouseEnter={ev => { ev.currentTarget.style.borderColor = '#d4d4d8'; ev.currentTarget.style.background = 'var(--soft)'; }}
                  onMouseLeave={ev => { ev.currentTarget.style.borderColor = 'var(--border)'; ev.currentTarget.style.background = 'var(--card-bg)'; }}>
                  <div style={{ fontSize: 26, marginBottom: 6 }}>{e.icon}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 3 }}>{e.title}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-dim)', lineHeight: 1.5 }}>{e.sub}</div>
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: m.role === 'user' ? '92%' : '100%',
            background: m.role === 'user' ? 'var(--soft)' : 'transparent',
            border: 'none',
            borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : 0,
            padding: m.role === 'user' ? '10px 14px' : '2px 0',
            fontSize: 15, lineHeight: 1.75,
          }}>
            {renderContent(m)}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div style={{ position: 'fixed', bottom: 0, left: 224, right: 0, padding: '8px 20px 20px',
                    background: 'linear-gradient(transparent, var(--bg) 40%)' }}>
        <div style={{ maxWidth: 760, margin: '0 auto 6px', display: 'flex', gap: 6 }}>
          <button onClick={() => { inputRef.current?.focus(); }}
            style={{ padding: '5px 12px', borderRadius: 14, cursor: 'pointer', fontSize: 12,
                     border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text-dim)' }}>
            ✍️ 记录今天
          </button>
          <button onClick={() => send('帮我看看最近的我有什么变化？')}
            style={{ padding: '5px 12px', borderRadius: 14, cursor: 'pointer', fontSize: 12,
                     border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text-dim)' }}>
            🪞 看看自己
          </button>
          <span style={{ fontSize: 10.5, color: 'var(--text-dim)', alignSelf: 'center', marginLeft: 4 }}>
            说"今天……"即自动记录，或明确说"帮我记录"
          </span>
        </div>
        <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 4,
                      background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 26,
                      padding: '6px 6px 6px 16px', boxShadow: '0 2px 12px var(--ring)' }}>
          <input ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="问一个关于你的问题…"
            style={{ flex: 1, border: 'none', background: 'transparent', fontSize: 15, outline: 'none', color: 'var(--text)' }}
          />
          {loading ? (
            <button onClick={stopGenerating}
              style={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid var(--border)', cursor: 'pointer', flexShrink: 0,
                       background: 'var(--soft)', color: 'var(--accent)', fontSize: 12,
                       display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              ■
            </button>
          ) : (
            <button onClick={() => send()} disabled={!input.trim()}
              style={{ width: 36, height: 36, borderRadius: '50%', border: 'none', cursor: 'pointer', flexShrink: 0,
                       background: 'var(--accent)', color: 'var(--bg)', fontSize: 15,
                       display: 'flex', alignItems: 'center', justifyContent: 'center',
                       opacity: !input.trim() ? 0.4 : 1, transition: 'opacity .15s' }}>
              ↑
            </button>
          )}
        </div>
      </div>
    </>
  );
}

/* ── 主页面（单全能 agent） ── */
const QUESTIONS = [
  '根据我的记录，我现在是什么状态？',
  '帮我记录今天：参加了机器人社团的技术分享',
  '我五年后会是什么样的人？',
  '帮我们战队拆解一下最近的比赛任务',
];

export default function AgentPage({ pendingQuery, onQueryConsumed }) {
  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '16px 20px 140px', minHeight: '70vh' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
        <h1 style={{ fontSize: 22, margin: 0 }}>镜界导师</h1>
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>全能成长伙伴 · 记录 / 看见 / 预见 / 共创，全部对话完成</span>
      </div>
      <ChatTab agent="mentor" questions={QUESTIONS}
        pendingQuery={pendingQuery} onQueryConsumed={onQueryConsumed} />
    </div>
  );
}
