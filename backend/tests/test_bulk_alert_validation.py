"""Bulk alert input-validation regression tests."""
import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "server.py"


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


def _validator():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "_validate_bulk_alert_update")
    scope = {"HTTPException": HTTPException}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 str(SOURCE), "exec"), scope)
    return scope["_validate_bulk_alert_update"]


@pytest.mark.parametrize("payload", [
    {}, {"ids": [], "status": "closed"},
    {"ids": "a", "status": "closed"},
    {"ids": ["a"], "status": None},
    {"ids": ["a"], "status": "  "},
    {"ids": [None], "status": "closed"},
    {"ids": ["a"] * 501, "status": "closed"},
])
def test_invalid_bulk_updates_rejected(payload):
    with pytest.raises(HTTPException) as exc:
        _validator()(payload)
    assert exc.value.status_code == 422


def test_valid_bulk_update_deduplicates_ids_and_trims_status():
    ids, status = _validator()({"ids": ["a", "a", "b"], "status": " closed "})
    assert ids == ["a", "b"]
    assert status == "closed"
