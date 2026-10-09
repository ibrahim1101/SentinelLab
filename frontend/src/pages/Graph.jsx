import { useEffect, useRef, useState, useCallback } from "react";
import client from "@/lib/api";
import { PageHead, Loading } from "@/components/common";
import { Share2, Crosshair } from "lucide-react";

const W = 1000, H = 620;
const COLORS = { alert: "#F87171", host: "#5B8DEF", ip: "#22B8CF", user: "#FBBF24",
  process: "#A78BFA", indicator: "#FB923C", investigation: "#22C55E" };
const RADIUS = { alert: 15, indicator: 12, investigation: 13, host: 11, ip: 10, user: 10, process: 9 };

function runLayout(nodes, edges) {
  const k = Math.sqrt((W * H) / Math.max(nodes.length, 1)) * 0.55;
  nodes.forEach((n, i) => {
    if (n.x == null) {
      const a = (i / nodes.length) * 2 * Math.PI;
      n.x = W / 2 + Math.cos(a) * 140 + Math.random() * 20;
      n.y = H / 2 + Math.sin(a) * 140 + Math.random() * 20;
    }
  });
  const idx = Object.fromEntries(nodes.map((n, i) => [n.id, i]));
  const adj = edges.map((e) => [idx[e.source], idx[e.target]]).filter(([a, b]) => a != null && b != null);
  for (let it = 0; it < 170; it++) {
    const disp = nodes.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < nodes.length; i++)
      for (let j = i + 1; j < nodes.length; j++) {
        let dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
        let d = Math.hypot(dx, dy) || 0.01;
        const rep = (k * k) / d, ux = dx / d, uy = dy / d;
        disp[i].x += ux * rep; disp[i].y += uy * rep;
        disp[j].x -= ux * rep; disp[j].y -= uy * rep;
      }
    for (const [a, b] of adj) {
      let dx = nodes[a].x - nodes[b].x, dy = nodes[a].y - nodes[b].y;
      let d = Math.hypot(dx, dy) || 0.01;
      const att = (d * d) / k, ux = dx / d, uy = dy / d;
      disp[a].x -= ux * att; disp[a].y -= uy * att;
      disp[b].x += ux * att; disp[b].y += uy * att;
    }
    const t = 12 * (1 - it / 170) + 1;
    nodes.forEach((n, i) => {
      if (n.fixed) return;
      let dl = Math.hypot(disp[i].x, disp[i].y) || 0.01;
      n.x += (disp[i].x / dl) * Math.min(dl, t);
      n.y += (disp[i].y / dl) * Math.min(dl, t);
      n.x += (W / 2 - n.x) * 0.012; n.y += (H / 2 - n.y) * 0.012;
      n.x = Math.max(34, Math.min(W - 34, n.x));
      n.y = Math.max(28, Math.min(H - 28, n.y));
    });
  }
  return nodes;
}

export default function Graph() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [sel, setSel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stype, setStype] = useState("alert");
  const [sval, setSval] = useState("");
  const svgRef = useRef();
  const drag = useRef(null);

  const build = useCallback(async (seedType, seedValue, merge = false) => {
    setLoading(true);
    const { data } = await client.post("/graph", { seed_type: seedType, seed_value: seedValue });
    setNodes((prev) => {
      const posMap = Object.fromEntries(prev.map((n) => [n.id, n]));
      const merged = {};
      (merge ? prev : []).forEach((n) => { merged[n.id] = n; });
      data.nodes.forEach((n) => {
        merged[n.id] = { ...n, x: posMap[n.id]?.x, y: posMap[n.id]?.y };
      });
      const arr = Object.values(merged);
      const eMap = {};
      (merge ? edges : []).forEach((e) => { eMap[`${e.source}|${e.target}|${e.label}`] = e; });
      data.edges.forEach((e) => { eMap[`${e.source}|${e.target}|${e.label}`] = e; });
      const allEdges = Object.values(eMap).filter((e) => arr.find((n) => n.id === e.source) && arr.find((n) => n.id === e.target));
      runLayout(arr, allEdges);
      setEdges(allEdges);
      return [...arr];
    });
    setLoading(false);
  }, [edges]);

  useEffect(() => { build("alert", null, false); /* eslint-disable-next-line */ }, []);

  const toSvg = (clientX, clientY) => {
    const r = svgRef.current.getBoundingClientRect();
    return { x: ((clientX - r.left) / r.width) * W, y: ((clientY - r.top) / r.height) * H };
  };
  const onDown = (n, e) => { drag.current = { id: n.id, moved: false, startX: e.clientX, startY: e.clientY }; };
  const onMove = (e) => {
    if (!drag.current) return;
    const d = drag.current;
    if (Math.hypot(e.clientX - d.startX, e.clientY - d.startY) > 4) d.moved = true;
    const p = toSvg(e.clientX, e.clientY);
    setNodes((ns) => ns.map((n) => (n.id === d.id ? { ...n, x: p.x, y: p.y, fixed: true } : n)));
  };
  const onUp = (n) => {
    const d = drag.current; drag.current = null;
    if (d && !d.moved) { setSel(n); }
  };

  const expand = (n) => { const [t, ...rest] = n.id.split(":"); build(t, rest.join(":"), true); };

  return (
    <div data-testid="graph-page">
      <PageHead title="Investigation Graph" desc="Pivot visually across alerts, hosts, users, IPs & indicators">
        <select className="inp max-w-[130px]" value={stype} onChange={(e) => setStype(e.target.value)} data-testid="graph-seed-type">
          {["alert", "ip", "host", "user", "indicator"].map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input className="inp max-w-[200px] font-mono text-[12px]" placeholder="seed value / alert id" value={sval} onChange={(e) => setSval(e.target.value)} data-testid="graph-seed-value" />
        <button className="btn btn-primary btn-sm" onClick={() => build(stype, sval || null, false)} data-testid="graph-build"><Share2 size={13} /> Build</button>
      </PageHead>

      <div className="flex gap-4">
        <div className="card flex-1 relative overflow-hidden" style={{ minHeight: 560 }} data-testid="graph-canvas">
          {loading && <div className="absolute inset-0 grid place-items-center z-10 text-[13px]" style={{ color: "var(--text-3)" }}>Computing layout…</div>}
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 560 }}
            onPointerMove={onMove} onPointerUp={() => (drag.current = null)} onPointerLeave={() => (drag.current = null)}>
            {edges.map((e, i) => {
              const a = nodes.find((n) => n.id === e.source), b = nodes.find((n) => n.id === e.target);
              if (!a || !b) return null;
              return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--border)" strokeWidth="1" />;
            })}
            {nodes.map((n) => (
              <g key={n.id} transform={`translate(${n.x},${n.y})`} style={{ cursor: "pointer" }}
                onPointerDown={(e) => onDown(n, e)} onPointerUp={() => onUp(n)}
                onDoubleClick={() => expand(n)} data-testid={`node-${n.id}`}>
                <circle r={RADIUS[n.type] || 9} fill={COLORS[n.type] || "#888"} fillOpacity={sel?.id === n.id ? 1 : 0.85}
                  stroke={sel?.id === n.id ? "#fff" : "var(--bg)"} strokeWidth={sel?.id === n.id ? 2 : 1.5} />
                <text y={-(RADIUS[n.type] || 9) - 5} textAnchor="middle" fontSize="10" fontFamily="JetBrains Mono"
                  fill="var(--text-2)" style={{ pointerEvents: "none" }}>{n.label.length > 22 ? n.label.slice(0, 20) + "…" : n.label}</text>
              </g>
            ))}
          </svg>
          <div className="absolute bottom-2 left-3 flex gap-2.5 flex-wrap text-[10.5px]" style={{ color: "var(--text-2)" }}>
            {Object.entries(COLORS).map(([t, c]) => <span key={t} className="flex items-center gap-1"><span className="status-dot" style={{ background: c }} />{t}</span>)}
          </div>
          <div className="absolute top-2 right-3 text-[10.5px]" style={{ color: "var(--text-3)" }}>{nodes.length} nodes · {edges.length} edges · double-click to expand</div>
        </div>

        <div className="w-64 shrink-0 card p-4" data-testid="graph-detail">
          <div className="flex items-center gap-2 mb-2"><Crosshair size={14} style={{ color: "var(--cyan)" }} /><span className="font-head font-semibold text-[14px]">Node</span></div>
          {!sel ? <div className="text-[12.5px] py-6 text-center" style={{ color: "var(--text-3)" }}>Click a node to inspect; double-click to expand its connections.</div> : (
            <>
              <div className="pill mb-2" style={{ color: COLORS[sel.type] }}>{sel.type}</div>
              <div className="font-mono text-[12.5px] mb-3 break-all" style={{ color: "var(--text)" }}>{sel.label}</div>
              {Object.entries(sel.meta || {}).map(([k, v]) => <div key={k} className="flex justify-between text-[12px] border-b py-1"><span style={{ color: "var(--text-3)" }}>{k}</span><span className="font-mono" style={{ color: "var(--text)" }}>{String(v)}</span></div>)}
              <button className="btn btn-primary btn-sm w-full justify-center mt-3" onClick={() => expand(sel)} data-testid="graph-expand"><Share2 size={13} /> Expand connections</button>
              <div className="text-[11px] mt-3" style={{ color: "var(--text-3)" }}>Connected to {edges.filter((e) => e.source === sel.id || e.target === sel.id).length} node(s).</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
