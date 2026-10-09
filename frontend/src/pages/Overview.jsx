import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { RefreshCw, Activity, Bell, AlertOctagon, Radio, FolderSearch, Cpu, Server, FlaskConical } from "lucide-react";
import client from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { Kpi, Sev, Loading, PageHead, SEV_COLORS, fmtTime } from "@/components/common";

const tip = { background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, color: "var(--text)" };

export default function Overview() {
  const { range, current } = useWorkspace();
  const [d, setD] = useState(null);
  const nav = useNavigate();

  const load = () => client.get(`/dashboard/overview?time_range=${range}`).then(({ data }) => setD(data));
  useEffect(() => { setD(null); load(); }, [range]);

  if (!d) return <Loading />;
  const k = d.kpis;
  const sev = Object.entries(d.alerts_by_severity).map(([name, value]) => ({ name, value }));
  const sevTotal = sev.reduce((a, b) => a + b.value, 0);

  return (
    <div data-testid="overview-dashboard">
      <PageHead title="Overview" desc="Security operations at a glance" testId="overview-head">
        <button className="btn btn-sm" onClick={load} data-testid="refresh-btn"><RefreshCw size={13} /> Refresh</button>
      </PageHead>

      {d.is_demo_workspace && (
        <div className="mb-4 flex items-center gap-2 text-[12.5px] px-3 py-2 rounded" data-testid="demo-banner"
          style={{ background: "color-mix(in srgb, var(--cyan) 12%, transparent)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}>
          <FlaskConical size={15} /> Training Lab — all telemetry below is <b>synthetic</b> and isolated from production analytics.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-4">
        <Kpi label="Total Events" value={k.total_events.toLocaleString()} sub={`${k.eps} events/sec · ${k.all_events.toLocaleString()} all-time`} accent="var(--cyan)" testId="kpi-total-events" onClick={() => nav("/events")} />
        <Kpi label="Open Alerts" value={k.open_alerts} sub={`${k.critical_alerts} critical · ${k.high_alerts} high`} accent="#FB923C" testId="kpi-open-alerts" onClick={() => nav("/alerts")} />
        <Kpi label="High Severity" value={k.critical_alerts + k.high_alerts} sub="Needs triage" accent="#F87171" testId="kpi-high-severity" />
        <Kpi label="Active Sources" value={`${k.active_sources}/${k.active_sources + k.inactive_sources}`} sub={`${k.inactive_sources} inactive`} accent="#22c55e" testId="kpi-active-sources" onClick={() => nav("/sources")} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-4">
        <Kpi label="Investigations" value={k.active_investigations} accent="var(--blue)" testId="kpi-investigations" onClick={() => nav("/investigations")} />
        <Kpi label="Rules Triggered" value={k.rules_triggered} accent="var(--cyan)" testId="kpi-rules" onClick={() => nav("/rules")} />
        <Kpi label="Monitored Assets" value={k.monitored_assets} accent="var(--text)" testId="kpi-assets" />
        <Kpi label="Events/sec" value={k.eps} accent="#22c55e" testId="kpi-eps" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="card p-4 lg:col-span-2" data-testid="events-over-time">
          <div className="flex items-center gap-2 mb-3"><Activity size={14} style={{ color: "var(--cyan)" }} /><span className="font-head font-semibold text-[14px]">Events Over Time</span></div>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={d.events_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "var(--text-3)" }} tickFormatter={(t) => t?.slice(11, 13) + "h"} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-3)" }} width={30} />
              <Tooltip contentStyle={tip} cursor={{ fill: "var(--hover)" }} />
              <Bar dataKey="count" fill="var(--cyan)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4" data-testid="alerts-by-severity">
          <div className="font-head font-semibold text-[14px] mb-3">Alerts by Severity</div>
          <div className="relative">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={sev} dataKey="value" innerRadius={52} outerRadius={78} paddingAngle={2}>
                  {sev.map((s) => <Cell key={s.name} fill={SEV_COLORS[s.name]} />)}
                </Pie>
                <Tooltip contentStyle={tip} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 grid place-items-center pointer-events-none" style={{ bottom: 0 }}>
              <div className="text-center"><div className="kpi-val">{sevTotal}</div><div className="text-[10px]" style={{ color: "var(--text-3)" }}>TOTAL</div></div>
            </div>
          </div>
          <div className="space-y-1 mt-2">
            {sev.map((s) => <div key={s.name} className="flex items-center justify-between text-[12px]"><span className="flex items-center gap-1.5 capitalize"><span className="status-dot" style={{ background: SEV_COLORS[s.name] }} />{s.name}</span><span className="font-mono">{s.value}</span></div>)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4" data-testid="events-by-source">
          <div className="font-head font-semibold text-[14px] mb-3">Events by Source</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart layout="vertical" data={d.events_by_source} margin={{ left: 10 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: "var(--text-3)" }} />
              <YAxis type="category" dataKey="source" width={90} tick={{ fontSize: 9, fill: "var(--text-3)" }} />
              <Tooltip contentStyle={tip} cursor={{ fill: "var(--hover)" }} />
              <Bar dataKey="count" fill="var(--blue)" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-4 lg:col-span-2" data-testid="recent-alerts">
          <div className="font-head font-semibold text-[14px] mb-2">Recent Alerts</div>
          <table className="dense w-full">
            <thead><tr><th>Time</th><th>Severity</th><th>Title</th><th>Host</th><th>Status</th></tr></thead>
            <tbody>
              {d.recent_alerts.map((a) => (
                <tr key={a.id} className="row-hover cursor-pointer border-t" onClick={() => nav("/alerts")} data-testid={`recent-alert-${a.id}`}>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(a.created_at).slice(11)}</td>
                  <td><Sev s={a.severity} /></td>
                  <td style={{ color: "var(--text)" }}>{a.title}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{a.host || "—"}</td>
                  <td style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{a.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!d.recent_alerts.length && <div className="text-center py-6 text-[12px]" style={{ color: "var(--text-3)" }}>No recent alerts</div>}
        </div>
      </div>
    </div>
  );
}
