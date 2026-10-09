import { AlertTriangle } from "lucide-react";

export function Sev({ s }) {
  const v = (s || "info").toLowerCase();
  return <span className={`sev sev-${v}`}>{v}</span>;
}

export function StatusPill({ status }) {
  const map = {
    online: "#22c55e", healthy: "#22c55e", ok: "#22c55e", resolved: "#22c55e", closed: "#64748b",
    new: "#06b6d4", open: "#06b6d4", triaged: "#3b82f6", investigating: "#fbbf24",
    degraded: "#fbbf24", warning: "#fbbf24", escalated: "#fb923c", contained: "#3b82f6",
    offline: "#64748b", inactive: "#64748b", error: "#f87171", false_positive: "#64748b",
  };
  const c = map[(status || "").toLowerCase()] || "#64748b";
  return (
    <span className="pill" data-testid={`status-${status}`}>
      <span className="status-dot" style={{ background: c }} />
      <span style={{ textTransform: "capitalize" }}>{(status || "").replace(/_/g, " ")}</span>
    </span>
  );
}

export function Kpi({ label, value, sub, accent, testId, onClick }) {
  return (
    <div className="card p-3.5 fade-in" data-testid={testId}
         onClick={onClick} style={{ cursor: onClick ? "pointer" : "default" }}>
      <div className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>{label}</div>
      <div className="kpi-val mt-2" style={{ color: accent || "var(--text)" }}>{value}</div>
      {sub && <div className="text-[11px] mt-1.5" style={{ color: "var(--text-2)" }}>{sub}</div>}
    </div>
  );
}

export function Empty({ msg, testId }) {
  return (
    <div className="flex flex-col items-center justify-center py-16" style={{ color: "var(--text-3)" }} data-testid={testId}>
      <AlertTriangle size={28} />
      <div className="mt-3 text-sm">{msg || "No data available"}</div>
    </div>
  );
}

export function Loading() {
  return <div className="p-10 text-center text-sm" style={{ color: "var(--text-3)" }}>Loading…</div>;
}

export function PageHead({ title, desc, children, testId }) {
  return (
    <div className="flex items-start justify-between mb-4 flex-wrap gap-3" data-testid={testId}>
      <div>
        <h1 className="font-head text-xl font-bold" style={{ color: "var(--text)" }}>{title}</h1>
        {desc && <p className="text-[13px] mt-0.5" style={{ color: "var(--text-2)" }}>{desc}</p>}
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}

export const SEV_COLORS = { critical: "#F87171", high: "#FB923C", medium: "#FBBF24", low: "#60A5FA", info: "#38BDF8" };
export const fmtTime = (t) => { try { return new Date(t).toISOString().slice(0, 19).replace("T", " "); } catch { return t; } };
