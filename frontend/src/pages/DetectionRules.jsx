import { useEffect, useState } from "react";
import { Plus, Power, FlaskConical, Cpu } from "lucide-react";
import client from "@/lib/api";
import { Sev, Loading, PageHead, StatusPill, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";

const RULE_TYPES = ["match", "threshold", "frequency", "indicator"];

export default function DetectionRules() {
  const [rules, setRules] = useState(null);
  const [sel, setSel] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [backtest, setBacktest] = useState(null);

  const load = () => client.get("/rules").then(({ data }) => setRules(data.rules));
  useEffect(() => { load(); }, []);

  const toggle = async (r) => { await client.post(`/rules/${r.id}/toggle`); load(); if (sel?.id === r.id) setSel({ ...sel, enabled: !sel.enabled }); };
  const runBacktest = async (r) => {
    setBacktest("running");
    const { data } = await client.post(`/rules/${r.id}/backtest?time_range=7d`);
    setBacktest(data); toast.success(`Backtest: ${data.would_alert} alerts over ${data.matched_events} events`);
  };

  return (
    <div data-testid="detection-rules-panel">
      <PageHead title="Detection Rules" desc="Manage and configure detection rules">
        <button className="btn btn-primary btn-sm" onClick={() => setNewOpen(true)} data-testid="new-rule-btn"><Plus size={13} /> New Rule</button>
      </PageHead>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card overflow-hidden lg:col-span-2">
          {!rules ? <Loading /> : (
            <table className="dense w-full">
              <thead><tr><th>Name</th><th>Type</th><th>Severity</th><th>Status</th><th>Matches</th><th>Last Run</th><th></th></tr></thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id} className="border-t row-hover cursor-pointer" onClick={() => { setSel(r); setBacktest(null); }} data-testid={`rule-row-${r.id}`}>
                    <td style={{ color: "var(--text)" }}>{r.name}</td>
                    <td style={{ color: "var(--text-2)" }}>{r.rule_type}</td>
                    <td><Sev s={r.severity} /></td>
                    <td><StatusPill status={r.enabled ? "healthy" : "offline"} /></td>
                    <td className="font-mono" style={{ color: "var(--cyan)" }}>{r.match_count}</td>
                    <td className="font-mono" style={{ color: "var(--text-3)" }}>{r.last_run ? fmtTime(r.last_run).slice(11) : "—"}</td>
                    <td><button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); toggle(r); }} data-testid={`toggle-${r.id}`}><Power size={12} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card p-4" data-testid="rule-details-panel">
          {!sel ? <div className="text-center py-10 text-[13px]" style={{ color: "var(--text-3)" }}><Cpu size={24} className="mx-auto mb-2" />Select a rule to view details</div> : (
            <>
              <div className="flex items-center gap-2 mb-1"><span className="font-head font-semibold text-[15px]" style={{ color: "var(--text)" }}>{sel.name}</span></div>
              <div className="flex items-center gap-2 mb-3"><Sev s={sel.severity} /><span className="pill">v{sel.version}</span><StatusPill status={sel.enabled ? "healthy" : "offline"} /></div>
              <p className="text-[12.5px] mb-3" style={{ color: "var(--text-2)" }}>{sel.description}</p>
              <div className="text-[12px] space-y-1 mb-3">
                <div className="flex justify-between border-b py-1"><span style={{ color: "var(--text-3)" }}>Type</span><span style={{ color: "var(--text)" }}>{sel.rule_type}</span></div>
                <div className="flex justify-between border-b py-1"><span style={{ color: "var(--text-3)" }}>Author</span><span className="font-mono text-[11px]" style={{ color: "var(--text)" }}>{sel.author}</span></div>
                <div className="flex justify-between border-b py-1"><span style={{ color: "var(--text-3)" }}>Matches</span><span className="font-mono" style={{ color: "var(--cyan)" }}>{sel.match_count}</span></div>
              </div>
              {sel.mitre?.length > 0 && <div className="mb-3">{sel.mitre.map((m) => <span key={m} className="pill mr-1" style={{ color: "var(--cyan)" }}>{m}</span>)}</div>}
              <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Logic</div>
              <pre className="font-mono text-[10.5px] p-2 rounded mb-3 overflow-auto max-h-40" style={{ background: "var(--bg)", color: "var(--cyan)" }}>{JSON.stringify(sel.params, null, 2)}</pre>
              <div className="flex gap-2">
                <button className="btn btn-sm flex-1 justify-center" onClick={() => runBacktest(sel)} data-testid="backtest-btn">Backtest (7d)</button>
                <button className="btn btn-sm flex-1 justify-center" onClick={() => toggle(sel)} data-testid="detail-toggle"><Power size={12} /> {sel.enabled ? "Disable" : "Enable"}</button>
              </div>
              {backtest && backtest !== "running" && (
                <div className="mt-3 text-[12px] p-2 rounded" style={{ background: "var(--bg)", color: "var(--text-2)" }} data-testid="backtest-result">
                  Would generate <b style={{ color: "var(--cyan)" }}>{backtest.would_alert}</b> alerts from <b>{backtest.matched_events}</b> matched events.
                </div>
              )}
            </>
          )}
        </div>
      </div>
      <NewRule open={newOpen} onClose={() => setNewOpen(false)} onSaved={() => { load(); setNewOpen(false); }} />
    </div>
  );
}

function NewRule({ open, onClose, onSaved }) {
  const [f, setF] = useState({ name: "", description: "", rule_type: "match", severity: "medium", field: "process_name", op: "contains", value: "", mitre: "" });
  const save = async () => {
    const params = f.rule_type === "match"
      ? { conditions: [{ field: f.field, op: f.op, value: f.value }] }
      : { conditions: [{ field: f.field, op: f.op, value: f.value }], group_by: "src_ip", window_minutes: 5, threshold: 5 };
    await client.post("/rules", { name: f.name, description: f.description, rule_type: f.rule_type, severity: f.severity, mitre: f.mitre ? f.mitre.split(",").map((s) => s.trim()) : [], params });
    toast.success("Rule created"); onSaved();
  };
  return (
    <Modal open={open} onClose={onClose} title="New Detection Rule" testId="new-rule-modal">
      <div className="space-y-3">
        <input className="inp" placeholder="Rule name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="rule-name" />
        <input className="inp" placeholder="Description" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} data-testid="rule-desc" />
        <div className="grid grid-cols-2 gap-2">
          <select className="inp" value={f.rule_type} onChange={(e) => setF({ ...f, rule_type: e.target.value })} data-testid="rule-type">{RULE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select>
          <select className="inp" value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} data-testid="rule-sev">{["critical", "high", "medium", "low"].map((s) => <option key={s} value={s}>{s}</option>)}</select>
        </div>
        <div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Condition</div>
        <div className="grid grid-cols-3 gap-2">
          <select className="inp" value={f.field} onChange={(e) => setF({ ...f, field: e.target.value })} data-testid="rule-field">{["process_name", "command_line", "src_ip", "username", "category", "outcome", "action", "dest_port"].map((x) => <option key={x}>{x}</option>)}</select>
          <select className="inp" value={f.op} onChange={(e) => setF({ ...f, op: e.target.value })} data-testid="rule-op">{["eq", "contains", "regex", "gt", "lt"].map((x) => <option key={x}>{x}</option>)}</select>
          <input className="inp" placeholder="value" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} data-testid="rule-value" />
        </div>
        <input className="inp" placeholder="MITRE techniques (comma sep, e.g. T1059)" value={f.mitre} onChange={(e) => setF({ ...f, mitre: e.target.value })} data-testid="rule-mitre" />
        <button className="btn btn-primary w-full justify-center" onClick={save} data-testid="rule-save">Create Rule</button>
      </div>
    </Modal>
  );
}
