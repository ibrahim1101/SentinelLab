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
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"Invalid event timestamp: {v!r}") from exc


def _valid_event_timestamp(event):
    """Exclude malformed timestamps from temporal correlation."""
    try:
        _parse_ts(event.get("timestamp"))
        return True
    except ValueError:
        return False


def event_matches(conditions, event) -> bool:
    """All conditions (AND). Malformed conditions fail closed."""
    if not isinstance(conditions, (list, tuple)):
        return False
    if not isinstance(event, dict):
        return False
    for c in conditions:
        if not isinstance(c, dict):
            return False
        field, op, value = c.get("field"), c.get("op", "eq"), c.get("value")
        if not isinstance(field, str) or not field:
            return False
        # Reject unhashable operators (e.g. JSON arrays/objects) before
        # dictionary lookup; malformed rules must never crash evaluation.
        if not isinstance(op, str):
            return False
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
    # Match and IOC rules may receive malformed timestamps from external sources.
    # Keep the alert and its evidence rather than dropping the entire rule run.
    dated = [e for e in events if _valid_event_timestamp(e)]
    if dated:
        first = min(dated, key=lambda e: _parse_ts(e["timestamp"]))
        last = max(dated, key=lambda e: _parse_ts(e["timestamp"]))
    else:
        first = last = events[0]
    first_seen = first["timestamp"] if dated else now_iso()
    last_seen = last["timestamp"] if dated else first_seen
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
        "related_events": list(dict.fromkeys(e["id"] for e in events)),
        "event_count": len(dict.fromkeys(e["id"] for e in events)),
        "mitre": rule.get("mitre", []),
        "first_seen": first_seen,
        "last_seen": last_seen,
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
        if not isinstance(group_by, str) or not group_by.strip():
            raise ValueError("Threshold group_by must be a non-empty field name")
        try:
            window = int(params.get("window_minutes", 5))
            threshold = int(params.get("threshold", 5))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Threshold window and count must be integers") from exc
        if not 1 <= window <= 1440 or not 1 <= threshold <= 10000:
            raise ValueError("Threshold window must be 1-1440 minutes and count 1-10000")
        filtered = [e for e in events if event_matches(conds, e) and _valid_event_timestamp(e)]
        groups = {}
        for e in filtered:
            raw_key = e.get(group_by)
            # Normalized telemetry is usually scalar, but malformed or custom
            # fields must not crash grouping when they contain dicts or lists.
            key = raw_key if isinstance(raw_key, (str, int, float, bool)) and raw_key != "" else "unknown"
            groups.setdefault(str(key), []).append(e)
        for key, evs in groups.items():
            evs.sort(key=lambda e: _parse_ts(e["timestamp"]))
            # sliding window
            # Mark qualifying index intervals in O(n) instead of repeatedly
            # adding every event in overlapping windows (quadratic at scale).
            from datetime import timedelta
            parsed_times = [_parse_ts(e["timestamp"]) for e in evs]
            changes = [0] * (len(evs) + 1)
            i = 0
            for j in range(len(evs)):
                while parsed_times[j] - parsed_times[i] > timedelta(minutes=window):
                    i += 1
                if j - i + 1 >= threshold:
                    changes[i] += 1
                    changes[j + 1] -= 1
            active = 0
            flagged = []
            for index, event in enumerate(evs):
                active += changes[index]
                if active:
                    flagged.append(event)
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
            if not isinstance(ind, dict):
                continue
            ioc_type, value = ind.get("ioc_type"), ind.get("value")
            if ioc_type not in ("ip", "domain", "hash") or not isinstance(value, str) or not value.strip():
                continue
            ioc_map.setdefault(ioc_type, {})[value.strip().casefold()] = ind
        fields = {"ip": ["src_ip", "dest_ip"], "domain": ["dns_query"],
                  "hash": ["file_hash"]}
        hits = []
        for e in events:
            # One event can match multiple IOC fields; it is still one event.
            is_match = any(
                isinstance(e.get(field), str) and e[field].strip().casefold() in ioc_map.get(ioc_type, {})
                for ioc_type, ev_fields in fields.items()
                for field in ev_fields
            )
            if is_match:
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
                {"id": rule["id"], "org_id": org_id},
                {"$set": {"last_error": str(ex), "last_run": now_iso()}})
            continue
        if matched and persist:
            await db.events.update_many(
                {"org_id": org_id, "id": {"$in": list(matched)}},
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
                    # Atomic union makes repeated scans idempotent and avoids a
                    # second write racing with other detection workers.
                    await db.alerts.update_one(
                        {"id": existing["id"], "org_id": org_id},
                        [{"$set": {
                            "related_events": {"$setUnion": [
                                {"$ifNull": ["$related_events", []]},
                                a["related_events"]]},
                            "last_seen": a["last_seen"],
                            "updated_at": now_iso(),
                        }},
                         {"$set": {"event_count": {"$size": "$related_events"}}}])
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
