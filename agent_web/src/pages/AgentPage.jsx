import { useState, useRef, useEffect } from 'react';
import Icon from '../components/Icon';
import { renderMarkdown } from '../utils/markdown';

/**
 * AgentPage — 智能体对话页（ZCode / DeepSeek Harness 工作台风格）
 * 扁平行式消息流（非气泡）· 统一思考折叠 · 工具时间线 · 自适应输入坞
 * SSE 协议: status/thought_stream/thought/tool_start/tool/token/done/error
 */

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

/* ── 工具时间线节点（ZCode 式: 状态点 + 连接线 + 可展开） ── */
function ToolNode({ tc, index, last }) {
  const [open, setOpen] = useState(false);
  const meta = TOOL_META[tc.name] || { icon: 'icon-cog', label: tc.name, group: '' };
  const links = (tc.name === 'web_search' || tc.name === 'activity_search') ? parseResultLinks(tc.result_summary) : [];
  const failed = (() => { try { return JSON.parse(tc.result_summary)?.error; } catch { return false; } })();
  return (
    <div style={{ position: 'relative', paddingLeft: 22 }}>
      {/* 时间线轴 */}
      {!last && <div style={{ position: 'absolute', left: 6, top: 18, bottom: -6, width: 1.5, background: 'var(--border)' }} />}
      <div style={{ position: 'absolute', left: 0, top: 4, width: 13, height: 13, borderRadius: '50%',
                    background: failed ? '#c0392b' : 'var(--card-bg)', border: `3px solid ${failed ? '#c0392b' : 'var(--accent)'}`,
                    boxSizing: 'border-box' }} />
      <div style={{ border: '1px solid var(--border)', borderRadius: 9, background: 'var(--card-bg)',
                    overflow: 'hidden', marginBottom: 6 }}>
        <div onClick={() => setOpen(!open)}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 11px', cursor: 'pointer', userSelect: 'none' }}>
          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'ui-monospace, monospace', minWidth: 18 }}>
            {String(index + 1).padStart(2, '0')}
          </span>
          <Icon name={meta.icon} size={15} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>{meta.label}</span>
          <span style={{ fontSize: 10.5, color: 'var(--text-dim)', background: 'var(--soft)',
                         padding: '2px 6px', borderRadius: 5, flexShrink: 0 }}>{meta.group}</span>
          <span style={{ flex: 1, minWidth: 0, fontSize: 11.5, color: 'var(--text-dim)', fontFamily: 'ui-monospace, monospace',
                         overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {Object.values(tc.args || {}).filter(v => typeof v === 'string').join(' ').slice(0, 44) || ''}
          </span>
          {failed && <span style={{ fontSize: 10.5, color: '#c0392b', flexShrink: 0 }}>⚠</span>}
          <span style={{ fontSize: 10, color: 'var(--text-dim)', transform: open ? 'rotate(90deg)' : 'none',
                         transition: 'transform .15s', flexShrink: 0 }}>▶</span>
        </div>
        {open && (
          <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)', fontSize: 12 }}>
            <div style={{ color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'ui-monospace, monospace' }}>
              {JSON.stringify(tc.args, null, 2)}
            </div>
            {links.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {links.map((l, i) => (
                  <div key={i} style={{ padding: '6px 9px', borderRadius: 7, background: 'var(--soft)', border: '1px solid var(--border)' }}>
                    <a href={l.url} target="_blank" rel="noreferrer"
                      style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--accent)', textDecoration: 'underline', display: 'block', marginBottom: 2 }}>
                      {l.title || l.url}
                    </a>
                    {l.snippet && <div style={{ fontSize: 11.5, color: 'var(--text-dim)', lineHeight: 1.5 }}>{l.snippet}</div>}
                    <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>🔗 {l.url}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim)', whiteSpace: 'pre-wrap', maxHeight: 180, overflow: 'auto' }}>{tc.result_summary}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── 运行中的工具节点（spinner） ── */
function ToolRunning({ name }) {
  const meta = TOOL_META[name] || { icon: 'icon-cog', label: name, group: '' };
  return (
    <div style={{ position: 'relative', paddingLeft: 22, marginBottom: 6 }}>
      <div style={{ position: 'absolute', left: 0, top: 5, width: 14, height: 14 }}>
        <span style={{ display: 'block', width: 14, height: 14, borderRadius: '50%', border: '2.5px solid var(--border)',
                       borderTopColor: 'var(--accent)', animation: 'spin 0.8s linear infinite', boxSizing: 'border-box' }} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 11px',
                    border: '1px dashed var(--border)', borderRadius: 9, fontSize: 13, color: 'var(--text-dim)' }}>
        <Icon name={meta.icon} size={15} />
        <span style={{ fontWeight: 600 }}>{meta.label}</span>
        <span style={{ fontSize: 10.5, background: 'var(--soft)', padding: '2px 6px', borderRadius: 5 }}>{meta.group}</span>
        <span style={{ fontSize: 11.5, color: 'var(--text-dim)', animation: 'pulse 1.2s infinite' }}>调用中…</span>
      </div>
    </div>
  );
}

/* ── 统一思考折叠块（一条 assistant 消息一个, 默认展开） ── */
function ThinkingBlock({ thoughts, live, streaming }) {
  const [open, setOpen] = useState(true);   // 默认展开
  const expanded = open;
  const n = thoughts.length + (live ? 1 : 0);
  if (!n) return null;
  return (
    <div style={{ margin: '2px 0 8px' }}>
      <div onClick={() => setOpen(!open)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 7, cursor: 'pointer', userSelect: 'none',
                  fontSize: 12, color: 'var(--text-dim)', padding: '4px 10px', borderRadius: 7,
                  background: 'var(--soft)', border: '1px solid var(--border)' }}>
        {streaming
          ? <span style={{ width: 14, height: 14, borderRadius: '50%', border: '2.5px solid var(--border)',
                           borderTopColor: 'var(--accent)', animation: 'spin 0.8s linear infinite',
                           boxSizing: 'border-box', flexShrink: 0 }} />
          : <span style={{ fontSize: 13 }}>✦</span>}
        <span>{streaming ? '正在思考…' : `思考过程（${n} 段）`}</span>
        <span style={{ fontSize: 9, transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}>▶</span>
      </div>
      {expanded && (
        <div style={{ marginTop: 6, borderLeft: '2.5px solid var(--border)', paddingLeft: 14,
                      fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.75, fontStyle: 'italic',
                      maxHeight: streaming ? 280 : 460, overflowY: 'auto' }}>
          {thoughts.map((t, i) => (
            <div key={i} style={{ margin: '5px 0' }}>{renderMarkdown(t)}</div>
          ))}
          {live && <div>{renderMarkdown(live)}
            <span style={{ display: 'inline-block', width: 8, height: 16, marginLeft: 4, background: 'var(--accent)',
                           borderRadius: 1, animation: 'pulse 1s infinite', verticalAlign: 'middle' }} /></div>}
        </div>
      )}
    </div>
  );
}

/* ── 对话主体 ── */
function ChatTab({ agent = 'mentor', pendingQuery, onQueryConsumed }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [notLoggedIn, setNotLoggedIn] = useState(false);
  const [mirror, setMirror] = useState(null);
  const [mirrorAnswer, setMirrorAnswer] = useState('');
  const bottomRef = useRef(null);
  const abortRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch('/api/agent/me', { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (!d.username) return;
        fetch(`/api/agent/chat/history?agent=${agent}&limit=50`, { credentials: 'include' })
          .then(r => r.json())
          .then(h => { if (h.history?.length) setMessages(h.history.map(m => ({ role: m.role, content: m.content }))); })
          .catch(() => {});
        fetch('/api/agent/daily_mirror', { credentials: 'include' })
          .then(r => r.json())
          .then(m => m.observations && setMirror(m))
          .catch(() => {});
      }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (pendingQuery) { send(pendingQuery); onQueryConsumed?.(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingQuery]);

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
        setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, content: '请先登录后刷新本页', streaming: false } : m));
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      const handleEvent = (evt) => {
        if (evt.type === 'status') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, status: evt.content } : m));
        } else if (evt.type === 'thought') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, curThought: null, events: [...m.events, { t: 'thought', text: evt.content }] } : m));
        } else if (evt.type === 'thought_stream') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? { ...m, curThought: (m.curThought || '') + evt.content } : m));
        } else if (evt.type === 'tool_start') {
          // 思考流固化: 工具开始前把 live 思考存入 events, 再清空
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
          // 回答开始前同样固化思考流（只固化一次: curThought 清空后不再重复）
          finalContent += evt.content;
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            ...m, content: m.content + evt.content,
            events: m.curThought ? [...m.events, { t: 'thought', text: m.curThought }] : m.events,
            curThought: null,
          } : m));
        } else if (evt.type === 'done') {
          setMessages(prev => prev.map(m => m.msgId === msgId ? {
            reasoningSummary: evt.reasoning_summary || null,
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
    if (finalContent) {
      fetch('/api/agent/chat/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ agent, role: 'assistant', content: finalContent }),
      }).catch(() => {});
    }
  };

  const stopGenerating = () => abortRef.current?.abort();

  const clearChat = async () => {
    if (!confirm('确定清空全部对话历史？')) return;
    await fetch('/api/agent/chat/clear', { method: 'DELETE', credentials: 'include' });
    setMessages([]);
  };

  const cleanContent = (text) => (text || '')
    .replace(/<tool_calls>[\s\S]*?<\/tool_calls>/g, '')
    .replace(/<invoke name="[^"]+">[\s\S]*?<\/invoke>/g, '')
    .replace(/\{TOOL:[\s\S]*?\}/g, '');

  const renderAssistant = (m) => {
    const thoughts = (m.events || []).filter(e => e.t === 'thought').map(e => e.text);
    const toolNodes = (m.events || []).filter(e => e.t !== 'thought');
    return (
      <div>
        {m.reasoningSummary && (
          <div style={{ marginBottom: 8, padding: '7px 11px', borderRadius: 8, background: 'var(--soft)',
                        border: '1px solid var(--border)', fontSize: 12 }}>
            <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginBottom: 4, letterSpacing: '.5px' }}>✦ 推理摘要</div>
            {m.reasoningSummary.split('\n').filter(Boolean).map((s, i) => (
              <div key={i} style={{ margin: '2px 0', lineHeight: 1.6, color: 'var(--text-dim)' }}>{s}</div>
            ))}
          </div>
        )}
        {m.safety === 'warning' && (
          <div style={{ marginBottom: 8, padding: '7px 11px', borderRadius: 8, fontSize: 12,
                        background: 'rgba(200,163,90,.08)', border: '1px solid rgba(200,163,90,.3)', color: '#C8A35A' }}>
            ⚠ 该回答涉及敏感内容，请以批判性思考对待。
          </div>
        )}
        <ThinkingBlock thoughts={thoughts} live={m.curThought} streaming={m.streaming} />
        {toolNodes.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            {toolNodes.map((ev, i) => ev.t === 'tool_start'
              ? <ToolRunning key={i} name={ev.name} />
              : <ToolNode key={i} tc={ev.tc} index={i} last={i === toolNodes.length - 1} />)}
          </div>
        )}
        {m.streaming && !m.curThought && !m.content && !m.events?.length && m.status && (
          <div style={{ fontSize: 12.5, color: 'var(--text-dim)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <span style={{ width: 14, height: 14, borderRadius: '50%', border: '2.5px solid var(--border)',
                           borderTopColor: 'var(--accent)', animation: 'spin 0.8s linear infinite', boxSizing: 'border-box' }} />
            {m.status}…
          </div>
        )}
        <div style={{ lineHeight: 1.8, fontSize: 14.5 }}>
          {renderMarkdown(cleanContent(m.content))}
          {m.streaming && !m.curThought && m.content && (
            <span style={{ display: 'inline-block', width: 7, height: 15, marginLeft: 3, background: 'var(--accent)',
                           animation: 'pulse 1s infinite', verticalAlign: 'middle' }} />
          )}
        </div>
        {m.suggestions?.length > 0 && !m.streaming && (
          <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {m.suggestions.map((s, i) => (
              <button key={i} onClick={() => send(s)}
                style={{ padding: '5px 12px', borderRadius: 14, cursor: 'pointer', fontSize: 12,
                         background: 'var(--soft)', border: '1px solid var(--border)', color: 'var(--text-dim)',
                         transition: 'all .15s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--text)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-dim)'; }}>
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 56px)' }}>
      {/* 消息滚动区 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 24px 12px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {notLoggedIn && (
            <div style={{ margin: '16px auto', padding: '12px 18px', borderRadius: 10, fontSize: 13,
                          background: 'var(--soft)', border: '1px solid var(--border)' }}>
              未登录。点击左下角「登录 / 注册」即可使用智能体，数据与看板同账号。
            </div>
          )}

          {mirror && (
            <div style={{ padding: '16px 18px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--card-bg)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Icon name="icon-brain" size={17} />
                <span style={{ fontSize: 13.5, fontWeight: 700 }}>今日镜像</span>
                <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  {mirror.name ? `${mirror.name}，` : ''}过去 7 天 · {mirror.stats?.journals_7d ?? 0} 条记录 · {mirror.stats?.events_7d ?? 0} 个事件
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 9 }}>
                {mirror.observations?.map((o, i) => (
                  <div key={i} style={{ fontSize: 12.5, lineHeight: 1.6 }}>{i === 0 ? '📚 ' : i === 1 ? '⚡ ' : '🔍 '}{o}</div>
                ))}
              </div>
              {mirror.suggestion && (
                <div style={{ fontSize: 12, color: 'var(--text-dim)', padding: '7px 11px', borderRadius: 8,
                              background: 'var(--soft)', marginBottom: 9, lineHeight: 1.6 }}>💡 今天：{mirror.suggestion}</div>
              )}
              <div style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 6, lineHeight: 1.6 }}>🎯 每日一问：{mirror.daily_question}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input value={mirrorAnswer} onChange={e => setMirrorAnswer(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && submitMirrorAnswer()}
                  placeholder="回答它（会自动记录为今天的经历）"
                  style={{ flex: 1, padding: '7px 12px', borderRadius: 16, border: '1px solid var(--border)',
                           background: 'var(--soft)', fontSize: 12.5, outline: 'none', color: 'var(--text)' }} />
                <button onClick={submitMirrorAnswer} disabled={!mirrorAnswer.trim()}
                  style={{ padding: '7px 14px', borderRadius: 16, cursor: 'pointer', fontSize: 12.5,
                           border: 'none', background: 'var(--accent)', color: 'var(--bg)',
                           opacity: !mirrorAnswer.trim() ? 0.4 : 1 }}>记录</button>
              </div>
            </div>
          )}

          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '28px 0 12px' }}>
              <div style={{ fontSize: 14.5, color: 'var(--text-dim)', marginBottom: 18 }}>🪞 今天，你想看看什么？</div>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                {[
                  { icon: '🌱', title: '看见自己', sub: '最近的我，好像变了吗？', q: '帮我看看最近的我有什么变化？结合我的记录、事件和人格画像。' },
                  { icon: '🌌', title: '看见未来', sub: '如果继续这样走，会成为怎样的人？', q: '如果继续这样走下去，我会成为怎样的人？帮我推演并给出当下可行的步骤。' },
                  { icon: '🌍', title: '连接世界', sub: '世界上有什么正在回应现在的我？', q: '世界上有哪些机会正在回应现在的我？结合我的画像推荐活动、比赛或伙伴。' },
                ].map((e, i) => (
                  <button key={i} onClick={() => send(e.q)}
                    style={{ width: 185, padding: '15px 13px', borderRadius: 12, cursor: 'pointer',
                             border: '1px solid var(--border)', background: 'var(--card-bg)', transition: 'all .15s', textAlign: 'center' }}
                    onMouseEnter={ev => { ev.currentTarget.style.borderColor = 'var(--accent)'; ev.currentTarget.style.background = 'var(--soft)'; }}
                    onMouseLeave={ev => { ev.currentTarget.style.borderColor = 'var(--border)'; ev.currentTarget.style.background = 'var(--card-bg)'; }}>
                    <div style={{ fontSize: 24, marginBottom: 5 }}>{e.icon}</div>
                    <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 3 }}>{e.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.5 }}>{e.sub}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => m.role === 'user' ? (
            /* 用户消息: 终端式扁平行（ZCode ❯ prompt） */
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent)', fontFamily: 'ui-monospace, monospace', fontSize: 14,
                             lineHeight: 1.75, flexShrink: 0, userSelect: 'none' }}>❯</span>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.75, fontSize: 14.5, flex: 1, minWidth: 0 }}>{m.content}</div>
            </div>
          ) : (
            /* Assistant: agent 标记 + 全宽内容 */
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span style={{ width: 22, height: 22, borderRadius: 6, background: 'var(--accent)', color: 'var(--bg)',
                             fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center',
                             flexShrink: 0, marginTop: 2, userSelect: 'none' }}>镜</span>
              <div style={{ flex: 1, minWidth: 0 }}>{renderAssistant(m)}</div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* 输入坞（flex 布局, 随内容自适应） */}
      <div style={{ flexShrink: 0, padding: '6px 24px 18px', background: 'linear-gradient(transparent, var(--bg) 30%)' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <div style={{ display: 'flex', gap: 6, marginBottom: 7, alignItems: 'center' }}>
            <button onClick={() => { inputRef.current?.focus(); }}
              style={{ padding: '4px 11px', borderRadius: 12, cursor: 'pointer', fontSize: 11.5,
                       border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text-dim)' }}>✍️ 记录今天</button>
            <button onClick={() => send('帮我看看最近的我有什么变化？')}
              style={{ padding: '4px 11px', borderRadius: 12, cursor: 'pointer', fontSize: 11.5,
                       border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text-dim)' }}>🪞 看看自己</button>
            {messages.length > 0 && (
              <button onClick={clearChat} title="清空对话历史"
                style={{ padding: '4px 11px', borderRadius: 12, cursor: 'pointer', fontSize: 11.5,
                         border: '1px solid var(--border)', background: 'var(--card-bg)', color: 'var(--text-dim)' }}>🗑 清空</button>
            )}
            <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 2 }}>
              说"今天……"即自动记录 · Enter 发送 · Shift+Enter 换行
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4,
                        background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 14,
                        padding: '8px 8px 8px 14', boxShadow: '0 2px 12px var(--ring)' }}>
            <textarea ref={inputRef} rows={1}
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
              }}
              placeholder="问一个关于你的问题…"
              style={{ flex: 1, border: 'none', background: 'transparent', fontSize: 14.5, outline: 'none',
                       color: 'var(--text)', resize: 'none', maxHeight: 160, lineHeight: 1.6 }} />
            {loading ? (
              <button onClick={stopGenerating} title="停止生成"
                style={{ width: 34, height: 34, borderRadius: 10, border: '1px solid var(--border)', cursor: 'pointer', flexShrink: 0,
                         background: 'var(--soft)', color: 'var(--accent)', fontSize: 11,
                         display: 'flex', alignItems: 'center', justifyContent: 'center' }}>■</button>
            ) : (
              <button onClick={() => send()} disabled={!input.trim()} title="发送"
                style={{ width: 34, height: 34, borderRadius: 10, border: 'none', cursor: 'pointer', flexShrink: 0,
                         background: 'var(--accent)', color: 'var(--bg)', fontSize: 14,
                         display: 'flex', alignItems: 'center', justifyContent: 'center',
                         opacity: !input.trim() ? 0.4 : 1, transition: 'opacity .15s' }}>↑</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── 主页面（顶栏 + 对话区） ── */
export default function AgentPage({ pendingQuery, onQueryConsumed }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* 顶栏 */}
      <div style={{ flexShrink: 0, height: 55, display: 'flex', alignItems: 'center', gap: 10,
                    padding: '0 24px', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}>
        <span style={{ fontSize: 17 }}>🪞</span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 14.5, fontWeight: 700, lineHeight: 1.2 }}>镜界导师</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.3 }}>记录 / 看见 / 预见 / 共创，全部对话完成</div>
        </div>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#5F8A6E', display: 'inline-block' }} />
          在线
        </span>
      </div>
      <ChatTab agent="mentor" pendingQuery={pendingQuery} onQueryConsumed={onQueryConsumed} />
    </div>
  );
}
