"""Behavioral tests for detection evaluation without a running MongoDB."""
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "sentinellab_ci")
os.environ.setdefault("JWT_SECRET", "ci-only-test-secret")

from detection import event_matches, safe_regex_search, run_detection
import detection


def test_safe_regex_matching_behavior():
    assert safe_regex_search("admin-login", "^admin") is True
    assert safe_regex_search("admin-login", "(a+)+$") is False
    assert safe_regex_search("admin-login", "a+") is False
    assert safe_regex_search("admin-login", "[") is False
    assert safe_regex_search("x" * 5000, "x") is False
    assert safe_regex_search("admin", "^admin$") is True


def test_detection_condition_behavior():
    assert event_matches([{"field": "host", "op": "eq", "value": "SERVER01"}], {"host": "server01"})
    assert not event_matches([{"field": "host", "op": "regex", "value": "(a+)+"}], {"host": "aaaa"})
    assert not event_matches([{"field": "missing", "op": "exists", "value": True}], {"host": "server01"})


@pytest.mark.asyncio
async def test_replay_does_not_write(monkeypatch):
    rule = {"id": "rule-1", "org_id": "org-1", "name": "Test", "enabled": True,
            "rule_type": "match", "params": {"conditions": [
                {"field": "host", "op": "eq", "value": "server01"}]}}
    event = {"id": "evt-1", "org_id": "org-1", "host": "server01",
             "timestamp": "2026-10-09T12:00:00+00:00", "severity": "high"}
    class Cursor:
        async def to_list(self, length):
            return [rule]
    class Rules:
        def find(self, *args, **kwargs):
            return Cursor()
        update_one = AsyncMock(side_effect=AssertionError("Replay wrote rule"))
    class Events:
        update_many = AsyncMock(side_effect=AssertionError("Replay wrote event"))
    class Alerts:
        find_one = AsyncMock(side_effect=AssertionError("Replay queried alert"))
        update_one = AsyncMock(side_effect=AssertionError("Replay updated alert"))
        insert_one = AsyncMock(side_effect=AssertionError("Replay inserted alert"))
    class DB:
        detection_rules = Rules()
        events = Events()
        alerts = Alerts()
    monkeypatch.setattr(detection, "db", DB())
    results = await run_detection("org-1", [event], persist=False)
    assert len(results) == 1
    assert results[0]["rule_id"] == "rule-1"
    DB.events.update_many.assert_not_awaited()
    DB.detection_rules.update_one.assert_not_awaited()
    DB.alerts.insert_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_alert_merges_evidence_without_count_inflation(monkeypatch):
    from types import SimpleNamespace

    rule = {"id": "rule-1", "org_id": "org-1", "name": "Authentication failure",
            "enabled": True, "rule_type": "match",
            "params": {"conditions": [{"field": "outcome", "op": "eq", "value": "failure"}]}}
    existing = {"id": "alert-1", "org_id": "org-1", "related_events": ["evt-1"],
                "event_count": 1}
    class Cursor:
        async def to_list(self, length):
            return [rule]
    class Rules:
        def find(self, *args, **kwargs):
            return Cursor()
        update_one = AsyncMock()
    class Alerts:
        find_one = AsyncMock(return_value=existing)
        insert_one = AsyncMock()
        update_one = AsyncMock()
    class Events:
        update_many = AsyncMock()
    fake = SimpleNamespace(detection_rules=Rules(), alerts=Alerts(), events=Events())
    monkeypatch.setattr(detection, "db", fake)
    events = [{"id": event_id, "org_id": "org-1", "outcome": "failure",
               "timestamp": "2026-10-09T12:00:00+00:00", "severity": "medium"}
              for event_id in ("evt-1", "evt-2")]
    assert await run_detection("org-1", events, persist=True) == []
    assert fake.alerts.update_one.await_count == 1
    call = fake.alerts.update_one.await_args
    assert call.args[0] == {"id": "alert-1", "org_id": "org-1",
                            "status": {"$in": ["new", "triaged", "investigating"]}}
    pipeline = call.args[1]
    assert pipeline[0]["$set"]["related_events"] == {
        "$setUnion": [{"$ifNull": ["$related_events", []]}, ["evt-1", "evt-2"]]}
    assert pipeline[1]["$set"]["event_count"] == {"$size": "$related_events"}
    fake.alerts.insert_one.assert_not_awaited()


def test_alert_preserves_more_than_200_evidence_references():
    events = [{"id": f"evt-{i}", "timestamp": "2026-10-09T12:00:00Z",
               "severity": "low"} for i in range(250)]
    alert = detection._build_alert({"id": "rule-1", "name": "Test"}, "org-1", events)
    assert len(alert["related_events"]) == 250
    assert alert["event_count"] == 250


@pytest.mark.asyncio
async def test_indicator_multi_field_match_counts_event_once(monkeypatch):
    from types import SimpleNamespace

    class Cursor:
        async def to_list(self, length):
            return [
                {"ioc_type": "ip", "value": "192.0.2.10", "active": True},
                {"ioc_type": "domain", "value": "malicious.example", "active": True},
            ]

    class Indicators:
        def find(self, *args, **kwargs):
            assert args[0]["org_id"] == "org-1"
            return Cursor()

    monkeypatch.setattr(detection, "db", SimpleNamespace(indicators=Indicators()))
    rule = {"id": "rule-ioc", "name": "IOC test", "rule_type": "indicator"}
    event = {"id": "event-1", "timestamp": "2026-10-09T12:00:00Z",
             "src_ip": "192.0.2.10", "dest_ip": "192.0.2.10",
             "dns_query": "malicious.example", "severity": "high"}
    alerts, matched = await detection.evaluate_rule(rule, [event], "org-1")
    assert matched == {"event-1"}
    assert len(alerts) == 1
    assert alerts[0]["event_count"] == 1
    assert alerts[0]["related_events"] == ["event-1"]


def test_invalid_timestamp_does_not_become_current_time():
    with pytest.raises(ValueError, match="Invalid event timestamp"):
        detection._parse_ts("not-a-timestamp")
    assert not detection._valid_event_timestamp({"timestamp": "not-a-timestamp"})
    assert not detection._valid_event_timestamp({})
    assert detection._valid_event_timestamp({"timestamp": "2026-10-09T12:00:00Z"})


@pytest.mark.asyncio
async def test_threshold_excludes_malformed_event_timestamps():
    rule = {"id": "threshold-1", "name": "Burst", "rule_type": "threshold",
            "params": {"conditions": [], "group_by": "src_ip",
                       "window_minutes": 5, "threshold": 2}}
    events = [
        {"id": "good-1", "src_ip": "192.0.2.1",
         "timestamp": "2026-10-09T12:00:00Z", "severity": "low"},
        {"id": "bad-1", "src_ip": "192.0.2.1",
         "timestamp": "garbled", "severity": "low"},
    ]
    alerts, matched = await detection.evaluate_rule(rule, events, "org-1")
    assert alerts == []
    assert matched == set()
