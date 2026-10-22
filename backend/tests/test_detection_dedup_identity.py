"""Alert deduplication must keep distinct source hosts and IPs separate."""
import ast
import asyncio
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_detection")

class Cursor:
    async def to_list(self, limit):
        return [{"id": "rule-1", "enabled": True}]

class Rules:
    def find(self, *args, **kwargs):
        return Cursor()
    async def update_one(self, *args, **kwargs):
        pass

class Events:
    async def update_many(self, *args, **kwargs):
        pass

class Alerts:
    def __init__(self):
        self.lookups = []
    async def find_one(self, query):
        self.lookups.append(query)
        return None
    async def insert_one(self, document):
        pass

class FakeDb:
    def __init__(self):
        self.detection_rules = Rules()
        self.events = Events()
        self.alerts = Alerts()

db = FakeDb()
async def evaluate_rule(rule, events, org_id):
    return ([{"id": "alert-1", "title": "Same title", "host": "host-a", "src_ip": "192.0.2.1",
              "first_seen": "2026-01-01T01:00:00+00:00",
              "last_seen": "2026-01-01T03:00:00+00:00",
              "related_events": ["event-1"]}], {"event-1"})

from datetime import datetime

def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def valid_timestamp(event):
    try:
        return isinstance(event.get("timestamp"), str) and parse_timestamp(event["timestamp"]).tzinfo is not None
    except (ValueError, TypeError, AttributeError):
        return False

namespace = {"db": db, "evaluate_rule": evaluate_rule, "now_iso": lambda: "2026-01-01T00:00:00Z",
             "_parse_ts": parse_timestamp, "_valid_event_timestamp": valid_timestamp}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<run_detection>", "exec"), namespace)

def test_dedup_lookup_includes_host_and_source_ip():
    asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
    assert len(db.alerts.lookups) == 1
    query = db.alerts.lookups[0]
    assert query["rule_id"] == "rule-1"
    assert query["title"] == "Same title"
    assert query["host"] == "host-a"
    assert query["src_ip"] == "192.0.2.1"


def test_dedup_update_keeps_latest_seen_timestamp():
    class ExistingAlerts(Alerts):
        def __init__(self):
            super().__init__()
            self.updates = []
        async def find_one(self, query):
            return {"id": "existing-alert"}
        async def update_one(self, query, pipeline):
            self.updates.append((query, pipeline))
            return type("UpdateResult", (), {"matched_count": 1})()

    original_alerts = db.alerts
    db.alerts = ExistingAlerts()
    try:
        asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert len(db.alerts.updates) == 1
        update_filter, pipeline = db.alerts.updates[0]
        assert update_filter["id"] == "existing-alert"
        assert update_filter["rule_id"] == "rule-1"
        assert update_filter["title"] == "Same title"
        assert update_filter["host"] == "host-a"
        assert update_filter["src_ip"] == "192.0.2.1"
        assert update_filter["status"] == {"$in": ["new", "triaged", "investigating"]}
        first_seen = pipeline[0]["$set"]["first_seen"]
        last_seen = pipeline[0]["$set"]["last_seen"]
        assert first_seen["$min"][0]["$ifNull"][0] == "$first_seen"
        assert first_seen["$min"][0]["$ifNull"][1] == "2026-01-01T01:00:00+00:00"
        assert first_seen["$min"][1] == "2026-01-01T01:00:00+00:00"
        assert last_seen["$max"][0]["$ifNull"][0] == "$last_seen"
        assert last_seen["$max"][0]["$ifNull"][1] == "2026-01-01T03:00:00+00:00"
        assert last_seen["$max"][1] == "2026-01-01T03:00:00+00:00"
        assert pipeline[1]["$set"]["event_count"] == {"$size": "$related_events"}
    finally:
        db.alerts = original_alerts


def test_invalid_rule_ids_are_skipped_without_stopping_valid_rules():
    class MixedRules(Rules):
        def find(self, *args, **kwargs):
            class MixedCursor:
                async def to_list(self, limit):
                    return [None, {}, {"id": " "}, {"id": 42},
                            {"id": "x" * 129}, {"id": "rule-1"}]
            return MixedCursor()

    original_rules = db.detection_rules
    original_alerts = db.alerts
    db.detection_rules = MixedRules()
    db.alerts = Alerts()
    try:
        created = asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert len(created) == 1
        assert len(db.alerts.lookups) == 1
        assert db.alerts.lookups[0]["rule_id"] == "rule-1"
    finally:
        db.detection_rules = original_rules
        db.alerts = original_alerts


def test_rule_failure_does_not_persist_sensitive_exception_text():
    class RecordingRules(Rules):
        def __init__(self):
            self.updates = []
        async def update_one(self, query, update):
            self.updates.append(update)

    async def failing_rule(rule, events, org_id):
        raise ValueError("secret-token-" + "x" * 10000)

    original_rules = db.detection_rules
    original_evaluator = namespace["evaluate_rule"]
    db.detection_rules = RecordingRules()
    namespace["evaluate_rule"] = failing_rule
    try:
        assert asyncio.run(namespace["run_detection"]("org-1", [], persist=True)) == []
        error = db.detection_rules.updates[0]["$set"]["last_error"]
        assert error == "ValueError: detection evaluation failed"
        assert "secret-token" not in error
    finally:
        db.detection_rules = original_rules
        namespace["evaluate_rule"] = original_evaluator


def test_malformed_alerts_are_skipped_and_valid_alerts_continue():
    async def mixed_alerts(rule, events, org_id):
        return ([None, {}, {"title": "incomplete"},
                 {"title": "No ID", "host": None, "src_ip": None, "related_events": [], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": " ", "title": "Blank ID", "host": None, "src_ip": None, "related_events": [], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": "a" * 129, "title": "Long ID", "host": None, "src_ip": None, "related_events": [], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": "alert-missing-host", "title": "Missing host", "src_ip": None, "related_events": [], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": "bad-related", "title": "Bad related events", "host": None, "src_ip": None, "related_events": [" ", 42], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": "oversized-related", "title": "Oversized related events", "host": None, "src_ip": None, "related_events": ["x" * 129], "first_seen": "2026-01-01", "last_seen": "2026-01-01"},
                 {"id": "bad-time", "title": "Invalid time", "host": None, "src_ip": None, "related_events": [], "first_seen": "not-a-date", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "reversed-time", "title": "Reversed time", "host": None, "src_ip": None, "related_events": [], "first_seen": "2026-01-02T03:00:00+00:00", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "dict-host", "title": "Dict host", "host": {"bad": 1}, "src_ip": None, "related_events": [], "first_seen": "2026-01-01T01:00:00+00:00", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "list-ip", "title": "List IP", "host": None, "src_ip": ["bad"], "related_events": [], "first_seen": "2026-01-01T01:00:00+00:00", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "long-host", "title": "Long host", "host": "x" * 257, "src_ip": None, "related_events": [], "first_seen": "2026-01-01T01:00:00+00:00", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "blank-ip", "title": "Blank IP", "host": None, "src_ip": " ", "related_events": [], "first_seen": "2026-01-01T01:00:00+00:00", "last_seen": "2026-01-01T03:00:00+00:00"},
                 {"id": "alert-ok", "title": "Valid alert", "host": "host-a",
                  "src_ip": "192.0.2.1", "related_events": ["event-1"],
                  "first_seen": "2026-01-01T01:00:00+00:00",
                  "last_seen": "2026-01-01T03:00:00+00:00"}], {"event-1"})

    original_evaluator = namespace["evaluate_rule"]
    original_alerts = db.alerts
    namespace["evaluate_rule"] = mixed_alerts
    db.alerts = Alerts()
    try:
        created = asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert len(created) == 1
        assert created[0]["id"] == "alert-ok"
        assert len(db.alerts.lookups) == 1
    finally:
        namespace["evaluate_rule"] = original_evaluator
        db.alerts = original_alerts


def test_closed_alert_race_creates_fresh_alert():
    class ClosedAlerts(Alerts):
        def __init__(self):
            super().__init__()
            self.inserted = []
        async def find_one(self, query):
            return {"id": "previously-open"}
        async def update_one(self, query, pipeline):
            return type("UpdateResult", (), {"matched_count": 0})()
        async def insert_one(self, document):
            self.inserted.append(document)

    original_alerts = db.alerts
    db.alerts = ClosedAlerts()
    try:
        created = asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert len(created) == 1
        assert created[0]["id"] == "alert-1"
        assert len(db.alerts.inserted) == 1
        assert db.alerts.inserted[0]["id"] == "alert-1"
    finally:
        db.alerts = original_alerts


def test_changed_alert_identity_creates_fresh_alert():
    class ChangedIdentityAlerts(Alerts):
        def __init__(self):
            super().__init__()
            self.inserted = []
            self.update_filter = None
        async def find_one(self, query):
            return {"id": "old-alert", "rule_id": "rule-1",
                    "title": "Same title", "host": "host-a", "src_ip": "192.0.2.1"}
        async def update_one(self, query, pipeline):
            self.update_filter = query
            # Simulate a concurrent identity change: the guarded update matches nothing.
            return type("UpdateResult", (), {"matched_count": 0})()
        async def insert_one(self, document):
            self.inserted.append(document)

    original_alerts = db.alerts
    db.alerts = ChangedIdentityAlerts()
    try:
        created = asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert db.alerts.update_filter["host"] == "host-a"
        assert db.alerts.update_filter["src_ip"] == "192.0.2.1"
        assert db.alerts.update_filter["title"] == "Same title"
        assert len(created) == 1
        assert len(db.alerts.inserted) == 1
        assert db.alerts.inserted[0]["id"] == created[0]["id"]
    finally:
        db.alerts = original_alerts


def test_malformed_existing_alert_id_does_not_drop_detection():
    for existing in ({}, {"id": None}, {"id": " "}, {"id": "x" * 129}):
        class MalformedExistingAlerts(Alerts):
            def __init__(self):
                super().__init__()
                self.inserted = []
            async def find_one(self, query):
                return existing
            async def update_one(self, query, pipeline):
                raise AssertionError("Malformed existing alert must not be updated")
            async def insert_one(self, document):
                self.inserted.append(document)

        original_alerts = db.alerts
        db.alerts = MalformedExistingAlerts()
        try:
            created = asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
            assert len(created) == 1
            assert created[0]["id"] == "alert-1"
            assert len(db.alerts.inserted) == 1
        finally:
            db.alerts = original_alerts
