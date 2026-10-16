"""IOC evaluation ignores malformed telemetry without losing valid matches."""
import ast
import asyncio
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")


class FakeCursor:
    async def to_list(self, limit):
        return [{"ioc_type": "ip", "value": "192.0.2.5", "active": True}]


class FakeCollection:
    def find(self, *args, **kwargs):
        return FakeCursor()


class FakeDB:
    indicators = FakeCollection()


namespace = {
    "db": FakeDB(),
    "_build_alert": lambda rule, org, events, title=None: {"related_events": [e["id"] for e in events]},
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<ioc>", "exec"), namespace)


def test_ioc_ignores_non_object_events_and_missing_identifiers():
    events = [None, [], "broken", 42, {"src_ip": "192.0.2.5"},
              {"id": None, "src_ip": "192.0.2.5"},
              {"id": "valid", "src_ip": "192.0.2.5"}]
    rule = {"id": "ioc-1", "name": "IOC", "rule_type": "indicator", "params": {}}
    alerts, matched = asyncio.run(namespace["evaluate_rule"](rule, events, "org-1"))
    assert matched == {"valid"}
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == ["valid"]
