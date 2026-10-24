"""Alert evidence should survive malformed external telemetry timestamps."""
import ast
from datetime import datetime, timezone
from pathlib import Path
from dateutil import parser as dtparse

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_alert")


def parse_ts(value):
    parsed = dtparse.parse(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def valid_ts(event):
    try:
        parse_ts(event.get("timestamp"))
        return True
    except (ValueError, TypeError, OverflowError):
        return False


namespace = {
    "_parse_ts": parse_ts,
    "_valid_event_timestamp": valid_ts,
    "new_id": lambda: "alert-1",
    "now_iso": lambda: "2026-10-15T00:00:00+00:00",
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<alert>", "exec"), namespace)
build_alert = namespace["_build_alert"]
RULE = {"id": "rule-1", "name": "Suspicious Event", "severity": "high"}


def test_malformed_timestamp_does_not_discard_valid_evidence():
    events = [
        {"id": "bad", "timestamp": "not-a-date"},
        {"id": "valid", "timestamp": "2026-10-15T12:00:00+00:00"},
    ]
    alert = build_alert(RULE, "org-1", events)
    assert alert["related_events"] == ["bad", "valid"]
    assert alert["event_count"] == 2
    assert alert["first_seen"] == alert["last_seen"] == events[1]["timestamp"]


def test_all_invalid_timestamps_still_produce_alert():
    events = [{"id": "bad-1", "timestamp": "invalid"}, {"id": "bad-2", "timestamp": ""}]
    alert = build_alert(RULE, "org-1", events)
    assert alert["related_events"] == ["bad-1", "bad-2"]
    assert alert["event_count"] == 2
    assert alert["first_seen"] == alert["last_seen"] == "2026-10-15T00:00:00+00:00"


def test_duplicate_event_ids_count_once():
    events = [
        {"id": "same", "timestamp": "2026-10-15T12:00:00+00:00"},
        {"id": "same", "timestamp": "2026-10-15T12:01:00+00:00"},
    ]
    alert = build_alert(RULE, "org-1", events)
    assert alert["related_events"] == ["same"]
    assert alert["event_count"] == 1
