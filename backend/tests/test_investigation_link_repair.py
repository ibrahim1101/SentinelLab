"""Reconcile investigation links from authoritative tenant-scoped alert records."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

tree = ast.parse((Path(__file__).resolve().parents[1] / "server.py").read_text())
functions = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
             and n.name in ("_inspect_investigation_alert_links",
                            "_repair_investigation_alert_links")]


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, limit):
        return self.rows[:limit]


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def find_one(self, query, projection=None):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                return dict(row)
        return None

    def find(self, query, projection=None):
        return Cursor([dict(row) for row in self.rows
                       if all(row.get(k) == v for k, v in query.items())])

    async def update_one(self, query, update):
        self.calls.append((query, update))


def case(existing, alerts):
    investigations = Collection([{"id": "inv", "org_id": "org-a",
                                  "related_alerts": existing}])
    alert_collection = Collection(alerts)
    ns = {"db": SimpleNamespace(investigations=investigations, alerts=alert_collection),
          "HTTPException": HTTPException, "now_iso": lambda: "now"}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "<repair>", "exec"), ns)
    return ns["_repair_investigation_alert_links"], investigations, ns["_inspect_investigation_alert_links"]


def test_repair_restores_missing_and_removes_stale_links():
    repair, invs, inspect = case(["stale"], [
        {"id": "good", "org_id": "org-a", "investigation_id": "inv"},
        {"id": "other", "org_id": "org-b", "investigation_id": "inv"},
        {"id": "wrong", "org_id": "org-a", "investigation_id": "different"},
    ])
    result = asyncio.run(repair("org-a", "inv"))
    assert result == {"investigation_id": "inv", "linked_alerts": 1, "repaired": True}
    assert invs.calls[0][1]["$set"]["related_alerts"] == ["good"]
    assert invs.calls[0][0]["org_id"] == "org-a"


def test_consistent_links_are_noop():
    repair, invs, inspect = case(["good"], [
        {"id": "good", "org_id": "org-a", "investigation_id": "inv"}])
    result = asyncio.run(repair("org-a", "inv"))
    assert result["repaired"] is False
    assert not invs.calls


def test_empty_links_can_be_repaired():
    repair, invs, inspect = case(["stale"], [])
    result = asyncio.run(repair("org-a", "inv"))
    assert result["linked_alerts"] == 0
    assert invs.calls[0][1]["$set"]["related_alerts"] == []


def test_link_health_reports_differences_without_writing():
    repair, invs, inspect = case(["stale"], [
        {"id": "good", "org_id": "org-a", "investigation_id": "inv"},
        {"id": "foreign", "org_id": "org-b", "investigation_id": "inv"},
    ])
    result = asyncio.run(inspect("org-a", "inv"))
    assert result["consistent"] is False
    assert result["missing_from_investigation"] == ["good"]
    assert result["stale_in_investigation"] == ["stale"]
    assert not invs.calls
