"""Regression checks for bounded detection-rule backtests."""
import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "backtest_rule")
fn.decorator_list = []
fn.args.defaults = [ast.Constant(value="7d"), ast.Constant(value=None)]
fn = ast.fix_missing_locations(fn)


class Cursor:
    def __init__(self, events):
        self.events = events
        self.sort_spec = None
        self.limit_count = None

    def sort(self, spec):
        self.sort_spec = spec
        self.events = sorted(self.events, key=lambda e: (e["timestamp"], e["id"]), reverse=True)
        return self

    def limit(self, count):
        self.limit_count = count
        self.events = self.events[:count]
        return self

    async def to_list(self, count):
        return list(self.events[:count])


class Collection:
    def __init__(self, events):
        self.events = events
        self.cursor = None

    async def find_one(self, query, projection):
        return {"id": query["id"]}

    def find(self, query, projection):
        self.cursor = Cursor([e for e in self.events if e["timestamp"] >= query["timestamp"]["$gte"]])
        return self.cursor


class DB:
    def __init__(self, events):
        self.detection_rules = Collection([])
        self.events = Collection(events)


def make_backtest(db, captured):
    async def evaluate(rule, events, org):
        captured.extend(events)
        return [], events

    def range_iso(value):
        seconds = {"15m": 900, "1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}[value]
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()

    namespace = {
        "db": db, "active_org": lambda user, request: "test-org",
        "evaluate_rule": evaluate, "_range_to_iso": range_iso,
        "HTTPException": HTTPException, "require_role": lambda role: None,
        "Request": object,
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<backtest>", "exec"), namespace)
    return namespace["backtest_rule"]


def test_backtest_uses_latest_events_in_chronological_order():
    now = datetime.now(timezone.utc)
    events = [{"id": str(i).zfill(5), "timestamp": (now - timedelta(seconds=12000-i)).isoformat()} for i in range(10020)]
    captured = []
    db = DB(events)
    result = asyncio.run(make_backtest(db, captured)("rule-1", object(), "7d", None))
    assert result["matched_events"] == 10000
    assert len(captured) == 10000
    assert captured[0]["id"] == "00020"
    assert captured[-1]["id"] == "10019"
    assert db.events.cursor.sort_spec == [("timestamp", -1), ("id", -1)]
    assert db.events.cursor.limit_count == 10000


def test_backtest_rejects_unsupported_range():
    db = DB([])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(make_backtest(db, [])("rule-1", object(), "forever", None))
    assert exc.value.status_code == 422
    assert db.events.cursor is None
