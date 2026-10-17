"""Timestamp validation must not crash on malformed telemetry records."""
import ast
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
parse_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_parse_ts")
valid_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_valid_event_timestamp")
from datetime import timezone
from dateutil import parser as dtparse
namespace = {"dtparse": dtparse, "timezone": timezone}
exec(compile(ast.Module(body=[parse_fn, valid_fn], type_ignores=[]), "<timestamp>", "exec"), namespace)
valid = namespace["_valid_event_timestamp"]


@pytest.mark.parametrize("event", [None, [], "event", 0, True, {}, {"timestamp": None}, {"timestamp": "not-a-date"}])
def test_malformed_event_rejected_without_exception(event):
    assert valid(event) is False


def test_valid_event_timestamp_accepted():
    assert valid({"timestamp": "2026-10-16T12:00:00Z"}) is True
