import asyncio
import math
import os
import subprocess
import sys
from pathlib import Path

import origin_mcp.server as server
import origin_mcp.tools.plotting as plotting_tools
from origin_mcp.errors import OriginDependencyError, OriginOperationError
from origin_mcp.server import _error, _json_safe


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


def test_default_mcp_tool_profile_is_compact() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}

    assert len(names) == 20
    assert names == server.COMPACT_TOOL_NAMES
    assert "origin_plot_line" not in names


def test_full_mcp_tool_profile_registers_all_tools() -> None:
    env = {**os.environ, "ORIGIN_MCP_TOOL_PROFILE": "full"}
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            (
                "import asyncio, origin_mcp.server as s; "
                "print(len(asyncio.run(s.mcp.list_tools())))"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
    )

    assert int(output.strip()) == 148


def test_error_response_includes_stable_error_code() -> None:
    result = _error(
        OriginOperationError(
            "Worksheet not found: [Book1]Sheet1",
            error_code="worksheet_not_found",
        )
    )

    assert result["ok"] is False
    assert result["error_code"] == "worksheet_not_found"
    assert result["data"]["error_type"] == "OriginOperationError"
    assert result["data"]["error_code"] == "worksheet_not_found"


def test_error_response_codes_dependency_failures() -> None:
    result = _error(OriginDependencyError("The 'originpro' package is not available."))

    assert result["error_code"] == "origin_dependency_unavailable"


def test_error_response_codes_unsupported_analysis() -> None:
    result = _error(
        OriginOperationError(
            "Unsupported analysis type: nope. Supported: linear_fit, polynomial_fit",
            error_code="unsupported_analysis_type",
        )
    )

    assert result["error_code"] == "unsupported_analysis_type"


def test_error_response_defaults_for_unmarked_operation_errors() -> None:
    result = _error(OriginOperationError("something went wrong"))

    assert result["error_code"] == "origin_operation_failed"


def test_heatmap_wrapper_routes_xyz_data_through_plot_type_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "xyz.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    calls = []

    def fake_plot_table_id(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "message": "ok", "data": {}}

    monkeypatch.setattr(plotting_tools, "_plot_table_id", fake_plot_table_id)

    result = server.origin_plot_heatmap(
        path=str(path),
        x_col="x",
        y_col="y",
        z_col="z",
        graph_name="Heat",
    )

    assert result["ok"] is True
    assert calls[0]["plot_type_id"] == 243
    assert calls[0]["template"] == "Contour"
    assert calls[0]["selected_cols"] == ["x", "y", "z"]
    assert calls[0]["graph_name"] == "Heat"


def test_xyz_3d_wrappers_route_through_plot_type_id(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "xyz.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    calls = []

    def fake_plot_table_id(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "message": "ok", "data": {}}

    monkeypatch.setattr(plotting_tools, "_plot_table_id", fake_plot_table_id)

    scatter = server.origin_plot_3d_scatter(str(path), "x", "y", "z", graph_name="Scatter3D")
    surface = server.origin_plot_3d_surface(str(path), "x", "y", "z", graph_name="Surface3D")

    assert scatter["ok"] is True
    assert surface["ok"] is True
    assert [(call["plot_type_id"], call["template"]) for call in calls] == [
        (240, "3d"),
        (242, "glmesh"),
    ]
    assert all(call["selected_cols"] == ["x", "y", "z"] for call in calls)
