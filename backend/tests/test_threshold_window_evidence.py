"""Threshold detection must preserve evidence from all qualifying windows."""
import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dateutil import parser as dtparse

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")


def parse_ts(value):
    result = dtparse.parse(value)
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def build_alert(rule, org, events, title=None):
    return {"related_events": [e["id"] for e in events], "title": title or rule["name"]}


namespace = {
    "db": None,
    "event_matches": lambda conditions, event: True,
    "_valid_event_timestamp": lambda event: True,
    "_parse_ts": parse_ts,
    "_build_alert": build_alert,
}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "<detection>", "exec"), namespace)
evaluate_rule = namespace["evaluate_rule"]


def test_disjoint_threshold_windows_keep_all_matched_evidence():
    start = datetime(2026, 10, 15, tzinfo=timezone.utc)
    events = [
        {"id": str(i), "src_ip": "192.0.2.1",
         "timestamp": (start + timedelta(minutes=offset)).isoformat()}
        for i, offset in enumerate((0, 1, 2, 60, 61, 62))
    ]
    rule = {"id": "threshold-1", "name": "Burst", "rule_type": "threshold",
            "params": {"conditions": [], "group_by": "src_ip",
                       "window_minutes": 5, "threshold": 3}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert matched == {str(i) for i in range(6)}
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == [str(i) for i in range(6)]


def test_nonqualifying_events_do_not_enter_evidence():
    start = datetime(2026, 10, 15, tzinfo=timezone.utc)
    events = [
        {"id": str(i), "src_ip": "192.0.2.1",
         "timestamp": (start + timedelta(minutes=offset)).isoformat()}
        for i, offset in enumerate((0, 1, 2, 60, 61))
    ]
    rule = {"id": "threshold-1", "name": "Burst", "rule_type": "frequency",
            "params": {"window_minutes": 5, "threshold": 3}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert matched == {"0", "1", "2"}
    assert alerts[0]["related_events"] == ["0", "1", "2"]


def test_overlapping_threshold_windows_do_not_duplicate_evidence():
    start = datetime(2026, 10, 15, tzinfo=timezone.utc)
    events = [
        {"id": str(i), "src_ip": "192.0.2.1",
         "timestamp": (start + timedelta(seconds=i)).isoformat()}
        for i in range(2000)
    ]
    rule = {"id": "threshold-1", "name": "Burst", "rule_type": "threshold",
            "params": {"group_by": "src_ip", "window_minutes": 5, "threshold": 3}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert len(matched) == 2000
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == [str(i) for i in range(2000)]
