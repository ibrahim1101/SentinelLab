"""Detection engine. Genuinely evaluates stored/normalized events against rules
and produces alerts. Supports match, threshold, frequency, indicator rule types.
No arbitrary code execution: rules are declarative condition sets only."""
from datetime import datetime, timezone
import re
from dateutil import parser as dtparse
from core import db, new_id, now_iso

OPS = {
    "eq": lambda a, b: str(a).lower() == str(b).lower(),
    "ne": lambda a, b: str(a).lower() != str(b).lower(),
    "contains": lambda a, b: b.lower() in str(a).lower(),
    "startswith": lambda a, b: str(a).lower().startswith(str(b).lower()),
    "gt": lambda a, b: _num(a) > _num(b),
    "lt": lambda a, b: _num(a) < _num(b),
    "exists": lambda a, b: a is not None and a != "",
    "regex": lambda a, b: safe_regex_search(a, b),
}


def safe_regex_search(value, pattern):
    """Reject dangerous regex constructs and oversized input; fail closed."""
    if not isinstance(pattern, str) or len(pattern) > 128 or len(str(value)) > 4096:
        return False
    # No groups, lookarounds, backreferences or unbounded quantifiers in analyst patterns.
    if re.search(r"[(){}]|\\[1-9]|(?<!\\)[*+]", pattern):
        return False
    try:
        return re.search(pattern, str(value), re.I) is not None
    except re.error:
        return False


def _num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return float("nan")


def _parse_ts(v):
    try:
        d = dtparse.parse(str(v))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return datetime.now(timezone.utc)


def event_matches(conditions, event) -> bool:
    """All conditions (AND). Each: {field, op, value}."""
    for c in conditions or []:
        field, op, value = c.get("field"), c.get("op", "eq"), c.get("value")
        fn = OPS.get(op)
        if not fn:
            return False
        ev_val = event.get(field)
        if op == "exists":
            if ev_val in (None, ""):
                return False
            continue
        if ev_val is None:
            return False
        try:
            if not fn(ev_val, value):
                return False
        except Exception:
            return False
    return True


def _build_alert(rule, org_id, events, title=None):
    sevs = ["info", "low", "medium", "high", "critical"]
    ev_sev = max((e.get("severity", "info") for e in events),
                 key=lambda s: sevs.index(s) if s in sevs else 0)
    first = min(events, key=lambda e: _parse_ts(e["timestamp"]))
    last = max(events, key=lambda e: _parse_ts(e["timestamp"]))
    return {
        "id": new_id(),
        "org_id": org_id,
        "rule_id": rule["id"],
        "rule_name": rule["name"],
        "title": title or rule["name"],
        "description": rule.get("description", ""),
        "severity": rule.get("severity") or ev_sev,
        "confidence": rule.get("confidence", 75),
        "source": first.get("source_name"),
        "host": first.get("host"),
        "src_ip": first.get("src_ip"),
        "username": first.get("username"),
        "related_events": [e["id"] for e in events][:200],
        "event_count": len(events),
        "mitre": rule.get("mitre", []),
        "first_seen": first["timestamp"],
        "last_seen": last["timestamp"],
        "assigned_to": None,
        "status": "new",
        "investigation_id": None,
        "comments": [],
        "tags": [],
        "audit": [{"ts": now_iso(), "action": "created", "by": "detection-engine"}],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "is_synthetic": first.get("is_synthetic", False),
    }


async def evaluate_rule(rule, events, org_id):
    """Evaluate a single rule against a list of events -> list of alert docs + matched event ids."""
    alerts = []
    matched_ids = set()
    rtype = rule.get("rule_type", "match")
    params = rule.get("params", {})

    if rtype == "match":
        hits = [e for e in events if event_matches(params.get("conditions", []), e)]
        for e in hits:
            matched_ids.add(e["id"])
        if hits:
            # group hits into a single alert per rule run (dedup noise)
            alerts.append(_build_alert(rule, org_id, hits))

    elif rtype in ("threshold", "frequency"):
        conds = params.get("conditions", [])
        group_by = params.get("group_by", "src_ip")
        window = int(params.get("window_minutes", 5))
        threshold = int(params.get("threshold", 5))
        filtered = [e for e in events if event_matches(conds, e)]
        groups = {}
        for e in filtered:
            key = e.get(group_by) or "unknown"
            groups.setdefault(key, []).append(e)
        for key, evs in groups.items():
            evs.sort(key=lambda e: _parse_ts(e["timestamp"]))
            # sliding window
            i = 0
            flagged = []
            for j in range(len(evs)):
                while _parse_ts(evs[j]["timestamp"]) - _parse_ts(evs[i]["timestamp"]) > \
                        __import__("datetime").timedelta(minutes=window):
                    i += 1
                if j - i + 1 >= threshold:
                    flagged = evs[i:j + 1]
            if flagged:
                for e in flagged:
                    matched_ids.add(e["id"])
                title = f"{rule['name']} — {group_by}={key} ({len(flagged)} events)"
                alerts.append(_build_alert(rule, org_id, flagged, title))

    elif rtype == "indicator":
        indicators = await db.indicators.find(
            {"org_id": org_id, "active": True}, {"_id": 0}).to_list(2000)
        ioc_map = {}
        for ind in indicators:
            ioc_map.setdefault(ind["ioc_type"], {})[str(ind["value"]).lower()] = ind
        fields = {"ip": ["src_ip", "dest_ip"], "domain": ["dns_query"],
                  "hash": ["file_hash"]}
        hits = []
        for e in events:
            for ioc_type, ev_fields in fields.items():
                for f in ev_fields:
                    val = e.get(f)
                    if val and str(val).lower() in ioc_map.get(ioc_type, {}):
                        hits.append(e)
                        matched_ids.add(e["id"])
        if hits:
            alerts.append(_build_alert(rule, org_id, hits,
                                       title=f"{rule['name']} — IOC match ({len(hits)})"))
    return alerts, matched_ids


async def run_detection(org_id, events, persist=True):
    """Run all enabled rules for org against the given events. Returns created alerts."""
    rules = await db.detection_rules.find(
        {"org_id": org_id, "enabled": True}, {"_id": 0}).to_list(500)
    created = []
    for rule in rules:
        try:
            alerts, matched = await evaluate_rule(rule, events, org_id)
        except Exception as ex:
            if not persist:
                continue
            await db.detection_rules.update_one(
                {"id": rule["id"]},
                {"$set": {"last_error": str(ex), "last_run": now_iso()}})
            continue
        if matched and persist:
            await db.events.update_many(
                {"id": {"$in": list(matched)}},
                {"$addToSet": {"rule_matches": rule["id"]}})
        new_alerts = []
        for a in alerts:
            if persist:
                # dedup: same rule + host + src_ip + title within open alerts
                existing = await db.alerts.find_one({
                    "org_id": org_id, "rule_id": rule["id"], "title": a["title"],
                    "status": {"$in": ["new", "triaged", "investigating"]},
                })
                if existing:
                    await db.alerts.update_one(
                        {"id": existing["id"]},
                        {"$set": {"last_seen": a["last_seen"], "updated_at": now_iso()},
                         "$inc": {"event_count": a["event_count"]}})
                    continue
                await db.alerts.insert_one(dict(a))
            new_alerts.append(a)
            created.append(a)
        if persist:
            await db.detection_rules.update_one(
                {"id": rule["id"], "org_id": org_id},
                {"$set": {"last_run": now_iso(), "last_error": None},
                 "$inc": {"match_count": len(new_alerts)}})
    return created
