import { useEffect, useState } from 'react';
import { Sparkline, AreaChart, HBar, Gauge, Radar, Donut, VBars, CHART_COLORS } from '../utils/charts';

/**
 * DashboardPage — 指标看板（dsh-client-ui-dashboard 风格）
 * StatCards + sparkline / 面积趋势 / 半圆仪表 / 雷达 / 环形构成 / 柱状分布
 * 数据源: /api/agent/dashboard（全部真实用户数据）
 */

const EVENT_LABEL = { achievement: '🏆 成就', competition: '⚔️ 比赛', turning_point: '🔀 转折', decision: '🎯 决定',
                      failure: '💥 挫折', project: '📦 项目', relationship: '💞 关系', social: '👥 社交',
                      habit: '🔁 习惯', study: '📚 学业', other: '📌 其他' };
const MOOD_COLOR = m => {
  const pos = ['开心', '兴奋', '幸福', '满足', '成就感', '期待', '舒服', '充实', '平静', '放松', '感动', '温暖'];
  const neg = ['迷茫', '烦躁', '焦虑', '低落', 'emo', '有点烦', '难过', '压力', '挫败', '孤独', '疲惫', '没精神', '紧张'];
  if (pos.includes(m)) return '#5F8A6E';
  if (neg.includes(m)) return '#c0392b';
  return '#C8A35A';
};

function Card({ title, hint, children, span = 1, right }) {
  return (
    <div style={{ gridColumn: `span ${span}`, padding: '14px 16px', borderRadius: 12,
                  background: 'var(--card-bg)', border: '1px solid var(--border)' }}>
      {(title || right) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div>
            <span style={{ fontSize: 12, fontWeight: 700 }}>{title}</span>
            {hint && <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 8 }}>{hint}</span>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

function StatCard({ label, value, unit, sub, spark, color = 'var(--accent)', onClick, title }) {
  return (
    <div onClick={onClick} title={title}
      style={{ padding: '12px 14px', borderRadius: 12, background: 'var(--card-bg)',
               border: '1px solid var(--border)', cursor: onClick ? 'pointer' : 'default',
               display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <div style={{ fontSize: 10.5, color: 'var(--text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 6 }}>
        <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
          {value}<span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-dim)', marginLeft: 3 }}>{unit}</span>
        </div>
        {spark && spark.length > 1 && <Sparkline data={spark} color={color} />}
      </div>
      {sub && <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{sub}</div>}
    </div>
  );
}

export default function DashboardPage({ onAsk }) {
  const [d, setD] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch('/api/agent/dashboard', { credentials: 'include' })
      .then(r => r.status === 401 ? { __unauth: true } : r.json())
      .then(setD)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <div style={{ padding: 40, color: 'var(--text-dim)', fontSize: 13 }}>看板加载失败，请刷新重试</div>;
  if (!d) return <div style={{ padding: 40, color: 'var(--text-dim)', fontSize: 13 }}>看板加载中…</div>;
  if (d.__unauth) {
    return <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>请先在左侧登录，再看你的镜像。</div>;
  }

  const s = d.stats || {};
  const p = d.persona;
  const name = (d.me?.real_name || d.me?.username || '');
  const conf = Math.round((p?.confidence || 0) * 100);
  const tl = d.timeline || [];
  const tlCounts = tl.map(t => t.count);
  const tlMoods = tl.map(t => t.mood);
  const recent6 = tl.slice(-6);
  const ask = q => () => onAsk?.(q);

  const moodItems = (d.mood_dist || []).map(([m, n], i) => ({ k: m, v: n, c: MOOD_COLOR(m) }));
  const eventItems = Object.entries(d.events_by_type || {})
    .sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ k: EVENT_LABEL[k] || k, v }));
  const interestItems = Object.entries(d.interests || {}).map(([k, v]) => ({ k, v }));
  const eventBars = Object.entries(d.events_by_month || {}).map(([k, v]) => ({ k, v }));
  const memorySpark = (d.memory_growth || []).slice(-12).map(m => m.new);
  const au = d.agent_usage || {};

  const radarAxes = {};
  if (p) {
    const pick = (obj, n) => Object.entries(obj || {}).sort((a, b) => b[1] - a[1]).slice(0, n);
    pick(p.ability, 3).forEach(([k, v]) => radarAxes[k] = v);
    pick(p.behavior, 1).forEach(([k, v]) => radarAxes[k + '行为'] = v);
    pick(p.interest, 1).forEach(([k, v]) => radarAxes[k] = Math.max(radarAxes[k] || 0, v));
  }

  return (
    <div style={{ padding: '20px 24px 48px', maxWidth: 1080, margin: '0 auto' }}>

      {/* ═══ 顶部摘要条（sticky 语义：一屏看清关键数字）═══ */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap',
                    padding: '12px 18px', borderRadius: 12, background: 'var(--card-bg)',
                    border: '1px solid var(--border)', marginBottom: 14 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{name || '我'}的镜像看板</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
            {p ? `${p.persona_type} · v${p.version} · ${d.insight ? d.insight.slice(0, 40) : ''}` : '镜像尚未形成——记录越多，看板越丰富'}
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
          {[['记录', s.record_count || 0], ['事件', s.event_count || 0], ['记忆', d.memory_total || 0],
            ['目标', s.goal_count || 0], ['对话', d.chat_messages || 0]].map(([k, v]) => (
            <div key={k} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 16, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{v}</div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{k}</div>
            </div>
          ))}
          <Gauge value={conf} size={92} label="人格形成度" />
        </div>
      </div>

      {/* ═══ StatCards 行 ═══ */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 14 }}>
        <StatCard label="🔥 连续记录" value={s.streak || 0} unit="天"
          sub={`本周 ${s.this_week ?? 0} 条 · 上周 ${s.last_week ?? 0} 条`}
          spark={tlCounts.slice(-12)} onClick={ask('我最近的记录节奏怎么样？有什么趋势？')}
          title="点击问智能体" />
        <StatCard label="📝 总记录（近30天窗口）" value={s.record_count || 0} unit="条"
          sub={`全量 ${(d.timeline || []).reduce((a, t) => a + t.count, 0)} 条`}
          spark={tlCounts.slice(-12)} />
        <StatCard label="🧠 生命记忆" value={d.memory_total || 0} unit="条"
          sub={`日记提炼 + 事件沉淀`} spark={memorySpark} color="#8b6bb1"
          onClick={ask('帮我检索几条最重要的生命记忆')} title="点击问智能体" />
        <StatCard label={`🎯 活跃目标`} value={s.goal_count || 0} unit="个"
          sub={`平均重要度 ${d.active_goals?.length ? Math.round(d.active_goals.reduce((a, g) => a + (g.importance || 0), 0) / d.active_goals.length) : 0}%`}
          color="#C8A35A" onClick={ask('我的目标和当前状态匹配吗？')} title="点击问智能体" />
        <StatCard label="🔮 未来人格" value={(d.futures || []).length} unit="个"
          sub={(d.futures || []).map(f => f.label).join(' · ') || '尚无模拟'}
          color="#4f9ea8" onClick={ask('给我讲讲我的未来路径')} title="点击问智能体" />
        <StatCard label="🤖 智能体调用" value={au.requests || 0} unit="次"
          sub={au.requests ? `均 ${au.avg_duration}s · 工具 ${au.tool_calls} 次` : '还没有对话'}
          spark={au.requests ? [] : undefined} color="#b0715a"
          onClick={ask('帮我复盘一下最近和你的对话')} title="点击问智能体" />
      </div>

      {/* ═══ 图表网格 ═══ */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>

        <Card title="📈 记录活跃" hint="按月 · 悬停看数值" span={2}>
          <AreaChart points={tl.map(t => ({ label: t.month.slice(2), v: t.count }))} height={140} fmt={v => `${v} 条`} />
        </Card>

        <Card title="🌡️ 情绪趋势" hint="月均效价 -2..+2 · 虚线为中性">
          <AreaChart points={tl.map(t => ({ label: t.month.slice(2), v: t.mood }))} height={140}
            color="#b0715a" zeroLine min={-2} max={2} fmt={v => (v > 0 ? '+' : '') + v} />
        </Card>

        <Card title="🎭 情绪构成" hint="Top 10 心情">
          <HBar items={moodItems} unit="次" />
        </Card>

        {p && (
          <Card title="🕸️ 人格画像" hint="能力/兴趣/行为信号" span={2}
            right={<button onClick={ask('详细解读我的五维人格画像')} style={{ fontSize: 10.5, color: 'var(--accent)',
                             background: 'transparent', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>让智能体解读 →</button>}>
            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', alignItems: 'center' }}>
              <Radar axes={radarAxes} size={210} />
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  {Object.entries(p.ability || {}).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-dim)', width: 60, textAlign: 'right', flexShrink: 0 }}>{k}</span>
                      <div style={{ flex: 1, height: 8, background: 'var(--ring)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: Math.min(100, v) + '%', background: 'var(--accent)', borderRadius: 4, transition: 'width .6s' }} />
                      </div>
                      <span style={{ fontSize: 10.5, width: 26, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{v}</span>
                    </div>
                  ))}
                </div>
                {(d.persona_history || []).length >= 2 && (
                  <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>置信度演进</span>
                    <Sparkline data={d.persona_history.map(h => h.confidence)} width={130} height={24} />
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>v{d.persona_history[0].version} → v{d.persona_history[d.persona_history.length - 1].version}</span>
                  </div>
                )}
              </div>
            </div>
          </Card>
        )}

        <Card title="🏆 人生事件分布" hint={`${Object.values(d.events_by_type || {}).reduce((a, b) => a + b, 0)} 个事件 · 按类型`}>
          <HBar items={eventItems} unit="个" color="#C8A35A" />
        </Card>

        <Card title="📅 事件时间分布" hint="按月">
          <VBars items={eventBars} height={130} color="#C8A35A" />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-dim)', marginTop: 4 }}>
            <span>{eventBars[0]?.k}</span><span>{eventBars[eventBars.length - 1]?.k}</span>
          </div>
        </Card>

        <Card title="🌱 兴趣信号" hint="真实追踪 + AI 提炼">
          <HBar items={interestItems} unit="分" color="#4f9ea8" />
        </Card>

        <Card title="🧬 记忆增长" hint="累计生命记忆">
          <AreaChart points={(d.memory_growth || []).map(m => ({ label: m.month.slice(2), v: m.total }))}
            height={130} color="#8b6bb1" fmt={v => `${v} 条`} />
        </Card>

        <Card title="🤖 智能体运行" hint={au.requests ? `均 ${au.avg_duration}s · P95 ${au.p95_duration}s` : '暂无调用'}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[['请求数', au.requests ?? 0, '次'], ['工具调用', au.tool_calls ?? 0, '次'],
              ['工具失败', au.failures ?? 0, '次'], ['致命错误', au.errors ?? 0, '次']].map(([k, v, u]) => (
              <div key={k} style={{ padding: '8px 10px', borderRadius: 8, background: 'var(--soft)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{k}</div>
                <div style={{ fontSize: 16, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{v}<span style={{ fontSize: 10, color: 'var(--text-dim)' }}> {u}</span></div>
              </div>
            ))}
          </div>
        </Card>

        {/* ═══ 未来人格卡 ═══ */}
        {(d.futures || []).length > 0 && (
          <Card title="🌌 可能的我" hint="点击与那个版本对话" span={2}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              {d.futures.slice(0, 3).map(f => (
                <div key={f.id} onClick={ask(`我想和${f.target_year}年的「${f.label}」聊聊`)}
                  style={{ padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                           background: 'var(--soft)', border: '1px solid var(--border)', transition: 'border-color .2s' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{f.label}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)' }}>{Math.round((f.confidence || 0.7) * 100)}%</span>
                  </div>
                  <div style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>{f.target_year} 年 · 基于 {f.path_type}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* ═══ 目标 ═══ */}
        <Card title="🎯 我要走向哪里" hint={d.active_goals?.length ? '点击让智能体拆解' : ''} span={2}>
          {(d.active_goals || []).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {d.active_goals.map(g => (
                <div key={g.id} onClick={ask(`帮我把目标「${g.title}」拆解成可执行的下一步`)}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '9px 12px', borderRadius: 8,
                           background: 'var(--soft)', cursor: 'pointer' }}>
                  <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.title}</span>
                  <div style={{ width: 90, height: 6, background: 'var(--ring)', borderRadius: 3, overflow: 'hidden', flexShrink: 0 }}>
                    <div style={{ height: '100%', width: (g.importance || 0) + '%', background: 'var(--accent)', opacity: 0.8 }} />
                  </div>
                  <span style={{ fontSize: 10.5, color: 'var(--text-dim)', width: 32, textAlign: 'right' }}>{g.importance}%</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', padding: 8 }}>
              还没有目标 · <button onClick={ask('根据我的画像推荐三个值得投入的方向')}
                style={{ color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, textDecoration: 'underline' }}>让智能体推荐 →</button>
            </div>
          )}
        </Card>
      </div>

      <p style={{ textAlign: 'center', fontSize: 10, color: 'var(--text-dim)', marginTop: 18 }}>
        所有指标来自你的真实数据 · 点击卡片可向智能体提问 · 镜·界·联
      </p>
    </div>
  );
}
