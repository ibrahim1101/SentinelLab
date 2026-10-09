import { useEffect, useState } from "react";
import client from "@/lib/api";
import { PageHead, Loading, Empty, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";
import { Plus, Upload, ScanLine, Trash2, Ban, Globe } from "lucide-react";

const TYPES = ["ip", "domain", "url", "hash", "email"];

export default function ThreatIntel() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState({ ioc_type: "", q: "" });
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [hits, setHits] = useState(null);

  const load = () => {
    const p = new URLSearchParams({ ...filter });
    client.get(`/indicators?${p}`).then(({ data }) => setData(data));
  };
  useEffect(() => { load(); }, [filter]);

  const scan = async () => {
    toast.loading("Scanning events against indicators…", { id: "scan" });
    const { data } = await client.post("/indicators/scan?time_range=7d");
    toast.success(`Scan complete: ${data.alerts_generated} alert(s) from ${data.events_scanned} events`, { id: "scan" });
  };
  const del = async (id) => { await client.delete(`/indicators/${id}`); load(); toast.success("Indicator deleted"); };
  const toggleFp = async (i) => { await client.put(`/indicators/${i.id}`, { false_positive: !i.false_positive, active: i.false_positive }); load(); };
  const showHits = async (id) => { const { data } = await client.get(`/indicators/${id}/hits`); setHits(data); };

  return (
    <div data-testid="threat-intel-page">
      <PageHead title="Threat Intelligence" desc="IOC management, import & live event matching">
        <button className="btn btn-sm" onClick={() => setImportOpen(true)} data-testid="import-ioc-btn"><Upload size={13} /> Import</button>
        <button className="btn btn-sm" onClick={scan} data-testid="scan-ioc-btn"><ScanLine size={13} /> Scan Events</button>
        <button className="btn btn-primary btn-sm" onClick={() => setAddOpen(true)} data-testid="add-ioc-btn"><Plus size={13} /> Add IOC</button>
      </PageHead>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        {TYPES.map((t) => (
          <div key={t} className="card p-3 cursor-pointer" onClick={() => setFilter({ ...filter, ioc_type: filter.ioc_type === t ? "" : t })}
            style={{ borderColor: filter.ioc_type === t ? "var(--cyan)" : "var(--border)" }} data-testid={`ioc-stat-${t}`}>
            <div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>{t}</div>
            <div className="kpi-val mt-1.5" style={{ fontSize: 22, color: "var(--cyan)" }}>{data?.stats?.[t] || 0}</div>
          </div>
        ))}
      </div>

      <div className="card p-3 mb-3 flex gap-2">
        <input className="inp max-w-xs font-mono text-[12px]" placeholder="Search indicator value…" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} data-testid="ioc-search" />
        <div className="ml-auto text-[12px]" style={{ color: "var(--text-3)" }}>{data?.indicators?.length || 0} indicators</div>
      </div>

      <div className="card overflow-hidden">
        {!data ? <Loading /> : !data.indicators.length ? <Empty msg="No indicators — add or import IOCs" testId="ioc-empty" /> : (
          <table className="dense w-full">
            <thead><tr><th>Type</th><th>Value</th><th>Confidence</th><th>Source</th><th>Tags</th><th>Status</th><th>Added</th><th></th></tr></thead>
            <tbody>
              {data.indicators.map((i) => (
                <tr key={i.id} className="border-t row-hover" data-testid={`ioc-row-${i.id}`}>
                  <td><span className="pill" style={{ color: "var(--cyan)" }}>{i.ioc_type}</span></td>
                  <td className="font-mono cursor-pointer" style={{ color: "var(--text)" }} onClick={() => showHits(i.id)}>{i.value}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{i.confidence}%</td>
                  <td style={{ color: "var(--text-2)" }}>{i.source}</td>
                  <td>{(i.tags || []).map((t) => <span key={t} className="pill mr-1" style={{ fontSize: 10 }}>{t}</span>)}</td>
                  <td style={{ color: i.false_positive ? "var(--text-3)" : i.active ? "#22c55e" : "var(--text-3)" }}>{i.false_positive ? "false positive" : i.active ? "active" : "inactive"}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(i.created_at).slice(0, 10)}</td>
                  <td className="flex gap-1">
                    <button className="btn btn-sm" onClick={() => toggleFp(i)} title="Mark false positive" data-testid={`ioc-fp-${i.id}`}><Ban size={12} /></button>
                    <button className="btn btn-sm" onClick={() => del(i.id)} data-testid={`ioc-del-${i.id}`}><Trash2 size={12} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AddIOC open={addOpen} onClose={() => setAddOpen(false)} onSaved={() => { setAddOpen(false); load(); }} />
      <ImportIOC open={importOpen} onClose={() => setImportOpen(false)} onSaved={() => { setImportOpen(false); load(); }} />

      <Modal open={!!hits} onClose={() => setHits(null)} wide title="Indicator Hits" testId="ioc-hits-modal">
        {hits && (
          <div>
            <div className="flex items-center gap-2 mb-3"><span className="pill" style={{ color: "var(--cyan)" }}>{hits.indicator.ioc_type}</span><span className="font-mono" style={{ color: "var(--text)" }}>{hits.indicator.value}</span><span className="text-[12px]" style={{ color: "var(--text-3)" }}>{hits.count} matching event(s)</span></div>
            {!hits.hits.length ? <Empty msg="No matching events in this workspace" /> : (
              <table className="dense w-full"><thead><tr><th>Timestamp</th><th>Type</th><th>Host</th><th>Src IP</th><th>Dest IP</th></tr></thead><tbody>
                {hits.hits.map((e) => <tr key={e.id} className="border-t"><td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.timestamp)}</td><td style={{ color: "var(--text-2)" }}>{e.event_type}</td><td className="font-mono" style={{ color: "var(--text)" }}>{e.host}</td><td className="font-mono" style={{ color: "var(--text-2)" }}>{e.src_ip}</td><td className="font-mono" style={{ color: "var(--text-2)" }}>{e.dest_ip}</td></tr>)}
              </tbody></table>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

function AddIOC({ open, onClose, onSaved }) {
  const [f, setF] = useState({ ioc_type: "ip", value: "", confidence: 80, source: "manual", tags: "" });
  const save = async () => {
    if (!f.value.trim()) return;
    await client.post("/indicators", { ...f, tags: f.tags ? f.tags.split(",").map((s) => s.trim()) : [] });
    toast.success("Indicator added"); onSaved();
  };
  return (
    <Modal open={open} onClose={onClose} title="Add Indicator" testId="add-ioc-modal">
      <div className="space-y-3">
        <select className="inp" value={f.ioc_type} onChange={(e) => setF({ ...f, ioc_type: e.target.value })} data-testid="ioc-type">{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select>
        <input className="inp font-mono" placeholder="Value (e.g. 185.220.101.5)" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} data-testid="ioc-value" />
        <div className="grid grid-cols-2 gap-2">
          <input className="inp" type="number" placeholder="Confidence" value={f.confidence} onChange={(e) => setF({ ...f, confidence: +e.target.value })} data-testid="ioc-confidence" />
          <input className="inp" placeholder="Source" value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })} data-testid="ioc-source" />
        </div>
        <input className="inp" placeholder="Tags (comma separated)" value={f.tags} onChange={(e) => setF({ ...f, tags: e.target.value })} data-testid="ioc-tags" />
        <button className="btn btn-primary w-full justify-center" onClick={save} data-testid="ioc-save">Add Indicator</button>
      </div>
    </Modal>
  );
}

function ImportIOC({ open, onClose, onSaved }) {
  const [fmt, setFmt] = useState("csv");
  const [text, setText] = useState("ip,185.220.101.5,90,TOR,c2;tor\ndomain,x9f3k2.ddns.net,75,DGA,malware");
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try { const { data } = await client.post("/indicators/import", { format: fmt, data: text }); toast.success(`Imported ${data.imported} of ${data.parsed} parsed`); onSaved(); }
    catch { toast.error("Import failed"); } finally { setBusy(false); }
  };
  const onFile = async (e) => { const file = e.target.files[0]; if (!file) return; setText(await file.text()); };
  return (
    <Modal open={open} onClose={onClose} wide title="Import Indicators" testId="import-ioc-modal">
      <div className="space-y-3">
        <div className="flex gap-2 items-center">
          <select className="inp max-w-[160px]" value={fmt} onChange={(e) => setFmt(e.target.value)} data-testid="import-format">
            <option value="csv">CSV (type,value,confidence,source,tags)</option>
            <option value="stix">STIX 2.1 Bundle (JSON)</option>
          </select>
          <label className="btn btn-sm cursor-pointer"><Upload size={12} /> From file<input type="file" className="hidden" onChange={onFile} data-testid="import-file" /></label>
        </div>
        <textarea className="inp font-mono text-[11.5px]" rows={9} value={text} onChange={(e) => setText(e.target.value)} data-testid="import-text" />
        <button className="btn btn-primary w-full justify-center" onClick={run} disabled={busy} data-testid="import-run">{busy ? "Importing…" : "Import Indicators"}</button>
      </div>
    </Modal>
  );
}
