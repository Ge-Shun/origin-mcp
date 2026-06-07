import asyncio
import base64
import math
import os
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import Image

import origin_mcp.server as server
import origin_mcp.tools.analysis as analysis_tools
import origin_mcp.tools.graph as graph_tools
import origin_mcp.tools.plotting as plotting_tools
import origin_mcp.tools.plotting_basic as plotting_basic_tools
import origin_mcp.tools.plotting_plot_ids as plotting_plot_ids_tools
from origin_mcp.errors import OriginDependencyError, OriginOperationError
from origin_mcp.origin_client import GraphRef, WorksheetRef
from origin_mcp.server import _error, _json_safe


class FakeGraphClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def set_plot_style(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("set_plot_style", kwargs))
        return {"styled_plots": 1, **kwargs}

    def apply_nature_style(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("apply_nature_style", kwargs))
        return {"styled_plots": 1, **kwargs}

    def apply_image_panel_style(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("apply_image_panel_style", kwargs))
        return {"styled_layers": 1, **kwargs}


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
    assert "origin_plot_style_setter_coverage" in names
    assert "origin_set_plot_property" in names
    assert "origin_set_axis" in names


def test_full_mcp_tool_profile_registers_more_than_compact() -> None:
    # The exact full-profile surface is pinned to the source in
    # tests/test_tool_registration.py; here we only assert that `full`
    # genuinely expands beyond the compact allow-list.
    env = {**os.environ, "ORIGIN_MCP_TOOL_PROFILE": "full"}
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            ("import asyncio, origin_mcp.server as s; print(len(asyncio.run(s.mcp.list_tools())))"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
    )

    assert int(output.strip()) > len(server.COMPACT_TOOL_NAMES)


def test_palette_catalog_tool_filters_by_color_count() -> None:
    result = server.origin_palette_catalog(
        colors_count=6,
        family="lcpmgh/colors",
        include_colors=True,
        limit=3,
    )

    assert result["ok"] is True
    palettes = result["data"]["palettes"]
    assert len(palettes) == 3
    assert all(entry["colors_count"] == 6 for entry in palettes.values())
    assert all(len(entry["colors"]) == 6 for entry in palettes.values())


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


def test_set_plot_property_routes_palette_name_to_nature_style(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="配色",
        value="lcpmgh_006_001",
        graph_name="Graph1",
        layer_index=0,
    )

    assert result["ok"] is True
    assert result["data"]["applied"] is True
    assert result["data"]["property_name"] == "palette_name"
    assert result["data"]["route"] == {
        "tool": "origin_apply_nature_style",
        "kwarg": "palette_name",
    }
    assert fake.calls == [
        (
            "apply_nature_style",
            {
                "graph_name": "Graph1",
                "layer_index": 0,
                "chart_type": None,
                "palette_name": "lcpmgh_006_001",
            },
        )
    ]


def test_set_plot_property_routes_image_annotations_with_structured_value(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="比例尺",
        value={"panel_label": "a", "scale_bar_label": "10 mm", "dark_panel": True},
        graph_name="Heat",
        layer_index=1,
        chart_type="热图",
    )

    assert result["ok"] is True
    assert result["data"]["applied"] is True
    assert result["data"]["property_name"] == "image_panel_annotations"
    assert result["data"]["route"] == {
        "tool": "origin_apply_image_panel_style",
        "kwarg": "annotations",
    }
    assert fake.calls == [
        (
            "apply_image_panel_style",
            {
                "graph_name": "Heat",
                "layer_index": 1,
                "panel_label": "a",
                "scale_bar_label": "10 mm",
                "dark_panel": True,
            },
        )
    ]


def test_set_plot_property_rejects_unstructured_image_annotations(monkeypatch) -> None:
    fake = FakeGraphClient()
    monkeypatch.setattr(graph_tools, "client", fake)

    result = server.origin_set_plot_property(
        property_name="比例尺",
        value="10 mm",
        chart_type="热图",
    )

    assert result["ok"] is False
    assert result["error_code"] == "invalid_request"
    assert "image_panel_annotations value must be an object" in result["message"]
    assert fake.calls == []


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


def test_plot_style_setter_coverage_has_no_unhandled_implemented_entries() -> None:
    result = server.origin_plot_style_setter_coverage()

    assert result["ok"] is True
    assert result["data"]["implemented_count"] == result["data"]["executable_count"]
    assert result["data"]["unhandled_implemented_count"] == 0
    routes = {item["name"]: item["route"]["tool"] for item in result["data"]["executable"]}
    assert routes["bar_gap"] == "origin_set_plot_style"
    assert routes["palette_name"] == "origin_apply_nature_style"
    assert routes["image_panel_annotations"] == "origin_apply_image_panel_style"


def test_plot_style_setter_coverage_filters_by_chart_type() -> None:
    result = server.origin_plot_style_setter_coverage(chart_type="热图")

    assert result["ok"] is True
    assert result["data"]["chart_type"] == "heatmap"
    names = {item["name"] for item in result["data"]["executable"]}
    assert "image_panel_annotations" in names
    assert "palette_name" in names
    assert result["data"]["unhandled_implemented_count"] == 0


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


def test_origin_run_analysis_delegates_linear_fit_to_structured_api(
    monkeypatch,
) -> None:
    calls = {}

    class FakeClient:
        def linear_fit_result(self, **kwargs):
            calls["linear_fit_result"] = kwargs
            return {"mode": "result", "result": {"parameters": []}}

    monkeypatch.setattr(analysis_tools, "client", FakeClient())

    result = server.origin_run_analysis(
        analysis="linear_fit",
        worksheet="[Book1]Data",
        x_col="x",
        y_col="y",
        options={"y_error_col": "err"},
    )

    assert result["ok"] is True
    assert result["data"]["mode"] == "result"
    assert calls["linear_fit_result"] == {
        "worksheet": "[Book1]Data",
        "x_col": "x",
        "y_col": "y",
        "y_error_col": "err",
        "options": {"y_error_col": "err"},
    }


def test_error_response_defaults_for_unmarked_operation_errors() -> None:
    result = _error(OriginOperationError("something went wrong"))

    assert result["error_code"] == "origin_operation_failed"


def test_plot_type_id_routes_keep_expected_origin_ids() -> None:
    assert plotting_tools.PLOT_TYPE_ID_ROUTES == {
        "area": (204, "area"),
        "stack_area": (214, "stackarea"),
        "fill_area": (249, "fillarea"),
        "bar": (215, "bar"),
        "stack_bar": (216, "bar"),
        "floating_bar": (207, "floatbar"),
        "column_stack": (213, "column"),
        "pie": (225, "pie"),
        "ternary": (245, "ternary"),
        "ternary_contour": (185, "TernaryContour"),
        "bubble": (193, "scatter"),
        "bubble_color_mapped": (248, "scatter"),
        "color_mapped": (247, "scatter"),
        "vector_xyam": (208, "vector"),
        "vector_xyxy": (218, "vectxyxy"),
        "vector_3d": (183, "gl3DVector"),
        "high_low_close": (205, "hclose"),
        "candlestick": (221, "Candlestick"),
        "waterfall": (210, "walls"),
        "ribbon_3d": (211, "ribbon"),
        "bars_3d": (212, "bar3d"),
        "errorbar_3d": (184, "gl3DError"),
        "polar_xr_ytheta": (186, "PolarXrYTheta"),
        "smith": (191, "SmithCht"),
        "dendrogram": (108, "Cluster"),
    }


def test_matrix_plot_type_id_routes_keep_expected_origin_ids() -> None:
    assert plotting_tools.MATRIX_PLOT_TYPE_ID_ROUTES == {
        "scatter_3d": (101, "gl3DScatterMat"),
        "surface_3d": (103, "glmesh"),
        "heatmap": (105, "heatmap"),
        "contour": (226, "contour"),
        "image": (220, "image"),
    }


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

    monkeypatch.setattr(plotting_basic_tools, "_plot_table_id", fake_plot_table_id)

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


def test_origin_plot_routes_kind_through_plot_type_id(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    calls = []

    def fake_plot_table_id(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "message": "ok", "data": {}}

    monkeypatch.setattr(plotting_plot_ids_tools, "_plot_table_id", fake_plot_table_id)

    result = server.origin_plot(
        path=str(path),
        kind="bar",
        selected_cols=["x", "y"],
        graph_name="Bar",
    )

    assert result["ok"] is True
    assert calls[0]["plot_type_id"] == 215
    assert calls[0]["template"] == "bar"
    assert calls[0]["selected_cols"] == ["x", "y"]
    assert calls[0]["graph_name"] == "Bar"


def test_origin_plot_rejects_unknown_kind(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")

    result = server.origin_plot(path=str(path), kind="not_a_kind")

    assert result["ok"] is False
    assert result["error_code"] == "invalid_request"
    assert "not_a_kind" in result["message"]


def test_origin_plot_is_in_compact_profile() -> None:
    from origin_mcp.tools._shared import COMPACT_TOOL_NAMES

    assert "origin_plot" in COMPACT_TOOL_NAMES


def test_distribution_wrappers_route_through_plot_type_id(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "distribution.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    calls = []
    legend_calls = []

    def fake_plot_table_id(**kwargs):
        calls.append(kwargs)
        return {
            "ok": True,
            "message": "ok",
            "data": {"graph": {"graph_name": kwargs["graph_name"]}},
        }

    monkeypatch.setattr(plotting_basic_tools, "_plot_table_id", fake_plot_table_id)
    monkeypatch.setattr(
        plotting_basic_tools.client,
        "format_graph",
        lambda **kwargs: legend_calls.append(kwargs) or {"formatted": True},
    )

    histogram = server.origin_plot_histogram(
        str(path),
        x_col="y",
        graph_name="Hist",
        show_legend=False,
    )
    box = server.origin_plot_box(str(path), y_cols=["y", "z"], graph_name="Box")

    assert histogram["ok"] is True
    assert box["ok"] is True
    assert [(call["plot_type_id"], call["template"]) for call in calls] == [
        (219, "hist"),
        (206, "box"),
    ]
    assert calls[0]["selected_cols"] == ["y"]
    assert calls[1]["selected_cols"] == ["y", "z"]
    assert legend_calls == [
        {"graph_name": "Hist", "show_legend": False, "rescale": False},
        {"graph_name": "Box", "show_legend": True, "rescale": False},
    ]


def test_dual_y_wrapper_passes_style_mode(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "dual.csv"
    path.write_text("time,left,right\n0,1,10\n", encoding="utf-8")
    calls = []

    class FakeClient:
        def plot_dual_y(self, **kwargs):
            calls.append(kwargs)
            return (
                WorksheetRef("Book1", "Sheet1", ["time", "left", "right"], 1),
                GraphRef("DualY", template="doubleY", style_mode=kwargs["style_mode"]),
            )

    monkeypatch.setattr(plotting_basic_tools, "client", FakeClient())

    result = server.origin_plot_dual_y(
        path=str(path),
        x_col="time",
        y1_cols=["left"],
        y2_cols=["right"],
        graph_name="DualY",
        style_mode="nature",
    )

    assert result["ok"] is True
    assert calls[0]["style_mode"] == "nature"
    assert result["data"]["graph"]["style_mode"] == "nature"


def test_xyz_3d_wrappers_route_through_plot_type_id(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "xyz.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    calls = []

    def fake_plot_table_id(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "message": "ok", "data": {}}

    monkeypatch.setattr(plotting_basic_tools, "_plot_table_id", fake_plot_table_id)

    scatter = server.origin_plot_3d_scatter(str(path), "x", "y", "z", graph_name="Scatter3D")
    surface = server.origin_plot_3d_surface(str(path), "x", "y", "z", graph_name="Surface3D")

    assert scatter["ok"] is True
    assert surface["ok"] is True
    assert [(call["plot_type_id"], call["template"]) for call in calls] == [
        (240, "3d"),
        (242, "glmesh"),
    ]
    assert all(call["selected_cols"] == ["x", "y", "z"] for call in calls)


# 1x1 transparent PNG, used to exercise origin_view_graph without real Origin.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def test_origin_view_graph_returns_text_and_image_content(monkeypatch) -> None:
    class FakeClient:
        def render_graph_png(self, graph_name=None, max_width=1600):
            self.max_width = max_width
            return {
                "graph_name": graph_name or "active_graph",
                "format": "png",
                "size_bytes": len(_TINY_PNG),
                "width": 1,
                "height": 1,
                "image_base64": base64.b64encode(_TINY_PNG).decode("ascii"),
            }

    monkeypatch.setattr(graph_tools, "client", FakeClient())

    result = server.origin_view_graph(graph_name="G1", max_width=900)

    assert isinstance(result, list) and len(result) == 2
    summary, image = result
    assert summary["ok"] is True
    assert summary["data"]["graph_name"] == "G1"
    assert "image_base64" not in summary["data"]
    assert isinstance(image, Image)
    assert image.data == _TINY_PNG
    assert image._mime_type == "image/png"


def test_origin_view_graph_reports_error_as_content(monkeypatch) -> None:
    class FakeClient:
        def render_graph_png(self, **_kwargs):
            raise OriginOperationError("Graph not found: G9", error_code="graph_not_found")

    monkeypatch.setattr(graph_tools, "client", FakeClient())

    result = server.origin_view_graph(graph_name="G9")

    assert isinstance(result, list) and len(result) == 1
    assert result[0]["ok"] is False
    assert result[0]["error_code"] == "graph_not_found"


def test_origin_view_graph_is_in_compact_profile() -> None:
    from origin_mcp.tools._shared import COMPACT_TOOL_NAMES

    assert "origin_view_graph" in COMPACT_TOOL_NAMES


def test_resolved_server_log_path_is_bridge_sibling(monkeypatch, tmp_path) -> None:
    import origin_mcp.logging_config as lc

    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(tmp_path / "bridge.log"))
    assert lc.resolved_server_log_path() == tmp_path / "server.log"

    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", "-")
    assert lc.resolved_server_log_path() is None


def test_wrap_logs_unexpected_error_traceback_to_server_log(monkeypatch, tmp_path) -> None:
    import logging

    import origin_mcp.logging_config as lc
    from origin_mcp.tools._shared import _wrap

    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(tmp_path / "bridge.log"))
    lc.reset_for_tests()
    try:

        def boom() -> dict:
            raise RuntimeError("kaboom-unexpected")

        result = _wrap(boom)
        for handler in logging.getLogger(lc.TOOLS_LOGGER_NAME).handlers:
            handler.flush()

        server_log = tmp_path / "server.log"
        assert result["ok"] is False
        assert result["error_code"] == "unexpected_error"
        assert server_log.exists()
        text = server_log.read_text(encoding="utf-8")
        assert "kaboom-unexpected" in text
        assert "Traceback (most recent call last)" in text
    finally:
        lc.reset_for_tests()


def test_wrap_does_not_create_server_log_when_disabled(monkeypatch, tmp_path) -> None:
    import origin_mcp.logging_config as lc
    from origin_mcp.errors import OriginOperationError
    from origin_mcp.tools._shared import _wrap

    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", "-")
    lc.reset_for_tests()
    try:
        # Expected, classified errors never reach the unexpected-error log path.
        result = _wrap(lambda: (_ for _ in ()).throw(OriginOperationError("expected")))
        assert result["ok"] is False
        assert not (tmp_path / "server.log").exists()
    finally:
        lc.reset_for_tests()
