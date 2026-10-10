import { useEffect, useState } from "react";
import { Settings as SIcon, Shield, Database, Clock, Plug, Info, FlaskConical, RefreshCw } from "lucide-react";
import client from "@/lib/api";
import { useTheme, THEMES } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";
import { PageHead, StatusPill, fmtTime } from "@/components/common";
import { toast } from "sonner";

const TABS = [
  { id: "general", label: "General", icon: SIcon },
  { id: "security", label: "Security", icon: Shield },
  { id: "ingestion", label: "Ingestion", icon: Database },
  { id: "retention", label: "Retention", icon: Clock },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "about", label: "About", icon: Info },
];

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { user, roles } = useAuth();
  const [tab, setTab] = useState("general");
  const [s, setS] = useState(null);
  const [users, setUsers] = useState([]);
  const [newUser, setNewUser] = useState({ name: "", email: "", password: "" });
  const [creatingUser, setCreatingUser] = useState(false);
  const [audit, setAudit] = useState([]);
  const [health, setHealth] = useState(null);
  const isAdmin = ["admin", "super_admin"].includes(user?.role);
  const isSuperAdmin = user?.role === "super_admin";
  const [members, setMembers] = useState([]);
  const [approvalQueue, setApprovalQueue] = useState([]);
  const [savingMember, setSavingMember] = useState("");

  useEffect(() => {
    client.get("/settings").then(({ data }) => setS(data.settings));
    client.get("/admin/health").then(({ data }) => setHealth(data)).catch(() => {});
    if (isAdmin) client.get("/admin/users").then(({ data }) => setUsers(data.users)).catch(() => {});
    if (isSuperAdmin) client.get("/admin/production-access-requests").then(({ data }) => setApprovalQueue(data.requests)).catch(() => {});
    if (isSuperAdmin) client.get("/admin/membership-review").then(({ data }) => setMembers(data.production_members)).catch(() => toast.error("Could not load production membership review"));
    client.get("/admin/audit").then(({ data }) => setAudit(data.audit)).catch(() => {});
  }, []);

  const save = async (patch) => { const { data } = await client.put("/settings", patch); setS(data); toast.success("Settings saved"); };
  const resetDemo = async () => { if (!window.confirm("Reset Training Lab synthetic data?")) return; await client.post("/demo/reset"); toast.success("Demo data regenerated"); };
  const setUserRole = async (id, role) => { await client.put(`/admin/users/${id}/role`, { role }); toast.success("Role updated"); setUsers(users.map((u) => u.id === id ? { ...u, role } : u)); };

  const createAnalyst = async (e) => {
    e.preventDefault();
    setCreatingUser(true);
    try {
      const { data } = await client.post("/admin/users", newUser);
      setUsers((prev) => [...prev, data.user]);
      setNewUser({ name: "", email: "", password: "" });
      toast.success("Analyst created with Training Lab access");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not create analyst");
    } finally {
      setCreatingUser(false);
    }
  };

  const changeMembership = async (target, enableProduction) => {
    const org_ids = enableProduction ? [...new Set([...(target.org_ids || []), "org-production"])] : (target.org_ids || []).filter((id) => id !== "org-production");
    if (!org_ids.length) org_ids.push("org-training");
    if (!window.confirm(`${enableProduction ? "Grant" : "Revoke"} production workspace access for ${target.email}?`)) return;
    setSavingMember(target.id);
    try {
      const { data } = enableProduction
        ? await client.post(`/admin/users/${target.id}/production-access-requests`)
        : await client.put(`/admin/users/${target.id}/workspaces`, { org_ids });
      if (!enableProduction) setUsers((prev) => prev.map((u) => u.id === target.id ? { ...u, org_ids: data.org_ids, default_org: data.default_org } : u));
      const review = await client.get("/admin/membership-review");
      setMembers(review.data.production_members);
      const queue = await client.get("/admin/production-access-requests");
      setApprovalQueue(queue.data.requests);
      toast.success(enableProduction ? "Approval requested — a different super admin must approve" : "Workspace membership updated");
    } catch (err) { toast.error(err.response?.data?.detail || "Workspace membership update failed"); }
    finally { setSavingMember(""); }
  };

  const approveRequest = async (entry) => {
    if (!window.confirm("Approve production access for this user? This is a privileged operation.")) return;
    setSavingMember(entry.target_id);
    try {
      await client.post(`/admin/production-access-requests/${entry.id}/approve`);
      const [queue, people, review] = await Promise.all([client.get("/admin/production-access-requests"), client.get("/admin/users"), client.get("/admin/membership-review")]);
      setApprovalQueue(queue.data.requests); setUsers(people.data.users); setMembers(review.data.production_members);
      toast.success("Production access approved");
    } catch (err) { toast.error(err.response?.data?.detail || "Approval failed"); }
    finally { setSavingMember(""); }
  };

  const reconcileRequest = async (entry) => {
    if (!window.confirm("Reconcile this interrupted approval against actual membership? This will not grant access.")) return;
    setSavingMember(entry.target_id);
    try {
      const { data } = await client.post(`/admin/production-access-requests/${entry.id}/reconcile`);
      const queue = await client.get("/admin/production-access-requests");
      setApprovalQueue(queue.data.requests);
      toast.success(`Reconciliation completed: ${data.status}`);
    } catch (err) { toast.error(err.response?.data?.detail || "Reconciliation failed"); }
    finally { setSavingMember(""); }
  };

  if (!s) return null;

  return (
    <div data-testid="settings-page">
      <PageHead title="Settings" desc="Application configuration and management" />
      <div className="flex gap-4">
        <div className="w-48 shrink-0 space-y-0.5">
          {TABS.map((t) => (
            <button key={t.id} className={`nav-item w-full ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)} data-testid={`settings-tab-${t.id}`}>
              <t.icon size={15} /> {t.label}
            </button>
          ))}
        </div>
        <div className="flex-1 card p-5 min-w-0">
          {tab === "general" && (
            <div className="space-y-4 max-w-md">
              <Field label="Application Name"><input className="inp" defaultValue={s.app_name} onBlur={(e) => save({ app_name: e.target.value })} data-testid="set-appname" /></Field>
              <Field label="Time Zone"><input className="inp" defaultValue={s.timezone} onBlur={(e) => save({ timezone: e.target.value })} data-testid="set-tz" /></Field>
              <Field label="Default Time Range">
                <select className="inp" defaultValue={s.default_time_range} onChange={(e) => save({ default_time_range: e.target.value })} data-testid="set-range">{["15m", "1h", "24h", "7d"].map((r) => <option key={r} value={r}>Last {r}</option>)}</select>
              </Field>
              <Field label="Theme">
                <select className="inp" value={theme} onChange={(e) => setTheme(e.target.value)} data-testid="set-theme">{THEMES.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
              </Field>
              <div className="flex items-center justify-between border-t pt-4">
                <div><div className="text-[13px] font-medium flex items-center gap-1.5" style={{ color: "var(--text)" }}><FlaskConical size={14} style={{ color: "var(--cyan)" }} /> Demo Mode</div><div className="text-[11.5px]" style={{ color: "var(--text-3)" }}>Use simulated data for demonstration</div></div>
                <Toggle on={s.demo_mode} onChange={(v) => save({ demo_mode: v })} testId="demo-toggle" />
              </div>
              <button className="btn btn-sm" onClick={resetDemo} data-testid="reset-demo"><RefreshCw size={13} /> Reset Training Lab Data</button>
            </div>
          )}
          {tab === "security" && (
            <div className="space-y-3 max-w-lg text-[13px]">
              <Row k="Password Hashing" v="bcrypt (Argon2id-ready adapter)" />
              <Row k="Session Token" v="JWT · 8h expiry · httpOnly cookie + Bearer" />
              <Row k="Login Rate Limiting" v="5 attempts → 15 min lockout" />
              <Row k="RBAC" v="Server-enforced · 5 roles" />
              <Row k="Audit Logging" v="Enabled" />
              <Row k="Organization Isolation" v="All resources workspace-scoped" />
              {isAdmin && (
                <>
                  <form className="space-y-2 border rounded-md p-3 mt-4" onSubmit={createAnalyst} data-testid="create-analyst-form">
                    <div className="text-[12px] font-semibold">Create analyst · Training Lab only</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <input className="inp" aria-label="Analyst name" placeholder="Full name" required maxLength={120} value={newUser.name} onChange={(e) => setNewUser((v) => ({ ...v, name: e.target.value }))} />
                      <input className="inp" aria-label="Analyst email" placeholder="Email address" type="email" required value={newUser.email} onChange={(e) => setNewUser((v) => ({ ...v, email: e.target.value }))} />
                    </div>
                    <input className="inp" aria-label="Initial analyst password" placeholder="Initial password (12+ characters)" type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={newUser.password} onChange={(e) => setNewUser((v) => ({ ...v, password: e.target.value }))} />
                    <button type="submit" className="btn btn-primary" disabled={creatingUser}>{creatingUser ? "Creating…" : "Create Analyst"}</button>
                  </form>
                  <div className="text-[11px] uppercase mt-5 mb-2" style={{ color: "var(--text-3)" }}>User & Role Management</div>
                  <table className="dense w-full"><thead><tr><th>User</th><th>Email</th><th>Role</th></tr></thead><tbody>
                    {users.map((u) => (<tr key={u.id} className="border-t"><td style={{ color: "var(--text)" }}>{u.name}</td><td className="font-mono" style={{ color: "var(--text-2)" }}>{u.email}</td>
                      <td><select className="inp max-w-[180px]" value={u.role} onChange={(e) => setUserRole(u.id, e.target.value)} data-testid={`role-${u.id}`}>{Object.entries(roles).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td></tr>))}
                  </tbody></table>
                  {isSuperAdmin && <div className="mt-5 space-y-3" data-testid="membership-review">
                    <div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Production workspace membership review</div>
                    <p className="text-[12px]" style={{ color: "var(--text-2)" }}>Currently approved production members: {members.length}. Review older accounts before deployment. Changes are audited and require confirmation.</p>
                    <div className="space-y-2">{approvalQueue.filter((q) => q.status === "pending").map((q) => <div key={q.id} className="flex items-center justify-between gap-2 border-b py-2"><span className="text-[12px]">Pending approval: {users.find((u) => u.id === q.target_id)?.email || q.target_id}</span><button className="btn btn-sm" disabled={!!savingMember || q.requester_id === user.id} onClick={() => approveRequest(q)}>{q.requester_id === user.id ? "Awaiting second admin" : "Approve"}</button></div>)}</div>
                    {approvalQueue.some((q) => q.status === "applying" || q.status === "failed") && <div className="space-y-2 border-t pt-3" data-testid="approval-recovery">
                      <div className="text-[11px] uppercase" style={{ color: "var(--text-3)" }}>Approval recovery review</div>
                      {approvalQueue.filter((q) => q.status === "applying" || q.status === "failed").map((q) => <div key={q.id} className="flex items-center justify-between gap-2 py-1 text-[12px]"><span>{users.find((u) => u.id === q.target_id)?.email || q.target_id} · {q.status}{q.needs_reconciliation ? " · Needs reconciliation (>5 min)" : ""}{q.failure_reason ? ` · ${q.failure_reason}` : ""}</span>{q.status === "applying" && <button className="btn btn-sm" disabled={!!savingMember || !q.needs_reconciliation} onClick={() => reconcileRequest(q)}>{q.needs_reconciliation ? "Reconcile" : "Wait for completion"}</button>}</div>)}
                    </div>}
                    <div className="space-y-2">{users.map((u) => {
                      const approved = (u.org_ids || []).includes("org-production");
                      return <div key={u.id} className="flex items-center justify-between gap-3 border-b py-2">
                        <div className="min-w-0"><div className="truncate">{u.name || u.email}</div><div className="text-[11px] truncate" style={{ color: "var(--text-3)" }}>{u.email} · {approved ? "Production approved" : "Training only"}</div></div>
                        <button type="button" className="btn btn-sm" disabled={!!savingMember || (u.role === "super_admin" && approved)} onClick={() => changeMembership(u, !approved)} data-testid={`membership-${u.id}`}>{savingMember === u.id ? "Saving…" : approved ? "Revoke production" : "Request production access"}</button>
                      </div>;
                    })}</div>
                  </div>}
                </>
              )}
            </div>
          )}
          {tab === "ingestion" && (
            <div className="space-y-3 max-w-lg text-[13px]">
              <Row k="Pipeline" v="Receive → Parse → Normalize → Enrich → Persist → Detect → Alert" />
              <Row k="Supported Formats" v="JSON, JSONL, CSV, Syslog (3164/5424), CEF" />
              <Row k="Schema Version" v="1.0" />
              <Row k="Parser Version" v="1.0" />
              <Row k="Dead-letter / Parse Errors" v="Captured per source" />
            </div>
          )}
          {tab === "retention" && (
            <div className="space-y-4 max-w-md">
              <Field label={`Data Retention: ${s.retention_days} days`}>
                <input type="range" min="30" max="365" step="5" defaultValue={s.retention_days} className="w-full" onChange={(e) => setS({ ...s, retention_days: +e.target.value })} onMouseUp={(e) => save({ retention_days: +e.target.value })} data-testid="retention-slider" />
                <div className="flex justify-between text-[10px]" style={{ color: "var(--text-3)" }}><span>30d</span><span>90d</span><span>365d</span></div>
              </Field>
              <p className="text-[12px]" style={{ color: "var(--text-3)" }}>Events older than the retention window are eligible for cleanup. Evidence is retained independently per chain-of-custody policy.</p>
            </div>
          )}
          {tab === "integrations" && (
            <div className="space-y-3 max-w-lg">
              <IntegrationRow name="AI Security Assistant" status={health?.ai_assistant === "configured" ? "online" : "offline"} desc="Provider-independent adapter (OpenAI-compatible / local). Currently uses the managed key." />
              <IntegrationRow name="VirusTotal" status="offline" desc="Threat intel enrichment — requires API key" />
              <IntegrationRow name="AbuseIPDB" status="offline" desc="IP reputation — requires API key" />
              <IntegrationRow name="Slack Webhook" status="offline" desc="Alert notifications — requires webhook URL" />
              <IntegrationRow name="SMTP / Email" status="offline" desc="Email delivery for reports & alerts" />
              <p className="text-[11.5px] mt-2" style={{ color: "var(--text-3)" }}>Optional integrations are credential-driven and disconnected until configured. No API keys are hardcoded.</p>
            </div>
          )}
          {tab === "about" && (
            <div className="text-[13px] space-y-3 max-w-lg">
              <div className="flex items-center gap-2"><Shield size={20} style={{ color: "var(--cyan)" }} /><span className="font-head font-bold text-lg">SentinelLab</span><span className="pill">v1.0.0</span></div>
              <p style={{ color: "var(--text-2)" }}>Self-hostable Security Operations Center — SIEM, detection engineering, threat hunting & incident response.</p>
              <div className="text-[11px] uppercase mt-4 mb-2" style={{ color: "var(--text-3)" }}>System Health</div>
              {health && <><Row k="Database" v={<StatusPill status={health.database} />} /><Row k="Search Backend" v={health.search_backend} /><Row k="AI Assistant" v={<StatusPill status={health.ai_assistant === "configured" ? "online" : "offline"} />} /></>}
              <div className="text-[11px] uppercase mt-4 mb-2" style={{ color: "var(--text-3)" }}>Recent Audit Log</div>
              <div className="max-h-48 overflow-auto space-y-1">
                {audit.slice(0, 20).map((a) => <div key={a.id} className="text-[11px] font-mono" style={{ color: "var(--text-3)" }}>{fmtTime(a.timestamp).slice(5, 16)} · {a.user_email} · {a.action} {a.resource_type}</div>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const Field = ({ label, children }) => <div><label className="text-[11px] uppercase block mb-1" style={{ color: "var(--text-3)" }}>{label}</label>{children}</div>;
const Row = ({ k, v }) => <div className="flex justify-between border-b py-1.5"><span style={{ color: "var(--text-3)" }}>{k}</span><span className="font-mono" style={{ color: "var(--text)" }}>{v}</span></div>;
const IntegrationRow = ({ name, status, desc }) => (
  <div className="flex items-center justify-between border-b py-2.5">
    <div><div className="text-[13px] font-medium" style={{ color: "var(--text)" }}>{name}</div><div className="text-[11.5px]" style={{ color: "var(--text-3)" }}>{desc}</div></div>
    <StatusPill status={status} />
  </div>
);
function Toggle({ on, onChange, testId }) {
  return <button onClick={() => onChange(!on)} data-testid={testId} className="relative w-11 h-6 rounded-full transition" style={{ background: on ? "var(--cyan)" : "var(--border)" }}>
    <span className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all" style={{ left: on ? 22 : 2 }} /></button>;
}
