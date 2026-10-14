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
    assert fake.alerts.update_one.await_count == 2
    first = fake.alerts.update_one.await_args_list[0]
    assert first.args[0] == {"id": "alert-1", "org_id": "org-1"}
    assert first.args[1]["$addToSet"]["related_events"]["$each"] == ["evt-1", "evt-2"]
    second = fake.alerts.update_one.await_args_list[1]
    assert second.args[1][0]["$set"]["event_count"] == {
        "$size": {"$ifNull": ["$related_events", []]}}
    fake.alerts.insert_one.assert_not_awaited()
