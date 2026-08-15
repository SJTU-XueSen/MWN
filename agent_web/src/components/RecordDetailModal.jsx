import { useEffect, useState } from 'react';
import { renderMarkdown } from '../utils/markdown';

/**
 * RecordDetailModal — 记录详情弹窗（展示入库时的 AI 分析, 同主站）
 * 日记: 情绪/兴趣领域/行为模式/长期影响/人格变化/鼓励/展望
 * 事件: AI 影响分析/兴趣标签/人格变化/情绪
 */
export default function RecordDetailModal({ type, id, onClose }) {
  const [rec, setRec] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    fetch(`/api/agent/record?type=${type}&id=${id}`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (d.ok) setRec(d.record);
        else setErr(d.error || '加载失败');
      }).catch(() => setErr('加载失败'));
  }, [type, id]);

  const a = rec?.analysis || {};
  const pd = rec?.persona_delta || a?.persona_delta || {};

  const Row = ({ label, value, md }) => value ? (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 2, fontWeight: 600 }}>{label}</div>
      {md ? (
        <div style={{ fontSize: 13, lineHeight: 1.7 }}>{renderMarkdown(String(value))}</div>
      ) : (
        <div style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
        </div>
      )}
    </div>
  ) : null;

  // 人格变化: {维度: 数值} → 正负色徽章
  const DeltaBadges = ({ delta }) => {
    const entries = Object.entries(delta || {});
    if (!entries.length) return null;
    return (
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {entries.map(([k, v]) => (
          <span key={k} style={{
            fontSize: 11, padding: '3px 10px', borderRadius: 6, fontWeight: 600,
            background: v > 0 ? 'rgba(95,138,110,.12)' : v < 0 ? 'rgba(181,84,63,.1)' : 'var(--soft)',
            border: `1px solid ${v > 0 ? 'rgba(95,138,110,.5)' : v < 0 ? 'rgba(181,84,63,.4)' : 'var(--border)'}`,
            color: v > 0 ? '#5F8A6E' : v < 0 ? '#B5543F' : 'var(--text-dim)',
          }}>
            {k} {v > 0 ? `+${v}` : v}
          </span>
        ))}
      </div>
    );
  };

  const TagList = ({ label, items }) => items?.length ? (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>{label}</div>
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
        {items.map((t, i) => (
          <span key={i} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 5,
                                background: 'var(--soft)', border: '1px solid var(--border)' }}>{t}</span>
        ))}
      </div>
    </div>
  ) : null;

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 1250,
                                   display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: 'var(--bg)', borderRadius: 14, width: '100%', maxWidth: 560, maxHeight: '82vh',
                 overflowY: 'auto', padding: '22px 26px', boxShadow: '0 16px 60px rgba(0,0,0,.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>
            {rec ? (rec.type === 'journal' ? '日记详情' : rec.type === 'event' ? '事件详情'
                   : rec.type === 'goal' ? '目标详情' : '记忆详情') : '记录详情'}
          </div>
          <span onClick={onClose} style={{ cursor: 'pointer', color: 'var(--text-dim)', fontSize: 15 }}>✕</span>
        </div>

        {err && <div style={{ color: '#c0392b', fontSize: 13 }}>{err}</div>}
        {!rec && !err && <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>加载中…</div>}

        {rec && (
          <>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>
              {rec.date}{rec.event_type ? ` · ${rec.event_type}` : ''}{rec.status ? ` · ${rec.status}` : ''}
              {rec.importance ? ` · 重要度 ${rec.importance}` : ''}
              {rec.mood ? ` · 心情：${rec.mood}` : ''}
              {rec.emotion ? ` · 情绪：${rec.emotion}` : ''}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: rec.content ? 6 : 16 }}>
              {rec.title || ''}
            </div>
            {rec.content && (
              <div style={{ fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap', marginBottom: 16,
                            padding: '12px 14px', borderRadius: 10, background: 'var(--soft)' }}>
                {rec.content}
              </div>
            )}

            {/* AI 分析（同主站） */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 10, fontWeight: 700, letterSpacing: '.5px' }}>
                ✨ AI 分析
              </div>
              {rec.type === 'journal' && (
                <>
                  <Row label="情绪" value={a.emotion_detail || a.emotion} />
                  <TagList label="兴趣领域" items={a.interest_fields || rec.interest_tags} />
                  <TagList label="行为模式" items={a.behavior_patterns} />
                  <Row label="长期影响" value={a.long_term_impact} md />
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>人格变化</div>
                    <DeltaBadges delta={pd} />
                  </div>
                  <TagList label="知识领域" items={a.knowledge_domains} />
                  <Row label="洞察" value={a.search_insight} md />
                  <Row label="鼓励" value={a.encouragement} md />
                  <Row label="展望" value={a.outlook} md />
                </>
              )}
              {rec.type === 'event' && (
                <>
                  <Row label="AI 影响分析" value={rec.ai_impact} md />
                  <TagList label="兴趣标签" items={rec.interest_tags} />
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>人格变化</div>
                    <DeltaBadges delta={pd} />
                  </div>
                </>
              )}
              {rec.type === 'goal' && (
                <Row label="差距分析" value={rec.ai_gap_analysis} md />
              )}
              {rec.type === 'memory' && (
                <Row label="来源" value={rec.source_type} />
              )}
              {rec.type === 'journal' && !Object.keys(a).length && (
                <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>该记录无 AI 分析（入库时未生成）</div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
