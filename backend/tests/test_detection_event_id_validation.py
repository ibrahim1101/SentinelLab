"""Malformed event IDs must never enter detection matches or alert evidence."""
import ast
import asyncio
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")
namespace = {
    "event_matches": lambda conditions, event: True,
    "_build_alert": lambda rule, org_id, events, title=None: {
        "related_events": [event["id"] for event in events],
    },
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<evaluate_rule>", "exec"), namespace)


@pytest.mark.parametrize("rule_type", ["match", "threshold"])
def test_detection_rejects_invalid_event_ids(rule_type):
    events = [
        {"id": " "}, {"id": "\t"}, {"id": "x" * 129},
        {"id": "valid-id"}, {"id": "y" * 128},
    ]
    if rule_type == "threshold":
        for event in events:
            event["timestamp"] = "2026-01-01T00:00:00Z"
        from datetime import datetime
        namespace["_valid_event_timestamp"] = lambda event: True
        namespace["_parse_ts"] = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    rule = {"id": "rule-1", "name": "Test rule", "rule_type": rule_type,
            "params": {"conditions": [{"field": "id", "op": "exists"}], "threshold": 1}}
    alerts, matched = asyncio.run(namespace["evaluate_rule"](rule, events, "org-1"))
    assert matched == {"valid-id", "y" * 128}
    assert alerts
    assert set(alerts[0]["related_events"]) == matched


@pytest.mark.parametrize("group_value", [" ", "x" * 257, float("nan"), float("inf")])
def test_threshold_normalizes_invalid_group_keys(group_value):
    from datetime import datetime
    namespace["_valid_event_timestamp"] = lambda event: True
    namespace["_parse_ts"] = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    rule = {"id": "rule-1", "name": "Test rule", "rule_type": "threshold",
            "params": {"conditions": [{"field": "id", "op": "exists"}], "threshold": 1}}
    events = [{"id": "valid-id", "src_ip": group_value, "timestamp": "2026-01-01T00:00:00Z"}]
    alerts, matched = asyncio.run(namespace["evaluate_rule"](rule, events, "org-1"))
    assert matched == {"valid-id"}
    assert len(alerts) == 1
