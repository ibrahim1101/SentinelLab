"""Threshold grouping must tolerate non-scalar telemetry values."""
import ast
import asyncio

import pytest
from pathlib import Path
from datetime import datetime, timezone

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")
namespace = {
    "event_matches": lambda conditions, event: True,
    "_valid_event_timestamp": lambda event: True,
    "_parse_ts": lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc),
    "_build_alert": lambda rule, org, events, title=None: {"title": title, "related_events": [e["id"] for e in events]},
    "db": None,
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<grouping>", "exec"), namespace)
evaluate_rule = namespace["evaluate_rule"]


def test_non_scalar_group_values_do_not_crash_threshold_detection():
    events = [
        {"id": "a", "timestamp": "2026-10-15T00:00:00+00:00", "src_ip": {"unexpected": "dict"}},
        {"id": "b", "timestamp": "2026-10-15T00:01:00+00:00", "src_ip": ["unexpected", "list"]},
    ]
    rule = {"id": "r1", "name": "Grouped", "rule_type": "threshold",
            "params": {"group_by": "src_ip", "window_minutes": 5, "threshold": 2}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert matched == {"a", "b"}
    assert len(alerts) == 1
    assert "src_ip=unknown" in alerts[0]["title"]


def test_valid_scalar_group_values_remain_distinct():
    events = [
        {"id": "a", "timestamp": "2026-10-15T00:00:00+00:00", "src_ip": "192.0.2.1"},
        {"id": "b", "timestamp": "2026-10-15T00:01:00+00:00", "src_ip": "192.0.2.2"},
    ]
    rule = {"id": "r1", "name": "Grouped", "rule_type": "frequency",
            "params": {"group_by": "src_ip", "window_minutes": 5, "threshold": 2}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert alerts == []
    assert matched == set()


@pytest.mark.parametrize("group_by", [None, "", "  ", [], {}, 42, True, "x" * 129])
def test_malformed_group_field_rejected(group_by):
    rule = {"id": "r1", "name": "Grouped", "rule_type": "threshold",
            "params": {"group_by": group_by, "window_minutes": 5, "threshold": 2}}
    with pytest.raises(ValueError, match="group_by"):
        asyncio.run(evaluate_rule(rule, [], "org-1"))


@pytest.mark.parametrize("bad_id", [None, "", 42, [], {}])
def test_threshold_skips_malformed_event_identifiers(bad_id):
    events = [
        {"id": bad_id, "timestamp": "2026-10-15T00:00:00+00:00", "src_ip": "192.0.2.1"},
        {"id": "valid-1", "timestamp": "2026-10-15T00:01:00+00:00", "src_ip": "192.0.2.1"},
        {"id": "valid-2", "timestamp": "2026-10-15T00:02:00+00:00", "src_ip": "192.0.2.1"},
    ]
    rule = {"id": "r1", "name": "Grouped", "rule_type": "threshold",
            "params": {"group_by": "src_ip", "window_minutes": 5, "threshold": 2}}
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert matched == {"valid-1", "valid-2"}
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == ["valid-1", "valid-2"]
