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
              "related_events": ["event-1"]}], {"event-1"})

namespace = {"db": db, "evaluate_rule": evaluate_rule, "now_iso": lambda: "2026-01-01T00:00:00Z"}
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

    original_alerts = db.alerts
    db.alerts = ExistingAlerts()
    try:
        asyncio.run(namespace["run_detection"]("org-1", [], persist=True))
        assert len(db.alerts.updates) == 1
        pipeline = db.alerts.updates[0][1]
        first_seen = pipeline[0]["$set"]["first_seen"]
        last_seen = pipeline[0]["$set"]["last_seen"]
        assert first_seen["$min"][0]["$ifNull"][0] == "$first_seen"
        assert len(first_seen["$min"]) == 2
        assert last_seen["$max"][0]["$ifNull"][0] == "$last_seen"
        assert len(last_seen["$max"]) == 2
    finally:
        db.alerts = original_alerts
