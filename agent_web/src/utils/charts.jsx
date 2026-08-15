/**
 * charts.jsx — 手写 SVG 图表组件（dsh-client-ui-dashboard 风格）
 * 全部响应 CSS 变量（深浅色自适应），无第三方依赖
 */
import { useState, useRef } from 'react';

// ── Sparkline：StatCard 内嵌迷你趋势线 ──
export function Sparkline({ data, width = 90, height = 26, color = 'var(--accent)' }) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data, 1), min = Math.min(...data, 0);
  const span = max - min || 1;
  const px = i => 1 + (i / (data.length - 1)) * (width - 2);
  const py = v => height - 2 - ((v - min) / span) * (height - 4);
  const path = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${px(i)},${py(v)}`).join(' ');
  const area = `${path} L${px(data.length - 1)},${height} L${px(0)},${height} Z`;
  const gid = `sp-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="1.4" />
      <circle cx={px(data.length - 1)} cy={py(data[data.length - 1])} r="1.8" fill={color} />
    </svg>
  );
}

// ── AreaChart：渐变面积 + 自定义悬浮提示（十字线 + 浮动数值）──
export function AreaChart({ points, height = 130, color = 'var(--accent)', fmt = v => v, zeroLine = false, min, max: maxProp }) {
  const W = 100, H = height, PADT = 8, PADB = 16, PADL = 4, PADR = 4;
  const [hover, setHover] = useState(-1);
  const boxRef = useRef(null);
  if (!points || points.length < 2) return <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: 20 }}>数据积累中…</div>;
  const vals = points.map(p => p.v);
  let lo = min !== undefined ? min : Math.min(...vals);
  let hi = maxProp !== undefined ? maxProp : Math.max(...vals);
  if (lo === hi) { hi += 1; lo -= 1; }
  const px = i => PADL + (i / (points.length - 1)) * (W - PADL - PADR);
  const py = v => PADT + (1 - (v - lo) / (hi - lo)) * (H - PADT - PADB);
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${px(i)},${py(p.v)}`).join(' ');
  const gid = `ac-${Math.random().toString(36).slice(2, 8)}`;
  const labels = [0, Math.floor(points.length / 2), points.length - 1];

  const onMove = (e) => {
    const box = boxRef.current?.getBoundingClientRect();
    if (!box) return;
    const frac = (e.clientX - box.left) / box.width;
    const idx = Math.round(frac * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, idx)));
  };

  return (
    <div ref={boxRef} style={{ position: 'relative' }}
      onMouseMove={onMove} onMouseLeave={() => setHover(-1)}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: H, display: 'block' }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f} x1={PADL} x2={W - PADR} y1={PADT + f * (H - PADT - PADB)} y2={PADT + f * (H - PADT - PADB)}
            stroke="var(--ring)" strokeWidth="0.4" />
        ))}
        {zeroLine && lo < 0 && hi > 0 && (
          <line x1={PADL} x2={W - PADR} y1={py(0)} y2={py(0)} stroke="var(--text-dim)" strokeWidth="0.5" strokeDasharray="2 2" />
        )}
        <path d={`${path} L${px(points.length - 1)},${H - PADB} L${px(0)},${H - PADB} Z`} fill={`url(#${gid})`} />
        <path d={path} fill="none" stroke={color} strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        {points.map((p, i) => (
          <circle key={i} cx={px(i)} cy={py(p.v)} r={i === hover ? 2.4 : 1} fill={color} opacity={i === hover ? 1 : 0.7} />
        ))}
        {hover >= 0 && (
          <line x1={px(hover)} x2={px(hover)} y1={PADT} y2={H - PADB} stroke={color} strokeWidth="0.6" vectorEffect="non-scaling-stroke" opacity="0.6" />
        )}
      </svg>
      {hover >= 0 && points[hover] && (
        <div style={{
          position: 'absolute', left: `${(px(hover) / W) * 100}%`, top: 2,
          transform: `translateX(${hover > points.length * 0.6 ? '-105%' : '5%'})`,
          padding: '4px 8px', borderRadius: 6, fontSize: 11, whiteSpace: 'nowrap',
          background: 'var(--card-bg)', border: '1px solid var(--border)',
          boxShadow: '0 2px 8px var(--ring)', pointerEvents: 'none', zIndex: 5,
          fontFamily: 'ui-monospace, monospace',
        }}>
          <span style={{ color: 'var(--text-dim)' }}>{points[hover].label || ''} </span>
          <span style={{ color: 'var(--text)', fontWeight: 700 }}>{fmt(points[hover].v)}</span>
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--text-dim)', padding: '2px 4px 0' }}>
        {labels.map(i => <span key={i}>{points[i]?.label}</span>)}
      </div>
    </div>
  );
}

// ── HBar：水平条形（Top N 构成, 整行悬停提示）──
export function HBar({ items, color = 'var(--accent)', unit = '', max: maxProp }) {
  const [hover, setHover] = useState(-1);
  if (!items || items.length === 0) return <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: 12 }}>暂无数据</div>;
  const max = maxProp || Math.max(...items.map(i => i.v), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((it, i) => (
        <div key={it.k} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(-1)}
          title={`${it.k}: ${it.v}${unit}`}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '1px 0',
                   background: hover === i ? 'var(--soft)' : 'transparent', borderRadius: 4,
                   opacity: hover === -1 || hover === i ? 1 : 0.55, transition: 'opacity .15s' }}>
          <span style={{ fontSize: 11, color: 'var(--text-dim)', width: 64, flexShrink: 0, textAlign: 'right',
                         overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={it.k}>{it.k}</span>
          <div style={{ flex: 1, height: 14, background: 'var(--ring)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: (it.v / max) * 100 + '%', background: it.c || color,
                         borderRadius: 3, transition: 'width .6s', opacity: 0.85 }} />
          </div>
          <span style={{ fontSize: 10.5, color: 'var(--text)', width: 34, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{it.v}{unit}</span>
        </div>
      ))}
    </div>
  );
}

// ── Gauge：半圆仪表（置信度等 0-100 指标）──
export function Gauge({ value, size = 120, label = '' }) {
  const v = Math.max(0, Math.min(100, value));
  const R = 44, CX = 60, CY = 54;
  const angle = Math.PI * (1 - v / 100);
  const x = CX + R * Math.cos(angle), y = CY - R * Math.sin(angle);
  const color = v >= 70 ? '#5F8A6E' : v >= 40 ? '#C8A35A' : '#c0392b';
  return (
    <svg width={size} height={size * 0.66} viewBox="0 0 120 66" style={{ display: 'block' }}>
      <path d={`M${CX - R},${CY} A${R},${R} 0 0 1 ${CX + R},${CY}`} fill="none" stroke="var(--ring)" strokeWidth="9" strokeLinecap="round" />
      <path d={`M${CX - R},${CY} A${R},${R} 0 0 1 ${x},${y}`} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" style={{ transition: 'all .8s' }} />
      <text x={CX} y={CY - 12} textAnchor="middle" fontSize="17" fontWeight="700" fill="var(--text)">{Math.round(v)}%</text>
      {label && <text x={CX} y={CY + 2} textAnchor="middle" fontSize="7.5" fill="var(--text-dim)">{label}</text>}
    </svg>
  );
}

// ── Radar：五维雷达图（人格画像, overflow 可见防标签裁切）──
export function Radar({ axes, size = 200 }) {
  const entries = Object.entries(axes || {}).slice(0, 6);
  if (entries.length < 3) return <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: 12 }}>维度数据积累中…</div>;
  const CX = size / 2, CY = size / 2 + 6, R = size / 2 - 40;
  const pt = (i, r) => {
    const a = -Math.PI / 2 + (i / entries.length) * Math.PI * 2;
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  };
  const poly = entries.map(([k, v], i) => pt(i, Math.min(100, v || 0) / 100 * R).join(',')).join(' ');
  return (
    <svg width={size} height={size + 10} viewBox={`0 0 ${size} ${size + 10}`}
      style={{ display: 'block', margin: '0 auto', overflow: 'visible', padding: '0 22px', boxSizing: 'content-box' }}>
      {[0.25, 0.5, 0.75, 1].map(f => (
        <polygon key={f} points={entries.map((_, i) => pt(i, R * f).join(',')).join(' ')}
          fill="none" stroke="var(--ring)" strokeWidth="0.8" />
      ))}
      {entries.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={CX} y1={CY} x2={x} y2={y} stroke="var(--ring)" strokeWidth="0.8" />;
      })}
      <polygon points={poly} fill="var(--accent)" fillOpacity="0.15" stroke="var(--accent)" strokeWidth="1.5" />
      {entries.map(([k, v], i) => {
        const [x, y] = pt(i, Math.min(100, v || 0) / 100 * R);
        return <circle key={k} cx={x} cy={y} r="2.2" fill="var(--accent)"><title>{`${k}: ${v}`}</title></circle>;
      })}
      {entries.map(([k, v], i) => {
        const [x, y] = pt(i, R + 14);
        return (
          <text key={k} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
            fontSize="9.5" fill="var(--text-dim)" style={{ overflow: 'visible' }}>{k} {v}</text>
        );
      })}
    </svg>
  );
}

// ── Donut：环形构成 ──
export function Donut({ items, size = 150, centerLabel = '' }) {
  const total = (items || []).reduce((s, i) => s + i.v, 0);
  if (!total) return <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: 12 }}>暂无数据</div>;
  const R = 30, C = size / 2, SW = 13;
  const circ = 2 * Math.PI * R;
  let acc = 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={size} height={size} viewBox="0 0 80 80" style={{ flexShrink: 0 }}>
        {items.map(it => {
          const frac = it.v / total;
          const el = (
            <circle key={it.k} cx={C} cy={C} r={R} fill="none" stroke={it.c || 'var(--accent)'} strokeWidth={SW}
              strokeDasharray={`${frac * circ} ${circ}`} strokeDashoffset={-acc * circ}
              transform="rotate(-90 40 40)" opacity="0.88">
              <title>{`${it.k}: ${it.v} (${Math.round(frac * 100)}%)`}</title>
            </circle>
          );
          acc += frac;
          return el;
        })}
        <text x="40" y="38" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--text)">{total}</text>
        <text x="40" y="48" textAnchor="middle" fontSize="6" fill="var(--text-dim)">{centerLabel}</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
        {items.map(it => (
          <div key={it.k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: it.c || 'var(--accent)', flexShrink: 0 }} />
            <span style={{ color: 'var(--text-dim)' }}>{it.k}</span>
            <span style={{ color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{Math.round(it.v / total * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── VBars：纵向柱状（月度事件等, 悬停浮层）──
export function VBars({ items, height = 110, color = 'var(--accent)' }) {
  const [hover, setHover] = useState(-1);
  if (!items || items.length === 0) return <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: 12 }}>暂无数据</div>;
  const max = Math.max(...items.map(i => i.v), 1);
  return (
    <div style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height, padding: '0 2px' }}>
        {items.map((it, i) => (
          <div key={i}
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(-1)}
            style={{ flex: 1, minWidth: 3, height: Math.max(2, (it.v / max) * (height - 16)),
                     background: it.c || color, borderRadius: '2px 2px 0 0',
                     opacity: hover === -1 || hover === i ? 0.85 : 0.4,
                     cursor: 'default', transition: 'height .6s, opacity .15s' }} />
        ))}
      </div>
      {hover >= 0 && items[hover] && (
        <div style={{
          position: 'absolute', bottom: height - 4, left: `calc(${((hover + 0.5) / items.length) * 100}% )`,
          transform: `translateX(${hover > items.length * 0.7 ? '-108%' : '8%'})`,
          padding: '3px 8px', borderRadius: 6, fontSize: 11, whiteSpace: 'nowrap',
          background: 'var(--card-bg)', border: '1px solid var(--border)',
          boxShadow: '0 2px 8px var(--ring)', pointerEvents: 'none', zIndex: 5,
          fontFamily: 'ui-monospace, monospace',
        }}>
          <span style={{ color: 'var(--text-dim)' }}>{items[hover].k} </span>
          <span style={{ color: 'var(--text)', fontWeight: 700 }}>{items[hover].v}</span>
        </div>
      )}
    </div>
  );
}

export const CHART_COLORS = ['#6b7fd7', '#5F8A6E', '#C8A35A', '#c0392b', '#8b6bb1', '#4f9ea8', '#b0715a', '#7a8a4f', '#a85b7e', '#5a7ba8'];
