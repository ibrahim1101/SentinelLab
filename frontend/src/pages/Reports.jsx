import { useEffect, useState } from "react";
import { FileBarChart, Download, Plus } from "lucide-react";
import client, { API } from "@/lib/api";
import { Loading, PageHead, Empty, fmtTime } from "@/components/common";
import { toast } from "sonner";

const TYPES = [
  { id: "soc_daily", name: "SOC Daily Summary" },
  { id: "soc_weekly", name: "SOC Weekly Summary" },
  { id: "alert_report", name: "Alert Report" },
  { id: "detection_coverage", name: "Detection Coverage" },
  { id: "source_health", name: "Source Health" },
  { id: "executive_summary", name: "Executive Security Summary" },
];

export default function Reports() {
  const [reports, setReports] = useState(null);
  const [type, setType] = useState("soc_weekly");
  const [range, setRange] = useState("7d");
  const [busy, setBusy] = useState(false);

  const load = () => client.get("/reports").then(({ data }) => setReports(data.reports));
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setBusy(true);
    try {
      const name = TYPES.find((t) => t.id === type)?.name;
      await client.post("/reports/generate", { type, time_range: range, title: name });
      toast.success("Report generated"); load();
    } finally { setBusy(false); }
  };
  const download = (id, fmt) => {
    const token = localStorage.getItem("sl_token"), ws = localStorage.getItem("sl_workspace");
    fetch(`${API}/reports/${id}/download?format=${fmt}`, { headers: { Authorization: `Bearer ${token}`, "X-Workspace-Id": ws } })
      .then((r) => r.blob()).then((b) => { const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = `report-${id}.${fmt}`; a.click(); });
  };

  return (
    <div data-testid="reports-export-page">
      <PageHead title="Reports & Export" desc="Generate and export SOC reports from stored data" />
      <div className="card p-4 mb-4">
        <div className="text-[11px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Generate New Report</div>
        <div className="flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[220px]">
            <label className="text-[11px]" style={{ color: "var(--text-3)" }}>Report Type</label>
            <select className="inp mt-1" value={type} onChange={(e) => setType(e.target.value)} data-testid="report-type">{TYPES.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
          </div>
          <div className="w-32">
            <label className="text-[11px]" style={{ color: "var(--text-3)" }}>Time Range</label>
            <select className="inp mt-1" value={range} onChange={(e) => setRange(e.target.value)} data-testid="report-range">{["24h", "7d", "30d"].map((r) => <option key={r} value={r}>Last {r}</option>)}</select>
          </div>
          <button className="btn btn-primary" onClick={generate} disabled={busy} data-testid="generate-report"><Plus size={13} /> {busy ? "Generating…" : "Generate"}</button>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
        {TYPES.map((t) => (
          <button key={t.id} className="card p-3.5 text-left row-hover" onClick={() => setType(t.id)} data-testid={`report-template-${t.id}`}
            style={{ borderColor: type === t.id ? "var(--cyan)" : "var(--border)" }}>
            <FileBarChart size={16} style={{ color: "var(--cyan)" }} />
            <div className="text-[13px] font-medium mt-2" style={{ color: "var(--text)" }}>{t.name}</div>
          </button>
        ))}
      </div>
      <div className="card overflow-hidden">
        <div className="px-4 py-2.5 border-b font-head font-semibold text-[14px]">Report History</div>
        {!reports ? <Loading /> : !reports.length ? <Empty msg="No reports generated yet" testId="reports-empty" /> : (
          <table className="dense w-full">
            <thead><tr><th>Title</th><th>Range</th><th>Events</th><th>Alerts</th><th>Generated</th><th>Download</th></tr></thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="border-t row-hover" data-testid={`report-row-${r.id}`}>
                  <td style={{ color: "var(--text)" }}>{r.title}</td>
                  <td className="font-mono" style={{ color: "var(--text-2)" }}>{r.time_range}</td>
                  <td className="font-mono" style={{ color: "var(--cyan)" }}>{r.summary?.events}</td>
                  <td className="font-mono" style={{ color: "#FB923C" }}>{r.summary?.alerts}</td>
                  <td className="font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(r.created_at).slice(0, 16)}</td>
                  <td className="flex gap-1.5">
                    <button className="btn btn-sm" onClick={() => download(r.id, "json")} data-testid={`dl-json-${r.id}`}><Download size={12} /> JSON</button>
                    <button className="btn btn-sm" onClick={() => download(r.id, "csv")} data-testid={`dl-csv-${r.id}`}><Download size={12} /> CSV</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
