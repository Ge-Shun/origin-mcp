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
            WorksheetRef("Book1", "Sheet1", ["x", "y", "z"], 2),
            GraphRef("Heat", export_path=str(kwargs.get("export_path") or "")),
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
        return {"rows": kwargs["rows"], "columns": kwargs["columns"]}

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
    assert result["data"]["layer_setup"]["arranged"] == {"rows": 1, "columns": 2}
    assert result["data"]["added_plots"][0]["plot_id"] == "plot_b"
    called = [name for name, _kwargs in fake.calls]
    assert "run_labtalk" in called
    assert "arrange_layers" in called
    assert "add_plot_to_graph" in called
