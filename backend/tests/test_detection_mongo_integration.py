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



@pytest.mark.asyncio
async def test_soc_windows_authentication_incident_lifecycle(monkeypatch):
    """SOC milestone: Windows failures -> alert -> triage -> replay isolation.

    Uses synthetic, non-sensitive events and an isolated per-run organization.
    """
    from uuid import uuid4

    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    db = client[os.environ["DB_NAME"]]
    org = f"soc-e2e-{uuid4().hex}"
    other_org = f"soc-e2e-other-{uuid4().hex}"
    rule_id = f"{org}-auth-rule"
    event_ids = [f"{org}-4625-{i}" for i in range(6)]
    events = [
        {
            "id": event_id,
            "org_id": org,
            "timestamp": f"2026-10-25T12:00:{i:02d}+00:00",
            "event_type": "windows_security_4625",
            "category": "authentication",
            "outcome": "failure",
            "host": "win-lab-01",
            "src_ip": "192.0.2.45",
            "username": "lab-user",
            "severity": "high",
            "is_synthetic": True,
        }
        for i, event_id in enumerate(event_ids)
    ]
    rule = {
        "id": rule_id,
        "org_id": org,
        "name": "Windows failed logon investigation",
        "enabled": True,
        "rule_type": "threshold",
        "severity": "high",
        "mitre": ["T1110"],
        "params": {
            "conditions": [
                {"field": "category", "op": "eq", "value": "authentication"},
                {"field": "outcome", "op": "eq", "value": "failure"},
            ],
            "group_by": "src_ip",
            "window_minutes": 5,
            "threshold": 5,
        },
    }
    try:
        await client.admin.command("ping")
        await db.detection_rules.insert_one(rule)
        await db.events.insert_many(events + [dict(events[0], org_id=other_org)])
        monkeypatch.setattr(detection, "db", db)

        preview = await detection.run_detection(org, events, persist=False)
        assert len(preview) == 1
        assert set(preview[0]["related_events"]) == set(event_ids)
        assert preview[0]["mitre"] == ["T1110"]
        assert await db.alerts.count_documents({"org_id": org}) == 0

        created = await detection.run_detection(org, events, persist=True)
        assert len(created) == 1
        assert await db.alerts.count_documents({"org_id": org}) == 1
        alert = await db.alerts.find_one({"org_id": org}, {"_id": 0})
        assert alert["status"] == "new"
        assert alert["severity"] == "high"
        assert alert["host"] == "win-lab-01"
        assert alert["src_ip"] == "192.0.2.45"
        assert set(alert["related_events"]) == set(event_ids)
        assert await db.events.count_documents({
            "org_id": org, "id": {"$in": event_ids}, "rule_matches": rule_id,
        }) == len(event_ids)
        assert "rule_matches" not in await db.events.find_one({"org_id": other_org})

        await db.alerts.update_one(
            {"org_id": org, "id": alert["id"]},
            {"$set": {"status": "triaged", "assigned_to": "soc-analyst"}},
        )
        await detection.run_detection(org, events, persist=True)
        assert await db.alerts.count_documents({"org_id": org}) == 1
        triaged = await db.alerts.find_one({"org_id": org}, {"_id": 0})
        assert triaged["status"] == "triaged"
        assert triaged["assigned_to"] == "soc-analyst"
        assert set(triaged["related_events"]) == set(event_ids)
        assert await db.alerts.count_documents({"org_id": other_org}) == 0
    finally:
        for collection in ("events", "alerts", "detection_rules"):
            await db[collection].delete_many({"org_id": {"$in": [org, other_org]}})
        client.close()
