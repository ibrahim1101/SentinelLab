import { useEffect, useState } from "react";
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import client from "@/lib/api";
import { PageHead, Loading, StatusPill, fmtTime } from "@/components/common";
import { Gauge, Activity, AlertTriangle, Database, RefreshCw, Clock } from "lucide-react";

const tip = { background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, color: "var(--text)" };

export default function Observatory() {
  const [d, setD] = useState(null);
  const load = () => client.get("/observatory").then(({ data }) => setD(data));
  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);
  if (!d) return <Loading />;

  const Stat = ({ icon: I, label, value, color, sub, tid }) => (
    <div className="card p-3.5 flex items-center gap-3" data-testid={tid}>
      <div className="grid place-items-center w-10 h-10 rounded-md" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}><I size={18} style={{ color }} /></div>
      <div><div className="kpi-val" style={{ fontSize: 22, color }}>{value}</div><div className="text-[11px]" style={{ color: "var(--text-3)" }}>{label}</div>{sub && <div className="text-[10px]" style={{ color: "var(--text-3)" }}>{sub}</div>}</div>
    </div>
  );

  return (
    <div data-testid="observatory-page">
      <PageHead title="Pipeline Observatory" desc="Live ingestion metrics, parser health & source throughput">
        <button className="btn btn-sm" onClick={load} data-testid="obs-refresh"><RefreshCw size={13} /> Refresh</button>
      </PageHead>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
        <Stat icon={Activity} label="Current EPS" value={d.eps_current} color="var(--cyan)" sub="events/sec (1h avg)" tid="obs-eps" />
        <Stat icon={Database} label="Indexed Events" value={d.total_indexed.toLocaleString()} color="#5B8DEF" tid="obs-indexed" />
        <Stat icon={Activity} label="Last 1h" value={d.events_last_1h.toLocaleString()} color="#22c55e" tid="obs-last1h" />
        <Stat icon={AlertTriangle} label="Parser Failures" value={d.parser_failures} color={d.parser_failures ? "#F87171" : "var(--text)"} tid="obs-errors" />
        <Stat icon={Clock} label="Ingest Delay" value={`${d.avg_ingest_delay_s}s`} color="#FBBF24" sub="avg event→index" tid="obs-delay" />
        <Stat icon={RefreshCw} label="Retry Queue" value={d.retry_queue_depth} color="var(--text)" sub={`backlog ${d.index_backlog}`} tid="obs-retry" />
      </div>

      <div className="card p-4 mb-4" data-testid="obs-eps-chart">
        <div className="flex items-center gap-2 mb-3"><Gauge size={14} style={{ color: "var(--cyan)" }} /><span className="font-head font-semibold text-[14px]">Events Per Second (last 60 min)</span></div>
        {d.eps_series.length ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={d.eps_series}>
              <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--cyan)" stopOpacity={0.4} /><stop offset="100%" stopColor="var(--cyan)" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "var(--text-3)" }} tickFormatter={(t) => t?.slice(11)} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-3)" }} width={34} />
              <Tooltip contentStyle={tip} />
              <Area type="monotone" dataKey="eps" stroke="var(--cyan)" fill="url(#g)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        ) : <div className="text-[12.5px] py-8 text-center" style={{ color: "var(--text-3)" }}>No ingestion in the last hour. Upload logs via Sources to see live throughput.</div>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card overflow-hidden lg:col-span-2" data-testid="obs-source-health">
          <div className="px-4 py-2.5 border-b font-head font-semibold text-[14px]">Source Health ({d.sources_online}/{d.sources_total} online)</div>
          <table className="dense w-full">
            <thead><tr><th>Source</th><th>Status</th><th>Events</th><th>1h Throughput</th><th>Parse Errors</th><th>Last Received</th></tr></thead>
            <tbody>
              {d.source_health.map((s) => (
                <tr key={s.id} className="border-t row-hover" data-testid={`obs-src-${s.id}`}>
                  <td style={{ color: "var(--text)" }}>{s.name}</td>
                  <td><StatusPill status={s.status} /></td>
                  <td className="font-mono" style={{ color: "var(--cyan)" }}>{(s.events_received || 0).toLocaleString()}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{s.throughput_1h}</td>
                  <td className="font-mono" style={{ color: s.parse_errors ? "#F87171" : "var(--text-3)" }}>{s.parse_errors}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{s.last_received ? fmtTime(s.last_received).slice(11) : "never"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card p-4" data-testid="obs-parser-errors">
          <div className="flex items-center gap-2 mb-2"><AlertTriangle size={14} style={{ color: "#F87171" }} /><span className="font-head font-semibold text-[14px]">Recent Parser Failures</span></div>
          {!d.recent_errors.length ? <div className="text-[12.5px] py-6 text-center" style={{ color: "var(--text-3)" }}>No parser failures — pipeline healthy.</div> : (
            <div className="max-h-72 overflow-auto space-y-2">
              {d.recent_errors.map((e, i) => (
                <div key={i} className="text-[11.5px] border-b pb-1.5">
                  <div className="font-mono" style={{ color: "#F87171" }}>{e.source_id}</div>
                  <div style={{ color: "var(--text-2)" }}>{e.error}</div>
                  <div className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.timestamp)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
