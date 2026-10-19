"""Alert creation must tolerate malformed event severity telemetry."""
import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_alert")
namespace = {"new_id": lambda: "alert-1", "now_iso": lambda: "2026-01-01T00:00:00Z", "_valid_event_timestamp": lambda event: isinstance(event.get("timestamp"), str), "_parse_ts": lambda value: datetime.fromisoformat(value).replace(tzinfo=timezone.utc) if datetime.fromisoformat(value).tzinfo is None else datetime.fromisoformat(value)}
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


@pytest.mark.parametrize("confidence", [None, "", "not-a-number", [], {}, True, False, -1, 101, float("inf"), 99.9, 0.5, -0.5, "9" * 1000, "  ", "1000"])
def test_invalid_rule_confidence_uses_default(confidence):
    rule = {"id": "rule-1", "name": "Test rule", "confidence": confidence}
    events = [{"id": "event-1", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["confidence"] == 75


@pytest.mark.parametrize("confidence", [0, 42, 100])
def test_valid_rule_confidence_preserved(confidence):
    rule = {"id": "rule-1", "name": "Test rule", "confidence": confidence}
    events = [{"id": "event-1", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["confidence"] == confidence


def test_integral_float_confidence_preserved():
    rule = {"id": "rule-1", "name": "Test rule", "confidence": 42.0}
    events = [{"id": "event-1", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["confidence"] == 42


@pytest.mark.parametrize("confidence", ["0", "75", "100"])
def test_valid_string_confidence_preserved(confidence):
    rule = {"id": "rule-1", "name": "Test rule", "confidence": confidence}
    events = [{"id": "event-1", "severity": "low"}]
    assert namespace["_build_alert"](rule, "org-1", events)["confidence"] == int(confidence)


def test_alert_timestamps_are_iso_strings_with_timezones():
    rule = {"id": "rule-1", "name": "Test rule"}
    events = [{"id": "event-1", "timestamp": "2026-01-02T12:00:00"}, {"id": "event-2", "timestamp": "2026-01-02T13:00:00+00:00"}]
    alert = namespace["_build_alert"](rule, "org-1", events)
    assert alert["first_seen"] == "2026-01-02T12:00:00+00:00"
    assert alert["last_seen"] == "2026-01-02T13:00:00+00:00"


def test_alert_evidence_excludes_invalid_ids_and_deduplicates():
    rule = {"id": "rule-1", "name": "Test rule"}
    events = [{"id": "event-1"}, {"id": "event-1"}, {"id": []}, {"id": None}, {"id": ""}, {"id": "event-2"}]
    alert = namespace["_build_alert"](rule, "org-1", events)
    assert alert["related_events"] == ["event-1", "event-2"]
    assert alert["event_count"] == 2
