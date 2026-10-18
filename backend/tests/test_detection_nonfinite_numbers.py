"""Non-finite numeric telemetry must never satisfy gt/lt conditions."""
import ast
import math
from pathlib import Path

import pytest

source = (Path(__file__).resolve().parents[1] / "detection.py").read_text()
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_num")
namespace = {"math": math}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<numbers>", "exec"), namespace)
_num = namespace["_num"]


@pytest.mark.parametrize("value", ["Infinity", "-Infinity", "NaN", float("inf"), float("-inf"), float("nan"), 10 ** 1000])
def test_nonfinite_values_are_rejected(value):
    number = _num(value)
    assert math.isnan(number)
    assert not (number > 5)
    assert not (number < 5)


def test_finite_numbers_still_compare():
    assert _num("6") > _num("5")
    assert _num("-2.5") < _num("0")
