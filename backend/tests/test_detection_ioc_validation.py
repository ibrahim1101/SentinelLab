"""IOC matching should reject malformed indicators and non-scalar event fields."""
import ast
import asyncio
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_rule")


class Cursor:
    async def to_list(self, count):
        return [
            {"ioc_type": "ip", "value": "192.0.2.5"},
            {"ioc_type": "domain", "value": "Example.COM"},
            {"ioc_type": "ip", "value": None},
            {"ioc_type": "unknown", "value": "anything"},
            {"ioc_type": [], "value": "192.0.2.5"},
            {"ioc_type": {}, "value": "192.0.2.5"},
            {"ioc_type": 7, "value": "192.0.2.5"},
            {"value": "no-type"},
            None,
        ]


class Indicators:
    def find(self, query, projection):
        assert query == {"org_id": "org-1", "active": True}
        return Cursor()


class DB:
    indicators = Indicators()


namespace = {
    "db": DB(),
    "_build_alert": lambda rule, org, events, title=None: {"related_events": [e["id"] for e in events]},
}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<ioc>", "exec"), namespace)
evaluate_rule = namespace["evaluate_rule"]


def test_ioc_matching_skips_malformed_values_and_normalizes_case():
    rule = {"id": "ioc-rule", "name": "IOC", "rule_type": "indicator"}
    events = [
        {"id": "match-ip", "src_ip": " 192.0.2.5 "},
        {"id": "match-domain", "dns_query": "example.com"},
        {"id": "invalid-list", "src_ip": ["192.0.2.5"]},
        {"id": "invalid-dict", "dns_query": {"value": "Example.COM"}},
    ]
    alerts, matched = asyncio.run(evaluate_rule(rule, events, "org-1"))
    assert matched == {"match-ip", "match-domain"}
    assert len(alerts) == 1
    assert alerts[0]["related_events"] == ["match-ip", "match-domain"]
