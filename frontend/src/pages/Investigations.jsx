import { useEffect, useState } from "react";
import { Plus, Upload, FileText } from "lucide-react";
import client from "@/lib/api";
import { Sev, Loading, PageHead, StatusPill, Empty, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";

const STATUSES = ["open", "investigating", "contained", "resolved", "closed"];

export default function Investigations() {
  const [list, setList] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [sel, setSel] = useState(null);
  const [note, setNote] = useState("");
  const [task, setTask] = useState("");

  const load = () => client.get("/investigations").then(({ data }) => setList(data.investigations));
  useEffect(() => { load(); }, []);

  const open = async (id) => { const { data } = await client.get(`/investigations/${id}`); setSel(data); };
  const create = async (f) => { await client.post("/investigations", f); setNewOpen(false); load(); toast.success("Investigation created"); };
  const update = async (patch) => { const { data } = await client.put(`/investigations/${sel.investigation.id}`, patch); setSel({ ...sel, investigation: data }); load(); };
  const upload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    const { data } = await client.post(`/investigations/${sel.investigation.id}/evidence`, fd);
    toast.success(`Evidence added · SHA256 ${data.evidence.sha256.slice(0, 12)}…`);
    open(sel.investigation.id);
  };

  return (
    <div data-testid="investigations-page">
      <PageHead title="Investigations" desc="Track investigation progress and evidence">
        <button className="btn btn-primary btn-sm" onClick={() => setNewOpen(true)} data-testid="new-investigation-btn"><Plus size={13} /> New Case</button>
      </PageHead>
      <div className="card overflow-hidden">
        {!list ? <Loading /> : !list.length ? <Empty msg="No investigations" testId="inv-empty" /> : (
          <table className="dense w-full">
            <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Lead</th><th>Alerts</th><th>Status</th><th>Updated</th></tr></thead>
            <tbody>
              {list.map((i) => (
                <tr key={i.id} className="border-t row-hover cursor-pointer" onClick={() => open(i.id)} data-testid={`inv-row-${i.id}`}>
                  <td className="font-mono" style={{ color: "var(--cyan)" }}>{i.id.slice(0, 8)}</td>
                  <td style={{ color: "var(--text)" }}>{i.title}</td>
                  <td><Sev s={i.severity} /></td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{i.lead}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{i.related_alerts?.length || 0}</td>
                  <td><StatusPill status={i.status} /></td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(i.updated_at).slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <NewInvestigation open={newOpen} onClose={() => setNewOpen(false)} onCreate={create} />

      <Modal open={!!sel} onClose={() => setSel(null)} wide title={sel?.investigation?.title || "Investigation"} testId="inv-detail-modal">
        {sel && (
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-3"><span className="font-mono" style={{ color: "var(--cyan)" }}>{sel.investigation.id.slice(0, 8)}</span><Sev s={sel.investigation.severity} /><StatusPill status={sel.investigation.status} /></div>
              <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Findings</div>
              <textarea className="inp mb-3" rows={3} defaultValue={sel.investigation.findings} onBlur={(e) => update({ findings: e.target.value })} data-testid="inv-findings" />
              <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Linked Alerts ({sel.alerts.length})</div>
              {sel.alerts.map((a) => <div key={a.id} className="flex items-center gap-2 py-1 border-b text-[12.5px]"><Sev s={a.severity} /><span style={{ color: "var(--text-2)" }}>{a.title}</span></div>)}
              <div className="text-[11px] uppercase mt-3 mb-1" style={{ color: "var(--text-3)" }}>Notes</div>
              {sel.investigation.notes?.map((n) => <div key={n.id} className="text-[12px] py-1 border-b"><span style={{ color: "var(--cyan)" }}>{n.by}:</span> <span style={{ color: "var(--text-2)" }}>{n.text}</span></div>)}
              <div className="flex gap-2 mt-2"><input className="inp" placeholder="Add note…" value={note} onChange={(e) => setNote(e.target.value)} data-testid="inv-note-input" /><button className="btn btn-sm" onClick={() => { update({ note }); setNote(""); }} data-testid="inv-note-add">Add</button></div>
            </div>
            <div className="space-y-3">
              <div><div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Status</div>
                <select className="inp" value={sel.investigation.status} onChange={(e) => update({ status: e.target.value })} data-testid="inv-status">{STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}</select>
              </div>
              <div><div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Tasks</div>
                {sel.investigation.tasks?.map((t) => <div key={t.id} className="text-[12px] py-0.5" style={{ color: "var(--text-2)" }}>□ {t.text}</div>)}
                <div className="flex gap-1.5 mt-1"><input className="inp" placeholder="New task…" value={task} onChange={(e) => setTask(e.target.value)} data-testid="inv-task-input" /><button className="btn btn-sm" onClick={() => { update({ task }); setTask(""); }} data-testid="inv-task-add"><Plus size={12} /></button></div>
              </div>
              <div><div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Evidence (chain of custody)</div>
                {sel.investigation.evidence?.map((e) => <div key={e.id} className="text-[11px] py-1 border-b font-mono" style={{ color: "var(--text-2)" }}><FileText size={11} className="inline mr-1" />{e.filename}<div style={{ color: "var(--text-3)" }}>{e.sha256.slice(0, 20)}…</div></div>)}
                <label className="btn btn-sm w-full justify-center mt-1.5 cursor-pointer"><Upload size={12} /> Add Evidence<input type="file" className="hidden" onChange={upload} data-testid="inv-evidence-upload" /></label>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function NewInvestigation({ open, onClose, onCreate }) {
  const [f, setF] = useState({ title: "", severity: "medium", priority: "medium", status: "open" });
  return (
    <Modal open={open} onClose={onClose} title="New Investigation" testId="new-inv-modal">
      <div className="space-y-3">
        <input className="inp" placeholder="Case title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} data-testid="inv-title" />
        <div className="grid grid-cols-2 gap-2">
          <select className="inp" value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} data-testid="inv-sev">{["critical", "high", "medium", "low"].map((s) => <option key={s}>{s}</option>)}</select>
          <select className="inp" value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })} data-testid="inv-priority">{["critical", "high", "medium", "low"].map((s) => <option key={s}>{s}</option>)}</select>
        </div>
        <button className="btn btn-primary w-full justify-center" onClick={() => onCreate(f)} disabled={!f.title} data-testid="inv-create">Create Case</button>
      </div>
    </Modal>
  );
}
