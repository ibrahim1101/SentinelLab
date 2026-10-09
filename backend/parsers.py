"""Event parsers + normalization. Converts raw telemetry (JSON/CSV/Syslog/CEF/LEEF)
into the versioned SentinelLab normalized schema. Original payload is preserved."""
import csv
import io
import json
import re
from core import new_id, now_iso

PARSER_VERSION = "1.0"
SCHEMA_VERSION = "1.0"

NORMALIZED_FIELDS = [
    "category", "event_type", "action", "outcome", "severity", "host",
    "src_ip", "dest_ip", "src_port", "dest_port", "username", "process_name",
    "process_id", "parent_process", "command_line", "file_path", "file_hash",
    "protocol", "auth_result", "mitre", "tags",
]

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_CEF_RE = re.compile(r"CEF:\d\|")


def _blank_event():
    return {
        "category": "other", "event_type": None, "action": None, "outcome": None,
        "severity": "info", "host": None, "src_ip": None, "dest_ip": None,
        "src_port": None, "dest_port": None, "username": None, "process_name": None,
        "process_id": None, "parent_process": None, "command_line": None,
        "file_path": None, "file_hash": None, "protocol": None, "auth_result": None,
        "mitre": [], "tags": [],
    }


# field aliases from common log vendors -> normalized field
_ALIAS = {
    "src_ip": ["src_ip", "source_ip", "sourceip", "srcip", "src", "clientip", "client_ip", "ip"],
    "dest_ip": ["dest_ip", "destination_ip", "dst_ip", "dstip", "dst", "destip"],
    "src_port": ["src_port", "source_port", "spt", "sport"],
    "dest_port": ["dest_port", "destination_port", "dpt", "dport", "port"],
    "username": ["username", "user", "user_name", "account", "suser", "duser", "login"],
    "host": ["host", "hostname", "computer", "dvchost", "device", "machine"],
    "process_name": ["process_name", "process", "proc", "image", "exe", "dproc"],
    "process_id": ["process_id", "pid", "dpid"],
    "parent_process": ["parent_process", "parent", "ppid_name", "parent_image"],
    "command_line": ["command_line", "cmd", "commandline", "command"],
    "file_path": ["file_path", "filepath", "path", "filename", "fname"],
    "file_hash": ["file_hash", "hash", "sha256", "md5", "filehash"],
    "protocol": ["protocol", "proto", "proto_name"],
    "action": ["action", "act", "activity"],
    "outcome": ["outcome", "result", "status", "disposition"],
    "category": ["category", "cat", "event_category", "type_category"],
    "event_type": ["event_type", "type", "eventtype", "signature"],
    "severity": ["severity", "sev", "priority", "level"],
    "auth_result": ["auth_result", "authentication_result", "auth"],
}

_SEV_MAP = {
    "0": "info", "1": "low", "2": "low", "3": "medium", "4": "medium",
    "5": "medium", "6": "high", "7": "high", "8": "critical", "9": "critical",
    "10": "critical", "info": "info", "informational": "info", "low": "low",
    "medium": "medium", "med": "medium", "warning": "medium", "high": "high",
    "critical": "critical", "crit": "critical", "emergency": "critical",
}


def _norm_severity(v):
    if v is None:
        return None
    return _SEV_MAP.get(str(v).strip().lower(), None)


def _map_flat(raw: dict) -> dict:
    ev = _blank_event()
    lower = {str(k).lower(): v for k, v in raw.items()}
    for target, aliases in _ALIAS.items():
        for a in aliases:
            if a in lower and lower[a] not in (None, "", "-"):
                ev[target] = lower[a]
                break
    sev = _norm_severity(ev.get("severity"))
    ev["severity"] = sev or "info"
    # categorize heuristically
    blob = json.dumps(lower).lower()
    if ev["category"] == "other":
        if any(k in blob for k in ["login", "auth", "logon", "password", "credential"]):
            ev["category"] = "authentication"
        elif any(k in blob for k in ["powershell", "cmd.exe", "process", "exec", ".exe"]):
            ev["category"] = "process"
        elif any(k in blob for k in ["dns", "query", "domain"]):
            ev["category"] = "dns"
        elif ev.get("dest_ip") or ev.get("protocol") or "connection" in blob:
            ev["category"] = "network"
        elif any(k in blob for k in ["file", "hash"]):
            ev["category"] = "file"
    # outcome normalization
    o = str(ev.get("outcome") or "").lower()
    if o in ("fail", "failure", "failed", "denied", "deny", "error", "0"):
        ev["outcome"] = "failure"
    elif o in ("success", "succeeded", "ok", "allow", "allowed", "1"):
        ev["outcome"] = "success"
    for p in ("src_port", "dest_port", "process_id"):
        if ev.get(p) is not None:
            try:
                ev[p] = int(ev[p])
            except (ValueError, TypeError):
                pass
    return ev


def _parse_cef(line: str) -> dict:
    # CEF:Version|Vendor|Product|Version|SignatureID|Name|Severity|Extension
    try:
        after = line.split("CEF:", 1)[1]
        parts = after.split("|")
        header = parts[:7]
        ext = "|".join(parts[7:]) if len(parts) > 7 else ""
        kv = {}
        for m in re.finditer(r"(\w+)=([^=]*?)(?=\s+\w+=|$)", ext):
            kv[m.group(1)] = m.group(2).strip()
        kv["event_type"] = header[5] if len(header) > 5 else None
        kv["severity"] = header[6] if len(header) > 6 else None
        return kv
    except Exception:
        return {"raw": line}


def _parse_syslog(line: str) -> dict:
    kv = {}
    # RFC5424: <pri>version timestamp host app procid msgid ...
    m5 = re.match(r"<(\d+)>(\d) (\S+) (\S+) (\S+) (\S+)", line)
    if m5:
        kv["host"] = m5.group(4)
        kv["process_name"] = m5.group(5)
    else:
        # RFC3164: <pri>Mon dd hh:mm:ss host tag: msg
        m3 = re.match(r"<(\d+)>\w{3}\s+\d+\s[\d:]+\s(\S+)\s(\S+?):?\s", line)
        if m3:
            kv["host"] = m3.group(2)
            kv["process_name"] = m3.group(3)
    for m in re.finditer(r"(\w+)=([\"']?)([^\"'\s]+)\2", line):
        kv[m.group(1)] = m.group(3)
    ips = _IP_RE.findall(line)
    if ips:
        kv.setdefault("src_ip", ips[0])
        if len(ips) > 1:
            kv.setdefault("dest_ip", ips[1])
    if re.search(r"fail|denied|invalid", line, re.I):
        kv["outcome"] = "failure"
    if re.search(r"authentication|login|logon|sshd|sudo", line, re.I):
        kv["category"] = "authentication"
    return kv


def parse_payload(payload, fmt: str):
    """Return list of raw dict records from a payload string/obj for the given format."""
    fmt = (fmt or "json").lower()
    records = []
    if fmt in ("json",):
        data = payload if isinstance(payload, (dict, list)) else json.loads(payload)
        records = data if isinstance(data, list) else [data]
    elif fmt in ("jsonl", "ndjson", "json_lines"):
        for line in str(payload).splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(str(payload)))
        records = [dict(r) for r in reader]
    elif fmt in ("syslog", "syslog3164", "syslog5424", "linux_auth"):
        for line in str(payload).splitlines():
            if line.strip():
                records.append(_parse_syslog(line))
    elif fmt == "cef":
        for line in str(payload).splitlines():
            if _CEF_RE.search(line):
                records.append(_parse_cef(line))
    else:
        # fall back: try json then plaintext-per-line
        try:
            data = json.loads(payload)
            records = data if isinstance(data, list) else [data]
        except Exception:
            records = [{"message": l} for l in str(payload).splitlines() if l.strip()]
    return records


def normalize(raw: dict, org_id: str, source: dict, is_synthetic=False) -> dict:
    ev = _map_flat(raw)
    ts = raw.get("timestamp") or raw.get("@timestamp") or raw.get("time") or now_iso()
    doc = {
        "id": new_id(),
        "org_id": org_id,
        "source_id": source.get("id"),
        "source_name": source.get("name"),
        "timestamp": str(ts),
        "ingested_at": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "raw": raw,
        "rule_matches": [],
        "is_synthetic": is_synthetic,
    }
    doc.update(ev)
    return doc
