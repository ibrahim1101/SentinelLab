"""Focused tests for bounded JSON ingestion request handling."""
import ast
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError


class IngestReq(BaseModel):
    source_id: str
    format: str = "json"
    payload: object


source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_read_bounded_ingest_json")
fn.decorator_list = []
fn.args.defaults = [ast.Constant(value=8 * 1024 * 1024)]
module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
namespace = {"Request": object, "IngestReq": IngestReq, "HTTPException": HTTPException, "INGEST_JSON_MAX_BYTES": 8 * 1024 * 1024}
exec(compile(module, "<ingest-json-test>", "exec"), namespace)
read_bounded = namespace["_read_bounded_ingest_json"]


class FakeRequest:
    def __init__(self, chunks, headers=None):
        self.chunks = chunks
        self.headers = headers or {}
        self.consumed = 0

    async def stream(self):
        for chunk in self.chunks:
            self.consumed += 1
            yield chunk


def test_ingest_json_accepts_chunked_valid_body():
    request = FakeRequest([b'{"source_id":"abc",', b'"payload":[{"event":"ok"}]}'])
    result = asyncio.run(read_bounded(request))
    assert result.source_id == "abc"
    assert result.payload == [{"event": "ok"}]
    assert request.consumed == 2


def test_ingest_json_rejects_declared_oversize_without_reading():
    request = FakeRequest([b'{}'], {"content-length": str(8 * 1024 * 1024 + 1)})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_bounded(request))
    assert exc.value.status_code == 413
    assert request.consumed == 0


def test_ingest_json_rejects_streamed_oversize():
    request = FakeRequest([b"a" * (8 * 1024 * 1024), b"b"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_bounded(request))
    assert exc.value.status_code == 413
    assert request.consumed == 2


def test_ingest_json_rejects_invalid_content_length():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_bounded(FakeRequest([], {"content-length": "not-a-number"})))
    assert exc.value.status_code == 400


def test_ingest_json_rejects_invalid_model():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_bounded(FakeRequest([b'{"payload":{}}'])))
    assert exc.value.status_code == 422
