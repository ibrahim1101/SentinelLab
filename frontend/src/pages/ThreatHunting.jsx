import { useState } from "react";
import { BarChart, Bar, ResponsiveContainer, XAxis, Tooltip } from "recharts";
import { Play, Save, Terminal, Zap } from "lucide-react";
import client from "@/lib/api";
import { Sev, PageHead, Empty, fmtTime } from "@/components/common";
import { toast } from "sonner";

const tip = { background: "var(--card)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, color: "var(--text)" };
const TEMPLATES = [
  { label: "Failed Logins", q: "category:authentication AND outcome:failure" },
  { label: "Suspicious PowerShell", q: "process_name:powershell.exe" },
  { label: "Network Connections", q: "category:network" },
  { label: "Critical Severity", q: "severity:critical" },
  { label: "DNS Queries", q: "category:dns" },
  { label: "Admin Activity", q: "username:admin" },
];

export default function ThreatHunting() {
  const [query, setQuery] = useState("category:authentication AND outcome:failure");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async (q) => {
    const qq = q ?? query;
    setBusy(true);
    try { const { data } = await client.post("/hunt", { query: qq, limit: 200 }); setRes(data); }
    catch { toast.error("Query failed"); } finally { setBusy(false); }
  };
  const save = async () => {
    const name = prompt("Save hunt as:"); if (!name) return;
    await client.post("/hunt/saved", { name, query }); toast.success("Hunt saved");
  };

  return (
    <div data-testid="threat-hunting-workspace">
      <PageHead title="Threat Hunting" desc="Advanced search and investigation workspace">
        <button className="btn btn-sm" onClick={save} data-testid="save-hunt"><Save size={13} /> Save</button>
      </PageHead>

      <div className="card p-3 mb-3">
        <div className="flex items-center gap-2 mb-2">
          <Terminal size={14} style={{ color: "var(--cyan)" }} />
          <input className="inp font-mono text-[13px]" value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()} placeholder='e.g. category:authentication AND outcome:failure' data-testid="hunt-query" />
          <button className="btn btn-primary" onClick={() => run()} disabled={busy} data-testid="hunt-run"><Play size={13} /> {busy ? "Running…" : "Run"}</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {TEMPLATES.map((t) => (
            <button key={t.label} className="pill" style={{ cursor: "pointer" }} onClick={() => { setQuery(t.q); run(t.q); }} data-testid={`template-${t.label.replace(/\s/g, "-")}`}>
              <Zap size={11} style={{ color: "var(--cyan)" }} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      {res && (
        <>
          <div className="flex items-center gap-4 mb-3 text-[12px]" style={{ color: "var(--text-3)" }} data-testid="hunt-stats">
            <span><b style={{ color: "var(--text)" }}>{res.total.toLocaleString()}</b> matches</span>
            <span>{res.returned} shown</span>
            <span>execution: <b style={{ color: "var(--cyan)" }}>{res.took_ms}ms</b></span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-3">
            <div className="card p-3 lg:col-span-1">
              <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Event Timeline</div>
              <ResponsiveContainer width="100%" height={110}>
                <BarChart data={res.timeline}><XAxis dataKey="time" hide /><Tooltip contentStyle={tip} /><Bar dataKey="count" fill="var(--cyan)" radius={[2, 2, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </div>
            {[["Top Source IPs", res.top_src_ip], ["Top Hosts", res.top_host], ["Top Processes", res.top_process]].map(([title, items]) => (
              <div key={title} className="card p-3">
                <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>{title}</div>
                {items.length ? items.map((it) => (
                  <div key={it.value} className="flex justify-between text-[12px] py-0.5"><span className="font-mono truncate" style={{ color: "var(--text-2)" }}>{it.value}</span><span className="font-mono" style={{ color: "var(--cyan)" }}>{it.count}</span></div>
                )) : <div className="text-[11px]" style={{ color: "var(--text-3)" }}>—</div>}
              </div>
            ))}
          </div>
          <div className="card overflow-hidden">
            {!res.events.length ? <Empty msg="No results" /> : (
              <table className="dense w-full">
                <thead><tr><th>Timestamp</th><th>Severity</th><th>Type</th><th>Host</th><th>Src IP</th><th>User</th></tr></thead>
                <tbody>
                  {res.events.map((e) => (
                    <tr key={e.id} className="border-t row-hover" data-testid={`hunt-row-${e.id}`}>
                      <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.timestamp)}</td>
                      <td><Sev s={e.severity} /></td><td style={{ color: "var(--text-2)" }}>{e.event_type}</td>
                      <td className="font-mono" style={{ color: "var(--text)" }}>{e.host || "—"}</td>
                      <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.src_ip || "—"}</td>
                      <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.username || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
      {!res && <div className="card p-10 text-center text-[13px]" style={{ color: "var(--text-3)" }}>Run a query to hunt across your telemetry.</div>}
    </div>
  );
}
