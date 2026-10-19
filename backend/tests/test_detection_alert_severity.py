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


@pytest.mark.parametrize("mitre", [None, {}, "T1059", 42, True])
def test_malformed_mitre_metadata_falls_back_to_empty_list(mitre):
    rule = {"id": "rule-1", "name": "Test rule", "mitre": mitre}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1"}])
    assert alert["mitre"] == []


def test_mitre_metadata_filters_invalid_and_duplicate_techniques():
    rule = {"id": "rule-1", "name": "Test rule", "mitre": ["T1059", None, [], " ", "T1059", "T1078"]}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1"}])
    assert alert["mitre"] == ["T1059", "T1078"]


@pytest.mark.parametrize("description", [None, [], {}, 42, True])
def test_malformed_rule_description_falls_back_to_empty_text(description):
    rule = {"id": "rule-1", "name": "Test rule", "description": description}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1"}])
    assert alert["description"] == ""


def test_valid_rule_description_preserved():
    rule = {"id": "rule-1", "name": "Test rule", "description": "Multiple failed logins"}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1"}])
    assert alert["description"] == "Multiple failed logins"


@pytest.mark.parametrize("synthetic", [None, 0, 1, "false", "true", [], {}])
def test_malformed_synthetic_event_flag_defaults_to_false(synthetic):
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1", "is_synthetic": synthetic}])
    assert alert["is_synthetic"] is False


@pytest.mark.parametrize("synthetic", [True, False])
def test_boolean_synthetic_event_flag_is_preserved(synthetic):
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1", "is_synthetic": synthetic}])
    assert alert["is_synthetic"] is synthetic


@pytest.mark.parametrize("field,alert_field", [("source_name", "source"), ("host", "host"), ("src_ip", "src_ip"), ("username", "username")])
@pytest.mark.parametrize("bad_value", [None, [], {}, 123, True, "  "])
def test_alert_source_metadata_rejects_invalid_values(field, alert_field, bad_value):
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1", field: bad_value}])
    assert alert[alert_field] is None


@pytest.mark.parametrize("field,alert_field", [("source_name", "source"), ("host", "host"), ("src_ip", "src_ip"), ("username", "username")])
def test_alert_source_metadata_preserves_valid_text(field, alert_field):
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [{"id": "event-1", field: "workstation-01"}])
    assert alert[alert_field] == "workstation-01"


@pytest.mark.parametrize("bad_name", [None, [], {}, 123, True, "  "])
def test_alert_uses_fallback_for_malformed_rule_name(bad_name):
    alert = namespace["_build_alert"]({"id": "rule-1", "name": bad_name}, "org-1", [{"id": "event-1"}])
    assert alert["rule_name"] == "Unnamed detection rule"
    assert alert["title"] == "Unnamed detection rule"


@pytest.mark.parametrize("bad_title", [None, [], {}, 123, True, "  "])
def test_alert_uses_rule_name_for_malformed_title(bad_title):
    alert = namespace["_build_alert"]({"id": "rule-1", "name": "Login anomalies"}, "org-1", [{"id": "event-1"}], title=bad_title)
    assert alert["title"] == "Login anomalies"


def test_valid_alert_title_override_is_preserved():
    alert = namespace["_build_alert"]({"id": "rule-1", "name": "Login anomalies"}, "org-1", [{"id": "event-1"}], title="Multiple failed logins")
    assert alert["rule_name"] == "Login anomalies"
    assert alert["title"] == "Multiple failed logins"


@pytest.mark.parametrize("malformed", [None, [], "bad-event", 42])
def test_alert_skips_malformed_event_entries(malformed):
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [malformed, {"id": "event-1", "severity": "high"}])
    assert alert["severity"] == "high"
    assert alert["related_events"] == ["event-1"]
    assert alert["event_count"] == 1


def test_alert_handles_no_valid_event_objects():
    rule = {"id": "rule-1", "name": "Test rule"}
    alert = namespace["_build_alert"](rule, "org-1", [None, [], 42])
    assert alert["severity"] == "info"
    assert alert["related_events"] == []
    assert alert["event_count"] == 0
    assert alert["first_seen"] == alert["last_seen"]


def test_alert_evidence_ignores_whitespace_only_ids():
    rule = {"id": "rule-1", "name": "Test rule"}
    events = [{"id": "  "}, {"id": "\t"}, {"id": "event-1"}, {"id": "event-1"}]
    alert = namespace["_build_alert"](rule, "org-1", events)
    assert alert["related_events"] == ["event-1"]
    assert alert["event_count"] == 1
