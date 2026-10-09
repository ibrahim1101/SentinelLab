import { useEffect, useState, useCallback } from "react";
import client from "@/lib/api";
import { Sev, Loading, PageHead, Empty, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";
import { Bot } from "lucide-react";

const STATUSES = ["new", "triaged", "investigating", "resolved", "false_positive", "closed"];

export default function Alerts() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({ status: "", severity: "" });
  const [sel, setSel] = useState(null);
  const [comment, setComment] = useState("");
  const [aiAns, setAiAns] = useState("");
  const [aiBusy, setAiBusy] = useState(false);

  const load = useCallback(() => {
    const p = new URLSearchParams({ ...filters });
    client.get(`/alerts?${p}`).then(({ data }) => setData(data));
  }, [filters]);
  useEffect(() => { load(); }, [load]);

  const open = async (id) => { const { data } = await client.get(`/alerts/${id}`); setSel(data); setAiAns(""); };
  const update = async (patch) => {
    const { data } = await client.put(`/alerts/${sel.alert.id}`, patch);
    setSel({ ...sel, alert: data }); load(); toast.success("Alert updated");
  };
  const addComment = async () => { if (!comment.trim()) return; await update({ comment }); setComment(""); };
  const explain = async () => {
    setAiBusy(true); setAiAns("");
    try { const { data } = await client.post("/ai/ask", { message: "Explain this alert, likely cause, and recommended next steps.", ctx_type: "alert", ctx_id: sel.alert.id }); setAiAns(data.answer); }
    catch { setAiAns("AI request failed"); } finally { setAiBusy(false); }
  };

  return (
    <div data-testid="alerts-page">
      <PageHead title="Alerts" desc="Triage and investigate detection alerts" />
      <div className="card p-3 mb-3 flex flex-wrap gap-2" data-testid="alerts-filters">
        <select className="inp max-w-[160px]" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} data-testid="alert-filter-status">
          <option value="">All Statuses</option>{STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
        <select className="inp max-w-[160px]" value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} data-testid="alert-filter-severity">
          <option value="">All Severities</option>{["critical", "high", "medium", "low"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <div className="ml-auto text-[12px]" style={{ color: "var(--text-3)" }}>{data?.total || 0} alerts</div>
      </div>
      <div className="card overflow-hidden">
        {!data ? <Loading /> : !data.alerts.length ? <Empty msg="No alerts" testId="alerts-empty" /> : (
          <table className="dense w-full">
            <thead><tr><th>ID</th><th>Severity</th><th>Title</th><th>Rule</th><th>Host</th><th>Status</th><th>First Seen</th></tr></thead>
            <tbody>
              {data.alerts.map((a) => (
                <tr key={a.id} className="row-hover cursor-pointer border-t" onClick={() => open(a.id)} data-testid={`alert-row-${a.id}`}>
                  <td className="font-mono" style={{ color: "var(--cyan)" }}>{a.id.slice(0, 8)}</td>
                  <td><Sev s={a.severity} /></td>
                  <td style={{ color: "var(--text)" }}>{a.title}</td>
                  <td style={{ color: "var(--text-2)" }}>{a.rule_name}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{a.host || "—"}</td>
                  <td style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{(a.status || "").replace(/_/g, " ")}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(a.first_seen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal open={!!sel} onClose={() => setSel(null)} wide title={sel?.alert?.title || "Alert"} testId="alert-detail-modal">
        {sel && (
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-3"><span className="font-mono" style={{ color: "var(--cyan)" }}>{sel.alert.id.slice(0, 8)}</span><Sev s={sel.alert.severity} /></div>
              <p className="text-[12.5px] mb-3" style={{ color: "var(--text-2)" }}>{sel.alert.description}</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px] mb-3">
                {[["Rule", sel.alert.rule_name], ["Host", sel.alert.host], ["Src IP", sel.alert.src_ip], ["User", sel.alert.username], ["Confidence", sel.alert.confidence + "%"], ["Events", sel.alert.event_count]].map(([l, v]) => (
                  <div key={l} className="flex justify-between border-b py-1"><span style={{ color: "var(--text-3)" }}>{l}</span><span className="font-mono" style={{ color: "var(--text)" }}>{v || "—"}</span></div>
                ))}
              </div>
              {sel.alert.mitre?.length > 0 && <div className="mb-3">{sel.alert.mitre.map((m) => <span key={m} className="pill mr-1" style={{ color: "var(--cyan)" }}>{m}</span>)}</div>}
              <button className="btn btn-sm mb-3" onClick={explain} disabled={aiBusy} data-testid="ai-explain-alert"><Bot size={13} /> {aiBusy ? "Analyzing…" : "Explain with AI"}</button>
              {aiAns && <div className="text-[12px] p-3 rounded mb-3 whitespace-pre-wrap" style={{ background: "var(--bg)", color: "var(--text-2)", border: "1px solid var(--border)" }}>{aiAns}</div>}
              <div className="text-[11px] uppercase mb-1.5" style={{ color: "var(--text-3)" }}>Supporting Events ({sel.events.length})</div>
              <div className="max-h-44 overflow-auto">
                <table className="dense w-full"><tbody>
                  {sel.events.map((e) => <tr key={e.id} className="border-t"><td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.timestamp)}</td><td style={{ color: "var(--text-2)" }}>{e.event_type}</td><td className="font-mono" style={{ color: "var(--text-2)" }}>{e.src_ip || e.host}</td><td><Sev s={e.severity} /></td></tr>)}
                </tbody></table>
              </div>
              <div className="text-[11px] uppercase mt-4 mb-1.5" style={{ color: "var(--text-3)" }}>Comments</div>
              {sel.alert.comments?.map((c) => <div key={c.id} className="text-[12px] py-1.5 border-b"><span style={{ color: "var(--cyan)" }}>{c.by}</span> <span style={{ color: "var(--text-2)" }}>{c.text}</span></div>)}
              <div className="flex gap-2 mt-2">
                <input className="inp" placeholder="Add comment…" value={comment} onChange={(e) => setComment(e.target.value)} data-testid="alert-comment-input" />
                <button className="btn btn-sm" onClick={addComment} data-testid="alert-comment-add">Add</button>
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Status</div>
                <select className="inp" value={sel.alert.status} onChange={(e) => update({ status: e.target.value })} data-testid="alert-status-select">
                  {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Severity</div>
                <select className="inp" value={sel.alert.severity} onChange={(e) => update({ severity: e.target.value })} data-testid="alert-severity-select">
                  {["critical", "high", "medium", "low"].map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Assigned To</div>
                <input className="inp" placeholder="analyst@…" defaultValue={sel.alert.assigned_to || ""} onBlur={(e) => e.target.value !== (sel.alert.assigned_to || "") && update({ assigned_to: e.target.value })} data-testid="alert-assign-input" />
              </div>
              <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Audit History</div>
              <div className="max-h-40 overflow-auto space-y-1">
                {sel.alert.audit?.slice().reverse().map((h, i) => <div key={i} className="text-[11px]" style={{ color: "var(--text-3)" }}>{fmtTime(h.ts).slice(11)} · {h.action}</div>)}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
