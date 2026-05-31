import asyncio
import math
import os
import subprocess
import sys
from pathlib import Path

import origin_mcp.server as server
import origin_mcp.tools.graph as graph_tools
import origin_mcp.tools.plotting as plotting_tools
from origin_mcp.errors import OriginDependencyError, OriginOperationError
from origin_mcp.server import _error, _json_safe


class FakeGraphClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def set_plot_style(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("set_plot_style", kwargs))
        return {"styled_plots": 1, **kwargs}


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

    assert len(names) == len(server.COMPACT_TOOL_NAMES)
    assert names == server.COMPACT_TOOL_NAMES
    assert "origin_plot_line" in names
    assert "origin_palette_catalog" in names
    assert "origin_plot_style_capabilities" in names
    assert "origin_set_plot_property" in names
    assert "origin_set_axis" in names


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

    assert int(output.strip()) == 153


def test_plot_style_capabilities_tool_finds_bar_gap() -> None:
    result = server.origin_plot_style_capabilities(chart_type="柱状图", query="柱宽")

    assert result["ok"] is True
    assert result["data"]["chart_type"] == "column"
    assert result["data"]["loaded_sources"] == ["core.json", "column_bar.json"]
    assert result["data"]["capabilities"][0]["name"] == "bar_gap"
    assert result["data"]["capabilities"][0]["origin_route"] == "LabTalk set -vg"


def test_set_plot_property_resolves_chinese_bar_width_alias(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="柱宽",
        value=80,
        graph_name="Graph1",
        layer_index=1,
        plot_index=2,
        chart_type="柱状图",
    )

    assert result["ok"] is True
    assert result["data"]["applied"] is True
    assert result["data"]["property_name"] == "bar_gap"
    assert result["data"]["capability"]["setter"] == "origin_set_plot_style(bar_gap=...)"
    assert fake.calls == [
        (
            "set_plot_style",
            {
                "graph_name": "Graph1",
                "layer_index": 1,
                "plot_index": 2,
                "bar_gap": 80,
            },
        )
    ]


def test_set_plot_property_reports_planned_capability_without_mutating(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="色带",
        value="viridis",
        chart_type="热图",
    )

    assert result["ok"] is True
    assert result["data"]["applied"] is False
    assert result["data"]["capability"]["name"] == "colormap"
    assert result["data"]["capability"]["status"] == "planned"
    assert result["data"]["alternatives"]
    assert fake.calls == []


def test_set_plot_property_rejects_unknown_property(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="不存在的样式属性",
        value=1,
        chart_type="柱状图",
    )

    assert result["ok"] is False
    assert result["error_code"] == "invalid_request"
    assert "Unsupported plot style property" in result["message"]
    assert fake.calls == []


def test_plot_style_capabilities_tool_accepts_plot_type_id() -> None:
    result = server.origin_plot_style_capabilities(plot_type_id=203, query="柱宽")

    assert result["ok"] is True
    assert result["data"]["plot_type"]["id"] == 203
    assert result["data"]["plot_type"]["chart_type"] == "column"
    assert result["data"]["loaded_sources"] == ["core.json", "column_bar.json"]
    assert result["data"]["capabilities"][0]["name"] == "bar_gap"


def test_plot_style_capabilities_maps_all_catalog_plot_types() -> None:
    from origin_mcp.compat import PLOT_TYPE_CATALOG
    from origin_mcp.plot_style_registry import plot_type_style_profile

    profiles = [plot_type_style_profile(item["id"]) for item in PLOT_TYPE_CATALOG]

    assert all(profile is not None for profile in profiles)
    assert all(profile["chart_type"] for profile in profiles if profile is not None)


def test_plot_style_capabilities_tool_reports_planned_image_controls() -> None:
    result = server.origin_plot_style_capabilities(chart_type="热图", query="色带")

    assert result["ok"] is True
    assert result["data"]["loaded_sources"] == ["core.json", "field_color.json", "image.json"]
    assert result["data"]["capabilities"][0]["name"] == "colormap"
    assert result["data"]["capabilities"][0]["status"] == "planned"


def test_plot_style_capabilities_tool_reports_specialized_profiles() -> None:
    result = server.origin_plot_style_capabilities(plot_type_id=221, query="涨跌颜色")

    assert result["ok"] is True
    assert result["data"]["plot_type"]["chart_type"] == "financial"
    assert result["data"]["loaded_sources"] == ["core.json", "financial.json"]
    assert result["data"]["capabilities"][0]["name"] == "financial_up_down_colors"


def test_plot_style_capabilities_keeps_core_small_without_query() -> None:
    result = server.origin_plot_style_capabilities()

    assert result["ok"] is True
    assert result["data"]["loaded_sources"] == ["core.json"]
    assert {item["source"] for item in result["data"]["capabilities"]} == {"core.json"}


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
