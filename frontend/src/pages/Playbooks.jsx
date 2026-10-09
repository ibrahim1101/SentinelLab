import { useEffect, useState } from "react";
import client from "@/lib/api";
import { PageHead, Loading, Sev, Empty, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";
import { PlayCircle, ShieldCheck, Workflow, CheckCircle2, Clock, AlertCircle } from "lucide-react";

export default function Playbooks() {
  const [pbs, setPbs] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [execs, setExecs] = useState([]);
  const [runFor, setRunFor] = useState(null);
  const [viewExec, setViewExec] = useState(null);

  const loadExecs = () => client.get("/playbooks/executions").then(({ data }) => setExecs(data.executions));
  useEffect(() => {
    client.get("/playbooks").then(({ data }) => setPbs(data.playbooks));
    client.get("/alerts?page_size=50").then(({ data }) => setAlerts(data.alerts));
    loadExecs();
  }, []);

  if (!pbs) return <Loading />;

  return (
    <div data-testid="playbooks-page">
      <PageHead title="Incident Response Playbooks" desc="Analyst-controlled workflows · dry-run & approval-gated" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
        {pbs.map((p) => (
          <div key={p.id} className="card p-4 flex flex-col" data-testid={`playbook-${p.id}`}>
            <div className="flex items-center gap-2 mb-1"><Workflow size={16} style={{ color: "var(--cyan)" }} /><span className="font-head font-semibold text-[14px]" style={{ color: "var(--text)" }}>{p.name}</span></div>
            <p className="text-[12px] mb-3 flex-1" style={{ color: "var(--text-2)" }}>{p.description}</p>
            <div className="flex items-center gap-1.5 mb-3 flex-wrap">
              <Sev s={p.severity} />
              <span className="pill" style={{ fontSize: 10 }}>{p.steps.length} steps</span>
              <span className="pill" style={{ fontSize: 10, color: "#FB923C" }}>{p.steps.filter((s) => s.approval).length} approval-gated</span>
            </div>
            <button className="btn btn-primary btn-sm w-full justify-center" onClick={() => setRunFor(p)} data-testid={`run-${p.id}`}><PlayCircle size={14} /> Run Playbook</button>
          </div>
        ))}
      </div>

      <div className="card overflow-hidden" data-testid="exec-history">
        <div className="px-4 py-2.5 border-b font-head font-semibold text-[14px]">Execution History (live runs)</div>
        {!execs.length ? <Empty msg="No live executions yet — dry-runs are not persisted" /> : (
          <table className="dense w-full">
            <thead><tr><th>Playbook</th><th>Alert</th><th>Mode</th><th>Status</th><th>By</th><th>When</th><th></th></tr></thead>
            <tbody>
              {execs.map((e) => (
                <tr key={e.id} className="border-t row-hover cursor-pointer" onClick={() => setViewExec(e)} data-testid={`exec-${e.id}`}>
                  <td style={{ color: "var(--text)" }}>{e.playbook_name}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.alert_id ? e.alert_id.slice(0, 8) : "—"}</td>
                  <td><span className="pill">{e.dry_run ? "dry-run" : "live"}</span></td>
                  <td style={{ color: e.status === "completed" ? "#22c55e" : "#FB923C", textTransform: "capitalize" }}>{e.status.replace(/_/g, " ")}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.run_by}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.created_at).slice(0, 16)}</td>
                  <td style={{ color: "var(--cyan)" }}>View</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <RunModal pb={runFor} alerts={alerts} onClose={() => setRunFor(null)} onDone={() => { loadExecs(); }} />
      <Modal open={!!viewExec} onClose={() => setViewExec(null)} wide title="Execution Detail" testId="exec-detail-modal">
        {viewExec && <StepList steps={viewExec.steps} />}
      </Modal>
    </div>
  );
}

function StepIcon({ status }) {
  if (status === "ok") return <CheckCircle2 size={14} style={{ color: "#22c55e" }} />;
  if (status === "pending_approval") return <Clock size={14} style={{ color: "#FB923C" }} />;
  if (status === "error") return <AlertCircle size={14} style={{ color: "#F87171" }} />;
  return <ShieldCheck size={14} style={{ color: "var(--text-3)" }} />;
}

function StepList({ steps }) {
  return (
    <div className="space-y-2">
      {steps.map((s) => (
        <div key={s.step_id} className="flex items-start gap-2.5 py-1.5 border-b" data-testid={`step-${s.step_id}`}>
          <StepIcon status={s.status} />
          <div className="flex-1">
            <div className="text-[13px] flex items-center gap-2" style={{ color: "var(--text)" }}>{s.name}
              {s.requires_approval && <span className="pill" style={{ fontSize: 9, color: "#FB923C" }}>approval</span>}</div>
            <div className="text-[11.5px]" style={{ color: "var(--text-3)" }}>{s.detail}</div>
          </div>
          <span className="text-[11px]" style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{(s.status || "").replace(/_/g, " ")}</span>
        </div>
      ))}
    </div>
  );
}

function RunModal({ pb, alerts, onClose, onDone }) {
  const [alertId, setAlertId] = useState("");
  const [result, setResult] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => { setResult(null); setApprovals([]); setAlertId(""); }, [pb]);
  if (!pb) return null;

  const approvalSteps = pb.steps.filter((s) => s.approval);
  const run = async (dry_run) => {
    setBusy(true);
    try {
      const { data } = await client.post("/playbooks/run", { playbook_id: pb.id, alert_id: alertId || null, dry_run, approvals });
      setResult(data);
      if (!dry_run) { toast.success("Playbook executed"); onDone(); }
      else toast.info("Dry-run complete — no changes made");
    } catch (e) { toast.error("Run failed"); } finally { setBusy(false); }
  };
  const toggleApproval = (id) => setApprovals((a) => a.includes(id) ? a.filter((x) => x !== id) : [...a, id]);

  return (
    <Modal open={!!pb} onClose={onClose} wide title={`Run: ${pb.name}`} testId="run-playbook-modal">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Target Alert (optional)</div>
          <select className="inp mb-3" value={alertId} onChange={(e) => setAlertId(e.target.value)} data-testid="run-alert-select">
            <option value="">— Manual (no alert) —</option>
            {alerts.map((a) => <option key={a.id} value={a.id}>{a.title} ({a.severity})</option>)}
          </select>
          <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Approval Gates</div>
          <p className="text-[11.5px] mb-2" style={{ color: "var(--text-3)" }}>External/impactful steps require explicit approval before a live run executes them.</p>
          {approvalSteps.map((s) => (
            <label key={s.id} className="flex items-center gap-2 py-1 text-[12.5px] cursor-pointer" style={{ color: "var(--text-2)" }} data-testid={`approve-${s.id}`}>
              <input type="checkbox" checked={approvals.includes(s.id)} onChange={() => toggleApproval(s.id)} /> {s.name}
            </label>
          ))}
          <div className="flex gap-2 mt-4">
            <button className="btn btn-sm flex-1 justify-center" onClick={() => run(true)} disabled={busy} data-testid="dry-run-btn"><ShieldCheck size={13} /> Dry Run</button>
            <button className="btn btn-primary flex-1 justify-center" onClick={() => run(false)} disabled={busy} data-testid="live-run-btn"><PlayCircle size={13} /> Execute Live</button>
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>{result ? "Execution Steps" : "Playbook Steps"}</div>
          {result ? <StepList steps={result.steps} /> : (
            <div className="space-y-1.5">
              {pb.steps.map((s) => (
                <div key={s.id} className="flex items-center gap-2 text-[12.5px] py-1 border-b" style={{ color: "var(--text-2)" }}>
                  <ShieldCheck size={13} style={{ color: "var(--text-3)" }} /> {s.name}
                  {s.approval && <span className="pill ml-auto" style={{ fontSize: 9, color: "#FB923C" }}>approval</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
