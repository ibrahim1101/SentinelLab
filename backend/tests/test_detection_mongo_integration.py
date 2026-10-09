"""MongoDB-backed detection integration checks; uses an isolated CI database."""
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "sentinellab_phase1_ci")
os.environ.setdefault("JWT_SECRET", "ci-only-test-secret")

import detection
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.mark.asyncio
async def test_detection_persistence_and_replay_isolation(monkeypatch):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    db = client[os.environ["DB_NAME"]]
    org_a, org_b = "phase1-a", "phase1-b"
    try:
        await client.admin.command("ping")
        for name in ("events", "alerts", "detection_rules"):
            await db[name].delete_many({"org_id": {"$in": [org_a, org_b]}})
        rule = {"id": "phase1-rule", "org_id": org_a, "name": "Phase1 rule",
                "enabled": True, "rule_type": "match", "params": {"conditions": [
                    {"field": "host", "op": "eq", "value": "target"}]}}
        event = {"id": "phase1-event", "org_id": org_a, "host": "target",
                 "timestamp": "2026-10-09T12:00:00+00:00", "severity": "high"}
        other = dict(event, org_id=org_b)
        await db.detection_rules.insert_one(rule)
        await db.events.insert_many([event, other])
        monkeypatch.setattr(detection, "db", db)
        replay = await detection.run_detection(org_a, [event], persist=False)
        assert len(replay) == 1
        assert await db.alerts.count_documents({"org_id": org_a}) == 0
        assert "rule_matches" not in await db.events.find_one({"org_id": org_a})
        assert "last_run" not in await db.detection_rules.find_one({"org_id": org_a})
        live = await detection.run_detection(org_a, [event], persist=True)
        assert len(live) == 1
        assert await db.alerts.count_documents({"org_id": org_a}) == 1
        assert "phase1-rule" in (await db.events.find_one({"org_id": org_a}))["rule_matches"]
        assert "rule_matches" not in await db.events.find_one({"org_id": org_b})
        assert await db.alerts.count_documents({"org_id": org_b}) == 0
        assert "last_run" in await db.detection_rules.find_one({"org_id": org_a})
    finally:
        for name in ("events", "alerts", "detection_rules"):
            await db[name].delete_many({"org_id": {"$in": [org_a, org_b]}})
        client.close()
