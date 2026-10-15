"""Regression coverage for bounded telemetry upload processing."""
import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "server.py"


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


def _reader():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
              and node.name == "_read_bounded_telemetry")
    scope = {"HTTPException": HTTPException}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 str(SOURCE), "exec"), scope)
    return scope["_read_bounded_telemetry"]


class FakeUpload:
    def __init__(self, content):
        self.content = content
        self.requested = None

    async def read(self, count):
        self.requested = count
        return self.content[:count]


@pytest.mark.asyncio
async def test_upload_at_limit_is_accepted():
    file = FakeUpload(b"abcd")
    assert await _reader()(file, max_bytes=4) == "abcd"
    assert file.requested == 5


@pytest.mark.asyncio
async def test_upload_over_limit_is_rejected():
    file = FakeUpload(b"abcde")
    with pytest.raises(HTTPException) as exc:
        await _reader()(file, max_bytes=4)
    assert exc.value.status_code == 413
    assert file.requested == 5


@pytest.mark.asyncio
async def test_upload_decodes_invalid_utf8_without_crashing():
    assert await _reader()(FakeUpload(b"\\xff"), max_bytes=4) == "\\xff"
