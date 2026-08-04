import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

/**
 * 记忆星图 — 把人生数据可视化为星空
 * 星星=记忆/事件/记录，大小=重要度，颜色=类型，连线=关联
 */
// 类型基色（HSL）：色相 = 类型；饱和度/亮度由「情绪 × 长期影响」动态调整
const TYPE_HSL: Record<string, { h: number; s: number; l: number }> = {
  memory: { h: 42, s: 78, l: 60 },    // 金 — 生命记忆（日记浓缩，可溯源）
  event: { h: 6, s: 72, l: 62 },      // 玫红 — 人生事件
  simulation: { h: 220, s: 8, l: 62 }, // 灰 — 未来模拟（不参与情绪分色）
  click: { h: 212, s: 62, l: 60 },    // 蓝 — 点击数据
  team: { h: 34, s: 78, l: 58 },      // 琥珀 — 组队数据
};

/**
 * 动态分色：类型定色相；长期影响（lasting）越高越亮越饱和，
 * 消极情绪偏冷偏暗；记忆点被后来的生活反复回响 → 颜色逐渐变亮。
 * 模拟（灰色）固定低饱和，与其他记忆区分。
 */
function nodeColor(n: Node): string {
  const base = TYPE_HSL[n.type] || TYPE_HSL.memory;
  if (n.type === "simulation") return `hsl(${base.h}, ${base.s}%, ${base.l}%)`;
  const lasting = typeof n.lasting === "number" ? n.lasting : 0.5;
  const neg = n.emotion === "negative";
  const s = Math.min(100, base.s * (0.5 + 0.55 * lasting) * (neg ? 0.72 : 1));
  const l = Math.min(90, base.l * (0.42 + 0.68 * lasting) * (neg ? 0.82 : 1));
  return `hsl(${base.h}, ${s.toFixed(0)}%, ${l.toFixed(0)}%)`;
}

interface Node {
  id: string; type: string; title: string; content: string;
  importance: number; date: string; source_id?: number;
  emotion?: "positive" | "negative" | "neutral";
  lasting?: number;  // 长期影响 0-1（被后来生活回响的程度）
}
interface Link { source: string; target: string; weight: number; }

export default function StarMap() {
  const [data, setData] = useState<{ nodes: Node[]; links: Link[]; stats: any } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");

  const [selected, setSelected] = useState<Node | null>(null);
  const [hovered, setHovered] = useState<Node | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  // ref 镜像：hover/选中只影响重绘，不触发力导向重新布局（否则节点会"跑"）
  const hoveredRef = useRef<Node | null>(null);
  const selectedRef = useRef<Node | null>(null);
  useEffect(() => { hoveredRef.current = hovered; }, [hovered]);
  useEffect(() => { selectedRef.current = selected; }, [selected]);

  // 加载星图数据；30s 轮询（数据有变化才更新，避免布局跳动）
  useEffect(() => {
    let lastKey = "";
    const load = () =>
      fetch("/api/mirror/starmap", { credentials: "include" })
        .then((r) => r.json())
        .then((d) => {
          const key = `${d?.stats?.nodes ?? 0}|${d?.stats?.links ?? 0}`;
          if (key !== lastKey) {
            lastKey = key;
            setData(d);
          }
        })
        .catch(() => {});
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, []);

  const filtered = useMemo(() => {
    if (!data) return { nodes: data?.nodes || [], links: data?.links || [] };
    if (!search.trim()) return { nodes: data.nodes, links: data.links };
    const kw = search.trim();
    const ids = new Set(
      data.nodes.filter((n) => (n.title + n.content).includes(kw)).map((n) => n.id)
    );
    return {
      nodes: data.nodes.filter((n) => ids.has(n.id)),
      links: data.links.filter((l) => ids.has(l.source) && ids.has(l.target)),
    };
  }, [data, search]);

  // ── 力导向布局 + 渲染（只随数据变化重建，hover/选中不触发重建） ──
  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap || !data) return;

    const ctx = canvas.getContext("2d")!;
    let W = wrap.clientWidth, H = wrap.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);

    // 节点位置初始化（中心散开）
    const pos = new Map<string, { x: number; y: number; vx: number; vy: number }>();
    filtered.nodes.forEach((n, i) => {
      const angle = (i / Math.max(1, filtered.nodes.length)) * Math.PI * 2;
      const rad = Math.min(W, H) * 0.3 * (0.5 + Math.random() * 0.5);
      pos.set(n.id, { x: W / 2 + Math.cos(angle) * rad, y: H / 2 + Math.sin(angle) * rad, vx: 0, vy: 0 });
    });

    // 预计算力导向（斥力 + 弹簧 + 向心）；节点越多迭代越少（千级节点仍保持秒级布局）
    const iters = filtered.nodes.length > 700 ? 90 : filtered.nodes.length > 300 ? 130 : 200;
    for (let iter = 0; iter < iters; iter++) {
      for (const [id, p] of pos) {
        // 向心力
        p.vx += (W / 2 - p.x) * 0.004;
        p.vy += (H / 2 - p.y) * 0.004;
        for (const [id2, q] of pos) {
          if (id === id2) continue;
          const dx = p.x - q.x, dy = p.y - q.y;
          const d2 = dx * dx + dy * dy || 1;
          const f = 4200 / d2;
          p.vx += (dx / Math.sqrt(d2)) * f;
          p.vy += (dy / Math.sqrt(d2)) * f;
        }
      }
      // 弹簧（沿边）
      for (const l of filtered.links) {
        const a = pos.get(l.source), b = pos.get(l.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const target = 110;
        const f = (dist - target) * 0.012;
        const fx = (dx / dist) * f, fy = (dy / dist) * f;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
      for (const [, p] of pos) {
        p.vx *= 0.82; p.vy *= 0.82;
        p.x += p.vx; p.y += p.vy;
      }
    }

    // 背景星星（静态散点）
    const bgStars = Array.from({ length: 90 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: 0.4 + Math.random() * 1.1, a: 0.15 + Math.random() * 0.35,
    }));

    let zoom = 1, panX = 0, panY = 0;
    let dragging: string | null = null;   // 拖拽中的节点 id
    let panning = false;                   // 空白处拖拽平移画布
    let downX = 0, downY = 0, moved = false;
    let mouseX = 0, mouseY = 0;

    // 非线性大小映射：重要度差异更明显（0.3→7px，0.95→26px）
    const nodeRadius = (n: Node) => 5 + Math.pow(n.importance, 1.6) * 22;

    function hitTest(x: number, y: number): Node | null {
      const wx = (x - panX) / zoom, wy = (y - panY) / zoom;
      let best: Node | null = null, bestD = Infinity;
      for (const n of filtered.nodes) {
        const p = pos.get(n.id);
        if (!p) continue;
        const d = Math.hypot(p.x - wx, p.y - wy);
        if (d < nodeRadius(n) + 6 && d < bestD) { bestD = d; best = n; }
      }
      return best;
    }

    let raf = 0;
    function draw() {
      ctx.clearRect(0, 0, W, H);
      // 深空背景
      const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) * 0.75);
      g.addColorStop(0, "#171512");
      g.addColorStop(1, "#0B0A08");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
      // 背景散星
      ctx.fillStyle = "#FFFFFF";
      for (const s of bgStars) {
        ctx.globalAlpha = s.a;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoom, zoom);

      const focusId = selectedRef.current?.id || hoveredRef.current?.id || null;

      // 连线
      for (const l of filtered.links) {
        const a = pos.get(l.source), b = pos.get(l.target);
        if (!a || !b) continue;
        const dim = focusId && focusId !== l.source && focusId !== l.target;
        ctx.strokeStyle = dim ? "rgba(201,168,124,0.03)" : `rgba(201,168,124,${0.10 + l.weight * 0.18})`;
        ctx.lineWidth = 0.6 + l.weight;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }

      // 节点
      for (const n of filtered.nodes) {
        const p = pos.get(n.id);
        if (!p) continue;
        const color = nodeColor(n);
        const r = nodeRadius(n);
        const isFocus = focusId === n.id;
        const isRelated = focusId && !isFocus && filtered.links.some(
          (l) => (l.source === focusId && l.target === n.id) || (l.target === focusId && l.source === n.id)
        );
        const dim = focusId && !isFocus && !isRelated;

        ctx.globalAlpha = dim ? 0.12 : 1;
        // 发光：仅焦点/关联/大节点开启（千级节点全开 shadow 会严重掉帧）
        ctx.shadowColor = color;
        ctx.shadowBlur = isFocus ? 30 : isRelated ? 14 : r > 15 ? 8 : 0;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
        // 核心亮点
        ctx.fillStyle = "rgba(255,255,255,0.9)";
        ctx.beginPath(); ctx.arc(p.x - r * 0.25, p.y - r * 0.25, Math.max(1.2, r * 0.3), 0, Math.PI * 2); ctx.fill();
        // 选中/悬停外圈
        if (isFocus) {
          ctx.strokeStyle = "rgba(255,255,255,0.75)";
          ctx.lineWidth = 1.3;
          ctx.beginPath(); ctx.arc(p.x, p.y, r + 5, 0, Math.PI * 2); ctx.stroke();
        }
        // 标签仅悬停/选中时显示（默认不打扰星空）
        if (isFocus && !dim) {
          ctx.font = "bold 11px 'PingFang SC', sans-serif";
          ctx.fillStyle = "rgba(237,234,228,0.9)";
          ctx.textAlign = "center";
          ctx.shadowColor = "rgba(0,0,0,0.8)";
          ctx.shadowBlur = 6;
          const label = (n.title || n.content || "").slice(0, 14);
          ctx.fillText(label, p.x, p.y - r - 8);
          ctx.shadowBlur = 0;
        }
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    }

    function onMouseDown(e: MouseEvent) {
      const rect = canvas.getBoundingClientRect();
      downX = e.clientX - rect.left; downY = e.clientY - rect.top;
      moved = false;
      const hit = hitTest(downX, downY);
      if (hit) dragging = hit.id;
      else panning = true;
    }

    function onMouseMove(e: MouseEvent) {
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left; mouseY = e.clientY - rect.top;
      if (dragging) {
        if (Math.abs(mouseX - downX) + Math.abs(mouseY - downY) > 4) moved = true;
        const p = pos.get(dragging);
        if (p) { p.x = (mouseX - panX) / zoom; p.y = (mouseY - panY) / zoom; }
        draw();
        return;
      }
      if (panning) {
        if (Math.abs(mouseX - downX) + Math.abs(mouseY - downY) > 4) moved = true;
        panX += mouseX - downX;
        panY += mouseY - downY;
        downX = mouseX; downY = mouseY;
        draw();
        return;
      }
      const hit = hitTest(mouseX, mouseY);
      setHovered(hit);
      draw();
    }

    function onMouseUp() {
      if (dragging && !moved) {
        // 未移动 = 点击 → 选中/取消
        const hit = hitTest(mouseX, mouseY);
        setSelected(hit || null);
      }
      dragging = null;
      panning = false;
      draw();
    }

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", () => { dragging = null; panning = false; setHovered(null); });
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      zoom = Math.min(2.4, Math.max(0.5, zoom * (e.deltaY < 0 ? 1.08 : 0.93)));
      draw();
    }, { passive: false });

    const onResize = () => {
      W = wrap.clientWidth; H = wrap.clientHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    };
    window.addEventListener("resize", onResize);

    draw();
    raf = requestAnimationFrame(function loop() {
      draw();
      raf = requestAnimationFrame(loop);
    });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, search]);

  const stats = data?.stats;

  return (
    <div style={{ padding: "28px 36px" }}>
      {/* 页头 */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 18 }}>
        <div>
          <p style={{
            display: "inline-block", padding: "3px 12px", borderRadius: 999, fontSize: "0.6rem",
            fontWeight: 600, letterSpacing: "0.18em", textTransform: "uppercase",
            color: "#C9A87C", background: "rgba(201,168,124,0.1)", border: "1px solid rgba(201,168,124,0.2)",
            marginBottom: 10,
          }}>
            Memory Constellation
          </p>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 700, letterSpacing: "-0.02em", color: "#EDEAE4" }}>记忆星图</h1>
          <p style={{ fontSize: "0.8rem", color: "#97917F", marginTop: 4, lineHeight: 1.6 }}>
            {stats
              ? `${stats.nodes} 颗星 · ${stats.links} 条连线 · ${stats.memories} 条记忆（源自 ${stats.records} 条日记）/ ${stats.events} 个事件 / ${stats.simulations} 条未来 / ${stats.clicks} 个点击 / ${stats.teams} 个战队`
              : "正在汇聚你的人生数据..."}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索记忆…"
            style={{
              background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)",
              color: "#EDEAE4", borderRadius: 8, padding: "8px 14px", outline: "none", fontSize: "0.82rem", width: 220,
            }}
          />
          <button
            onClick={() => { setRefreshing(true); fetch("/api/mirror/starmap?fresh=1", { credentials: "include" }).then(r => r.json()).then(setData).catch(() => {}).finally(() => setRefreshing(false)); }}
            disabled={refreshing}
            style={{
              background: "rgba(201,168,124,0.12)", border: "1px solid rgba(201,168,124,0.25)",
              color: "#C9A87C", borderRadius: 8, padding: "8px 14px", cursor: "pointer",
              fontSize: "0.78rem", fontWeight: 600,
            }}
          >
            {refreshing ? "刷新中…" : "↻ 刷新"}
          </button>
        </div>
      </div>

      {/* 星图画布 */}
      <div ref={wrapRef} style={{ position: "relative", height: "calc(100vh - 220px)", minHeight: 480, borderRadius: 16, overflow: "hidden", border: "1px solid rgba(255,255,255,0.08)" }}>
        <canvas ref={canvasRef} style={{ width: "100%", height: "100%", display: "block", cursor: "grab" }} />

        {/* 悬停提示 */}
        {hovered && !selected && (
          <div style={{ position: "absolute", left: 18, bottom: 18, maxWidth: 340, padding: "12px 16px", borderRadius: 10, background: "rgba(27,26,23,0.92)", border: "1px solid rgba(201,168,124,0.2)", backdropFilter: "blur(6px)" }}>
            <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#EDEAE4", marginBottom: 4 }}>
              {hovered.title || hovered.content.slice(0, 30)}
            </p>
            <p style={{ fontSize: "0.68rem", color: "#97917F" }}>
              {typeLabel(hovered.type)} · {hovered.date}
            </p>
          </div>
        )}

        {/* 选中详情面板 */}
        {selected && (
          <div style={{ position: "absolute", right: 18, top: 18, width: 300, maxHeight: "70%", overflowY: "auto", padding: "18px 20px", borderRadius: 14, background: "rgba(27,26,23,0.94)", border: "1px solid rgba(201,168,124,0.22)", boxShadow: "0 16px 48px rgba(0,0,0,0.5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ padding: "2px 10px", borderRadius: 999, fontSize: "0.62rem", fontWeight: 600, background: "rgba(201,168,124,0.12)", color: "#C9A87C" }}>
                {typeLabel(selected.type)}
              </span>
              <button onClick={() => setSelected(null)} style={{ border: "none", background: "none", color: "#6E695C", cursor: "pointer", fontSize: "1rem" }}>×</button>
            </div>
            <p style={{ fontSize: "0.92rem", fontWeight: 700, color: "#EDEAE4", marginBottom: 6 }}>{selected.title}</p>
            <p style={{ fontSize: "0.78rem", color: "#CFCBC2", lineHeight: 1.8, marginBottom: 10 }}>{selected.content}</p>
            <p style={{ fontSize: "0.68rem", color: "#97917F", marginBottom: 12 }}>
              {selected.date} · 重要度 {(selected.importance * 100).toFixed(0)}%
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {selected.source_type === "event" && selected.source_id && (
                <Link to={`/events/${selected.source_id}`} style={{ fontSize: "0.72rem", color: "#C9A87C", textDecoration: "none", border: "1px solid rgba(201,168,124,0.25)", padding: "5px 12px", borderRadius: 8 }}>查看事件 →</Link>
              )}
              {selected.source_type === "diary" && selected.source_id && (
                <Link to={`/journal/${selected.source_id}`} style={{ fontSize: "0.72rem", color: "#C9A87C", textDecoration: "none", border: "1px solid rgba(201,168,124,0.25)", padding: "5px 12px", borderRadius: 8 }}>溯源日记 →</Link>
              )}
              <button
                onClick={() => {
                  const el = document.getElementById("starmap-evidence");
                  if (el) el.style.display = el.style.display === "none" ? "block" : "none";
                }}
                style={{ fontSize: "0.72rem", color: "#C9A87C", border: "1px solid rgba(201,168,124,0.25)", background: "none", padding: "5px 12px", borderRadius: 8, cursor: "pointer" }}
              >
                🔍 证据链
              </button>
            </div>
          </div>
        )}

        {/* 无数据空态 */}
        {stats && stats.nodes === 0 && (
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <p style={{ fontSize: "2rem" }}>🌌</p>
            <p style={{ color: "#97917F", fontSize: "0.85rem" }}>星空中还没有星星——记录你的第一段经历，它会在这里亮起</p>
            <Link to="/journal" style={{ color: "#C9A87C", fontSize: "0.8rem" }}>去记录 →</Link>
          </div>
        )}
      </div>

      {/* 图例 */}
      <div style={{ display: "flex", gap: 18, marginTop: 14, justifyContent: "center", flexWrap: "wrap" }}>
        {[["memory", "生命记忆"], ["event", "人生事件"], ["simulation", "未来模拟"], ["click", "点击数据"], ["team", "组队数据"]].map(([t, label]) => (
          <span key={t} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.72rem", color: "#97917F" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: nodeColor({ type: t } as Node), boxShadow: "0 0 8px rgba(255,255,255,0.3)" }} />
            {label}
          </span>
        ))}
        <span style={{ fontSize: "0.72rem", color: "#6E695C" }}>· 颜色随人生演化：被后来生活反复回响的记忆更亮，消极时刻偏冷偏暗</span>
        <span style={{ fontSize: "0.72rem", color: "#6E695C" }}>· 空白拖拽平移 / 节点拖拽 / 滚轮缩放 / 点击查看 / 搜索定位</span>
      </div>
    </div>
  );
}

function typeLabel(t: string): string {
  switch (t) {
    case "memory": return "生命记忆";
    case "event": return "人生事件";
    case "simulation": return "未来模拟";
    case "click": return "点击数据";
    case "team": return "组队数据";
    default: return t;
  }
}
