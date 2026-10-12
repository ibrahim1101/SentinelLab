"""Incident-response playbooks. Analyst-controlled, safe-by-default: every step that
touches an external system or sends a notification is gated behind explicit approval.
Dry-run simulates all steps with zero side effects."""
from core import db, new_id, now_iso

# action -> requires explicit approval (external/impactful)
BUILTIN = [
    {"id": "brute_force", "name": "Brute-Force Investigation", "severity": "high",
     "description": "Triage repeated authentication failures and a possible account compromise.",
     "steps": [
         {"id": "collect", "name": "Collect related authentication events", "action": "collect_events", "approval": False},
         {"id": "enrich", "name": "Enrich source IPs against threat intel", "action": "enrich_iocs", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "assign", "name": "Assign to on-call analyst", "action": "assign_analyst", "approval": False},
         {"id": "tasks", "name": "Add containment tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Confirm whether login eventually succeeded", "Force password reset for targeted account", "Review source IP reputation"]},
         {"id": "notify", "name": "Notify account owner (external email)", "action": "notify", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "suspicious_process", "name": "Suspicious Process Investigation", "severity": "high",
     "description": "Investigate anomalous or suspicious process execution (e.g. encoded PowerShell).",
     "steps": [
         {"id": "collect", "name": "Collect related process events", "action": "collect_events", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "tasks", "name": "Add triage tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Decode command line arguments", "Check parent-child process chain", "Validate binary hash reputation"]},
         {"id": "isolate", "name": "Isolate host (EDR action)", "action": "isolate_host", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "phishing", "name": "Phishing Investigation", "severity": "medium",
     "description": "Handle a reported or detected phishing attempt.",
     "steps": [
         {"id": "collect", "name": "Collect related email/web events", "action": "collect_events", "approval": False},
         {"id": "enrich", "name": "Enrich URLs/domains against threat intel", "action": "enrich_iocs", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "tasks", "name": "Add response tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Identify all recipients", "Pull the message from mailboxes", "Block sender domain"]},
         {"id": "block", "name": "Block sender domain (mail gateway)", "action": "block_indicator", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "malware_triage", "name": "Malware Alert Triage", "severity": "critical",
     "description": "Triage a malware/IOC alert and scope the impact.",
     "steps": [
         {"id": "collect", "name": "Collect related events", "action": "collect_events", "approval": False},
         {"id": "enrich", "name": "Enrich file hashes against threat intel", "action": "enrich_iocs", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "assign", "name": "Assign to incident responder", "action": "assign_analyst", "approval": False},
         {"id": "tasks", "name": "Add containment tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Determine infection vector", "Scope affected hosts", "Collect forensic artifacts"]},
         {"id": "isolate", "name": "Isolate affected host (EDR action)", "action": "isolate_host", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "compromised_account", "name": "Compromised Account Investigation", "severity": "high",
     "description": "Investigate signs of account takeover (suspicious login after failures).",
     "steps": [
         {"id": "collect", "name": "Collect authentication events", "action": "collect_events", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "tasks", "name": "Add tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Review login geolocations", "Check for new MFA devices", "Audit recent account activity"]},
         {"id": "disable", "name": "Disable account (IdP action)", "action": "disable_account", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "suspicious_network", "name": "Suspicious Network Connection", "severity": "medium",
     "description": "Investigate outbound connections to rare/flagged destinations or beaconing.",
     "steps": [
         {"id": "collect", "name": "Collect related network events", "action": "collect_events", "approval": False},
         {"id": "enrich", "name": "Enrich destination IPs against threat intel", "action": "enrich_iocs", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "tasks", "name": "Add tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Identify initiating process", "Assess data volume transferred", "Check destination reputation"]},
         {"id": "block", "name": "Block destination IP (firewall)", "action": "block_indicator", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
    {"id": "data_exfiltration", "name": "Potential Data Exfiltration", "severity": "critical",
     "description": "Respond to indicators of large or anomalous outbound data transfer.",
     "steps": [
         {"id": "collect", "name": "Collect related events", "action": "collect_events", "approval": False},
         {"id": "case", "name": "Open an investigation case", "action": "create_investigation", "approval": False},
         {"id": "assign", "name": "Assign to incident responder", "action": "assign_analyst", "approval": False},
         {"id": "tasks", "name": "Add tasks", "action": "add_tasks", "approval": False,
          "tasks": ["Quantify data volume", "Identify data classification", "Determine destination"]},
         {"id": "block", "name": "Block destination (firewall)", "action": "block_indicator", "approval": True},
         {"id": "summary", "name": "Generate investigation summary", "action": "generate_summary", "approval": False},
     ]},
]

PLAYBOOK_MAP = {p["id"]: p for p in BUILTIN}


async def execute(playbook, org_id, alert, user, dry_run=True, approvals=None):
    """Run a playbook against an alert. Returns an execution record. Approval-gated
    steps execute only when their step id is in `approvals` and dry_run is False."""
    approvals = set(approvals or [])
    results = []
    created_investigation_id = None
    related = []

    for step in playbook["steps"]:
        entry = {"step_id": step["id"], "name": step["name"], "action": step["action"],
                 "requires_approval": step["approval"]}
        # gate
        if step["approval"] and (dry_run or step["id"] not in approvals):
            entry["status"] = "pending_approval" if not dry_run else "simulated"
            entry["detail"] = "Approval required before this action runs." if not dry_run \
                else "DRY-RUN: external action simulated, no changes made."
            results.append(entry)
            continue

        action = step["action"]
        try:
            if action == "collect_events":
                related = alert.get("related_events", []) if alert else []
                entry["status"] = "ok"
                entry["detail"] = f"Collected {len(related)} related event(s)."
            elif action == "enrich_iocs":
                iocs = [alert["src_ip"]] if alert and alert.get("src_ip") else []
                if not iocs:
                    entry["status"] = "skipped"
                    entry["detail"] = "No indicators available for enrichment."
                    results.append(entry)
                    continue
                matches = 0
                for v in iocs:
                    if await db.indicators.find_one({"org_id": org_id, "value": v, "active": True}):
                        matches += 1
                entry["status"] = "ok"
                entry["detail"] = f"Checked {len(iocs)} indicator(s); {matches} known-bad match(es)."
            elif action == "create_investigation":
                if dry_run:
                    entry["detail"] = "DRY-RUN: investigation would be created."
                else:
                    inv = {"id": new_id(), "org_id": org_id,
                           "title": f"{playbook['name']}: {alert.get('title','alert') if alert else 'manual'}",
                           "severity": alert.get("severity", playbook["severity"]) if alert else playbook["severity"],
                           "priority": playbook["severity"], "status": "investigating",
                           "lead": user["email"], "related_alerts": [alert["id"]] if alert else [],
                           "related_events": related, "related_assets": [], "notes": [], "tasks": [],
                           "evidence": [], "findings": f"Auto-created by playbook '{playbook['name']}'.",
                           "created_at": now_iso(), "updated_at": now_iso(),
                           "is_synthetic": org_id == "org-training"}
                    await db.investigations.insert_one(dict(inv))
                    created_investigation_id = inv["id"]
                    if alert:
                        await db.alerts.update_one({"id": alert["id"], "org_id": org_id},
                                                   {"$set": {"investigation_id": inv["id"], "status": "investigating"}})
                    entry["detail"] = f"Created investigation {inv['id'][:8]}."
                    entry["investigation_id"] = created_investigation_id
                entry["status"] = "ok"
            elif action == "assign_analyst":
                entry["status"] = "ok"
                if not dry_run and created_investigation_id:
                    await db.investigations.update_one({"id": created_investigation_id, "org_id": org_id},
                                                       {"$set": {"lead": user["email"]}})
                entry["detail"] = f"Assigned to {user['email']}."
            elif action == "add_tasks":
                tasks = step.get("tasks", [])
                if not dry_run and created_investigation_id:
                    for t in tasks:
                        await db.investigations.update_one({"id": created_investigation_id, "org_id": org_id},
                            {"$push": {"tasks": {"id": new_id(), "text": t, "done": False, "ts": now_iso()}}})
                entry["status"] = "ok"
                entry["detail"] = f"{'Would add' if dry_run else 'Added'} {len(tasks)} task(s)."
            elif action == "generate_summary":
                entry["status"] = "ok"
                entry["detail"] = (f"Summary: playbook '{playbook['name']}' executed for "
                                   f"alert '{alert.get('title') if alert else 'manual'}' with "
                                   f"{len(related)} related events.")
            elif action in ("notify", "isolate_host", "block_indicator", "disable_account"):
                # approved external action — recorded, not actually performed against real systems
                entry["status"] = "simulated"
                entry["detail"] = f"APPROVED external action '{action}' recorded in audit trail (no live system connected)."
            else:
                entry["status"] = "skipped"
                entry["detail"] = "Unknown action."
        except Exception as ex:
            entry["status"] = "error"
            entry["detail"] = str(ex)
        results.append(entry)

    record = {
        "id": new_id(), "org_id": org_id, "playbook_id": playbook["id"],
        "playbook_name": playbook["name"], "alert_id": alert["id"] if alert else None,
        "dry_run": dry_run, "run_by": user["email"], "created_at": now_iso(),
        "investigation_id": created_investigation_id,
        "status": ("failed" if any(r["status"] == "error" for r in results) else
                   "needs_approval" if any(r["status"] == "pending_approval" for r in results) else
                   "completed_with_skips" if any(r["status"] == "skipped" for r in results) else "completed"),
        "steps": results,
    }
    if not dry_run:
        await db.automation_executions.insert_one(dict(record))
        record.pop("_id", None)
    return record
