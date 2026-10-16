"""Alert-to-investigation links must stay tenant-scoped and bidirectional."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "update_alert")
fn.decorator_list = []


class Collection:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    async def find_one(self, query, projection=None):
        return next((dict(d) for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)

    async def update_one(self, query, update):
        self.calls.append((query, update))


def run_case(target_exists=True):
    alerts = Collection([{"id": "alert-1", "org_id": "org-a", "investigation_id": "old"}])
    invs = Collection([{"id": "old", "org_id": "org-a"}] +
                      ([{"id": "new", "org_id": "org-a"}] if target_exists else
                       [{"id": "new", "org_id": "org-b"}]))
    async def audit(*args, **kwargs):
        return None
    namespace = {
        "db": SimpleNamespace(alerts=alerts, investigations=invs),
        "active_org": lambda user, request: "org-a",
        "now_iso": lambda: "2026-10-16T00:00:00+00:00",
        "audit": audit,
        "clean": lambda value: value,
        "HTTPException": HTTPException,
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<alert-update>", "exec"), namespace)
    body = SimpleNamespace(status=None, severity=None, assigned_to=None,
                           investigation_id="new", tags=None, comment=None)
    return namespace["update_alert"], body, alerts, invs


def test_cross_tenant_investigation_rejected_without_writes():
    update, body, alerts, invs = run_case(False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update("alert-1", body, None, {"email": "analyst@example.test"}))
    assert exc.value.status_code == 404
    assert not alerts.calls and not invs.calls


def test_reassignment_unlinks_old_and_links_new():
    update, body, alerts, invs = run_case(True)
    asyncio.run(update("alert-1", body, None, {"email": "analyst@example.test"}))
    assert len(alerts.calls) == 1
    assert alerts.calls[0][1]["$set"]["investigation_id"] == "new"
    assert invs.calls[0][1]["$pull"]["related_alerts"] == "alert-1"
    assert invs.calls[1][1]["$addToSet"]["related_alerts"] == "alert-1"
    assert all(query["org_id"] == "org-a" for query, _ in invs.calls)
