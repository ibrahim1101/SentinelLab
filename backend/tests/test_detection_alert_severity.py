"""Alert creation must tolerate malformed event severity telemetry."""
import ast
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_alert")
namespace = {"new_id": lambda: "alert-1", "now_iso": lambda: "2026-01-01T00:00:00Z", "_valid_event_timestamp": lambda event: False}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<alert>", "exec"), namespace)


@pytest.mark.parametrize("severity", [[], {}, None, 3, True, "not-a-severity"])
def test_invalid_event_severity_falls_back_to_info(severity):
    rule = {"id": "rule-1", "name": "Test rule"}
    events = [{"id": "event-1", "severity": severity}]
    assert namespace["_build_alert"](rule, "org-1", events)["severity"] == "info"


def test_highest_valid_event_severity_wins():
    rule = {"id": "rule-1", "name": "Test rule"}
    events = [{"id": "event-1", "severity": []}, {"id": "event-2", "severity": "high"}, {"id": "event-3", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["severity"] == "high"


@pytest.mark.parametrize("severity", [[], {}, None, 0, True, "unknown", "HIGH"])
def test_invalid_rule_severity_uses_valid_event_severity(severity):
    rule = {"id": "rule-1", "name": "Test rule", "severity": severity}
    events = [{"id": "event-1", "severity": "medium"}]
    assert namespace["_build_alert"](rule, "org-1", events)["severity"] == "medium"


def test_valid_rule_severity_overrides_event_severity():
    rule = {"id": "rule-1", "name": "Test rule", "severity": "critical"}
    events = [{"id": "event-1", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["severity"] == "critical"
