"""Built-in detection rules + synthetic telemetry seeding for the Training Lab workspace.
All seeded telemetry is flagged is_synthetic=True and partitioned by workspace."""
import random
from datetime import datetime, timezone, timedelta
from core import db, new_id, now_iso
from detection import run_detection

random.seed(1337)


def builtin_rules(org_id):
    base = lambda **k: {
        "id": new_id(), "org_id": org_id, "version": "1.0", "enabled": True,
        "match_count": 0, "last_run": None, "last_error": None,
        "author": "SentinelLab", "created_at": now_iso(), "updated_at": now_iso(),
        "confidence": 80, **k}
    return [
        base(name="Brute Force Authentication", rule_type="threshold", severity="high",
             description="Multiple failed logins from the same source within a short window.",
             mitre=["T1110"],
             params={"conditions": [{"field": "category", "op": "eq", "value": "authentication"},
                                    {"field": "outcome", "op": "eq", "value": "failure"}],
                     "group_by": "src_ip", "window_minutes": 5, "threshold": 5}),
        base(name="Password Spraying", rule_type="threshold", severity="high",
             description="Single source attempting failed logins across many accounts.",
             mitre=["T1110.003"],
             params={"conditions": [{"field": "category", "op": "eq", "value": "authentication"},
                                    {"field": "outcome", "op": "eq", "value": "failure"}],
                     "group_by": "src_ip", "window_minutes": 10, "threshold": 8}),
        base(name="Port Scan Detected", rule_type="threshold", severity="medium",
             description="Many distinct destination ports contacted by one source.",
             mitre=["T1046"],
             params={"conditions": [{"field": "category", "op": "eq", "value": "network"}],
                     "group_by": "src_ip", "window_minutes": 2, "threshold": 10}),
        base(name="Suspicious PowerShell Execution", rule_type="match", severity="high",
             description="PowerShell launched with encoded/hidden command flags.",
             mitre=["T1059.001"],
             params={"conditions": [{"field": "process_name", "op": "contains", "value": "powershell"},
                                    {"field": "command_line", "op": "regex", "value": "-enc|-nop|-w hidden|downloadstring|frombase64"}]}),
        base(name="Known Malicious IOC Match", rule_type="indicator", severity="critical",
             description="Event field matched an active threat-intel indicator.",
             mitre=["T1071"], confidence=90, params={}),
        base(name="Repeated Access Denied", rule_type="threshold", severity="medium",
             description="Repeated access-denied events for a single user.",
             mitre=["T1078"],
             params={"conditions": [{"field": "action", "op": "eq", "value": "access-denied"}],
                     "group_by": "username", "window_minutes": 10, "threshold": 6}),
        base(name="New Administrative Account Creation", rule_type="match", severity="high",
             description="Creation of a privileged/admin account.", mitre=["T1136"],
             params={"conditions": [{"field": "action", "op": "eq", "value": "account-created"},
                                    {"field": "tags", "op": "contains", "value": "admin"}]}),
        base(name="Suspicious Outbound Connection", rule_type="match", severity="medium",
             description="Outbound connection to a flagged/rare destination.", mitre=["T1071"],
             params={"conditions": [{"field": "category", "op": "eq", "value": "network"},
                                    {"field": "tags", "op": "contains", "value": "outbound-suspicious"}]}),
    ]


SRC_DEFS = [
    ("auth-srv-01", "Windows Security", "192.168.1.10", "windows"),
    ("nscout", "Network Sensor", "10.0.0.1", "network"),
    ("win-log-01", "Windows Logs", "PC-DEV-01", "windows"),
    ("web-proxy", "Proxy Logs", "10.0.0.5", "firewall"),
    ("filemon", "File Monitor", "SRV-DB-01", "application"),
    ("linux-auth", "Linux Auth", "10.0.0.20", "linux"),
    ("dns-srv-01", "DNS Logs", "10.0.4.12", "network"),
    ("ids-01", "Suricata IDS", "10.0.0.2", "ids_ips"),
]

HOSTS = ["192.168.1.10", "10.0.0.45", "PC-DEV-01", "SRV-DB-01", "10.0.4.12", "WKS-FIN-07"]
USERS = ["admin", "jsmith", "svc_backup", "arao", "root", "dkhan", "administrator"]
ATTACKER_IPS = ["185.220.101.5", "45.133.1.88", "193.27.228.12"]
INTERNAL_IPS = ["192.168.1.105", "10.0.4.12", "10.0.0.45", "192.168.1.50"]


def _ts(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _mk(org_id, source, **kw):
    base = {
        "id": new_id(), "org_id": org_id, "source_id": source[0], "source_name": source[1],
        "ingested_at": now_iso(), "schema_version": "1.0", "parser_version": "1.0",
        "is_synthetic": True, "rule_matches": [], "severity": "info",
        "category": "other", "outcome": None, "action": None, "host": None,
        "src_ip": None, "dest_ip": None, "src_port": None, "dest_port": None,
        "username": None, "process_name": None, "command_line": None,
        "file_hash": None, "protocol": None, "dns_query": None, "tags": [],
        "mitre": [], "parent_process": None, "file_path": None, "process_id": None,
    }
    base["raw"] = {k: v for k, v in kw.items() if v is not None}
    base.update(kw)
    return base


def generate_events(org_id):
    events = []
    src = {s[0]: s for s in SRC_DEFS}
    # 1) Brute force burst (auth-srv-01): 12 failures same src_ip/user in 4 min
    for i in range(12):
        events.append(_mk(org_id, src["auth-srv-01"], category="authentication",
                          event_type="Authentication", action="login", outcome="failure",
                          severity="high", host="192.168.1.10", username="admin",
                          src_ip="185.220.101.5", auth_result="failure",
                          timestamp=_ts(30 - i * 0.3), tags=["auth"]))
    # success after failures
    events.append(_mk(org_id, src["auth-srv-01"], category="authentication",
                      event_type="Authentication", action="login", outcome="success",
                      severity="medium", host="192.168.1.10", username="admin",
                      src_ip="185.220.101.5", timestamp=_ts(25), tags=["auth"]))
    # 2) Password spray: one IP, many users, 10 failures in 8 min
    for i, u in enumerate((USERS * 2)[:10]):
        events.append(_mk(org_id, src["linux-auth"], category="authentication",
                          event_type="Authentication", action="login", outcome="failure",
                          severity="medium", host="10.0.0.20", username=u,
                          src_ip="45.133.1.88", timestamp=_ts(120 - i * 0.7), tags=["auth"]))
    # 3) Port scan: one src, many dest ports in 90s
    for p in range(20, 20 + 14):
        events.append(_mk(org_id, src["nscout"], category="network",
                          event_type="Connection", action="connect", outcome="success",
                          severity="low", host="10.0.0.45", src_ip="193.27.228.12",
                          dest_ip="10.0.0.45", dest_port=p, protocol="TCP",
                          timestamp=_ts(60 - (p - 20) * 0.1), tags=["network"]))
    # 4) Suspicious PowerShell
    for i in range(3):
        events.append(_mk(org_id, src["win-log-01"], category="process",
                          event_type="Process", action="process-create", outcome="success",
                          severity="high", host="PC-DEV-01", username="jsmith",
                          process_name="powershell.exe", parent_process="winword.exe",
                          process_id=4120 + i,
                          command_line="powershell.exe -nop -w hidden -enc SQBFAFgA",
                          timestamp=_ts(45 + i * 3), mitre=["T1059.001"], tags=["process"]))
    # 5) IOC match (malicious IP) - also seed the indicator
    for i in range(2):
        events.append(_mk(org_id, src["web-proxy"], category="network",
                          event_type="Connection", action="connect", outcome="success",
                          severity="medium", host="10.0.0.45", src_ip="192.168.1.105",
                          dest_ip="185.220.101.5", dest_port=443, protocol="TCP",
                          timestamp=_ts(15 + i), tags=["outbound-suspicious", "network"]))
    # 6) DNS noise
    for i in range(25):
        events.append(_mk(org_id, src["dns-srv-01"], category="dns",
                          event_type="DNS", action="query", outcome="success",
                          severity="info", host="WKS-FIN-07",
                          src_ip=random.choice(INTERNAL_IPS),
                          dns_query=random.choice(["update.microsoft.com", "example.com",
                                                   "cdn.cloudflare.com", "x9f3k2.ddns.net"]),
                          timestamp=_ts(random.randint(1, 1400)), tags=["dns"]))
    # 7) general background noise
    cats = ["network", "process", "file", "authentication"]
    for i in range(400):
        c = random.choice(cats)
        events.append(_mk(org_id, random.choice(list(src.values())), category=c,
                          event_type=c.title(), action="observed",
                          outcome=random.choice(["success", "success", "failure"]),
                          severity=random.choice(["info", "low", "low", "medium"]),
                          host=random.choice(HOSTS), username=random.choice(USERS),
                          src_ip=random.choice(INTERNAL_IPS + ATTACKER_IPS),
                          dest_ip=random.choice(INTERNAL_IPS),
                          dest_port=random.choice([80, 443, 22, 3389, 53, 8080]),
                          protocol=random.choice(["TCP", "UDP"]),
                          process_name=random.choice(["chrome.exe", "sshd", "nginx", "python"]),
                          timestamp=_ts(random.randint(1, 1440)), tags=[c]))
    return events


async def seed_training_workspace(org_id):
    if await db.events.count_documents({"org_id": org_id, "is_synthetic": True}) > 0:
        return
    # sources
    for name, typ, host, cat in SRC_DEFS:
        await db.sources.insert_one({
            "id": name, "org_id": org_id, "name": name, "display_name": typ,
            "source_type": cat, "host": host, "status": "online", "enabled": True,
            "events_received": 0, "last_received": now_iso(),
            "token_hint": "sl_" + new_id()[:8], "parse_errors": 0,
            "created_at": now_iso(), "is_synthetic": True})
    # indicator for IOC rule
    await db.indicators.insert_one({
        "id": new_id(), "org_id": org_id, "ioc_type": "ip", "value": "185.220.101.5",
        "confidence": 90, "source": "Internal TI", "tags": ["c2", "tor-exit"],
        "active": True, "created_at": now_iso(), "is_synthetic": True})
    # rules
    for r in builtin_rules(org_id):
        await db.detection_rules.insert_one(r)
    # events
    events = generate_events(org_id)
    await db.events.insert_many([dict(e) for e in events])
    for name, *_ in [(s[0],) for s in SRC_DEFS]:
        cnt = await db.events.count_documents({"org_id": org_id, "source_id": name})
        await db.sources.update_one({"id": name, "org_id": org_id},
                                    {"$set": {"events_received": cnt}})
    # run detection -> real alerts
    stored = await db.events.find({"org_id": org_id}, {"_id": 0}).to_list(5000)
    await run_detection(org_id, stored, persist=True)
    # seed a couple of investigations
    alerts = await db.alerts.find({"org_id": org_id}, {"_id": 0}).limit(3).to_list(3)
    inv_defs = [
        ("Suspicious authentication activity", "high", "investigating"),
        ("Network scan investigation", "medium", "open"),
    ]
    for i, (title, sev, status) in enumerate(inv_defs):
        rel = [alerts[i]["id"]] if i < len(alerts) else []
        await db.investigations.insert_one({
            "id": new_id(), "org_id": org_id, "title": title, "severity": sev,
            "priority": sev, "status": status, "lead": "admin",
            "related_alerts": rel, "related_events": [], "related_assets": [],
            "notes": [], "tasks": [], "evidence": [], "findings": "",
            "created_at": now_iso(), "updated_at": now_iso(), "is_synthetic": True})
        if rel:
            await db.alerts.update_one({"id": rel[0]},
                                       {"$set": {"investigation_id": title}})
