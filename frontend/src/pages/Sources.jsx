import { useEffect, useState } from "react";
import { Plus, Radio, Upload, Copy, Trash2, Server } from "lucide-react";
import client from "@/lib/api";
import { Loading, PageHead, StatusPill, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";

const SRC_TYPES = ["windows", "linux", "network", "firewall", "ids_ips", "application", "cloud", "custom"];

export default function Sources() {
  const [sources, setSources] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [token, setToken] = useState(null);
  const [uploadFor, setUploadFor] = useState(null);

  const load = () => client.get("/sources").then(({ data }) => setSources(data.sources));
  useEffect(() => { load(); }, []);

  const create = async (f) => {
    const { data } = await client.post("/sources", f);
    setToken({ source: f.name, token: data.ingestion_token }); setNewOpen(false); load();
  };
  const del = async (id) => { if (!window.confirm("Delete source?")) return; await client.delete(`/sources/${id}`); load(); toast.success("Source deleted"); };

  const total = sources?.length || 0;
  const online = sources?.filter((s) => s.status === "online").length || 0;
  const errors = sources?.reduce((a, s) => a + (s.parse_errors || 0), 0) || 0;

  return (
    <div data-testid="sources-ingestion-page">
      <PageHead title="Sources & Ingestion" desc="Monitor telemetry sources and ingestion status">
        <button className="btn btn-primary btn-sm" onClick={() => setNewOpen(true)} data-testid="add-source-btn"><Plus size={13} /> Add Source</button>
      </PageHead>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard icon={Server} label="Total Sources" value={total} color="var(--cyan)" />
        <StatCard icon={Radio} label="Online" value={online} color="#22c55e" />
        <StatCard icon={Radio} label="Inactive" value={total - online} color="#64748b" />
        <StatCard icon={Upload} label="Parse Errors" value={errors} color={errors ? "#F87171" : "var(--text)"} />
      </div>
      <div className="card overflow-hidden">
        {!sources ? <Loading /> : (
          <table className="dense w-full">
            <thead><tr><th>Name</th><th>Type</th><th>Host/Endpoint</th><th>Events</th><th>Last Received</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id} className="border-t row-hover" data-testid={`source-row-${s.id}`}>
                  <td style={{ color: "var(--text)" }}>{s.display_name || s.name}</td>
                  <td style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{s.source_type}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{s.host || "—"}</td>
                  <td className="font-mono" style={{ color: "var(--cyan)" }}>{(s.events_received || 0).toLocaleString()}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{s.last_received ? fmtTime(s.last_received).slice(11) : "never"}</td>
                  <td><StatusPill status={s.status} /></td>
                  <td className="flex gap-1">
                    <button className="btn btn-sm" onClick={() => setUploadFor(s)} data-testid={`upload-${s.id}`}><Upload size={12} /></button>
                    <button className="btn btn-sm" onClick={() => del(s.id)} data-testid={`delete-source-${s.id}`}><Trash2 size={12} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <NewSource open={newOpen} onClose={() => setNewOpen(false)} onCreate={create} />
      <UploadModal source={uploadFor} onClose={() => { setUploadFor(null); load(); }} />

      <Modal open={!!token} onClose={() => setToken(null)} title="Ingestion Credential" testId="token-modal">
        {token && (
          <div>
            <p className="text-[12.5px] mb-3" style={{ color: "var(--text-2)" }}>Copy this ingestion token now — it won't be shown again. Use it to authenticate <b>{token.source}</b>.</p>
            <div className="flex gap-2">
              <input className="inp font-mono text-[11.5px]" readOnly value={token.token} data-testid="ingestion-token" />
              <button className="btn btn-sm" onClick={() => { navigator.clipboard.writeText(token.token); toast.success("Copied"); }}><Copy size={12} /></button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="card p-3.5 flex items-center gap-3">
      <div className="grid place-items-center w-10 h-10 rounded-md" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}><Icon size={18} style={{ color }} /></div>
      <div><div className="kpi-val" style={{ color, fontSize: 22 }}>{value}</div><div className="text-[11px]" style={{ color: "var(--text-3)" }}>{label}</div></div>
    </div>
  );
}

function NewSource({ open, onClose, onCreate }) {
  const [f, setF] = useState({ name: "", display_name: "", source_type: "windows", host: "" });
  return (
    <Modal open={open} onClose={onClose} title="Add Telemetry Source" testId="new-source-modal">
      <div className="space-y-3">
        <input className="inp" placeholder="Source ID (e.g. auth-srv-02)" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="source-name" />
        <input className="inp" placeholder="Display name" value={f.display_name} onChange={(e) => setF({ ...f, display_name: e.target.value })} data-testid="source-display" />
        <select className="inp" value={f.source_type} onChange={(e) => setF({ ...f, source_type: e.target.value })} data-testid="source-type">{SRC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select>
        <input className="inp" placeholder="Host / IP endpoint" value={f.host} onChange={(e) => setF({ ...f, host: e.target.value })} data-testid="source-host" />
        <button className="btn btn-primary w-full justify-center" onClick={() => onCreate(f)} disabled={!f.name} data-testid="source-create">Create & Generate Token</button>
      </div>
    </Modal>
  );
}

function UploadModal({ source, onClose }) {
  const [fmt, setFmt] = useState("json");
  const [busy, setBusy] = useState(false);
  const upload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    setBusy(true);
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await client.post(`/ingest/upload?source_id=${source.id}&format=${fmt}`, fd);
      toast.success(`Ingested ${data.ingested} events · ${data.alerts_generated} alerts generated`);
      onClose();
    } catch (ex) { toast.error("Upload failed"); } finally { setBusy(false); }
  };
  return (
    <Modal open={!!source} onClose={onClose} title={`Upload Logs → ${source?.display_name || ""}`} testId="upload-modal">
      <div className="space-y-3">
        <select className="inp" value={fmt} onChange={(e) => setFmt(e.target.value)} data-testid="upload-format">
          {["json", "jsonl", "csv", "syslog", "cef"].map((x) => <option key={x} value={x}>{x.toUpperCase()}</option>)}
        </select>
        <input type="file" className="inp" onChange={upload} disabled={busy} data-testid="upload-file" />
        <p className="text-[11.5px]" style={{ color: "var(--text-3)" }}>Uploaded events are parsed, normalized, persisted, and evaluated by the detection engine in real time.</p>
      </div>
    </Modal>
  );
}
