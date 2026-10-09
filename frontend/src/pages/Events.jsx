import { useEffect, useState, useCallback } from "react";
import { Download, Filter, ChevronLeft, ChevronRight, Copy, FolderPlus } from "lucide-react";
import client, { API } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { Sev, Loading, PageHead, Empty, fmtTime } from "@/components/common";
import Modal from "@/components/Modal";
import { toast } from "sonner";

const CATS = ["", "authentication", "network", "process", "dns", "file"];
const SEVS = ["", "critical", "high", "medium", "low", "info"];

export default function Events() {
  const { range } = useWorkspace();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ q: "", severity: "", category: "" });
  const [sel, setSel] = useState(null);
  const [tab, setTab] = useState("overview");

  const load = useCallback(() => {
    const p = new URLSearchParams({ time_range: range, page, page_size: 50, ...filters });
    client.get(`/events?${p}`).then(({ data }) => setData(data));
  }, [range, page, filters]);
  useEffect(() => { load(); }, [load]);

  const openEvent = async (id) => {
    const { data } = await client.get(`/events/${id}`);
    setSel(data); setTab("overview");
  };

  const exportData = (fmt) => {
    const token = localStorage.getItem("sl_token"), ws = localStorage.getItem("sl_workspace");
    fetch(`${API}/events/export/data?format=${fmt}&time_range=${range}&severity=${filters.severity}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": ws },
    }).then((r) => r.blob()).then((b) => {
      const u = URL.createObjectURL(b); const a = document.createElement("a");
      a.href = u; a.download = `events.${fmt}`; a.click();
    });
  };

  const totalPages = data ? Math.ceil(data.total / 50) : 1;

  return (
    <div data-testid="events-explorer">
      <PageHead title="Events Explorer" desc="Search and analyze ingested security events">
        <button className="btn btn-sm" onClick={() => exportData("csv")} data-testid="export-csv"><Download size={13} /> CSV</button>
        <button className="btn btn-sm" onClick={() => exportData("json")} data-testid="export-json"><Download size={13} /> JSON</button>
      </PageHead>

      <div className="card p-3 mb-3 flex flex-wrap items-center gap-2" data-testid="events-filters">
        <input className="inp max-w-xs font-mono text-[12px]" placeholder="Search host, IP, user, process…"
          value={filters.q} onChange={(e) => { setPage(1); setFilters({ ...filters, q: e.target.value }); }} data-testid="events-search" />
        <select className="inp max-w-[150px]" value={filters.severity} onChange={(e) => { setPage(1); setFilters({ ...filters, severity: e.target.value }); }} data-testid="filter-severity">
          {SEVS.map((s) => <option key={s} value={s}>{s || "All Severities"}</option>)}
        </select>
        <select className="inp max-w-[150px]" value={filters.category} onChange={(e) => { setPage(1); setFilters({ ...filters, category: e.target.value }); }} data-testid="filter-category">
          {CATS.map((c) => <option key={c} value={c}>{c || "All Types"}</option>)}
        </select>
        <div className="ml-auto text-[12px]" style={{ color: "var(--text-3)" }}>{data?.total?.toLocaleString() || 0} events</div>
      </div>

      <div className="card overflow-hidden">
        {!data ? <Loading /> : !data.events.length ? <Empty msg="No events match your filters" testId="events-empty" /> : (
          <table className="dense w-full">
            <thead><tr><th>Timestamp</th><th>Severity</th><th>Type</th><th>Source</th><th>Host</th><th>Src IP</th><th>User</th><th>Action</th></tr></thead>
            <tbody>
              {data.events.map((e) => (
                <tr key={e.id} className="row-hover cursor-pointer border-t" onClick={() => openEvent(e.id)} data-testid={`event-row-${e.id}`}>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(e.timestamp)}</td>
                  <td><Sev s={e.severity} /></td>
                  <td style={{ color: "var(--text-2)" }}>{e.event_type || e.category}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.source_name}</td>
                  <td className="font-mono" style={{ color: "var(--text)" }}>{e.host || "—"}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.src_ip || "—"}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{e.username || "—"}</td>
                  <td style={{ color: "var(--text-2)" }}>{e.action || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 text-[12px]" style={{ color: "var(--text-3)" }}>
        <span>Page {page} of {totalPages}</span>
        <div className="flex gap-1.5">
          <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)} data-testid="prev-page"><ChevronLeft size={13} /></button>
          <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)} data-testid="next-page"><ChevronRight size={13} /></button>
        </div>
      </div>

      <Modal open={!!sel} onClose={() => setSel(null)} wide title="Event Details" testId="event-details-modal">
        {sel && <EventDetail d={sel} tab={tab} setTab={setTab} />}
      </Modal>
    </div>
  );
}

function EventDetail({ d, tab, setTab }) {
  const e = d.event;
  const normalized = Object.fromEntries(Object.entries(e).filter(([k]) => !["raw", "_id", "org_id"].includes(k)));
  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2"><span className="font-mono text-[13px]" style={{ color: "var(--cyan)" }}>{e.id}</span><Sev s={e.severity} /></div>
        <div className="flex gap-1.5">
          <button className="btn btn-sm" onClick={() => copy(e.id)} data-testid="copy-event-id"><Copy size={12} /> ID</button>
          <button className="btn btn-sm" onClick={() => copy(JSON.stringify(e, null, 2))} data-testid="copy-json"><Copy size={12} /> JSON</button>
        </div>
      </div>
      <div className="flex gap-1 border-b mb-3">
        {["overview", "raw", "normalized", "related"].map((t) => (
          <button key={t} onClick={() => setTab(t)} data-testid={`event-tab-${t}`}
            className="px-3 py-1.5 text-[12.5px] font-medium capitalize"
            style={{ color: tab === t ? "var(--cyan)" : "var(--text-3)", borderBottom: tab === t ? "2px solid var(--cyan)" : "2px solid transparent" }}>
            {t === "raw" ? "Raw Data" : t}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[12.5px]">
          {[["Event Type", e.event_type], ["Category", e.category], ["Action", e.action], ["Outcome", e.outcome], ["Host", e.host], ["Source", e.source_name], ["Src IP", e.src_ip], ["Dest IP", e.dest_ip], ["User", e.username], ["Process", e.process_name], ["Protocol", e.protocol], ["Timestamp", fmtTime(e.timestamp)]].map(([l, v]) => (
            <div key={l} className="flex justify-between border-b py-1"><span style={{ color: "var(--text-3)" }}>{l}</span><span className="font-mono" style={{ color: "var(--text)" }}>{v || "—"}</span></div>
          ))}
          {e.command_line && <div className="col-span-2 border-b py-1"><div style={{ color: "var(--text-3)" }}>Command Line</div><div className="font-mono text-[11.5px] mt-1" style={{ color: "#FB923C" }}>{e.command_line}</div></div>}
          {e.mitre?.length > 0 && <div className="col-span-2 py-1"><span style={{ color: "var(--text-3)" }}>MITRE: </span>{e.mitre.map((m) => <span key={m} className="pill mr-1" style={{ color: "var(--cyan)" }}>{m}</span>)}</div>}
        </div>
      )}
      {tab === "raw" && <pre className="font-mono text-[11.5px] p-3 rounded overflow-auto max-h-96" style={{ background: "var(--bg)", color: "#86efac" }}>{JSON.stringify(e.raw, null, 2)}</pre>}
      {tab === "normalized" && <pre className="font-mono text-[11.5px] p-3 rounded overflow-auto max-h-96" style={{ background: "var(--bg)", color: "var(--cyan)" }}>{JSON.stringify(normalized, null, 2)}</pre>}
      {tab === "related" && (
        <div>
          <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Related Alerts ({d.related_alerts.length})</div>
          {d.related_alerts.map((a) => <div key={a.id} className="flex items-center gap-2 py-1.5 border-b text-[12.5px]"><Sev s={a.severity} /><span>{a.title}</span></div>)}
          <div className="text-[11px] uppercase mt-4 mb-2" style={{ color: "var(--text-3)" }}>Related Events ({d.related_events.length})</div>
          {d.related_events.map((re) => <div key={re.id} className="font-mono py-1 border-b text-[11.5px]" style={{ color: "var(--text-2)" }}>{fmtTime(re.timestamp)} · {re.event_type} · {re.host}</div>)}
        </div>
      )}
    </div>
  );
}
