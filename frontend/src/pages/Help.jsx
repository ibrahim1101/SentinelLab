import { useMemo, useState } from "react";
import { PageHead } from "@/components/common";

const guide = [
  ["Getting started", [
    ["Install and launch", "Install MongoDB Community Server locally and ensure port 27017 is reachable. Install the SentinelLab Windows app and launch it; its bundled API starts automatically. MongoDB is a separate service."],
    ["First administrator setup", "On an empty database, complete the initial administrator form. On an existing database, sign in using the previously created account. Do not manually edit password hashes in MongoDB."],
    ["Login modes", "Administrator Login accepts admin and super_admin roles; Non-Admin Login accepts other roles. Correct credentials in the wrong mode are rejected. Repeated invalid passwords can trigger temporary account lockouts."],
    ["Service indicators", "On the login screen, the bottom-right lights show backend diagnostics, MongoDB reachability and API readiness. Red indicates unavailable or still starting; verify MongoDB service and restart if necessary."],
    ["Closing and upgrading", "Click the window close button, review the process confirmation and confirm. The bundled API should terminate; MongoDB continues independently. Verify the API is stopped before upgrading."],
  ]],
  ["Workspace and navigation", [
    ["Sidebar", "Use the left navigation to open SOC modules. Administration appears only for administrators. How to Use is available to signed-in users."],
    ["Workspace selector", "Choose Training Lab for synthetic demonstrations or an authorized production workspace for real data. Always check the active workspace before modifying records."],
    ["Time range", "Use the top-bar range selector to control supported dashboard and search windows. A narrower range is useful for triage; a longer range helps trend analysis."],
    ["Global search", "Search for event, alert, investigation, rule, asset, host or IP identifiers in the top bar. Open a result to continue in its module."],
    ["Notifications and profile", "Use the bell for recent notifications, the palette menu to change appearance, and the profile menu to inspect your role and sign out."],
  ]],
  ["Monitoring and detection", [
    ["Overview", "Start with summary metrics and activity charts. Confirm the workspace and time range, then follow unusual counts or trends into Events or Alerts."],
    ["Events Explorer", "Inspect normalized security events, filter by available fields and time, and examine details before deciding whether an event is suspicious."],
    ["Sources & Ingestion", "Review configured sources and incoming event health. Supported input formats include JSON, JSONL, CSV, Syslog and CEF. Check parsing failures and source status if events are missing."],
    ["Pipeline Observatory", "Inspect the event pipeline stages and throughput or failures. Follow ingestion or parsing anomalies to the affected source."],
    ["Detection Rules", "Review detection logic and rule status. Test changes with known sample events before enabling them for production workflows."],
    ["Detection Replay", "Replay eligible historical or sample events against detection logic to validate results without assuming a live incident occurred."],
    ["Alerts", "Review triggered detections, severity and context. Open the alert, compare supporting events and assign or escalate according to your response process."],
    ["Threat Hunting", "Use hypotheses, filters and available query controls to search for suspicious behavior across events. Save or document findings in an investigation."],
    ["MITRE ATT&CK", "Use technique mappings to understand attacker behaviors and detection coverage. Mappings provide context; they do not prove compromise on their own."],
    ["Threat Intelligence", "Review available indicators and enrichment. External reputation services require configuration; unavailable integrations must not be treated as clean results."],
  ]],
  ["Investigation and response", [
    ["Investigations", "Create or open a case, link relevant evidence and alerts, record findings, and track the response state. Preserve original evidence when possible."],
    ["Investigation Graph", "Explore linked entities and relationships to understand which hosts, IPs, alerts or events may be connected. Validate relationships against underlying evidence."],
    ["Playbooks", "Review available response steps and prerequisites before running actions. Confirm targets, scope and permissions, especially in production."],
    ["Reports", "Choose the available report scope and time window, review the generated information, and export or share only with authorized recipients."],
    ["AI Security Assistant", "Ask for help interpreting security data or planning an investigation. Verify its suggestions against evidence; provider availability depends on configuration."],
  ]],
  ["Settings and administration", [
    ["General settings", "Configure application name, timezone, default time range and theme. Demo Mode uses simulated data; Reset Training Lab Data can replace demonstration records and requires confirmation."],
    ["Security overview", "Review password hashing, session policy, rate limits, role-based access, audit logging and workspace isolation. These summaries are informational."],
    ["Create analyst", "Settings → Security → Create analyst: enter full name, unique email and username, and a strong initial password. The account starts with Training Lab access."],
    ["User and role management", "Settings → Security → User & Role Management: inspect users and change roles only when required. Confirm role changes and apply least privilege."],
    ["Account actions", "Super administrators can change usernames, reset other users' passwords, and enable or disable eligible accounts. Password resets revoke existing sessions; verify the user's identity first."],
    ["Login security alerts", "Super administrators can review repeated failed-login incidents and unlock an account after verifying the user. Never unlock solely because someone requests it."],
    ["Production membership", "Review workspace memberships and request or revoke production access. Approval may require a second super administrator. Review reconciliation states after interrupted approvals."],
    ["Ingestion settings", "Review the pipeline sequence, accepted formats, parser/schema versions and dead-letter behavior. This tab describes ingestion capabilities rather than automatically configuring sources."],
    ["Retention", "Set the supported retention window carefully. Events older than the configured period may be eligible for cleanup; evidence handling can follow separate rules."],
    ["Integrations", "Check the status of the AI adapter and optional reputation, webhook or email integrations. Offline integrations require their own credentials and configuration."],
    ["About and audit", "Review application information, database and service health, and recent audit entries. Use the audit history to investigate administrative changes."],
  ]],
  ["Troubleshooting and safe operation", [
    ["Backend offline", "Check that SentinelLab launched correctly and that the API process is running. Restart the desktop application if the backend remains unavailable."],
    ["MongoDB unavailable", "Check the MongoDB Windows service and local port 27017. A service being installed does not guarantee it is reachable."],
    ["No events or alerts", "Verify workspace, time range, source configuration and ingestion health. No alerts does not automatically mean no threats."],
    ["Permissions denied", "Check your account role and workspace membership. Ask an administrator for access rather than changing MongoDB records directly."],
    ["Installer cannot replace API", "Close SentinelLab, confirm shutdown, and verify no sentinellab-api.exe process remains before retrying the installer. Do not select Ignore on a locked executable."],
    ["Security practices", "Use unique strong passwords, least privilege, separate Training Lab from production, and review audit records after sensitive operations."],
  ]],
];

export function HelpContent() {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState({});
  const sections = useMemo(() => guide.map(([title, entries]) => [title, entries.filter(([name, body]) => (title+" "+name+" "+body).toLowerCase().includes(query.toLowerCase()))]).filter(([,entries]) => entries.length), [query]);
  return <div className="space-y-4" data-testid="complete-user-guide">
    <p className="text-[12px] leading-relaxed" style={{color:"var(--text-2)"}}>This guide covers the current SentinelLab navigation and main controls. Some capabilities require administrator permissions, an active data source or an optional integration. Available actions can vary by role and workspace.</p>
    <input className="inp w-full max-w-xl" type="search" aria-label="Search user guide" placeholder="Search every feature or setting…" value={query} onChange={e=>setQuery(e.target.value)} />
    <div className="text-[11px]" style={{color:"var(--text-3)"}}>{guide.reduce((n,[,entries])=>n+entries.length,0)} documented options across {guide.length} sections</div>
    {sections.map(([title,entries])=><section key={title} className="card p-4 space-y-2">
      <h2 className="text-[15px] font-semibold" style={{color:"var(--text)"}}>{title}</h2>
      {entries.map(([name,body])=>{const key=title+"/"+name;const open=query.trim() || expanded[key];return <div key={key} className="border-t pt-2">
        <button type="button" className="w-full text-left text-[13px] font-medium py-1 flex justify-between gap-3" aria-expanded={Boolean(open)} onClick={()=>setExpanded(p=>({...p,[key]:!p[key]}))}>{name}<span aria-hidden="true">{open?"−":"+"}</span></button>
        {open && <p className="text-[12px] leading-relaxed py-2" style={{color:"var(--text-2)"}}>{body}</p>}
      </div>})}
    </section>)}
    {!sections.length && <p className="text-[13px]">No guide entries match that search.</p>}
  </div>;
}

export default function Help() {
  return <div data-testid="how-to-use-page" className="max-w-5xl">
    <PageHead title="How to Use SentinelLab" desc="Feature-by-feature user and administrator manual" />
    <HelpContent />
  </div>;
}
