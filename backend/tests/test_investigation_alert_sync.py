"""Investigation alert updates must validate tenant ownership before writing."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Depends, Request

tree = ast.parse((Path(__file__).resolve().parents[1] / "server.py").read_text())
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "update_investigation")
fn.decorator_list = []


class Collection:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    async def find_one(self, query, projection=None):
        return next((dict(d) for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)

    async def count_documents(self, query):
        return sum(d.get("org_id") == query["org_id"] and d.get("id") in query["id"]["$in"] for d in self.docs)

    async def update_one(self, query, update):
        self.calls.append((query, update))

    async def update_many(self, query, update):
        self.calls.append((query, update))


def setup(ids):
    invs = Collection([{"id": "inv", "org_id": "org-a", "related_alerts": ["old"]}])
    alerts = Collection([{"id": "old", "org_id": "org-a"}, {"id": "new", "org_id": "org-a"},
                         {"id": "other", "org_id": "org-b"}])
    async def audit(*args, **kwargs):
        pass
    ns = {"db": SimpleNamespace(investigations=invs, alerts=alerts),
          "active_org": lambda user, request: "org-a", "now_iso": lambda: "now",
          "new_id": lambda: "id", "audit": audit, "clean": lambda d: d,
          "HTTPException": HTTPException, "Depends": Depends, "Request": Request,
          "InvUpdate": object, "require_role": lambda role: lambda: None}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<inv-update>", "exec"), ns)
    body = SimpleNamespace(related_alerts=ids, related_events=None, status=None,
                           priority=None, findings=None, note=None, task=None)
    return ns["update_investigation"], body, invs, alerts


@pytest.mark.parametrize("ids", [["other"], ["new", "new"], [{"id": "new"}], [None]])
def test_invalid_alert_links_do_not_write(ids):
    update, body, invs, alerts = setup(ids)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(update("inv", body, None, {"email": "analyst@example.test"}))
    assert exc.value.status_code == 422
    assert not invs.calls and not alerts.calls


def test_alert_links_update_both_sides():
    update, body, invs, alerts = setup(["new"])
    asyncio.run(update("inv", body, None, {"email": "analyst@example.test"}))
    assert len(alerts.calls) == 2
    assert alerts.calls[0][1]["$set"]["investigation_id"] is None
    assert alerts.calls[1][1]["$set"]["investigation_id"] == "inv"
    assert all(q["org_id"] == "org-a" for q, _ in alerts.calls)
