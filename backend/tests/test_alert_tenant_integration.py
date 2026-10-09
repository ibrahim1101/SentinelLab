"""Mongo-backed isolation checks for alert details and linked records."""
import os
import sys
from pathlib import Path
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "sentinellab_phase1_ci")
os.environ.setdefault("JWT_SECRET", "ci-only-test-secret")
import server

@pytest.mark.asyncio
async def test_alert_detail_never_joins_foreign_tenant_records(monkeypatch):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    database = client[os.environ["DB_NAME"]]
    tenant_a, tenant_b = "ci-alert-tenant-a", "ci-alert-tenant-b"
    request = Request({"type": "http", "headers": [(b"x-workspace-id", tenant_a.encode())]})
    user_a = {"id": "ci-user-a", "email": "a@example.com", "role": "analyst", "org_ids": [tenant_a], "default_org": tenant_a}
    user_b = {"id": "ci-user-b", "email": "b@example.com", "role": "analyst", "org_ids": [tenant_b], "default_org": tenant_b}
    monkeypatch.setattr(server, "db", database)
    try:
        for coll in ("events", "alerts", "detection_rules"):
            await database[coll].delete_many({"org_id": {"$in": [tenant_a, tenant_b]}})
        await database.alerts.insert_one({"id": "ci-alert-a", "org_id": tenant_a, "related_events": ["ci-event-a", "ci-event-b"], "rule_id": "ci-rule-b", "created_at": "2026-10-09T00:00:00Z"})
        await database.events.insert_many([{"id": "ci-event-a", "org_id": tenant_a}, {"id": "ci-event-b", "org_id": tenant_b}])
        await database.detection_rules.insert_one({"id": "ci-rule-b", "org_id": tenant_b, "name": "foreign rule"})
        result = await server.alert_detail("ci-alert-a", request, user_a)
        assert result["alert"]["org_id"] == tenant_a
        assert [event["id"] for event in result["events"]] == ["ci-event-a"]
        assert result["rule"] is None
        for endpoint in (server.list_events, server.list_alerts, server.list_rules):
            # A user with no membership in tenant A cannot query tenant A.
            with pytest.raises(HTTPException) as exc:
                await endpoint(request=request, user=user_b)
            assert exc.value.status_code == 403
        with pytest.raises(HTTPException) as exc:
            await server.alert_detail("ci-alert-a", request, user_b)
        assert exc.value.status_code == 403
    finally:
        for coll in ("events", "alerts", "detection_rules"):
            await database[coll].delete_many({"org_id": {"$in": [tenant_a, tenant_b]}})
        client.close()

@pytest.mark.asyncio
async def test_investigation_detail_filters_cross_tenant_alerts(monkeypatch):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
    database = client[os.environ["DB_NAME"]]
    tenant_a, tenant_b = "ci-investigation-a", "ci-investigation-b"
    request = Request({"type": "http", "headers": [(b"x-workspace-id", tenant_a.encode())]})
    user_a = {"id": "ci-investigator-a", "email": "a@example.com", "role": "analyst", "org_ids": [tenant_a], "default_org": tenant_a}
    monkeypatch.setattr(server, "db", database)
    try:
        await database.investigations.delete_many({"org_id": tenant_a})
        await database.alerts.delete_many({"org_id": {"$in": [tenant_a, tenant_b]}})
        await database.investigations.insert_one({"id": "ci-inv-a", "org_id": tenant_a, "related_alerts": ["ci-alert-local", "ci-alert-foreign"]})
        await database.alerts.insert_many([{"id": "ci-alert-local", "org_id": tenant_a}, {"id": "ci-alert-foreign", "org_id": tenant_b}])
        result = await server.investigation_detail("ci-inv-a", request, user_a)
        assert [alert["id"] for alert in result["alerts"]] == ["ci-alert-local"]
    finally:
        await database.investigations.delete_many({"org_id": tenant_a})
        await database.alerts.delete_many({"org_id": {"$in": [tenant_a, tenant_b]}})
        client.close()
