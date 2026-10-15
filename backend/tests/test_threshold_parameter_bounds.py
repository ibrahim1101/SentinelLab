"""Invalid temporal rule settings must fail safely and predictably."""
import ast
import asyncio
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")
namespace = {
    "event_matches": lambda conditions, event: True,
    "_valid_event_timestamp": lambda event: True,
    "_parse_ts": lambda value: value,
    "_build_alert": lambda rule, org, events, title=None: {"related_events": [e["id"] for e in events]},
    "db": None,
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<threshold>", "exec"), namespace)
evaluate_rule = namespace["evaluate_rule"]


@pytest.mark.parametrize("window,threshold", [
    (0, 2), (-1, 2), (1441, 2), ("bad", 2), (None, 2),
    (5, 0), (5, -1), (5, 10001), (5, "bad"), (5, None),
])
def test_invalid_threshold_settings_rejected(window, threshold):
    rule = {"rule_type": "threshold", "params": {"window_minutes": window, "threshold": threshold}}
    with pytest.raises(ValueError):
        asyncio.run(evaluate_rule(rule, [], "org-1"))


def test_valid_threshold_bounds_accepted():
    rule = {"rule_type": "frequency", "params": {"window_minutes": 1440, "threshold": 10000}}
    assert asyncio.run(evaluate_rule(rule, [], "org-1")) == ([], set())
