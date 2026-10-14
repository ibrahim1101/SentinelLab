"""Regression coverage for event search filter composition."""
import ast
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / "server.py"


def _filter_builder():
    # Compile only the pure filter builder: avoid importing the FastAPI app,
    # MongoDB connection and startup side effects.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == "_build_event_list_filter")
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    namespace = {"re": re, "_range_to_iso": lambda value: "2026-10-01T00:00:00Z"}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["_build_event_list_filter"]


def test_ip_and_keyword_are_both_required():
    filt = _filter_builder()("org-1", "24h", ip="192.0.2.10", q="failed")
    assert filt["org_id"] == "org-1"
    assert len(filt["$and"]) == 2
    assert filt["$and"][0] == {"$or": [
        {"src_ip": "192.0.2.10"}, {"dest_ip": "192.0.2.10"}]}
    assert len(filt["$and"][1]["$or"]) == 6
    assert filt["$and"][1]["$or"][0]["host"]["$regex"] == "failed"


def test_keyword_is_regex_escaped_and_org_scoped():
    filt = _filter_builder()("org-2", "24h", q=".*")
    assert filt["org_id"] == "org-2"
    assert filt["$and"][0]["$or"][0]["host"]["$regex"] == r"\.\*"


def test_ip_only_does_not_require_keyword():
    filt = _filter_builder()("org-3", "24h", ip="198.51.100.7")
    assert len(filt["$and"]) == 1
    assert "$or" not in filt
