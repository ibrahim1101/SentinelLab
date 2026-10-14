"""Regression tests for event-detail correlation filter."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "server.py"


def _builder():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "_related_event_filter")
    scope = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 str(SOURCE), "exec"), scope)
    return scope["_related_event_filter"]


def test_missing_identifiers_do_not_match_unrelated_events():
    build = _builder()
    assert build("org-1", "evt-1", {}) is None
    assert build("org-1", "evt-1", {"src_ip": None, "host": ""}) is None
    assert build("org-1", "evt-1", {"src_ip": "  ", "host": None}) is None


def test_single_identifier_is_tenant_scoped():
    query = _builder()("org-1", "evt-1", {"src_ip": "192.0.2.10"})
    assert query == {"org_id": "org-1", "id": {"$ne": "evt-1"},
                     "$or": [{"src_ip": "192.0.2.10"}]}


def test_two_identifiers_both_participate():
    query = _builder()("org-2", "evt-2", {
        "src_ip": "198.51.100.2", "host": "workstation-7"})
    assert query["org_id"] == "org-2"
    assert query["$or"] == [{"src_ip": "198.51.100.2"},
                            {"host": "workstation-7"}]
