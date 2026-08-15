/**
 * markdown 简易渲染（粗体/斜体/代码/链接/列表/表格/引用/mermaid）——AgentPage 与记录详情共用
 */

function sanitizeMermaid(code) {
  let c = (code || '').replace(/\r/g, '');
  c = c.replace(/"([^"]*)"/g, (m, inner) =>
    inner.includes('\n') ? '"' + inner.replace(/\n+/g, '<br/>') + '"' : m);
  const t = c.trim();
  if (/^mindmap\b/.test(t) && !t.includes('\n')) {
    const protectedParts = [];
    const masked = t.replace(/\(\([^)]*\)\)|"[^"]*"/g, m => {
      protectedParts.push(m);
      return `\x00${protectedParts.length - 1}\x00`;
    });
    const tokens = masked.split(/\s+/).map(tok =>
      tok.replace(/\x00(\d+)\x00/g, (_, idx) => protectedParts[+idx]));
    if (tokens.length > 1) {
      c = tokens.map((tok, idx) =>
        idx === 0 || tok.startsWith('root') ? tok : '  ' + tok).join('\n');
    }
  }
  return c;
}

function renderMermaid(code) {
  return (
    <div style={{ position: 'relative', margin: '10px 0' }}>
      <div className="mermaid" style={{ display: 'flex', justifyContent: 'center', overflowX: 'auto' }}>
        {sanitizeMermaid(code)}
      </div>
    </div>
  );
}

function renderInline(text) {
  const parts = (text || '').split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]*\]\([^)]*\)|~~[^~]+~~)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith('*') && p.endsWith('*') && p.length > 2) return <em key={i}>{p.slice(1, -1)}</em>;
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i} style={{ background: 'var(--soft)', padding: '1px 5px', borderRadius: 4, fontSize: '0.92em' }}>{p.slice(1, -1)}</code>;
    const lm = p.match(/^\[([^\]]*)\]\(([^)]*)\)$/);
    if (lm) {
      const href = lm[2];
      if (/^(https?:|#|\/)/.test(href)) {
        return <a key={i} href={href} target="_blank" rel="noreferrer"
          style={{ color: 'var(--accent)', textDecoration: 'underline' }}>{lm[1]}</a>;
      }
      return lm[0];
    }
    if (p.startsWith('~~') && p.endsWith('~~')) return <del key={i} style={{ color: 'var(--text-dim)' }}>{p.slice(2, -2)}</del>;
    return p;
  });
}

let outSeq = 0;
export function renderMarkdown(text) {
  const lines = (text || '').split('\n');
  const out = [];
  let fence = null;
  let fenceLines = [];
  const flushFence = () => {
    if (fence !== null) {
      const code = fenceLines.join('\n');
      if (fence === 'mermaid') out.push(renderMermaid(code));
      else out.push(<pre key={`p${out.length}`} style={{ background: 'var(--soft)', padding: '10px 12px', borderRadius: 8, overflowX: 'auto', fontSize: 12.5, lineHeight: 1.6 }}>{code}</pre>);
      fenceLines = [];
    }
    fence = null;
  };
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (fence !== null) {
      if (trimmed.startsWith('```')) flushFence();
      else fenceLines.push(line);
      i++; continue;
    }
    const fm = trimmed.match(/^```(\w*)\s*$/);
    if (fm) { fence = fm[1] || ''; i++; continue; }
    if (/^(flowchart|graph)\s+(TD|LR|TB|RL|BT)\b/.test(trimmed) || /^mindmap\b/.test(trimmed)) {
      const block = [trimmed];
      let j = i + 1;
      while (j < lines.length && lines[j].trim() !== '') { block.push(lines[j]); j++; }
      out.push(renderMermaid(block.join('\n')));
      i = j; continue;
    }
    if (trimmed.startsWith('|') && i + 1 < lines.length &&
        /^\|[\s\-:|]+\|?$/.test(lines[i + 1].trim()) && lines[i + 1].includes('-')) {
      const headers = trimmed.split('|').slice(1, -1).map(c => c.trim());
      const rows = [];
      let j = i + 2;
      while (j < lines.length && lines[j].trim().startsWith('|')) {
        rows.push(lines[j].trim().split('|').slice(1, -1).map(c => c.trim()));
        j++;
      }
      out.push(
        <div key={`tbl${outSeq++}`} style={{ overflowX: 'auto', margin: '10px 0' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13, lineHeight: 1.6 }}>
            <thead><tr>{headers.map((h, k) => (
              <th key={k} style={{ border: '1px solid var(--border)', padding: '6px 10px', background: 'var(--soft)', fontWeight: 600, textAlign: 'left' }}>{renderInline(h)}</th>
            ))}</tr></thead>
            <tbody>{rows.map((r, k) => (
              <tr key={k}>{r.map((c, j) => (
                <td key={j} style={{ border: '1px solid var(--border)', padding: '6px 10px' }}>{renderInline(c)}</td>
              ))}</tr>
            ))}</tbody>
          </table>
        </div>
      );
      i = j; continue;
    }
    const imgMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imgMatch) {
      out.push(<div key={i} style={{ margin: '8px 0' }}>
        <img src={imgMatch[2]} alt={imgMatch[1]}
          style={{ maxWidth: '100%', maxHeight: 480, borderRadius: 8, border: '1px solid var(--border)' }} />
      </div>);
      i++; continue;
    }
    if (trimmed.startsWith('> ')) {
      out.push(<blockquote key={i} style={{ margin: '8px 0', padding: '6px 12px', borderLeft: '3px solid var(--border)', color: 'var(--text-dim)', background: 'var(--soft)', borderRadius: 4 }}>{renderInline(trimmed.slice(2))}</blockquote>);
    } else if (/^[-*] \[[ xX]\] /.test(trimmed)) {
      const checked = /^[-*] \[[xX]\] /.test(trimmed);
      out.push(<div key={i} style={{ paddingLeft: '1.2em', margin: '2px 0', display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span style={{ color: checked ? 'var(--success)' : 'var(--text-dim)', fontSize: 12 }}>{checked ? '☑' : '☐'}</span>
        <span style={{ textDecoration: checked ? 'line-through' : 'none', color: checked ? 'var(--text-dim)' : 'inherit' }}>
          {renderInline(trimmed.replace(/^[-*] \[[ xX]\] /, ''))}
        </span>
      </div>);
    } else if (/^[-*] |^\d+\. /.test(trimmed)) {
      out.push(<div key={i} style={{ paddingLeft: '1.2em', margin: '2px 0' }}>· {renderInline(trimmed.replace(/^[-*] |^\d+\. /, ''))}</div>);
    } else if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      out.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '12px 0' }} />);
    } else if (trimmed.startsWith('#### ')) {
      out.push(<div key={i} style={{ fontWeight: 700, fontSize: 13, margin: '6px 0 2px', color: 'var(--text-dim)' }}>{renderInline(trimmed.slice(5))}</div>);
    } else if (trimmed.startsWith('### ')) {
      out.push(<div key={i} style={{ fontWeight: 700, fontSize: 13.5, margin: '8px 0 3px', color: 'var(--text)' }}>{renderInline(trimmed.slice(4))}</div>);
    } else if (trimmed.startsWith('## ')) {
      out.push(<div key={i} style={{ fontWeight: 700, fontSize: 15, margin: '10px 0 4px' }}>{renderInline(trimmed.slice(3))}</div>);
    } else if (trimmed.startsWith('# ')) {
      out.push(<div key={i} style={{ fontWeight: 700, fontSize: 17, margin: '12px 0 6px' }}>{renderInline(trimmed.slice(2))}</div>);
    } else if (!trimmed) {
      out.push(<div key={i} style={{ height: 6 }} />);
    } else {
      out.push(<div key={i} style={{ margin: '2px 0' }}>{renderInline(trimmed)}</div>);
    }
    i++;
  }
  flushFence();
  return out;
}
