import { useEffect, useState } from "react";
import client from "@/lib/api";
import { PageHead, Loading } from "@/components/common";
import { Target, ShieldCheck, ShieldAlert } from "lucide-react";

export default function Mitre() {
  const [d, setD] = useState(null);
  const [sel, setSel] = useState(null);

  useEffect(() => { client.get("/mitre/coverage").then(({ data }) => setD(data)); }, []);
  if (!d) return <Loading />;

  const byTactic = (tid) => d.techniques.filter((t) => t.tactics.includes(tid));
  const cellColor = (t) => {
    if (t.alerts > 0) return { bg: "rgba(248,113,113,.22)", bd: "rgba(248,113,113,.55)", fg: "#F87171" };
    if (t.covered) return { bg: "rgba(6,182,212,.16)", bd: "rgba(6,182,212,.5)", fg: "var(--cyan)" };
    return { bg: "var(--surface)", bd: "var(--border)", fg: "var(--text-3)" };
  };

  return (
    <div data-testid="mitre-page">
      <PageHead title="MITRE ATT&CK Coverage" desc={`Detection coverage & gap analysis · ${d.version}`} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="card p-3.5"><div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Coverage</div><div className="kpi-val mt-2" style={{ color: "var(--cyan)" }}>{d.coverage_pct}%</div></div>
        <div className="card p-3.5"><div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Techniques Covered</div><div className="kpi-val mt-2" style={{ color: "#22c55e" }}>{d.covered_count}/{d.total}</div></div>
        <div className="card p-3.5"><div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Detection Gaps</div><div className="kpi-val mt-2" style={{ color: "#FB923C" }}>{d.gap_count}</div></div>
        <div className="card p-3.5"><div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>With Live Alerts</div><div className="kpi-val mt-2" style={{ color: "#F87171" }}>{d.techniques.filter((t) => t.alerts > 0).length}</div></div>
      </div>

      <div className="flex gap-3 mb-3 text-[11px]" style={{ color: "var(--text-2)" }}>
        <span className="flex items-center gap-1.5"><span className="status-dot" style={{ background: "var(--cyan)" }} /> Covered by rule</span>
        <span className="flex items-center gap-1.5"><span className="status-dot" style={{ background: "#F87171" }} /> Active alerts</span>
        <span className="flex items-center gap-1.5"><span className="status-dot" style={{ background: "var(--text-3)" }} /> No coverage (gap)</span>
      </div>

      <div className="card p-3 overflow-x-auto" data-testid="mitre-matrix">
        <div className="flex gap-2 min-w-max">
          {d.tactics.map((tac) => (
            <div key={tac.id} className="w-[150px] shrink-0">
              <div className="text-[11px] font-semibold mb-2 pb-1.5 border-b" style={{ color: "var(--text)" }}>{tac.name}</div>
              <div className="space-y-1">
                {byTactic(tac.id).map((t) => {
                  const c = cellColor(t);
                  return (
                    <button key={t.id + tac.id} onClick={() => setSel(t)} data-testid={`mitre-tech-${t.id}`}
                      className="w-full text-left px-2 py-1.5 rounded text-[10.5px] transition"
                      style={{ background: c.bg, border: `1px solid ${c.bd}`, color: c.fg }}>
                      <div className="font-mono">{t.id}</div>
                      <div className="truncate" style={{ color: "var(--text-2)" }}>{t.name}</div>
                      {t.alerts > 0 && <div className="mt-0.5 font-mono" style={{ color: "#F87171" }}>{t.alerts} alert(s)</div>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <div className="card p-4" data-testid="mitre-detail">
          <div className="flex items-center gap-2 mb-2"><Target size={15} style={{ color: "var(--cyan)" }} /><span className="font-head font-semibold text-[14px]">Technique Detail</span></div>
          {!sel ? <div className="text-[12.5px] py-6 text-center" style={{ color: "var(--text-3)" }}>Select a technique</div> : (
            <>
              <div className="flex items-center gap-2 mb-1"><span className="font-mono" style={{ color: "var(--cyan)" }}>{sel.id}</span><span className="text-[14px]" style={{ color: "var(--text)" }}>{sel.name}</span></div>
              <div className="text-[12px] mb-3" style={{ color: "var(--text-2)" }}>{sel.covered ? <ShieldCheck size={13} className="inline mr-1" style={{ color: "var(--cyan)" }} /> : <ShieldAlert size={13} className="inline mr-1" style={{ color: "#FB923C" }} />}{sel.covered ? "Covered" : "No detection coverage (gap)"} · {sel.alerts} alert(s)</div>
              <div className="text-[11px] uppercase mb-1" style={{ color: "var(--text-3)" }}>Mapped Rules</div>
              {sel.rules.length ? sel.rules.map((r) => <div key={r.id} className="text-[12.5px] py-1 border-b" style={{ color: "var(--text-2)" }}>{r.name}</div>) : <div className="text-[12px]" style={{ color: "var(--text-3)" }}>None — consider authoring a detection rule.</div>}
            </>
          )}
        </div>
        <div className="card p-4" data-testid="mitre-gaps">
          <div className="flex items-center gap-2 mb-2"><ShieldAlert size={15} style={{ color: "#FB923C" }} /><span className="font-head font-semibold text-[14px]">Detection Gaps ({d.gap_count})</span></div>
          <div className="max-h-72 overflow-auto">
            {d.gaps.map((t) => (
              <div key={t.id} className="flex items-center justify-between py-1 border-b text-[12px]">
                <span><span className="font-mono" style={{ color: "#FB923C" }}>{t.id}</span> <span style={{ color: "var(--text-2)" }}>{t.name}</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
