"""Match detection must preserve valid alerts amid malformed event identifiers."""
import ast
import asyncio
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")
namespace = {
    "event_matches": lambda conditions, event: event.get("src_ip") == "192.0.2.5",
    "_build_alert": lambda rule, org, events, title=None: {"related_events": [e["id"] for e in events]},
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<match>", "exec"), namespace)


def test_match_rule_skips_invalid_ids_and_keeps_valid_matches():
    events = [
        None, [], "broken",
        {"src_ip": "192.0.2.5"},
        {"id": None, "src_ip": "192.0.2.5"},
        {"id": [], "src_ip": "192.0.2.5"},
        {"id": "", "src_ip": "192.0.2.5"},
        {"id": "valid", "src_ip": "192.0.2.5"},
    ]
    rule = {"id": "r1", "name": "Match", "rule_type": "match", "params": {"conditions": []}}
    alerts, matched = asyncio.run(namespace["evaluate_rule"](rule, events, "org-1"))
    assert matched == {"valid"}
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == ["valid"]
