from __future__ import annotations

from pathlib import Path
from typing import Any

import origin_mcp.tools.figurespec as figurespec_tools
from origin_mcp.origin_client import GraphRef, WorksheetRef


class FakeFigureSpecClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def new_project(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("new_project", kwargs))
        return {"created": True}

    def plot_table(self, **kwargs: Any) -> tuple[WorksheetRef, GraphRef]:
        self.calls.append(("plot_table", kwargs))
        return (
            WorksheetRef("Book1", "Sheet1", ["time", "response"], 2),
            GraphRef(
                "Graph1",
                export_path=str(kwargs["export_path"]) if kwargs.get("export_path") else None,
                style_mode=kwargs.get("style_mode"),
            ),
        )

    def plot_table_by_id(self, **kwargs: Any) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
        self.calls.append(("plot_table_by_id", kwargs))
        return (
            WorksheetRef("Book1", "Sheet1", ["time", "response", "lo", "hi"], 2),
            GraphRef("Graph1", export_path=str(kwargs.get("export_path") or "")),
            {"plot_type_id": kwargs["plot_type_id"]},
        )

    def set_axis(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("set_axis", kwargs))
        return {
            "axis": kwargs["axis"],
            "graph_name": kwargs.get("graph_name"),
            "layer_index": kwargs.get("layer_index", 0),
        }

    def run_labtalk(self, script: str) -> dict[str, Any]:
        self.calls.append(("run_labtalk", {"script": script}))
        return {"result": True, "script": script}

    def arrange_layers(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("arrange_layers", kwargs))
        return {
            "rows": kwargs["rows"],
            "columns": kwargs["columns"],
            "gap_x": kwargs.get("gap_x"),
            "gap_y": kwargs.get("gap_y"),
            "layer_geometries": kwargs.get("layer_geometries", []),
        }

    def set_graph_page(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("set_graph_page", kwargs))
        return kwargs

    def import_table(self, **kwargs: Any) -> WorksheetRef:
        self.calls.append(("import_table", kwargs))
        return WorksheetRef("Book2", "Sheet1", ["time", "other"], 2)

    def add_plot_to_graph(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("add_plot_to_graph", kwargs))
        return {
            "graph_name": kwargs.get("graph_name"),
            "layer_index": kwargs["layer_index"],
            "plot_type": kwargs["plot_type"],
        }

    def add_uncertainty_band(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("add_uncertainty_band", kwargs))
        return {
            "graph_name": kwargs.get("graph_name"),
            "layer_index": kwargs["layer_index"],
            "lower_col": kwargs["lower_col"],
            "upper_col": kwargs["upper_col"],
        }

    def set_plot_style(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("set_plot_style", kwargs))
        return {
            "graph_name": kwargs.get("graph_name"),
            "layer_index": kwargs.get("layer_index", 0),
            "styled_plots": 1,
        }

    def add_graph_label(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("add_graph_label", kwargs))
        return {"text": kwargs["text"]}

    def format_legend(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("format_legend", kwargs))
        return {"legend": True}

    def add_reference_line(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("add_reference_line", kwargs))
        return {"value": kwargs["value"]}

    def export_graph(self, path: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("export_graph", {"path": path, **kwargs}))
        return {"path": str(path)}

    def inspect_export(self, path: Any) -> dict[str, Any]:
        self.calls.append(("inspect_export", {"path": path}))
        return {"path": str(path), "looks_nonempty": True}

    def diagnose_graph(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("diagnose_graph", kwargs))
        return {"issues": []}

    def save_project(self, path: Any) -> dict[str, Any]:
        self.calls.append(("save_project", {"path": path}))
        return {"path": str(path)}


def _single_line_spec(path: Path, output_dir: Path) -> dict[str, Any]:
    return {
        "figure": {"id": "line_demo", "title": "Line Demo"},
        "runtime": {"new_project": True, "save_project": True},
        "data": [
            {
                "id": "ds_line",
                "source": str(path),
                "roles": {"x": "time", "y": "response"},
            }
        ],
        "page": {"layout": "single"},
        "layers": [
            {
                "id": "panel_a",
                "data_ref": "ds_line",
                "panel_tag": "(a)",
                "x": {"title": "Time (s)", "scale": "linear", "limits": [0, 10]},
                "y": {"title": "Response", "limits": "auto"},
            }
        ],
        "plots": [
            {
                "id": "plot_a",
                "layer": "panel_a",
                "type": "line",
                "map": {"x": "time", "y": "response"},
            }
        ],
        "annotations": [{"id": "legend", "type": "legend", "layer": "panel_a", "frame": False}],
        "style": {"theme": "nature"},
        "export": {
            "dir_figures": str(output_dir / "figures"),
            "dir_opju": str(output_dir / "opju"),
            "png": {"enabled": True},
            "pdf": {"enabled": True},
            "qa": {"require_opju": True, "require_axis_titles": True},
        },
    }


def test_origin_plan_figure_spec_returns_operations(tmp_path: Path) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response\n0,1\n", encoding="utf-8")

    result = figurespec_tools.origin_plan_figure_spec(_single_line_spec(data_path, tmp_path))

    assert result["ok"] is True
    assert result["data"]["executor_executable"] is True
    assert result["data"]["data_validation"]["datasets"][0]["columns"] == ["time", "response"]
    assert [item["op"] for item in result["data"]["operations"]] == [
        "new_project",
        "load_data",
        "configure_layer",
        "plot",
        "annotate",
        "export_graph",
        "export_graph",
        "save_project",
        "qa",
    ]


def test_origin_execute_figure_spec_runs_single_layer_mvp(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response\n0,1\n", encoding="utf-8")
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    result = figurespec_tools.origin_execute_figure_spec(_single_line_spec(data_path, tmp_path))

    assert result["ok"] is True
    assert result["data"]["executed"] is True
    assert result["data"]["graph"]["graph_name"] == "Graph1"
    called = [name for name, _kwargs in fake.calls]
    assert called[:2] == ["new_project", "plot_table"]
    assert "set_axis" in called
    assert "add_graph_label" in called
    assert "format_legend" in called
    assert "export_graph" in called
    assert "diagnose_graph" in called
    assert "save_project" in called
    panel_tag_call = next(
        kwargs
        for name, kwargs in fake.calls
        if name == "add_graph_label" and kwargs["name"] == "panel_a_panel_tag"
    )
    assert panel_tag_call["font_size"] == 18


def test_origin_execute_figure_spec_rejects_missing_columns(tmp_path: Path) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("x,y\n0,1\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)

    result = figurespec_tools.origin_plan_figure_spec(spec)

    assert result["ok"] is False
    assert result["error_code"] == "invalid_request"
    assert "FigureSpec data column validation failed" in result["message"]


def test_origin_execute_figure_spec_runs_grid_multi_panel(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,other\n0,1,2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["page"] = {"layout": "grid"}
    spec["layers"][0]["grid_cell"] = [0, 0]
    spec["layers"].append(
        {
            "id": "panel_b",
            "data_ref": "ds_line",
            "panel_tag": "(b)",
            "grid_cell": [0, 1],
            "x": {"title": "Time (s)", "limits": "auto"},
            "y": {"title": "Other", "limits": "auto"},
        }
    )
    spec["plots"].append(
        {
            "id": "plot_b",
            "layer": "panel_b",
            "type": "scatter",
            "map": {"x": "time", "y": "other"},
        }
    )
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert result["ok"] is True
    assert result["data"]["executed"] is True
    assert result["data"]["layer_setup"]["added_layers"] == 1
    assert result["data"]["layer_setup"]["arranged"]["rows"] == 1
    assert result["data"]["layer_setup"]["arranged"]["columns"] == 2
    assert result["data"]["added_plots"][0]["plot_id"] == "plot_b"
    axis_calls = [kwargs for name, kwargs in fake.calls if name == "set_axis"]
    assert {
        "graph_name": "Graph1",
        "layer_index": 1,
        "axis": "x",
        "scale": None,
        "start": None,
        "end": None,
        "step": None,
        "title": "Time (s)",
    } in axis_calls
    assert {
        "graph_name": "Graph1",
        "layer_index": 1,
        "axis": "y",
        "scale": None,
        "start": None,
        "end": None,
        "step": None,
        "title": "Other",
    } in axis_calls
    called = [name for name, _kwargs in fake.calls]
    assert "run_labtalk" in called
    assert "arrange_layers" in called
    assert "add_plot_to_graph" in called


def test_origin_execute_figure_spec_runs_custom_layout_with_spans(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,other,third\n0,1,2,3\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["page"] = {
        "layout": "custom",
        "size_mm": [180, 120],
        "margins_mm": [18, 12, 12, 10],
        "panel_spacing_mm": [6, 8],
    }
    spec["layers"][0]["grid_cell"] = [0, 0]
    spec["layers"][0]["grid_span"] = [1, 2]
    spec["layers"].extend(
        [
            {
                "id": "panel_b",
                "data_ref": "ds_line",
                "grid_cell": [1, 0],
                "x": {"title": "Time (s)", "limits": "auto"},
                "y": {"title": "Other", "limits": "auto"},
            },
            {
                "id": "panel_c",
                "data_ref": "ds_line",
                "grid_cell": [1, 1],
                "x": {"title": "Time (s)", "limits": "auto"},
                "y": {"title": "Third", "limits": "auto"},
            },
        ]
    )
    spec["plots"].extend(
        [
            {
                "id": "plot_b",
                "layer": "panel_b",
                "type": "scatter",
                "map": {"x": "time", "y": "other"},
            },
            {
                "id": "plot_c",
                "layer": "panel_c",
                "type": "line",
                "map": {"x": "time", "y": "third"},
            },
        ]
    )
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    plan = figurespec_tools.origin_plan_figure_spec(spec)
    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert plan["ok"] is True
    assert plan["data"]["executor_executable"] is True
    ops = [item["op"] for item in plan["data"]["operations"]]
    assert "set_graph_page" in ops
    arrange_op = next(item for item in plan["data"]["operations"] if item["op"] == "arrange_layers")
    assert arrange_op["rows"] == 2
    assert arrange_op["columns"] == 2
    assert round(arrange_op["gap_x"], 3) == 3.333
    assert round(arrange_op["gap_y"], 3) == 6.667
    assert arrange_op["layer_geometries"][0]["layer_index"] == 0
    assert round(arrange_op["layer_geometries"][0]["width"], 3) == 83.333
    assert result["ok"] is True
    assert result["data"]["layer_setup"]["page"]["unit"] == "inch"
    assert round(result["data"]["layer_setup"]["page"]["width"], 3) == 7.087
    arrange_call = next(kwargs for name, kwargs in fake.calls if name == "arrange_layers")
    assert len(arrange_call["layer_geometries"]) == 3
    assert (
        arrange_call["layer_geometries"][0]["width"] > arrange_call["layer_geometries"][1]["width"]
    )


def test_origin_plan_figure_spec_requires_absolute_position(tmp_path: Path) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response\n0,1\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["page"] = {"layout": "custom"}
    spec["layers"][0]["position_mode"] = "absolute"

    result = figurespec_tools.origin_plan_figure_spec(spec)

    assert result["ok"] is True
    assert result["data"]["executor_executable"] is False
    assert result["data"]["warnings"] == ["executor_requires_absolute_layer_position"]
    detail = result["data"]["warning_details"][0]
    assert detail["field"] == "layers.position"
    assert detail["missing_keys"] == ["left", "top", "width", "height"]


def test_origin_execute_figure_spec_runs_absolute_custom_layout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,other\n0,1,2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["page"] = {"layout": "custom", "size_mm": [160, 100]}
    spec["layers"][0]["position_mode"] = "absolute"
    spec["layers"][0]["position"] = {"left": 12, "top": 10, "width": 76, "height": 35}
    spec["layers"].append(
        {
            "id": "panel_b",
            "data_ref": "ds_line",
            "position_mode": "absolute",
            "position": {"left": 12, "top": 55, "width": 76, "height": 35},
            "x": {"title": "Time (s)", "limits": "auto"},
            "y": {"title": "Other", "limits": "auto"},
        }
    )
    spec["plots"].append(
        {
            "id": "plot_b",
            "layer": "panel_b",
            "type": "scatter",
            "map": {"x": "time", "y": "other"},
        }
    )
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert result["ok"] is True
    arrange_call = next(kwargs for name, kwargs in fake.calls if name == "arrange_layers")
    assert arrange_call["layer_geometries"] == [
        {"layer_index": 0, "left": 12.0, "top": 10.0, "width": 76.0, "height": 35.0},
        {"layer_index": 1, "left": 12.0, "top": 55.0, "width": 76.0, "height": 35.0},
    ]


def test_origin_execute_figure_spec_applies_combo_plot_styles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("month,y2020,y2021,mean\n1,10,12,11\n2,20,24,22\n", encoding="utf-8")
    spec = {
        "figure": {"id": "combo_demo", "title": "Combo Demo"},
        "data": [
            {
                "id": "rain",
                "source": str(data_path),
                "roles": {"x": "month"},
            }
        ],
        "layers": [
            {
                "id": "panel",
                "data_ref": "rain",
                "x": {"title": "Month"},
                "y": {"title": "Rainfall"},
            }
        ],
        "plots": [
            {
                "id": "bars",
                "layer": "panel",
                "type": "column",
                "map": {"x": "month", "y": ["y2020", "y2021"]},
                "style": {"bar_gap": 80},
            },
            {
                "id": "mean",
                "layer": "panel",
                "type": "line",
                "map": {"x": "month", "y": "mean"},
                "style": {"line_width": 1.2, "color": "black"},
            },
        ],
    }
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert result["ok"] is True
    style_calls = [kwargs for name, kwargs in fake.calls if name == "set_plot_style"]
    assert style_calls == [
        {"graph_name": "Graph1", "layer_index": 0, "plot_index": 0, "bar_gap": 80},
        {"graph_name": "Graph1", "layer_index": 0, "plot_index": 1, "bar_gap": 80},
        {
            "graph_name": "Graph1",
            "layer_index": 0,
            "plot_index": 2,
            "color": "black",
            "line_width": 1.2,
        },
    ]


def test_origin_execute_figure_spec_maps_uncertainty_to_error_columns(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,se\n0,1,0.1\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["data"][0]["roles"] = {"x": "time", "y": "response"}
    spec["plots"][0]["uncertainty"] = {"type": "errorbar", "y_error": "se"}
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    plan = figurespec_tools.origin_plan_figure_spec(spec)
    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert plan["ok"] is True
    assert plan["data"]["executor_executable"] is True
    plot_op = next(item for item in plan["data"]["operations"] if item["op"] == "plot")
    assert plot_op["uncertainty_mapping"] == {"y_error": "se"}
    assert plot_op["uncertainty_supported"] is True
    assert result["ok"] is True
    plot_call = next(kwargs for name, kwargs in fake.calls if name == "plot_table")
    assert plot_call["y_error_col"] == "se"


def test_origin_execute_figure_spec_adds_uncertainty_band(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,lo,hi\n0,1,0.8,1.2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["plots"][0]["uncertainty"] = {
        "type": "band",
        "lower": "lo",
        "upper": "hi",
        "fill_color": "lightblue",
        "transparency": 65,
    }
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    plan = figurespec_tools.origin_plan_figure_spec(spec)
    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert plan["ok"] is True
    assert plan["data"]["executor_executable"] is True
    assert plan["data"]["warnings"] == []
    plot_op = next(item for item in plan["data"]["operations"] if item["op"] == "plot")
    assert plot_op["uncertainty_mapping"] == {"lower": "lo", "upper": "hi"}
    assert plot_op["uncertainty_style"] == {"fill_color": "lightblue", "transparency": 65}
    assert plot_op["uncertainty_supported"] is True
    assert result["ok"] is True
    assert result["data"]["executed"] is True
    assert result["data"]["band_updates"] == [
        {
            "plot_id": "plot_a",
            "graph_name": "Graph1",
            "layer_index": 0,
            "mode": "native_fillarea_base",
            "lower_col": "lo",
            "upper_col": "hi",
            "plot_indices": [0, 1],
            "fill_color": "lightblue",
            "transparency": 65,
        }
    ]
    fillarea_call = next(kwargs for name, kwargs in fake.calls if name == "plot_table_by_id")
    assert fillarea_call["plot_type_id"] == 249
    assert fillarea_call["template"] == "fillarea"
    assert fillarea_call["selected_cols"] == [
        "__origin_mcp_band_x",
        "__origin_mcp_band_lower",
        "__origin_mcp_band_upper",
    ]
    assert str(fillarea_call["path"]).endswith("line_demo_plot_a_band.csv")
    assert fillarea_call["export_path"] is None
    labtalk_call = next(
        kwargs
        for name, kwargs in fake.calls
        if name == "run_labtalk" and "-pfv 9" in kwargs["script"]
    )
    assert "set __origin_mcp_band_plot -paap 65;" in labtalk_call["script"]
    line_call = next(kwargs for name, kwargs in fake.calls if name == "add_plot_to_graph")
    assert line_call == {
        "worksheet": "[Book1]Sheet1",
        "x_col": "__origin_mcp_band_x",
        "y_col": "__origin_mcp_band_y",
        "graph_name": "Graph1",
        "layer_index": 0,
        "plot_type": "line",
        "z_col": None,
        "y_error_col": None,
        "x_error_col": None,
    }
    legend_call = next(kwargs for name, kwargs in fake.calls if name == "format_legend")
    assert legend_call["text"] == "\\l(3) response"
    export_call = next(kwargs for name, kwargs in fake.calls if name == "export_graph")
    assert str(export_call["path"]).endswith("line_demo.png")
    assert export_call["graph_name"] == "Graph1"


def test_origin_plan_figure_spec_requires_band_bounds(tmp_path: Path) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,lo\n0,1,0.8\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["plots"][0]["uncertainty"] = {"type": "band", "lower": "lo"}

    result = figurespec_tools.origin_plan_figure_spec(spec)

    assert result["ok"] is True
    assert result["data"]["executor_executable"] is False
    assert result["data"]["warnings"] == ["executor_does_not_apply_uncertainty_bands"]
    assert result["data"]["warning_details"] == [
        {
            "code": "executor_does_not_apply_uncertainty_bands",
            "plot_id": "plot_a",
            "field": "uncertainty",
            "unsupported_keys": ["upper"],
            "supported_alternatives": ["uncertainty.y_error", "uncertainty.x_error"],
        }
    ]
    plot_op = next(item for item in result["data"]["operations"] if item["op"] == "plot")
    assert plot_op["uncertainty_supported"] is False
    assert plot_op["uncertainty_unsupported_keys"] == ["upper"]


def test_origin_execute_figure_spec_supports_non_base_band(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,other,lo,hi\n0,1,2,0.8,1.2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["plots"].append(
        {
            "id": "plot_b",
            "layer": "panel_a",
            "type": "line",
            "map": {"x": "time", "y": "other"},
            "uncertainty": {"type": "band", "lower": "lo", "upper": "hi"},
        }
    )
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    plan = figurespec_tools.origin_plan_figure_spec(spec)
    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert plan["ok"] is True
    assert plan["data"]["executor_executable"] is True
    assert plan["data"]["warnings"] == []
    plot_op = next(
        item
        for item in plan["data"]["operations"]
        if item["op"] == "plot" and item["id"] == "plot_b"
    )
    assert plot_op["uncertainty_supported"] is True
    assert result["ok"] is True
    assert result["data"]["band_updates"] == [
        {
            "plot_id": "plot_b",
            "graph_name": "Graph1",
            "layer_index": 0,
            "lower_col": "lo",
            "upper_col": "hi",
        }
    ]
    call_names = [name for name, _kwargs in fake.calls]
    assert call_names.index("add_uncertainty_band") < call_names.index("add_plot_to_graph")
    band_call = next(kwargs for name, kwargs in fake.calls if name == "add_uncertainty_band")
    assert band_call == {
        "worksheet": "[Book1]Sheet1",
        "x_col": "time",
        "lower_col": "lo",
        "upper_col": "hi",
        "graph_name": "Graph1",
        "layer_index": 0,
    }
    legend_call = next(kwargs for name, kwargs in fake.calls if name == "format_legend")
    assert legend_call["text"] == "\\l(1) response\n\\l(4) other"


def test_origin_execute_figure_spec_uses_source_data_for_plots_after_base_band(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response,other,lo,hi\n0,1,2,0.8,1.2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["plots"][0]["uncertainty"] = {"type": "band", "lower": "lo", "upper": "hi"}
    spec["plots"].append(
        {
            "id": "plot_b",
            "layer": "panel_a",
            "type": "line",
            "map": {"x": "time", "y": "other"},
        }
    )
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert result["ok"] is True
    import_call = next(kwargs for name, kwargs in fake.calls if name == "import_table")
    assert import_call["path"] == data_path
    added_call = [
        kwargs
        for name, kwargs in fake.calls
        if name == "add_plot_to_graph" and kwargs["y_col"] == "other"
    ][0]
    assert added_call["worksheet"] == "[Book2]Sheet1"


def test_origin_execute_figure_spec_applies_group_style_sequences(
    monkeypatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,a,b\n0,1,2\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["data"][0]["roles"] = {"x": "time", "y": ["a", "b"]}
    spec["plots"][0]["map"] = {"x": "time", "y": ["a", "b"]}
    spec["plots"][0]["group_style"] = {
        "colors": ["red", "blue"],
        "line_widths": [1.0, 2.0],
    }
    fake = FakeFigureSpecClient()
    monkeypatch.setattr(figurespec_tools, "client", fake)

    plan = figurespec_tools.origin_plan_figure_spec(spec)
    result = figurespec_tools.origin_execute_figure_spec(spec)

    assert plan["ok"] is True
    assert plan["data"]["executor_executable"] is True
    plot_op = next(item for item in plan["data"]["operations"] if item["op"] == "plot")
    assert plot_op["group_style_supported"] is True
    assert plot_op["group_style_unsupported_keys"] == []
    assert result["ok"] is True
    style_calls = [kwargs for name, kwargs in fake.calls if name == "set_plot_style"]
    assert style_calls[:2] == [
        {
            "graph_name": "Graph1",
            "layer_index": 0,
            "plot_index": 0,
            "color": "red",
            "line_width": 1.0,
        },
        {
            "graph_name": "Graph1",
            "layer_index": 0,
            "plot_index": 1,
            "color": "blue",
            "line_width": 2.0,
        },
    ]


def test_origin_plan_figure_spec_reports_unsupported_group_style_details(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("time,response\n0,1\n", encoding="utf-8")
    spec = _single_line_spec(data_path, tmp_path)
    spec["plots"][0]["group_style"] = {"dash_patterns": ["solid", "dash"]}

    result = figurespec_tools.origin_plan_figure_spec(spec)

    assert result["ok"] is True
    assert result["data"]["executor_executable"] is False
    assert result["data"]["warnings"] == ["executor_does_not_apply_group_style"]
    detail = result["data"]["warning_details"][0]
    assert detail["code"] == "executor_does_not_apply_group_style"
    assert detail["plot_id"] == "plot_a"
    assert detail["field"] == "group_style"
    assert detail["unsupported_keys"] == ["dash_patterns"]
    assert "colors" in detail["supported_keys"]
    plot_op = next(item for item in result["data"]["operations"] if item["op"] == "plot")
    assert plot_op["group_style_supported"] is False
    assert plot_op["group_style_unsupported_keys"] == ["dash_patterns"]
