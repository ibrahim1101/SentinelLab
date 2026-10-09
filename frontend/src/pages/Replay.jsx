import { useEffect, useState } from "react";
import client from "@/lib/api";
import { PageHead, Sev } from "@/components/common";
import { Repeat, Play, FlaskConical, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function Replay() {
  const [samples, setSamples] = useState([]);
  const [format, setFormat] = useState("json");
  const [payload, setPayload] = useState("[]");
  const [expected, setExpected] = useState([]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { client.get("/replay/samples").then(({ data }) => setSamples(data.samples)); }, []);

  const loadSample = (s) => { setFormat(s.format); setPayload(s.payload); setExpected(s.expected_rules); setRes(null); };
  const run = async () => {
    setBusy(true);
    try {
      let body;
      try { body = format === "json" ? JSON.parse(payload) : payload; } catch { body = payload; }
      const { data } = await client.post("/replay", { format, payload: body, expected_rules: expected });
      setRes(data);
      if (data.comparison) data.comparison.passed ? toast.success("Regression PASSED") : toast.error("Regression FAILED — see comparison");
      else toast.success(`${data.triggered_count} rule(s) triggered`);
    } catch (e) { toast.error("Replay failed — check payload format"); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="replay-page">
      <PageHead title="Detection Replay Lab" desc="Replay telemetry against rules — isolated, no alerts persisted" />
      <div className="mb-4 flex items-center gap-2 text-[12.5px] px-3 py-2 rounded" data-testid="isolation-banner"
        style={{ background: "color-mix(in srgb, var(--cyan) 10%, transparent)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}>
        <FlaskConical size={15} /> Isolated sandbox — replayed events are evaluated in-memory and <b>never persisted</b> to production events or alerts.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Sample Scenarios</div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {samples.map((s) => <button key={s.name} className="pill" style={{ cursor: "pointer" }} onClick={() => loadSample(s)} data-testid={`sample-${s.name.split(" ")[0]}`}><Repeat size={11} style={{ color: "var(--cyan)" }} /> {s.name}</button>)}
          </div>
          <div className="flex gap-2 mb-2">
            <select className="inp max-w-[120px]" value={format} onChange={(e) => setFormat(e.target.value)} data-testid="replay-format">
              {["json", "jsonl", "csv", "syslog", "cef"].map((f) => <option key={f} value={f}>{f.toUpperCase()}</option>)}
            </select>
            <button className="btn btn-primary ml-auto" onClick={run} disabled={busy} data-testid="replay-run"><Play size={13} /> {busy ? "Replaying…" : "Run Replay"}</button>
          </div>
          {expected.length > 0 && <div className="text-[11.5px] mb-2" style={{ color: "var(--text-3)" }}>Expected: {expected.map((r) => <span key={r} className="pill mr-1" style={{ color: "var(--cyan)" }}>{r}</span>)}</div>}
          <textarea className="inp font-mono text-[11px]" rows={14} value={payload} onChange={(e) => setPayload(e.target.value)} data-testid="replay-payload" />
        </div>

        <div className="card p-4" data-testid="replay-results">
          <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Results</div>
          {!res ? <div className="text-[13px] py-10 text-center" style={{ color: "var(--text-3)" }}>Load a sample or paste telemetry, then Run Replay.</div> : (
            <>
              <div className="flex gap-4 text-[12px] mb-3" style={{ color: "var(--text-3)" }}>
                <span><b style={{ color: "var(--text)" }}>{res.parsed_events}</b> parsed</span>
                <span><b style={{ color: "var(--cyan)" }}>{res.triggered_count}</b> rules triggered</span>
                <span>{res.rules_evaluated} evaluated</span>
                <span>took <b style={{ color: "var(--cyan)" }}>{res.took_ms}ms</b></span>
              </div>
              {res.comparison && (
                <div className="mb-3 p-3 rounded" style={{ background: "var(--bg)", border: `1px solid ${res.comparison.passed ? "#22c55e" : "#F87171"}` }} data-testid="replay-comparison">
                  <div className="flex items-center gap-2 text-[13px] font-semibold mb-2" style={{ color: res.comparison.passed ? "#22c55e" : "#F87171" }}>
                    {res.comparison.passed ? <CheckCircle2 size={15} /> : <XCircle size={15} />} Regression {res.comparison.passed ? "PASSED" : "FAILED"}
                  </div>
                  {res.comparison.matched.length > 0 && <div className="text-[11.5px]" style={{ color: "#22c55e" }}>✓ Matched: {res.comparison.matched.join(", ")}</div>}
                  {res.comparison.missing.length > 0 && <div className="text-[11.5px]" style={{ color: "#F87171" }}>✗ Missing: {res.comparison.missing.join(", ")}</div>}
                  {res.comparison.unexpected.length > 0 && <div className="text-[11.5px]" style={{ color: "#FB923C" }}><AlertCircle size={11} className="inline" /> Unexpected: {res.comparison.unexpected.join(", ")}</div>}
                </div>
              )}
              {!res.results.length ? <div className="text-[12.5px]" style={{ color: "var(--text-3)" }}>No rules matched this telemetry.</div> : (
                <table className="dense w-full">
                  <thead><tr><th>Rule</th><th>Severity</th><th>Type</th><th>Alerts</th><th>Matched</th></tr></thead>
                  <tbody>
                    {res.results.map((r) => (
                      <tr key={r.rule_id} className="border-t" data-testid={`replay-rule-${r.rule_id}`}>
                        <td style={{ color: "var(--text)" }}>{r.rule_name}</td>
                        <td><Sev s={r.severity} /></td>
                        <td style={{ color: "var(--text-2)" }}>{r.rule_type}</td>
                        <td className="font-mono" style={{ color: "var(--cyan)" }}>{r.would_alert}</td>
                        <td className="font-mono" style={{ color: "var(--text-2)" }}>{r.matched_events}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
