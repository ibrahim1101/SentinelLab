"""Malformed detection conditions must not match events or crash evaluation."""
import ast
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "event_matches")
namespace = {"OPS": {"eq": lambda a, b: str(a).lower() == str(b).lower()}}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<conditions>", "exec"), namespace)
event_matches = namespace["event_matches"]


@pytest.mark.parametrize("conditions", [
    None, "src_ip", {"field": "src_ip"}, [None], ["bad"],
    [{"field": None, "op": "eq", "value": "1"}],
    [{"field": "", "op": "eq", "value": "1"}],
    [{"field": "  ", "op": "eq", "value": "1"}],
    [{"field": "x" * 129, "op": "eq", "value": "1"}],
    [{"field": 123, "op": "eq", "value": "1"}],
    [{"field": "src_ip", "op": "unknown", "value": "1"}],
    [{"field": "src_ip", "op": [], "value": "1"}],
    [{"field": "src_ip", "op": {}, "value": "1"}],
    [{"field": "src_ip", "op": None, "value": "1"}],
    [{"field": "src_ip", "op": 42, "value": "1"}],
])
def test_invalid_conditions_do_not_match(conditions):
    # Malformed condition inputs fail closed, including null.
    assert event_matches(conditions, {"src_ip": "1"}) is False


def test_valid_condition_matches():
    assert event_matches([{"field": "src_ip", "op": "eq", "value": "192.0.2.1"}],
                         {"src_ip": "192.0.2.1"})


def test_invalid_event_fails_closed():
    assert not event_matches([{"field": "src_ip", "op": "eq", "value": "1"}], None)
