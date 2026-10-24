"""Blank regex patterns must not match every telemetry event."""
import ast
import re
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "safe_regex_search")
namespace = {"re": re}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<regex>", "exec"), namespace)
search = namespace["safe_regex_search"]


@pytest.mark.parametrize("pattern", ["", " ", "\\t", None, [], {}])
def test_blank_or_invalid_regex_rejected(pattern):
    assert search("security event", pattern) is False


def test_normal_regex_still_matches():
    assert search("Failed Login", "failed") is True
    assert search("Successful Login", "failed") is False
