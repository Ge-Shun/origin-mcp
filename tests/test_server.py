import math

from origin_mcp.server import _json_safe


def test_json_safe_replaces_non_finite_floats() -> None:
    data = {
        "ok": 1.0,
        "bad": float("nan"),
        "nested": [float("inf"), -float("inf"), {"value": 2.0}],
    }

    assert _json_safe(data) == {
        "ok": 1.0,
        "bad": None,
        "nested": [None, None, {"value": 2.0}],
    }
    assert math.isnan(data["bad"])
