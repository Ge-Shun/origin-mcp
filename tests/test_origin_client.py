import os
import struct
import zlib
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from origin_mcp.chart_palette import normalize_palette_name, palette_catalog
from origin_mcp.compat import PLOT_TYPE_CATALOG
from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import GraphRef, OriginClient, WorksheetRef


def test_read_table_csv(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("time,value\n0,1\n1,2\n", encoding="utf-8")

    df = OriginClient._read_table(path)

    assert list(df.columns) == ["time", "value"]
    assert df["value"].tolist() == [1, 2]


def test_read_table_tsv(tmp_path: Path) -> None:
    path = tmp_path / "data.tsv"
    path.write_text("time\tvalue\n0\t1\n1\t2\n", encoding="utf-8")

    df = OriginClient._read_table(path)

    assert list(df.columns) == ["time", "value"]
    assert df["time"].tolist() == [0, 1]


def test_read_table_excel(tmp_path: Path) -> None:
    path = tmp_path / "data.xlsx"
    expected = pd.DataFrame({"time": [0, 1], "value": [1.5, 2.5]})
    expected.to_excel(path, index=False, sheet_name="Run1")

    df = OriginClient._read_table(path, excel_sheet="Run1")

    assert list(df.columns) == ["time", "value"]
    assert df["value"].tolist() == [1.5, 2.5]


def test_read_table_rejects_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(OriginOperationError):
        OriginClient._read_table(path)


def test_read_table_custom_delimiter_and_skiprows(tmp_path: Path) -> None:
    path = tmp_path / "data.txt"
    path.write_text("# comment\nx;value\n0;1\n1;2\n", encoding="utf-8")

    df = OriginClient._read_table(path, delimiter=";", skiprows=1)

    assert list(df.columns) == ["x", "value"]
    assert df["value"].tolist() == [1, 2]


def test_allowed_roots_blocks_paths_outside_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    blocked = tmp_path / "blocked.csv"
    blocked.write_text("x,y\n1,2\n", encoding="utf-8")
    monkeypatch.setenv("ORIGIN_MCP_ALLOWED_ROOTS", str(allowed))

    with pytest.raises(OriginOperationError):
        OriginClient._validate_file(blocked)


def test_normalize_user_path_blocks_paths_outside_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    blocked = tmp_path / "outside"
    monkeypatch.setenv("ORIGIN_MCP_ALLOWED_ROOTS", str(allowed))

    with pytest.raises(OriginOperationError) as excinfo:
        OriginClient._normalize_user_path(blocked)
    assert excinfo.value.error_code == "path_not_allowed"


def test_normalize_user_path_resolves_and_returns_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ORIGIN_MCP_ALLOWED_ROOTS", raising=False)
    relative = tmp_path / "sub" / ".." / "child.txt"

    resolved = OriginClient._normalize_user_path(relative)
    assert resolved == (tmp_path / "child.txt").resolve()


def test_connect_records_set_show_warning() -> None:
    client = OriginClient()

    class FakeOrigin:
        def set_show(self, _show: bool) -> None:
            raise SystemError("bad automation state")

    client._op = FakeOrigin()

    result = client.connect(show=True)

    assert result["connected"] is True
    assert result["show_set"] is False
    assert "bad automation state" in result["show_warning"]


def test_new_project_wraps_automation_failure() -> None:
    client = OriginClient()

    class FakeOrigin:
        def set_show(self, _show: bool) -> None:
            return None

        def new(self) -> None:
            raise SystemError("bad automation state")

    client._op = FakeOrigin()

    with pytest.raises(OriginOperationError, match="create a new project"):
        client.new_project()


def test_save_project_falls_back_to_pe_save_on_originpro_save_failure(
    tmp_path: Path,
) -> None:
    client = OriginClient()
    scripts = []

    class FakeOrigin:
        def save(self, _path: str) -> None:
            raise SystemError("bad automation state")

        def lt_exec(self, script: str) -> bool:
            scripts.append(script)
            return True

    client._op = FakeOrigin()

    result = client.save_project(tmp_path / "saved.opju")

    assert result["saved"] is True
    assert result["method"] == "labtalk.pe_save"
    assert result["fallback_error"].startswith("SystemError:")
    expected_path = OriginClient._escape_labtalk(str(tmp_path / "saved.opju"))
    assert scripts == [f'pe_save fname:="{expected_path}";']


def test_analysis_script_linear_fit() -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,force)"  # type: ignore[method-assign]
    script = client._analysis_script(
        analysis="linear_fit",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="force",
        output_sheet="FitOut",
        options={"intercept": False},
    )

    assert "fitlr iy:=[Book1]Sheet1!(time,force)" in script
    assert "oy:=FitOut" in script
    assert "fixintercept:=0" in script


def test_analysis_script_requires_range() -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}

    with pytest.raises(OriginOperationError, match="requires an input range"):
        client._analysis_script("smooth", None, None, None, None, {})


def test_run_analysis_marks_false_labtalk_result() -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,signal)"  # type: ignore[method-assign]
    client.run_labtalk = lambda _script: {"result": False}  # type: ignore[method-assign]

    result = client.run_analysis(
        analysis="smooth",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="signal",
    )

    assert result["executed"] is False
    assert "warning" in result
    assert result["parameters"] == []
    assert result["metrics"] == {}
    assert result["warnings"] == ["Origin returned false for this analysis command."]


def test_run_analysis_reads_output_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,signal)"  # type: ignore[method-assign]
    client.run_labtalk = lambda _script: {"result": True}  # type: ignore[method-assign]
    monkeypatch.setattr(
        client,
        "_analysis_output",
        lambda output_sheet, max_rows: {"output_sheet": output_sheet, "max_rows": max_rows},
    )
    monkeypatch.setattr(
        client,
        "_prepare_analysis_xy_output",
        lambda output_sheet: f"[{output_sheet}]Result!(1,2)",
    )

    result = client.run_analysis(
        analysis="smooth",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="signal",
        output_sheet="SmoothOut",
        include_output=True,
        output_max_rows=5,
    )

    assert result["executed"] is True
    assert result["output_target"] == "[SmoothOut]Result!(1,2)"
    assert "oy:=[SmoothOut]Result!(1,2)" in result["script"]
    assert result["output"] == {"output_sheet": "SmoothOut", "max_rows": 5}
    assert result["parameters"] == []
    assert result["metrics"] == {}
    assert result["warnings"] == []


def test_run_analysis_structures_polynomial_output(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,signal)"  # type: ignore[method-assign]
    client.run_labtalk = lambda _script: {"result": True}  # type: ignore[method-assign]
    monkeypatch.setattr(
        client,
        "_analysis_output",
        lambda _output_sheet, _max_rows: {
            "rows": [
                {"Parameter": "Intercept", "Value": 1.0, "Standard Error": 0.1},
                {"Parameter": "B1", "Value": 2.0},
                {"Parameter": "RSquare", "Value": 0.99},
            ],
        },
    )
    monkeypatch.setattr(
        client,
        "_prepare_analysis_xy_output",
        lambda output_sheet: f"[{output_sheet}]Result!(1,2)",
    )
    monkeypatch.setattr(
        client,
        "_polynomial_output_variables",
        lambda: {
            "coef": "coefVec",
            "err": "errVec",
            "N": "nVal",
            "AdjRSq": "adjVal",
            "RSqCOD": "rsqVal",
        },
    )
    values = {
        "coefVec[1]": 1.0,
        "coefVec[2]": 2.0,
        "errVec[1]": 0.1,
        "errVec[2]": 0.2,
        "nVal": 7,
        "adjVal": 0.98,
        "rsqVal": 0.99,
    }
    monkeypatch.setattr(client, "_safe_eval", lambda expression: values.get(expression))

    result = client.run_analysis(
        analysis="polynomial_fit",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="signal",
        output_sheet="PolyOut",
        options={"order": 1},
        include_output=True,
    )

    assert result["analysis"] == "polynomial_fit"
    assert "oy:=[PolyOut]Result!(1,2)" in result["script"]
    assert "coef:=coefVec" in result["script"]
    assert "RSqCOD:=rsqVal" in result["script"]
    assert {"name": "Intercept", "path": "coefVec[1]", "value": 1.0, "stderr": 0.1} in result[
        "parameters"
    ]
    assert {"name": "B1", "path": "coefVec[2]", "value": 2.0, "stderr": 0.2} in result["parameters"]
    assert result["metrics"]["RSquare"] == 0.99
    assert result["metrics"]["RSqCOD"] == 0.99


def test_run_analysis_structures_moments_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(signal)"  # type: ignore[method-assign]
    captured = {}

    def fake_run_labtalk(script: str):
        captured["script"] = script
        return {"result": True}

    monkeypatch.setattr(client, "run_labtalk", fake_run_labtalk)
    monkeypatch.setattr(
        client,
        "_moments_output_variables",
        lambda: {
            "mean": "meanVar",
            "sd": "sdVar",
            "se": "seVar",
            "n": "nVar",
            "sum": "sumVar",
            "skewness": "skewVar",
            "kurtosis": "kurtVar",
            "cv": "cvVar",
        },
    )
    values = {
        "meanVar": 10.5,
        "sdVar": 2.0,
        "seVar": 0.5,
        "nVar": 16,
        "sumVar": 168.0,
        "skewVar": 0.1,
        "kurtVar": -1.2,
        "cvVar": 0.19,
    }
    monkeypatch.setattr(client, "_safe_eval", lambda expression: values.get(expression))

    result = client.run_analysis(
        analysis="descriptive_stats",
        worksheet="[Book1]Sheet1",
        y_col="signal",
        output_sheet="StatsOut",
    )

    assert "moments ix:=[Book1]Sheet1!(signal)" in captured["script"]
    assert "oy:=" not in captured["script"]
    assert "mean:=meanVar" in captured["script"]
    assert result["metrics"]["Mean"] == 10.5
    assert result["metrics"]["StandardDeviation"] == 2.0
    assert result["metrics"]["N"] == 16
    assert result["metrics"]["Sum"] == 168.0
    assert result["metrics"]["CoefficientOfVariation"] == 0.19


def test_run_analysis_prepares_xy_output_for_differentiate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,signal)"  # type: ignore[method-assign]
    client.run_labtalk = lambda _script: {"result": True}  # type: ignore[method-assign]
    monkeypatch.setattr(
        client,
        "_prepare_analysis_xy_output",
        lambda output_sheet: f"[{output_sheet}]Result!(1,2)",
    )

    result = client.run_analysis(
        analysis="differentiate",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="signal",
        output_sheet="DiffOut",
    )

    assert result["output_target"] == "[DiffOut]Result!(1,2)"
    assert "oy:=[DiffOut]Result!(1,2)" in result["script"]


def test_run_analysis_prepares_peak_find_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3, "features": {}}
    client._analysis_range = lambda *_args: "[Book1]Sheet1!(time,signal)"  # type: ignore[method-assign]
    client.run_labtalk = lambda _script: {"result": True}  # type: ignore[method-assign]
    monkeypatch.setattr(
        client,
        "_prepare_peak_find_outputs",
        lambda output_sheet: {
            "worksheet": f"[{output_sheet}]Peaks",
            "ocenter": f"[{output_sheet}]Peaks!(1)",
            "ocenter_x": f"[{output_sheet}]Peaks!(2)",
            "ocenter_y": f"[{output_sheet}]Peaks!(3)",
        },
    )

    result = client.run_analysis(
        analysis="peak_find",
        worksheet="[Book1]Sheet1",
        x_col="time",
        y_col="signal",
        output_sheet="PeakOut",
    )

    assert result["output_target"] == "[PeakOut]Peaks"
    assert "oy:=" not in result["script"]
    assert "ocenter:=[PeakOut]Peaks!(1)" in result["script"]
    assert "ocenter_x:=[PeakOut]Peaks!(2)" in result["script"]
    assert "ocenter_y:=[PeakOut]Peaks!(3)" in result["script"]


def test_structure_fit_result_extracts_parameters_and_metrics() -> None:
    client = OriginClient()

    structured = client._structure_fit_result(
        {
            "Parameters": {"Slope": 2.0, "Intercept": 1.0},
            "Statistics": {"RSquare": 0.99},
        }
    )

    assert {"name": "Slope", "path": "Parameters.Slope", "value": 2.0} in structured["parameters"]
    assert structured["metrics"]["RSquare"] == 0.99


def test_origin_name_matches_truncated_short_name() -> None:
    assert OriginClient._origin_name_matches("OfficialImport", {"OfficialImpor"})
    assert OriginClient._origin_name_matches("Book1", {"Book1"})
    assert not OriginClient._origin_name_matches("OtherBook", {"Book1"})


def test_origin_name_matches_rejects_short_prefix_collisions() -> None:
    # Short, unrelated short names must not collide via prefix matching: this is
    # the "Tr"/"Trans" vs existing "T" workbook-reuse bug.
    assert not OriginClient._origin_name_matches("Trans", {"T"})
    assert not OriginClient._origin_name_matches("Tr", {"T"})
    assert not OriginClient._origin_name_matches("T", {"Trans"})
    assert not OriginClient._origin_name_matches("Spectrum2", {"Spectrum"})
    assert not OriginClient._origin_name_matches("Data2", {"Data"})
    # Exact matches (case-insensitive) still resolve, even alongside a prefix book.
    assert OriginClient._origin_name_matches("trans", {"T", "Trans"})


def test_find_sheet_from_ref_falls_back_to_output_book_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"fit": [1]}))

    class OutputBook:
        name = "Book2"
        lname = "SmokeSmooth"

        def __iter__(self):
            return iter([wks])

        def __getitem__(self, index: int) -> FakeWorksheet:
            if index != 0:
                raise IndexError(index)
            return wks

    class FakeOrigin:
        def find_sheet(self, _kind: str, _ref: str) -> None:
            return None

        def pages(self, _kind: str) -> list[OutputBook]:
            return [OutputBook()]

    monkeypatch.setattr(client, "_op", FakeOrigin())

    assert client._find_sheet_from_ref("SmokeSmooth") is wks


def test_prepare_analysis_xy_output_converts_sheet_ref() -> None:
    client = OriginClient()

    assert client._prepare_analysis_xy_output("[Book1]Result") == "[Book1]Result!(1,2)"
    assert client._prepare_analysis_xy_output("[Book1]Result!(3,4)") == "[Book1]Result!(3,4)"


def test_ensure_feature_reports_detected_version() -> None:
    client = OriginClient()
    client._capabilities = {
        "origin_version": 9.5,
        "features": {
            "graph_list": {
                "available": False,
                "minimum_origin_version": None,
                "note": "Required for export all graphs.",
            }
        },
    }

    with pytest.raises(OriginOperationError, match="Detected Origin version: 9.5"):
        client.ensure_feature("graph_list", "Batch graph export")


def test_detach_clears_cached_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    client._capabilities = {"origin_version": 10.3}

    class FakeOrigin:
        def detach(self) -> None:
            return None

    monkeypatch.setattr(client, "_op", FakeOrigin())

    result = client.detach()

    assert result == {"detached": True, "closed": False}
    assert client._capabilities is None
    assert client._op is None


class FakeBook:
    name = "Book1"
    lname = "Book1"


class FakeWorksheet:
    name = "Sheet1"
    lname = "Sheet1"

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        self.df = df if df is not None else pd.DataFrame()
        self.rows = len(self.df)
        self.cols = len(self.df.columns)

    def get_book(self) -> FakeBook:
        return FakeBook()

    def to_df(self) -> pd.DataFrame:
        return self.df.copy()

    def from_df(self, df: pd.DataFrame, c1: str | int = 0) -> None:
        self.df = df.copy()
        self.rows = len(df)
        self.cols = len(df.columns)
        self.start_col = c1

    def get_labels(self, label_type: str) -> list[str]:
        if label_type == "L":
            return [str(column) for column in self.df.columns]
        if label_type == "U":
            return ["s", "N"][: len(self.df.columns)]
        return []

    def set_labels(self, labels: list[str], label_type: str, offset: int = 0) -> None:
        self.labels = {"labels": labels, "label_type": label_type, "offset": offset}


def test_read_worksheet_returns_window_and_nulls(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"time": [0, 1, 2], "force": [1.0, None, 3.0]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.read_worksheet(start_row=1, max_rows=2)

    assert result["columns"] == ["time", "force"]
    assert result["returned_rows"] == 2
    assert result["rows"][0] == {"time": 1, "force": None}


def test_write_worksheet_uses_rows_and_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet()
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.write_worksheet(
        rows=[[1, 2], [3, 4]],
        columns=["x", "y"],
        start_col=1,
    )

    assert result["worksheet"]["columns"] == ["x", "y"]
    assert wks.df["y"].tolist() == [2, 4]
    assert wks.start_col == 1


def test_worksheet_info_returns_label_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"time": [0], "force": [1]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.worksheet_info(label_types=["L", "U"])

    assert result["columns_count"] == 2
    assert result["labels"]["L"] == ["time", "force"]
    assert result["labels"]["U"] == ["s", "N"]


class FakeGraph:
    name = "Graph1"

    def __init__(self, layer: "FakeLayer | list[FakeLayer] | None" = None) -> None:
        self.layers = layer if isinstance(layer, list) else ([layer] if layer is not None else [])
        self.layer = self.layers[0] if self.layers else None
        self.lname = ""

    def __len__(self) -> int:
        return len(self.layers)

    def __getitem__(self, index: int) -> "FakeLayer":
        try:
            return self.layers[index]
        except IndexError as exc:
            raise IndexError(index) from exc


class GPage(FakeGraph):
    pass


class FakePlot:
    name = "Plot1"

    def __init__(self) -> None:
        self.commands = []
        self.removed = False
        self.symbol_size = 0
        self.line_width = None
        self.bar_gap = None
        self.width = None

    def set_cmd(self, command: str) -> None:
        self.commands.append(command)

    def remove(self) -> None:
        self.removed = True


class FakeAxis:
    def __init__(self) -> None:
        self.title = "Axis"
        self.scale = "linear"
        self.limits = None


class FakeLabel:
    name = "Label1"

    def __init__(self, text: str) -> None:
        self.text = text
        self.removed = False
        self.properties = {}

    def remove(self) -> None:
        self.removed = True

    def set_int(self, name: str, value: int) -> None:
        self.properties[name] = value


class FakeLayer:
    name = "Layer1"

    def __init__(self, plots: list[FakePlot] | None = None) -> None:
        self.plots = plots if plots is not None else []
        self.added = []
        self.labels = {}
        self.axes = {"x": FakeAxis(), "y": FakeAxis(), "z": FakeAxis()}
        self.group_calls = 0

    def plot_list(self) -> list[FakePlot]:
        return self.plots

    def axis(self, name: str) -> FakeAxis:
        return self.axes[name]

    def add_plot(self, wks: FakeWorksheet, **kwargs: object) -> None:
        self.added.append((wks, kwargs))
        self.plots.append(FakePlot())

    def add_label(self, text: str) -> FakeLabel:
        label = FakeLabel(text)
        label.name = f"Label{len(self.labels) + 1}"
        self.labels[label.name] = label
        return label

    def label(self, name: str) -> FakeLabel | None:
        return self.labels.get(name)

    def group(self) -> None:
        self.group_calls += 1


def test_set_graph_page_updates_fake_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    graph = FakeGraph()
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.set_graph_page(graph_name="Graph1", width=6.0, height=4.0)

    assert result["page"]["width"] == 6.0
    assert graph.width == 6.0
    assert graph.height == 4.0


def test_get_set_cell_and_delete_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"time": [0, 1], "force": [2, 3], "drop": [9, 9]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    assert client.get_cell_value(1, "force")["value"] == 3
    updated = client.set_cell_value(0, "force", 5)
    deleted = client.delete_columns(["drop"])

    assert updated["value"] == 5
    assert wks.df["force"].tolist() == [5, 3]
    assert deleted["deleted_columns"] == ["drop"]
    assert list(wks.df.columns) == ["time", "force"]


def test_export_worksheet_csv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [1], "y": [2]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)
    path = tmp_path / "out.csv"

    result = client.export_worksheet_csv(path)

    assert result["rows"] == 1
    assert path.read_text(encoding="utf-8").startswith("x,y")


def test_list_graph_templates_scans_directory(tmp_path: Path) -> None:
    (tmp_path / "journal.otpu").write_text("placeholder", encoding="utf-8")

    result = OriginClient().list_graph_templates(tmp_path)

    assert "line" in result["builtin"]
    assert result["discovered"] == [{"name": "journal", "path": str(tmp_path / "journal.otpu")}]


def test_get_graph_info_reports_layers_and_plots(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    plot = FakePlot()
    plot.bar_gap = 80.0
    graph = FakeGraph(FakeLayer([plot]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.get_graph_info("Graph1")

    assert result["layers_count"] == 1
    assert result["layers"][0]["plots_count"] == 1
    assert result["layers"][0]["plots"][0]["bar_gap"] == 80.0
    assert result["layers"][0]["axes"]["x"]["scale"] == "linear"
    assert result["layers"][0]["axes"]["x"]["scale_name"] == "linear"


def test_get_graph_info_detects_parenthesized_panel_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer([FakePlot()])
    layer.labels["panel_a_panel_tag"] = FakeLabel("(a)")
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.get_graph_info("Graph1")

    assert result["layers"][0]["panel_label_present"] is True


def test_set_axis_returns_readback_and_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    layer = FakeLayer()
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    result = client.set_axis(
        graph_name="Graph1",
        axis="x",
        scale="log10",
        start=1,
        end=10000,
        title="Suction",
    )

    assert layer.axis("x").scale == 2
    assert layer.axis("x").limits == (1, 10000, None)
    assert result["axis_info"]["scale"] == 2
    assert result["axis_info"]["scale_name"] == "log10"
    assert result["axis_info"]["limits"] == (1, 10000, None)
    assert result["verified"] is True


def test_run_labtalk_can_capture_message_log() -> None:
    client = OriginClient()

    class FakeOp:
        def __init__(self) -> None:
            self.scripts: list[str] = []
            self.log_path: Path | None = None

        def lt_exec(self, script: str) -> bool:
            self.scripts.append(script)
            if script.startswith('type -gb "'):
                self.log_path = Path(script.split('"')[1])
                return True
            if script == "type -ge;":
                return True
            assert self.log_path is not None
            self.log_path.write_text("message line\n", encoding="utf-8")
            return script == "type ok;"

    fake_op = FakeOp()
    client._op = fake_op

    result = client.run_labtalk("type ok;", capture_log=True)

    assert result["result"] is True
    assert result["message_log"]["captured"] is True
    assert result["message_log"]["lines"] == ["message line"]
    assert fake_op.scripts[1] == "type ok;"


def test_run_labtalk_false_result_includes_diagnostics() -> None:
    client = OriginClient()

    class FakeOrigin:
        def lt_exec(self, _script: str) -> bool:
            return False

    client._op = FakeOrigin()

    result = client.run_labtalk("bad command;")

    assert result["result"] is False
    assert result["warning"] == "Origin returned false for this LabTalk script."
    assert result["script_preview"] == "bad command;"


def test_get_graph_info_tolerates_origin_plot_property_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()

    class BrokenPlot(FakePlot):
        @property
        def symbol_kind(self) -> int:
            raise ValueError("cannot convert float NaN to integer")

    graph = FakeGraph(FakeLayer([BrokenPlot()]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.get_graph_info("Graph1")

    assert result["layers"][0]["plots"][0]["symbol_kind"] is None


def test_format_graph_formats_axis_titles_and_sets_graph_long_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer()
    graph = FakeGraph(layer)
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(client, "run_labtalk", lambda script: scripts.append(script))

    client.format_graph(
        "Graph1",
        title="CO_2 response",
        x_label="time (s)",
        y_label="rate m^-2",
        rescale=True,
    )

    assert layer.axis("x").title == "time (s)"
    assert layer.axis("y").title == "rate m\\+(-2)"
    assert graph.lname == "CO_2 response"
    assert layer.labels == {}
    assert scripts == [
        'win -a "Graph1"; page.longname$="CO_2 response";',
        'win -a "Graph1"; title.show=0; title.text$=""; '
        'Title.show=0; Title.text$=""; GraphTitle.show=0; GraphTitle.text$="";',
    ]


def test_format_graph_removes_template_title_label(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    layer = FakeLayer()
    title_label = FakeLabel("Graph1")
    title_label.name = "Title"
    layer.labels["Title"] = title_label
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})

    client.format_graph("Graph1", rescale=False)

    assert title_label.removed is True
    assert layer.labels == {}


def test_format_legend_does_not_move_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    legend = FakeLabel("Legend")
    layer = FakeLayer()
    layer.labels["Legend"] = legend
    graph = FakeGraph(layer)
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.format_legend("Graph1", font_size=12, show_frame=True)

    assert legend.properties["fsize"] == 12
    assert legend.properties["showframe"] == 1
    assert result["position"] is None
    assert scripts == []


def test_format_legend_reasserts_font_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    legend = FakeLabel("Legend")
    layer = FakeLayer()
    layer.labels["Legend"] = legend
    graph = FakeGraph(layer)
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    client.format_legend("Graph1", font_family="Arial")

    assert any("legend.font=font(Arial);" in script for script in scripts)


def test_format_legend_positions_inside_layer_anchor_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    legend = FakeLabel("Legend")
    layer = FakeLayer()
    layer.labels["Legend"] = legend
    graph = FakeGraph(layer)
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.format_legend("Graph1", position="inside_upper_left")

    assert result["position"]["mode"] == "layer_anchor"
    assert result["position"]["position"] == "inside_upper_left"
    assert "legend.x=layer.x.from+" in scripts[-1]
    assert "legend.y=layer.y.to-" in scripts[-1]
    assert "legend.left" not in scripts[-1]
    assert "legend.top" not in scripts[-1]


def test_format_legend_interprets_small_left_top_as_layer_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    legend = FakeLabel("Legend")
    layer = FakeLayer()
    layer.labels["Legend"] = legend
    graph = FakeGraph(layer)
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.format_legend("Graph1", left=20, top=10)

    assert result["position"]["mode"] == "layer_percent"
    assert result["position"]["left_percent"] == 20
    assert result["position"]["top_percent"] == 10
    assert "layer.x.from+(layer.x.to-layer.x.from)*0.2+legend.dx/2" in scripts[-1]
    assert "layer.y.to-(layer.y.to-layer.y.from)*0.1-legend.dy/2" in scripts[-1]
    assert "left" not in legend.properties
    assert "top" not in legend.properties


def test_format_legend_can_still_use_page_pixels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    legend = FakeLabel("Legend")
    layer = FakeLayer()
    layer.labels["Legend"] = legend
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.format_legend(
        "Graph1",
        left=1200,
        top=620,
        coordinate_mode="page_pixel",
    )

    assert result["position"] == {"mode": "page_pixel", "left": 1200, "top": 620}
    assert legend.properties["left"] == 1200
    assert legend.properties["top"] == 620


def test_format_legend_requires_left_and_top_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer()
    layer.labels["Legend"] = FakeLabel("Legend")
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    with pytest.raises(OriginOperationError, match="left and top must be provided together"):
        client.format_legend("Graph1", left=20)

    with pytest.raises(OriginOperationError, match="left and top must be provided together"):
        client.format_legend("Graph1", top=10)


def test_format_legend_rejects_invalid_coordinate_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer()
    layer.labels["Legend"] = FakeLabel("Legend")
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    with pytest.raises(OriginOperationError, match="coordinate_mode must be one of"):
        client.format_legend("Graph1", left=20, top=10, coordinate_mode="screen")


def test_format_legend_rejects_invalid_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer()
    layer.labels["Legend"] = FakeLabel("Legend")
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    with pytest.raises(OriginOperationError, match="Unsupported legend position"):
        client.format_legend("Graph1", position="outside")


def _one_by_one_png() -> bytes:
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )


class _FakeRenderGraph:
    def __init__(self, png: bytes, name: str = "G1", accept_kwargs: bool = True) -> None:
        self._png = png
        self.name = name
        self._accept_kwargs = accept_kwargs
        self.saved_path: str | None = None
        self.saved_width: int | None = None

    def save_fig(self, path: str, type: str = "png", replace: bool = True, width: int = 0) -> None:
        if not self._accept_kwargs:
            raise TypeError("save_fig() takes 1 positional argument")
        self.saved_path = path
        self.saved_width = width
        Path(path).write_bytes(self._png)

    def _save_fig_minimal(self, path: str) -> None:
        self.saved_path = path
        Path(path).write_bytes(self._png)


def test_render_graph_png_returns_base64_and_deletes_temp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64

    png = _one_by_one_png()
    client = OriginClient()
    graph = _FakeRenderGraph(png, name="G1")
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.render_graph_png(graph_name="G1", max_width=800)

    assert result["format"] == "png"
    assert result["graph_name"] == "G1"
    assert result["size_bytes"] == len(png)
    assert result["width"] == 1 and result["height"] == 1
    assert base64.b64decode(result["image_base64"]) == png
    assert graph.saved_width == 800
    # The temp render file must not be left behind.
    assert graph.saved_path is not None
    assert not Path(graph.saved_path).exists()


def test_render_graph_png_falls_back_when_save_fig_rejects_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64

    png = _one_by_one_png()
    client = OriginClient()

    class MinimalGraph:
        name = "G2"

        def __init__(self) -> None:
            self.saved_path: str | None = None

        def save_fig(self, path: str) -> None:
            self.saved_path = path
            Path(path).write_bytes(png)

    graph = MinimalGraph()
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.render_graph_png(graph_name="G2")

    assert base64.b64decode(result["image_base64"]) == png
    assert not Path(graph.saved_path).exists()


def test_render_graph_png_requires_save_fig(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()

    class NoSaveFig:
        name = "G3"

    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: NoSaveFig())

    with pytest.raises(OriginOperationError) as excinfo:
        client.render_graph_png(graph_name="G3")
    assert excinfo.value.error_code == "graph_render_unavailable"


def test_prune_preview_dir_keeps_most_recent(tmp_path: Path) -> None:
    from origin_mcp.client.export import _ExportMixin

    for i in range(25):
        entry = tmp_path / f"p{i}.png"
        entry.write_bytes(b"x")
        os.utime(entry, (i, i))  # increasing mtime: p24 is newest

    _ExportMixin._prune_preview_dir(tmp_path, keep=20)

    remaining = {p.name for p in tmp_path.iterdir()}
    assert len(remaining) == 20
    assert "p24.png" in remaining  # newest kept
    assert "p0.png" not in remaining  # oldest pruned


def test_export_preview_prunes_default_temp_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import origin_mcp.client.export as export_mod

    client = OriginClient()
    monkeypatch.setattr(export_mod.tempfile, "gettempdir", lambda: str(tmp_path))
    preview_dir = tmp_path / "origin-mcp-previews"
    preview_dir.mkdir()
    for i in range(25):
        entry = preview_dir / f"old{i}.png"
        entry.write_bytes(b"x")
        os.utime(entry, (i, i))

    def fake_export_graph(path: Any, graph_name: Any = None, overwrite: bool = True) -> dict:
        Path(path).write_bytes(b"PNG")
        os.utime(path, (10_000, 10_000))  # newest, must survive pruning
        return {"path": str(path)}

    monkeypatch.setattr(client, "export_graph", fake_export_graph)
    monkeypatch.setattr(client, "inspect_export", lambda _p: {"looks_nonempty": True})

    result = client.export_preview(graph_name="G")

    remaining = {p.name for p in preview_dir.iterdir()}
    assert len(remaining) == 20
    assert Path(result["path"]).name in remaining


def test_export_preview_does_not_prune_caller_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = OriginClient()
    out = tmp_path / "my-exports"
    out.mkdir()
    for i in range(25):
        (out / f"keep{i}.png").write_bytes(b"x")

    def fake_export_graph(path: Any, graph_name: Any = None, overwrite: bool = True) -> dict:
        Path(path).write_bytes(b"PNG")
        return {"path": str(path)}

    monkeypatch.setattr(client, "export_graph", fake_export_graph)
    monkeypatch.setattr(client, "inspect_export", lambda _p: {"looks_nonempty": True})

    client.export_preview(graph_name="G", output_dir=out)

    # A caller-supplied directory is never pruned: all 25 pre-existing files plus
    # the new preview remain.
    assert len([p for p in out.iterdir() if p.is_file()]) == 26


def test_export_graph_prefers_labtalk_when_graph_name_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    path = tmp_path / "graph.png"
    scripts = []
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.export_graph(path, graph_name="Graph 1")

    assert result["path"] == str(path)
    assert 'title.show=0; title.text$="";' in scripts[0]
    assert 'win -a "Graph 1"; expGraph pages:="Graph 1" type:=png path:="' in scripts[1]
    assert 'filename:="graph" overwrite:=replace;' in scripts[1]


def test_add_graph_label_formats_text(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    layer = FakeLayer()
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.add_graph_label("H₂O <sup>18</sup>O", graph_name="Graph1")

    assert result["formatted_text"] == "H\\-(2)O \\+(18)O"
    assert layer.labels["Label1"].text == "H\\-(2)O \\+(18)O"


def test_set_column_labels_formats_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"co2": [1]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.set_column_labels(["CO_2", "m^2"], label_type="L")

    assert wks.labels["labels"] == ["CO\\-(2)", "m\\+(2)"]


def test_plot_table_reports_origin_default_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    graph = FakeGraph(FakeLayer())
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    worksheet, graph_ref = client.plot_table(path=path, kind="scatter", show_legend=False)

    assert worksheet.rows == 1
    assert graph_ref.template == "scatter"
    assert graph_ref.style_mode == "origin_default"


def test_new_sheet_reuses_named_worksheet(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet()

    class FakeOrigin:
        def find_sheet(self, _kind: str, ref: str) -> FakeWorksheet | None:
            return wks if ref == "NamedData" else None

        def new_sheet(self, *_args: object) -> None:
            raise AssertionError("new_sheet should not be called")

    monkeypatch.setattr(client, "_op", FakeOrigin())

    assert client._new_sheet(book_name="NamedData", sheet_name=None) is wks


def test_new_graph_reuses_named_graph_and_clears_plots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    old_plot = FakePlot()
    graph = FakeGraph(FakeLayer([old_plot]))

    class FakeOrigin:
        def find_graph(self, name: str) -> FakeGraph | None:
            return graph if name == "NamedGraph" else None

        def new_graph(self, **_kwargs: object) -> None:
            raise AssertionError("new_graph should not be called")

    monkeypatch.setattr(client, "_op", FakeOrigin())

    assert client._new_graph(kind="line", graph_name="NamedGraph") is graph
    assert old_plot.removed is True
    assert graph.layer.plots == []
    assert graph.lname == "NamedGraph"


def test_plot_table_reuses_named_graph_and_stable_data_sheet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"old": [9]}))
    old_plot = FakePlot()
    layer = FakeLayer([old_plot])
    graph = FakeGraph(layer)

    class FakeOrigin:
        def find_sheet(self, _kind: str, ref: str) -> FakeWorksheet | None:
            return wks if ref == "NamedLine_Data" else None

        def find_graph(self, name: str) -> FakeGraph | None:
            return graph if name == "NamedLine" else None

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    worksheet, graph_ref = client.plot_table(
        path=path,
        kind="line",
        graph_name="NamedLine",
        show_legend=False,
    )

    assert worksheet.book_name == "Book1"
    assert wks.df.to_dict("list") == {"x": [0], "y": [1]}
    assert old_plot.removed is True
    assert len(layer.plots) == 1
    assert graph_ref.graph_name == "Graph1"
    assert graph_ref.requested_graph_name == "NamedLine"


def test_plot_table_groups_multi_y_column_plots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("month,y2020,y2021\n1,10,12\n2,20,24\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    layer = FakeLayer()
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    client.plot_table(
        path=path,
        kind="column",
        x_col="month",
        y_cols=["y2020", "y2021"],
        show_legend=False,
    )

    assert len(layer.added) == 2
    assert layer.group_calls == 1


def test_plot_table_rejects_publication_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    graph = FakeGraph(FakeLayer())
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    with pytest.raises(OriginOperationError, match="Unsupported style_mode"):
        client.plot_table(
            path=path,
            kind="line",
            show_legend=False,
            style_mode="publication",
        )


def test_plot_table_nature_style_applies_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    graph = FakeGraph(FakeLayer())
    nature_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(
        client,
        "apply_nature_style",
        lambda **kwargs: nature_calls.append(kwargs) or {"styled": True},
    )

    _, graph_ref = client.plot_table(
        path=path,
        kind="line",
        show_legend=False,
        style_mode="nature",
    )

    assert graph_ref.style_mode == "nature"
    assert nature_calls == [{"graph_name": "Graph1", "chart_type": "line"}]


def test_plot_table_exports_by_graph_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    export_path = tmp_path / "line.png"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    graph = FakeGraph(FakeLayer())
    export_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(
        client,
        "_export_plot_command_graph",
        lambda path_arg, graph_name: (
            export_calls.append((path_arg, graph_name)) or {"path": str(path_arg)}
        ),
    )

    _worksheet, graph_ref = client.plot_table(
        path=path,
        kind="line",
        graph_name="NamedLine",
        export_path=export_path,
    )

    assert graph_ref.export_path == str(export_path)
    assert export_calls == [(export_path, "Graph1")]
    assert graph_ref.graph_name == "Graph1"
    assert graph_ref.requested_graph_name == "NamedLine"
    assert graph_ref.display_name == "NamedLine"

    graph.layer.labels["Legend"] = FakeLabel("Legend")

    class FakeOrigin:
        def find_graph(self, name: str) -> FakeGraph | None:
            return graph if name == "Graph1" else None

    monkeypatch.setattr(client, "_op", FakeOrigin())

    formatted = client.format_legend("NamedLine", position="inside_upper_left")

    assert formatted["graph_name"] == "Graph1"


def test_format_legend_finds_graph_by_long_name_when_short_name_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    graph = GPage(FakeLayer())
    graph.lname = "OriginMcpStdioSmokeLine"
    graph.layer.labels["Legend"] = FakeLabel("Legend")
    scripts = []

    class FakeOrigin:
        def find_graph(self, _name: str) -> None:
            return None

        def pages(self) -> list[GPage]:
            return [graph]

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.format_legend(
        graph_name="OriginMcpStdioSmokeLine",
        position="inside_lower_right",
    )

    assert result["graph_name"] == "Graph1"
    assert result["position"]["mode"] == "layer_anchor"
    assert 'win -a "Graph1";' in scripts[-1]


def test_default_plot_config_discovers_user_templates(tmp_path: Path) -> None:
    (tmp_path / "CustomLine.otpu").write_text("placeholder", encoding="utf-8")
    client = OriginClient()
    client._capabilities = {
        "origin_version": 10.3,
        "originpro_version": "1.1.15",
        "originext_version": "1.2.5",
        "python_version": "3.12.0",
    }

    class FakeOrigin:
        def path(self, path_type: str = "u") -> str:
            if path_type == "u":
                return str(tmp_path)
            if path_type == "e":
                return str(tmp_path / "missing")
            return ""

    client._op = FakeOrigin()

    config = client.default_plot_config(max_templates=10)

    assert config["style_mode_default"] == "origin_default"
    assert config["default_templates"]["scatter"] == "scatter"
    assert config["template_search_paths"]["user_files"] == str(tmp_path)
    assert config["templates"]["discovered"][0]["name"] == "CustomLine"


def test_apply_nature_style_updates_plots(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    plot = FakePlot()
    graph = FakeGraph(FakeLayer([plot]))
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    result = client.apply_nature_style("Graph1", page_width=None, page_height=None)

    assert result["style"] == "nature"
    assert result["styled_plots"] == 1
    assert "-w 1500" in plot.commands
    assert "-wp 3.0" in plot.commands
    assert plot.line_width == 3.0
    assert plot.width == 3.0
    assert plot.symbol_size == 4.5
    assert plot.color == (39, 68, 124)
    assert plot.transparency == 0
    assert "layer.x.label.font=font(Arial);" in scripts[-1]
    assert "layer.x.ticklabel.font=font(Arial);" in scripts[-1]
    assert "xb.font=font(Arial);" in scripts[-1]
    assert "yl.font=font(Arial);" in scripts[-1]
    assert 'xb.text$="\\f:Arial(Axis)";' in scripts[-1]
    assert 'yl.text$="\\f:Arial(Axis)";' in scripts[-1]
    assert "layer.x.label.pt=20;" in scripts[-1]
    assert "layer.y.label.pt=20;" in scripts[-1]
    assert "layer.x.ticklabel.pt=18;" in scripts[-1]
    assert "layer.y.ticklabel.pt=18;" in scripts[-1]
    assert "xb.fsize=20;" in scripts[-1]
    assert "yl.fsize=20;" in scripts[-1]
    assert "legend.font=font(Arial);" in scripts[-1]
    assert "legend.fsize=20;" in scripts[-1]
    assert "range __omcpNaturePlot1 = !1;" in scripts[-1]
    assert "set __omcpNaturePlot1 -w 1500;" in scripts[-1]
    assert "set __omcpNaturePlot1 -wp 3.0;" in scripts[-1]
    assert "legend.showframe=0;" in scripts[-1]
    assert result["diagnostics"]["summary"]["plots"] == 1


def test_apply_nature_style_uses_chart_specific_scatter_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    plot = FakePlot()
    graph = FakeGraph(FakeLayer([plot]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    result = client.apply_nature_style("Graph1", chart_type="scatter")

    assert result["chart_type"] == "scatter"
    assert "-w 900" in plot.commands
    assert "-wp 1.8" in plot.commands
    assert plot.symbol_size == 5.0


def test_apply_nature_style_quotes_graph_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    graph = FakeGraph(FakeLayer([FakePlot()]))
    graph.name = "Graph 1"
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    client.apply_nature_style("Graph 1")

    assert scripts[-1].startswith('win -a "Graph 1";')


def test_apply_nature_style_uses_semantic_palette_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    hero = FakePlot()
    baseline = FakePlot()
    graph = FakeGraph(FakeLayer([hero, baseline]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    result = client.apply_nature_style("Graph1", palette_role="hero,baseline")

    assert hero.color == (39, 68, 124)
    assert baseline.color == (231, 60, 54)
    assert result["applied_palette_roles"] == ["hero", "baseline"]
    assert result["diagnostics"]["checklist"][3]["name"] == "palette"
    assert result["diagnostics"]["checklist"][3]["passed"] is True


def test_palette_catalog_exposes_lcpmgh_nature_source() -> None:
    catalog = palette_catalog()

    assert catalog["nature"]["semantic_roles"]["hero"] == "#27447C"
    assert catalog["nature"]["source_url"] == "https://github.com/lcpmgh/colors"
    assert "colors" not in catalog["nature"]
    with pytest.raises(OriginOperationError):
        normalize_palette_name("nature_skill")


@pytest.mark.parametrize("colors_count", range(2, 17))
def test_palette_catalog_exposes_lcpmgh_counts(colors_count: int) -> None:
    catalog = palette_catalog(
        colors_count=colors_count,
        family="lcpmgh/colors",
        include_colors=True,
        limit=None,
    )

    assert catalog
    assert all(entry["colors_count"] == colors_count for entry in catalog.values())
    assert all(len(entry["colors"]) == colors_count for entry in catalog.values())


def test_palette_catalog_filters_lcpmgh_color_range() -> None:
    catalog = palette_catalog(
        min_colors=6,
        max_colors=8,
        family="lcpmgh/colors",
        include_colors=False,
        limit=None,
    )

    assert catalog
    assert all(6 <= entry["colors_count"] <= 8 for entry in catalog.values())
    assert all("colors" not in entry for entry in catalog.values())


def test_apply_nature_style_uses_named_palette(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    hero = FakePlot()
    baseline = FakePlot()
    graph = FakeGraph(FakeLayer([hero, baseline]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    result = client.apply_nature_style(
        "Graph1",
        palette_role="hero,baseline",
        palette_name="nature",
    )

    assert hero.color == (39, 68, 124)
    assert baseline.color == (231, 60, 54)
    assert result["palette_name"] == "nature"
    assert result["diagnostics"]["palette_name"] == "nature"
    assert result["diagnostics"]["checklist"][3]["passed"] is True


def test_apply_nature_style_rejects_removed_legacy_palette(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    hero = FakePlot()
    baseline = FakePlot()
    graph = FakeGraph(FakeLayer([hero, baseline]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    with pytest.raises(OriginOperationError):
        client.apply_nature_style(
            "Graph1",
            palette_role="hero,baseline",
            palette_name="nature_skills_legacy",
        )


@pytest.mark.parametrize(
    ("plot_count", "expected_count", "warns"),
    [(1, 2, False), (2, 2, False), (6, 6, False), (16, 16, False), (17, 16, True)],
)
def test_apply_nature_style_auto_selects_lcpmgh_palette(
    monkeypatch: pytest.MonkeyPatch,
    plot_count: int,
    expected_count: int,
    warns: bool,
) -> None:
    client = OriginClient()
    plots = [FakePlot() for _ in range(plot_count)]
    graph = FakeGraph(FakeLayer(plots))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(client, "format_legend", lambda *_args, **_kwargs: {"legend": True})

    result = client.apply_nature_style("Graph1", palette_name="lcpmgh_auto")

    assert result["palette_name"].startswith(f"lcpmgh_{expected_count:03d}_")
    assert result["auto_palette"]["colors_count"] == expected_count
    if warns:
        assert result["auto_palette"]["warning"] is not None
    else:
        assert result["auto_palette"]["warning"] is None
    assert len(result["palette"]) == expected_count


def test_diagnose_graph_reports_missing_axis_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer([FakePlot()])
    layer.axis("x").title = "Time"
    layer.axis("y").title = ""
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.diagnose_graph("Graph1")

    assert result["passed"] is True
    assert result["score"] == 85
    assert result["issues"][0]["code"] == "missing_axis_title"


def test_diagnose_graph_reports_semantic_palette_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    plot = FakePlot()
    plot.color = (39, 68, 124)
    plot.transparency = 0
    layer = FakeLayer([plot])
    layer.axis("x").title = "Time"
    layer.axis("y").title = "Value"
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.diagnose_graph("Graph1", style="nature", palette_role="positive")

    assert result["issues"][0]["code"] == "semantic_palette_mismatch"
    assert result["checklist"][3]["passed"] is False


def test_diagnose_graph_checks_export_quality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer([FakePlot()])
    layer.axis("x").title = "Time"
    layer.axis("y").title = "Value"
    graph = FakeGraph(layer)
    path = tmp_path / "blank.png"
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
        b"\xf6\x178U"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.diagnose_graph(
        "Graph1",
        export_path=path,
        min_export_width=2,
        min_export_height=2,
    )

    issue_codes = {issue["code"] for issue in result["issues"]}
    assert "export_blank_or_near_blank" in issue_codes
    assert "export_width_too_small" in issue_codes
    assert result["checklist"][-2]["name"] == "export_quality"
    assert result["checklist"][-2]["passed"] is False


def test_diagnose_graph_accepts_external_palette_without_nature_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    layer = FakeLayer([FakePlot()])
    layer.axis("x").title = "Time"
    layer.axis("y").title = "Value"
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.diagnose_graph("Graph1", palette_name="Viridis")

    assert result["palette_name"] == "Viridis"
    assert result["issues"][0]["code"] == "external_palette_name"


def test_chart_atlas_route_selects_correlation_scatter() -> None:
    client = OriginClient()

    route = client.chart_atlas_route("correlation", columns=["x", "y"])

    assert route["intent"] == "correlation"
    assert route["kind"] == "scatter"
    assert route["regression"] is True
    assert route["palette_role"] == "hero"


def test_chart_atlas_route_accepts_3d_scatter_alias() -> None:
    client = OriginClient()

    route = client.chart_atlas_route("3d scatter xyz", columns=["x", "y", "z"])

    assert route["intent"] == "3d_scatter"
    assert route["plot_type_id"] == 240
    assert route["template"] == "3d"


def test_plot_auto_routes_bubble_color_mapped_to_plot_type_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "bubble.csv"
    path.write_text(
        "x,y,size,intensity\n0,0.1,5,100\n1,0.4,10,120\n",
        encoding="utf-8",
    )
    client = OriginClient()
    worksheet = WorksheetRef("Book1", "Sheet1", ["x", "y", "size", "intensity"], 2)
    graph = GraphRef("AutoBubble", template="scatter", style_mode="origin_default")
    calls = {}

    def fake_plot_table_by_id(**kwargs: object) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
        calls["plot_table_by_id"] = kwargs
        return worksheet, graph, {"script": "plotxy iy:=... plot:=248;"}

    monkeypatch.setattr(client, "plot_table_by_id", fake_plot_table_by_id)
    monkeypatch.setattr(
        client,
        "diagnose_graph",
        lambda **kwargs: calls.setdefault("diagnose", kwargs) or {"passed": True},
    )

    result = client.plot_auto(path=path, intent="color_mapped", graph_name="AutoBubble")

    assert calls["plot_table_by_id"]["plot_type_id"] == 248
    assert calls["plot_table_by_id"]["template"] == "scatter"
    assert calls["plot_table_by_id"]["selected_cols"] == ["x", "y", "size", "intensity"]
    assert result["recommendation"]["selected"]["chart"] == "bubble_color_mapped"
    assert result["command"] == {"script": "plotxy iy:=... plot:=248;"}


def test_plot_auto_prefers_3d_scatter_for_3d_xyz_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "xyz.csv"
    path.write_text("x,y,z\n0,0,1\n0,1,2\n1,0,3\n1,1,4\n", encoding="utf-8")
    client = OriginClient()
    worksheet = WorksheetRef("Book1", "Sheet1", ["x", "y", "z"], 4)
    graph = GraphRef("Auto3D", template="3d", style_mode="origin_default")
    calls = {}

    def fake_plot_table_by_id(**kwargs: object) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
        calls["plot_table_by_id"] = kwargs
        return worksheet, graph, {"script": "plotxyz iz:=... plot:=240;"}

    monkeypatch.setattr(client, "plot_table_by_id", fake_plot_table_by_id)
    monkeypatch.setattr(client, "diagnose_graph", lambda **_kwargs: {"passed": True})

    result = client.plot_auto(path=path, intent="3d scatter xyz", graph_name="Auto3D")

    assert calls["plot_table_by_id"]["plot_type_id"] == 240
    assert calls["plot_table_by_id"]["template"] == "3d"
    assert result["recommendation"]["selected"]["chart"] == "3d_scatter"


def test_plot_chart_atlas_defaults_to_origin_style_and_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    worksheet = WorksheetRef("Book1", "Sheet1", ["x", "y"], 1)
    graph = GraphRef("AtlasGraph", template="scatter", style_mode="origin_default")
    calls = {}

    def fake_plot_table(**kwargs: object) -> tuple[WorksheetRef, GraphRef]:
        calls["plot_table"] = kwargs
        return worksheet, graph

    monkeypatch.setattr(
        client,
        "plot_table",
        fake_plot_table,
    )
    monkeypatch.setattr(
        client,
        "apply_nature_style",
        lambda **kwargs: calls.setdefault("style", kwargs) or {"styled": True},
    )
    monkeypatch.setattr(
        client,
        "_atlas_linear_fit",
        lambda **kwargs: calls.setdefault("fit", kwargs) or {"mode": "result"},
    )
    monkeypatch.setattr(
        client,
        "diagnose_graph",
        lambda **kwargs: calls.setdefault("diagnose", kwargs) or {"passed": True},
    )

    result = client.plot_chart_atlas(
        path=path,
        intent="correlation",
        x_col="x",
        y_cols=["y"],
    )

    assert result["route"]["intent"] == "correlation"
    assert calls["plot_table"]["kind"] == "scatter"
    assert calls["plot_table"]["style_mode"] == "origin_default"
    assert "style" not in calls
    assert calls["fit"]["worksheet"] == worksheet
    assert calls["diagnose"]["style"] is None
    assert result["graph"]["style_mode"] == "origin_default"


def test_plot_chart_atlas_applies_nature_only_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    worksheet = WorksheetRef("Book1", "Sheet1", ["x", "y"], 1)
    graph = GraphRef("AtlasGraph", template="scatter", style_mode="origin_default")
    calls = {}

    def fake_plot_table(**kwargs: object) -> tuple[WorksheetRef, GraphRef]:
        calls["plot_table"] = kwargs
        return worksheet, graph

    monkeypatch.setattr(client, "plot_table", fake_plot_table)
    monkeypatch.setattr(
        client,
        "apply_nature_style",
        lambda **kwargs: calls.setdefault("style", kwargs) or {"styled": True},
    )
    monkeypatch.setattr(client, "_atlas_linear_fit", lambda **kwargs: {"mode": "result"})
    monkeypatch.setattr(client, "diagnose_graph", lambda **kwargs: {"passed": True})

    result = client.plot_chart_atlas(
        path=path,
        intent="correlation",
        x_col="x",
        y_cols=["y"],
        style_mode="nature",
    )

    assert calls["plot_table"]["style_mode"] == "origin_default"
    assert calls["style"]["palette_role"] == "hero"
    assert result["graph"]["style_mode"] == "nature"


def test_apply_image_panel_style_adds_panel_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    graph = FakeGraph(FakeLayer([FakePlot()]))
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.apply_image_panel_style(
        graph_name="Graph1",
        panel_label="A",
        channel_label="Channel 1",
        scale_bar_label="10 um",
        dynamic_range_label="min-max matched",
        dark_panel=True,
    )

    label_texts = {label.text for label in graph.layer.labels.values()}
    assert {"A", "Channel 1", "10 um", "min-max matched"} <= label_texts
    labels_by_text = {label.text: label for label in graph.layer.labels.values()}
    assert labels_by_text["A"].properties["fsize"] == 20
    assert labels_by_text["Channel 1"].properties["fsize"] == 18
    assert labels_by_text["10 um"].properties["fsize"] == 18
    assert labels_by_text["min-max matched"].properties["fsize"] == 18
    scale_bar = next(
        item for item in result["diagnostics"]["checklist"] if item["name"] == "scale_bar"
    )
    assert scale_bar["passed"] is True
    assert "page.color=1;" in scripts[-1]


def test_normalize_style_mode_accepts_nature_aliases() -> None:
    assert OriginClient._normalize_style_mode("nature") == "nature"
    assert OriginClient._normalize_style_mode("nature-style") == "nature"


def test_change_and_remove_plot(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    plot = FakePlot()
    graph = FakeGraph(FakeLayer([plot]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    changed = client.change_plot_type(0, "s", "Graph1")
    removed = client.remove_plot_from_graph(0, "Graph1")

    assert changed["plot_type"] == "s"
    assert "-c s" in plot.commands
    assert removed["removed_plot_index"] == 0
    assert plot.removed is True


def test_add_plot_to_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"time": [0], "force": [1]}))
    layer = FakeLayer()
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "_find_sheet_from_ref", lambda _worksheet: wks)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    result = client.add_plot_to_graph("[Book1]Sheet1", "time", "force", "Graph1")

    assert result["x_col"] == "time"
    assert result["y_col"] == "force"
    assert layer.added[0][1]["coly"] == "force"


def test_set_plot_style_converts_line_width_points_to_origin_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    plot = FakePlot()
    graph = FakeGraph(FakeLayer([plot]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.set_plot_style("Graph1", line_width=2.5)

    assert result["styled_plots"] == 1
    assert "-w 1250" in plot.commands
    assert "-wp 2.5" in plot.commands
    assert plot.line_width == 2.5
    assert plot.width == 2.5


def test_set_plot_style_sets_column_bar_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    plot = FakePlot()
    graph = FakeGraph(FakeLayer([plot]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.set_plot_style("Graph1", bar_gap=80)

    assert result["styled_plots"] == 1
    assert "-vg 80" in plot.commands
    assert plot.bar_gap == 80.0


def test_set_plot_style_uses_zero_based_layer_index(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    first_plot = FakePlot()
    second_plot = FakePlot()

    class MultiLayerGraph:
        name = "Graph1"

        def __getitem__(self, index: int) -> FakeLayer:
            if index == 0:
                return FakeLayer([first_plot])
            if index == 1:
                return FakeLayer([second_plot])
            raise IndexError(index)

    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: MultiLayerGraph())

    result = client.set_plot_style("Graph1", layer_index=1, line_width=1.5)

    assert result["layer_index"] == 1
    assert first_plot.width is None
    assert second_plot.width == 1.5


def test_graph_layer_index_error_mentions_zero_based() -> None:
    client = OriginClient()
    graph = FakeGraph(FakeLayer())

    with pytest.raises(OriginOperationError, match="zero-based"):
        client._graph_layer(graph, 1)


def test_plot_range_rejects_empty_created_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()

    class EmptyAddLayer(FakeLayer):
        def add_plot(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: FakeGraph(EmptyAddLayer()))

    with pytest.raises(OriginOperationError, match="no plot was added"):
        client.plot_range("[Book1]Sheet1!(1,2)")


def test_new_graph_uses_extended_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    created = {}

    class FakeOrigin:
        def new_graph(self, **kwargs: object) -> FakeGraph:
            created.update(kwargs)
            return FakeGraph()

    monkeypatch.setattr(client, "_op", FakeOrigin())

    client._new_graph(kind="heatmap", graph_name="Heatmap")

    assert created["template"] == "heatmap"
    assert created["lname"] == "Heatmap"


def test_line_symbol_uses_compatible_line_template(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    created = {}

    class FakeOrigin:
        def new_graph(self, **kwargs: object) -> FakeGraph:
            created.update(kwargs)
            return FakeGraph()

    monkeypatch.setattr(client, "_op", FakeOrigin())

    client._new_graph(kind="line_symbol", graph_name="LineSymbol")

    assert created["template"] == "line"


def test_add_plot_maps_basic_kinds_to_origin_codes() -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [0], "y": [1], "z": [2]}))

    for kind, expected in (
        ("scatter", "s"),
        ("line", "l"),
        ("column", "c"),
        ("contour", "contour"),
    ):
        layer = FakeLayer()
        client._add_plot(layer, wks, x_name="x", y_name="y", z_name="z", kind=kind)
        assert layer.added[0][1]["type"] == expected


def test_add_plot_uses_auto_type_for_template_driven_kinds() -> None:
    # polar and the 3D families have no basic add_plot code; originpro.add_plot
    # would raise KeyError on the multi-char name, so they must fall back to "?"
    # and let the layer's template drive the rendering.
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [0], "y": [1], "z": [2]}))

    for kind in ("polar", "surface3d", "scatter3d", "unknown_kind"):
        layer = FakeLayer()
        client._add_plot(layer, wks, x_name="x", y_name="y", z_name="z", kind=kind)
        assert layer.added[0][1]["type"] == "?"


def test_plot_table_by_id_builds_labtalk_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,size\n0,1,3\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    worksheet, graph, command = client.plot_table_by_id(
        path=path,
        plot_type_id=193,
        template="scatter",
        selected_cols=["x", "y", "size"],
        graph_name="Bubble",
    )

    assert worksheet.columns == ["x", "y", "size"]
    assert graph.graph_name == "Bubble"
    assert command["plot_type_id"] == 193
    assert any("plotxy iy:=[Book1]Sheet1!(1,2,3) plot:=193" in script for script in scripts)
    assert any('title.show=0; title.text$="";' in script for script in scripts)


def test_plot_table_by_id_reuses_named_graph_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    old_plot = FakePlot()
    graph = GPage(FakeLayer([old_plot]))
    graph.name = "Bubble"
    scripts = []

    class FakeOrigin:
        def find_sheet(self, _kind: str, ref: str) -> FakeWorksheet | None:
            return wks if ref == "Bubble_Data" else None

        def find_graph(self, name: str) -> GPage | None:
            return graph if name == "Bubble" else None

        def pages(self, kind: str | None = None) -> list[GPage]:
            return [graph] if kind in {None, "g"} else []

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, graph_ref, _command = client.plot_table_by_id(
        path=path,
        plot_type_id=200,
        template="line",
        selected_cols=["x", "y"],
        graph_name="Bubble",
    )

    assert old_plot.removed is True
    assert graph.layer.plots == []
    assert graph_ref.graph_name == "Bubble"
    assert any("ogl:=[Bubble]1" in script for script in scripts)
    assert not any("<new template" in script for script in scripts)


def test_plot_table_by_id_uses_plotxyz_for_xyz_plot_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, _graph, command = client.plot_table_by_id(
        path=path,
        plot_type_id=240,
        template="3d",
        selected_cols=["x", "y", "z"],
        graph_name="Scatter3D",
    )

    assert command["command"] == "plotxyz"
    assert command["range_option"] == "iz"
    assert "wks.col1.type=4;" in scripts[0]
    assert "wks.col2.type=1;" in scripts[0]
    assert "wks.col3.type=6;" in scripts[0]
    assert any("plotxyz iz:=[Book1]Sheet1!(1,2,3) plot:=240" in script for script in scripts)
    assert any('title.show=0; title.text$="";' in script for script in scripts)


def test_plot_table_by_id_uses_worksheet_command_for_box_plot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("group_a,group_b,group_c\n1,2,3\n4,5,6\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, _graph, command = client.plot_table_by_id(
        path=path,
        plot_type_id=206,
        template="box",
        selected_cols=["group_a", "group_b", "group_c"],
        graph_name="BoxPlot",
    )

    assert command["command"] == "worksheet"
    assert command["range_option"] == "selection"
    assert "worksheet -s 1 0 3 0; worksheet -p 206 box;" in scripts
    assert not any("plotxy" in script and "plot:=206" in script for script in scripts)


@pytest.mark.parametrize(
    ("plot_type_id", "template"),
    [
        (214, "stackarea"),
        (215, "bar"),
        (216, "bar"),
        (225, "pie"),
        (249, "fillarea"),
    ],
)
def test_plot_table_by_id_uses_worksheet_command_for_selection_plot_types(
    plot_type_id: int,
    template: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, _graph, command = client.plot_table_by_id(
        path=path,
        plot_type_id=plot_type_id,
        template=template,
        selected_cols=["x", "y", "z"],
        graph_name="SelectionPlot",
    )

    assert command["command"] == "worksheet"
    assert command["range_option"] == "selection"
    assert f"worksheet -s 1 0 3 0; worksheet -p {plot_type_id} {template};" in scripts
    assert not any(f"plot:={plot_type_id}" in script for script in scripts)


def test_plot_table_by_id_worksheet_command_prefers_new_graph_over_existing_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    existing = GPage(FakeLayer())
    existing.name = "BoxPlot"
    created = GPage(FakeLayer())
    created.name = "Graph9"
    scripts = []

    class FakeOrigin:
        def find_graph(self, name: str) -> GPage | None:
            return existing if name == "BoxPlot" else None

        def pages(self) -> list[GPage]:
            if any("worksheet -p 206 box;" in script for script in scripts):
                return [existing, created]
            return [existing]

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, graph_ref, command = client.plot_table_by_id(
        path=path,
        plot_type_id=206,
        template="box",
        selected_cols=["x", "y"],
        graph_name="BoxPlot",
    )

    assert graph_ref.graph_name == "Graph9"
    assert graph_ref.requested_graph_name == "BoxPlot"
    assert command["warning"] == (
        "Origin did not create or expose the requested graph 'BoxPlot'; "
        "using actual graph 'Graph9'."
    )


def test_all_documented_table_plot_ids_use_expected_labtalk_routes() -> None:
    matrix_only_ids = {item["id"] for item in PLOT_TYPE_CATALOG if item["input"] == "Matrix Object"}
    expected_plotxyz_ids = {103, 185, 240, 242, 243, 245}
    expected_worksheet_ids = {183, 184, 206, 210, 211, 212, 214, 215, 216, 225, 249}

    for item in PLOT_TYPE_CATALOG:
        plot_type_id = item["id"]
        if plot_type_id in matrix_only_ids:
            continue
        command, range_option = OriginClient._table_plot_command_options(plot_type_id)
        if plot_type_id in expected_worksheet_ids:
            assert (command, range_option) == ("worksheet", "selection"), item
        elif plot_type_id in expected_plotxyz_ids:
            assert (command, range_option) == ("plotxyz", "iz"), item
        else:
            assert (command, range_option) == ("plotxy", "iy"), item


def test_plot_table_by_id_sets_xyzxyz_designations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,z,dx,dy,dz\n0,1,2,0.1,0.2,0.3\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, _graph, command = client.plot_table_by_id(
        path=path,
        plot_type_id=183,
        template="gl3DVector",
        selected_cols=["x", "y", "z", "dx", "dy", "dz"],
        graph_name="Vector3D",
    )

    assert "wks.col1.type=4;" in scripts[0]
    assert "wks.col2.type=1;" in scripts[0]
    assert "wks.col3.type=6;" in scripts[0]
    assert "wks.col4.type=4;" in scripts[0]
    assert "wks.col5.type=1;" in scripts[0]
    assert "wks.col6.type=6;" in scripts[0]
    assert command["command"] == "worksheet"
    assert command["range_option"] == "selection"
    assert any("worksheet -s 1 0 6 0; worksheet -p 183 gl3DVector;" in script for script in scripts)
    assert any('title.show=0; title.text$="";' in script for script in scripts)


def test_plot_table_by_id_nature_style_applies_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    nature_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    monkeypatch.setattr(
        client,
        "apply_nature_style",
        lambda **kwargs: nature_calls.append(kwargs) or {"styled": True},
    )

    _worksheet, graph, _command = client.plot_table_by_id(
        path=path,
        plot_type_id=200,
        template="line",
        selected_cols=["x", "y"],
        graph_name="NatureLine",
        style_mode="nature",
    )

    assert graph.style_mode == "nature"
    assert nature_calls == [{"graph_name": "NatureLine", "chart_type": "line"}]


def test_plot_table_by_id_exports_active_graph_when_named_graph_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    export_path = tmp_path / "plot.png"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "run_labtalk", lambda _script: {"result": True})
    calls = []

    def fake_export(path_arg: Path, graph_name: str | None = None) -> dict[str, str]:
        calls.append(graph_name)
        if graph_name:
            raise OriginOperationError(f"Graph not found: {graph_name}")
        return {"path": str(path_arg)}

    monkeypatch.setattr(client, "export_graph", fake_export)

    _worksheet, graph, _command = client.plot_table_by_id(
        path=path,
        plot_type_id=200,
        template="line",
        selected_cols=["x", "y"],
        graph_name="Line",
        export_path=export_path,
    )

    assert graph.export_path == str(export_path)
    assert calls == ["Line", None]


def test_plot_table_by_id_records_alias_when_origin_uses_different_short_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    graph = GPage(FakeLayer())
    graph.name = "Graph7"
    graph.lname = "Generated Graph"
    graph.layer.labels["Legend"] = FakeLabel("Legend")

    class FakeOrigin:
        def find_graph(self, name: str) -> GPage | None:
            return graph if name == "Graph7" else None

        def pages(self) -> list[GPage]:
            return [graph] if any("plotxyz " in script for script in scripts) else []

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, graph_ref, _command = client.plot_table_by_id(
        path=path,
        plot_type_id=243,
        template="Contour",
        selected_cols=["x", "y", "z"],
        graph_name="RequestedHeatmap",
    )

    assert graph_ref.graph_name == "Graph7"
    assert graph_ref.requested_graph_name == "RequestedHeatmap"
    assert graph_ref.display_name == "Generated Graph"
    assert _command["warning"] == (
        "Origin did not create or expose the requested graph 'RequestedHeatmap'; "
        "using actual graph 'Graph7'."
    )

    formatted = client.format_legend("RequestedHeatmap", position="inside_upper_left")

    assert formatted["graph_name"] == "Graph7"
    assert 'win -a "Graph7";' in scripts[-1]


def test_plot_table_by_id_uses_active_graph_when_pages_do_not_report_new_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y,z\n0,1,2\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    scripts = []
    graph = GPage(FakeLayer())
    graph.name = "Graph12"

    class FakeOrigin:
        def find_graph(self, name: str) -> GPage | None:
            return graph if name == "Graph12" else None

        def pages(self) -> list[GPage]:
            return []

        def graph_active(self) -> GPage:
            return graph

    monkeypatch.setattr(client, "_op", FakeOrigin())
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    _worksheet, graph_ref, _command = client.plot_table_by_id(
        path=path,
        plot_type_id=240,
        template="3d",
        selected_cols=["x", "y", "z"],
        graph_name="Requested3D",
    )

    assert graph_ref.graph_name == "Graph12"
    assert client._find_or_active_graph("Requested3D") is graph


def test_assert_plot_created_raises_when_worksheet_route_creates_no_graph() -> None:
    # The worksheet route's lt_exec boolean comes back as None over the bridge,
    # so a rejected command (no new graph page) must be detected and raised
    # instead of silently returning a non-existent graph.
    client = OriginClient()

    class FakeOrigin:
        def pages(self) -> list[object]:
            return []

    client._op = FakeOrigin()  # type: ignore[assignment]

    with pytest.raises(OriginOperationError, match="created no graph"):
        client._assert_plot_created(
            plot_type_id=225,
            template="pie",
            selected=["share"],
            existing_graphs=set(),
            reuse_existing=False,
            result={"result": None},
            script="worksheet -s 1 0 1 0; worksheet -p 225 pie;",
        )


def test_assert_plot_created_passes_when_new_graph_page_appears() -> None:
    client = OriginClient()
    created = GPage(FakeLayer())
    created.name = "Graph7"

    class FakeOrigin:
        def pages(self) -> list[GPage]:
            return [created]

    client._op = FakeOrigin()  # type: ignore[assignment]

    # No exception: a new page appeared even though the worksheet result is None.
    client._assert_plot_created(
        plot_type_id=225,
        template="pie",
        selected=["label", "share"],
        existing_graphs=set(),
        reuse_existing=False,
        result={"result": None},
        script="worksheet -s 1 0 2 0; worksheet -p 225 pie;",
    )


def test_assert_plot_created_trusts_plotxyz_boolean_result() -> None:
    # plotxy/plotxyz return an authoritative boolean; an explicit True is a
    # success even if page enumeration reports no new page (a known quirk).
    client = OriginClient()

    class FakeOrigin:
        def pages(self) -> list[object]:
            return []

    client._op = FakeOrigin()  # type: ignore[assignment]

    client._assert_plot_created(
        plot_type_id=240,
        template="3d",
        selected=["x", "y", "z"],
        existing_graphs=set(),
        reuse_existing=False,
        result={"result": True},
        script="plotxyz iz:=[Book1]Sheet1!(1,2,3) plot:=240 ...;",
    )

    with pytest.raises(OriginOperationError, match="created no graph"):
        client._assert_plot_created(
            plot_type_id=240,
            template="3d",
            selected=["x", "y", "z"],
            existing_graphs=set(),
            reuse_existing=False,
            result={"result": False},
            script="plotxyz iz:=[Book1]Sheet1!(1,2,3) plot:=240 ...;",
        )


def test_plot_matrix_by_id_builds_plotm_command(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    scripts = []
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    graph = client.plot_matrix_by_id("[MBook1]MSheet1!1", 105, "heatmap", "Heat")

    assert graph.graph_name == "Heat"
    assert 'win -a "MBook1";' in scripts[0]
    assert any("plotm im:=[MBook1]MSheet1!1 plot:=105" in script for script in scripts)
    assert any('title.show=0; title.text$="";' in script for script in scripts)


def test_plot_matrix_by_id_uses_plotm_for_surface_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = OriginClient()
    scripts = []
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    graph = client.plot_matrix_by_id("[MBook1]MSheet1!1", 103, "glmesh", "Surface")

    assert graph.graph_name == "Surface"
    assert 'win -a "MBook1";' in scripts[0]
    assert any("plotm im:=[MBook1]MSheet1!1 plot:=103" in script for script in scripts)
    assert any('title.show=0; title.text$="";' in script for script in scripts)


def test_add_reference_line_selects_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    graph = FakeGraph()
    scripts = []
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(
        client,
        "run_labtalk",
        lambda script: scripts.append(script) or {"result": True},
    )

    result = client.add_reference_line(value=2.5, axis="y", graph_name="Graph1", layer_index=1)

    assert result["result"] is True
    assert "layer -s 2;" in scripts[-1]
    assert "draw -n ref_y_2_5 -l y 2.5;" in scripts[-1]


def test_inspect_export_reads_png_dimensions(tmp_path: Path) -> None:
    path = tmp_path / "preview.png"
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x02\x00\x00\x00\x03"
        b"\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    path.write_bytes(png)

    result = OriginClient().inspect_export(path)

    assert result["width"] == 2
    assert result["height"] == 3
    assert result["looks_nonempty"] is True


def test_inspect_export_detects_blank_png(tmp_path: Path) -> None:
    path = tmp_path / "blank.png"
    _write_png(path, width=8, height=8, pixels=[(255, 255, 255)] * 64)

    result = OriginClient().inspect_export(path)

    assert result["image_quality"]["decoded"] is True
    assert result["image_quality"]["has_visual_content"] is False
    assert "blank_or_near_blank" in result["image_quality"]["issues"]
    assert result["looks_nonempty"] is False


def test_inspect_export_detects_visual_content(tmp_path: Path) -> None:
    path = tmp_path / "line.png"
    pixels = [(255, 255, 255)] * 100
    for index in range(10):
        pixels[index * 10 + index] = (0, 0, 0)
    _write_png(path, width=10, height=10, pixels=pixels)

    result = OriginClient().inspect_export(path)

    assert result["image_quality"]["decoded"] is True
    assert result["image_quality"]["has_visual_content"] is True
    assert result["looks_nonempty"] is True


def _write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    rows = []
    for row_index in range(height):
        row = bytearray([0])
        for red, green, blue in pixels[row_index * width : (row_index + 1) * width]:
            row.extend([red, green, blue])
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows))
    data = bytearray(b"\x89PNG\r\n\x1a\n")
    data.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    data.extend(_png_chunk(b"IDAT", raw))
    data.extend(_png_chunk(b"IEND", b""))
    path.write_bytes(data)


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)


def test_filter_rows_keeps_matching_rows_in_place(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"name": ["a", "b", "c"], "val": [1, 5, 9]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.filter_rows(conditions=[{"column": "val", "op": "ge", "value": 5}])

    assert result["matched_rows"] == 2
    assert result["total_rows"] == 3
    assert wks.df["name"].tolist() == ["b", "c"]


def test_filter_rows_combines_with_or(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"val": [1, 5, 9]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.filter_rows(
        conditions=[
            {"column": "val", "op": "lt", "value": 2},
            {"column": "val", "op": "gt", "value": 8},
        ],
        combine="or",
    )

    assert wks.df["val"].tolist() == [1, 9]
    assert result["matched_rows"] == 2


def test_drop_duplicates_on_subset(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"k": [1, 1, 2], "v": [10, 11, 12]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.drop_duplicates(subset=["k"], keep="first")

    assert wks.df["k"].tolist() == [1, 2]
    assert result["removed_rows"] == 1


def test_fill_missing_with_mean(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [1.0, None, 3.0]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.fill_missing(strategy="mean")

    assert wks.df["x"].tolist() == [1.0, 2.0, 3.0]


def test_fill_missing_drop_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [1.0, None, 3.0], "y": [4, 5, 6]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.fill_missing(strategy="drop_rows", columns=["x"])

    assert wks.df["x"].tolist() == [1.0, 3.0]


def test_transpose_worksheet_uses_label_column(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"metric": ["a", "b"], "m1": [1, 2], "m2": [3, 4]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.transpose_worksheet(label_column="metric")

    assert wks.df["Field"].tolist() == ["m1", "m2"]
    assert wks.df["a"].tolist() == [1, 3]
    assert wks.df["b"].tolist() == [2, 4]


def test_pivot_worksheet_long_to_wide(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(
        pd.DataFrame({"day": [1, 1, 2, 2], "grp": ["a", "b", "a", "b"], "val": [10, 20, 30, 40]})
    )
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.pivot_worksheet(index="day", columns="grp", values="val", aggfunc="sum")

    assert wks.df["day"].tolist() == [1, 2]
    assert wks.df["a"].tolist() == [10, 30]
    assert wks.df["b"].tolist() == [20, 40]


def test_melt_worksheet_wide_to_long(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"id": [1, 2], "a": [10, 30], "b": [20, 40]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    client.melt_worksheet(id_vars=["id"], var_name="grp", value_name="val")

    assert set(wks.df.columns) == {"id", "grp", "val"}
    assert len(wks.df) == 4
    assert sorted(wks.df["val"].tolist()) == [10, 20, 30, 40]


def test_merge_worksheets_inner_join(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    left = FakeWorksheet(pd.DataFrame({"k": [1, 2], "x": [10, 20]}))
    right = FakeWorksheet(pd.DataFrame({"k": [2, 3], "y": [200, 300]}))

    def fake_find(book_name: str | None = None, sheet_name: str | None = None) -> FakeWorksheet:
        return right if book_name == "Right" else left

    monkeypatch.setattr(client, "_find_sheet", fake_find)

    result = client.merge_worksheets(right_book="Right", on="k", how="inner")

    assert left.df["k"].tolist() == [2]
    assert left.df["y"].tolist() == [200]
    assert result["result_rows"] == 1


def test_add_calculated_columns_applies_each(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [1, 2]}))
    scripts: list[str] = []
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(
        client,
        "_execute_on_worksheet",
        lambda _wks, script: scripts.append(script) or {"result": 1},
    )

    result = client.add_calculated_columns(
        columns=[
            {"name": "double", "formula": "col(x)*2"},
            {"name": "ref", "formula": "[Other]Sheet1!col(B)"},
        ]
    )

    assert [c["column_name"] for c in result["columns"]] == ["double", "ref"]
    assert any("col(x)*2" in script for script in scripts)
    assert any("[Other]Sheet1!col(B)" in script for script in scripts)


def test_add_calculated_columns_requires_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [1]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_execute_on_worksheet", lambda *_a: {"result": 1})

    with pytest.raises(OriginOperationError, match="missing 'formula'"):
        client.add_calculated_columns(columns=[{"name": "bad"}])


def test_concat_worksheets_stacks_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    primary = FakeWorksheet(pd.DataFrame({"k": [1], "v": [10]}))
    other = FakeWorksheet(pd.DataFrame({"k": [2], "v": [20]}))

    def fake_find(book_name: str | None = None, sheet_name: str | None = None) -> FakeWorksheet:
        return other if book_name == "Other" else primary

    monkeypatch.setattr(client, "_find_sheet", fake_find)

    result = client.concat_worksheets(others=[{"book": "Other", "sheet": "Data"}], axis="rows")

    assert primary.df["k"].tolist() == [1, 2]
    assert result["result_rows"] == 2
    assert result["combined_sheets"] == 2


def test_concat_worksheets_columns_dedupes_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    primary = FakeWorksheet(pd.DataFrame({"v": [1, 2]}))
    other = FakeWorksheet(pd.DataFrame({"v": [3, 4]}))

    def fake_find(book_name: str | None = None, sheet_name: str | None = None) -> FakeWorksheet:
        return other if book_name == "Other" else primary

    monkeypatch.setattr(client, "_find_sheet", fake_find)

    client.concat_worksheets(others=[{"book": "Other", "sheet": "Data"}], axis="columns")

    assert list(primary.df.columns) == ["v", "v_1"]
    assert primary.df["v"].tolist() == [1, 2]
    assert primary.df["v_1"].tolist() == [3, 4]


def test_concat_worksheets_rejects_bad_axis(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"v": [1]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    with pytest.raises(OriginOperationError, match="concat axis"):
        client.concat_worksheets(others=[{"book": "X"}], axis="diagonal")


def test_plot_dual_y_requires_both_axis_column_lists() -> None:
    client = OriginClient()

    with pytest.raises(OriginOperationError, match="y1_cols .* and y2_cols .* are required"):
        client.plot_dual_y(path=Path("data.csv"), x_col="time", y1_cols=["a"], y2_cols=None)

    with pytest.raises(OriginOperationError, match="y1_cols .* and y2_cols .* are required"):
        client.plot_dual_y(path=Path("data.csv"), x_col="time", y1_cols=None, y2_cols=["b"])


def test_plot_dual_y_rejects_unsupported_style_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "dual.csv"
    path.write_text("time,left,right\n0,1,10\n", encoding="utf-8")
    client = OriginClient()
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: FakeWorksheet())

    with pytest.raises(OriginOperationError, match="Unsupported style_mode"):
        client.plot_dual_y(
            path=path,
            x_col="time",
            y1_cols=["left"],
            y2_cols=["right"],
            style_mode="publication",
        )


def test_plot_dual_y_nature_style_applies_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "dual.csv"
    path.write_text("time,left,right\n0,1,10\n", encoding="utf-8")
    client = OriginClient()
    left = FakeLayer()
    right = FakeLayer()
    graph = FakeGraph([left, right])
    nature_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: FakeWorksheet())
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(
        client,
        "apply_nature_style",
        lambda **kwargs: nature_calls.append(kwargs) or {"styled": True},
    )

    _, graph_ref = client.plot_dual_y(
        path=path,
        x_col="time",
        y1_cols=["left"],
        y2_cols=["right"],
        plot_type="line_symbol",
        style_mode="nature",
    )

    assert len(left.added) == 1
    assert len(right.added) == 1
    assert graph_ref.template == "doubleY"
    assert graph_ref.style_mode == "nature"
    assert nature_calls == [{"graph_name": "Graph1", "chart_type": "line_symbol"}]


def test_add_inset_layer_requires_x_and_y_cols() -> None:
    client = OriginClient()

    with pytest.raises(OriginOperationError, match="x_col and y_cols are required"):
        client.add_inset_layer(worksheet="[Book1]Sheet1", x_col=None, y_cols=["a"])

    with pytest.raises(OriginOperationError, match="x_col and y_cols are required"):
        client.add_inset_layer(worksheet="[Book1]Sheet1", x_col="time", y_cols=None)


def test_set_axis_break_validates_axis_and_range() -> None:
    client = OriginClient()

    with pytest.raises(OriginOperationError, match="axis must be"):
        client.set_axis_break(break_from=1, break_to=2, axis="z")

    with pytest.raises(OriginOperationError, match="break_from and break_to are required"):
        client.set_axis_break(break_from=None, break_to=None, axis="x")

    with pytest.raises(OriginOperationError, match="break_from must be less than break_to"):
        client.set_axis_break(break_from=5, break_to=3, axis="x")


def test_diagnose_worksheet_flags_quality_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    df = pd.DataFrame(
        {
            "good": [1.0, 2.0, 3.0, 4.0],
            "empty": [None, None, None, None],
            "sparse": [1.0, None, None, None],
            "const": [5.0, 5.0, 5.0, 5.0],
            "label": ["a", "b", "c", "d"],
        }
    )
    wks = FakeWorksheet(df)
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.diagnose_worksheet()
    codes = {(i["code"], i.get("column")) for i in result["issues"]}

    assert result["rows"] == 4
    assert result["columns_count"] == 5
    assert ("all_null_column", "empty") in codes
    assert ("high_missing", "sparse") in codes
    assert ("constant_column", "const") in codes
    assert ("non_numeric_column", "label") in codes
    # all_null_column is error severity -> overall not passed
    assert result["passed"] is False


def test_diagnose_worksheet_clean_data_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [0.0, 1.0, 2.0], "y": [1.5, 2.5, 9.0]}))
    monkeypatch.setattr(client, "_find_sheet", lambda **_kwargs: wks)

    result = client.diagnose_worksheet()

    assert result["passed"] is True
    assert result["issues"] == []


def test_axis_range_issues_detects_silent_clipping() -> None:
    client = OriginClient()

    log_zero = client._axis_range_issues(0, "y", {"scale_name": "log10", "limits": [0, 100, 1]})
    assert [i["code"] for i in log_zero] == ["nonpositive_log_axis"]
    assert log_zero[0]["severity"] == "error"

    rev = client._axis_range_issues(1, "x", {"scale_name": "linear", "limits": [10, 2, 1]})
    assert [i["code"] for i in rev] == ["reversed_axis_limits"]
    assert rev[0]["severity"] == "info"

    degenerate = client._axis_range_issues(0, "x", {"scale_name": "linear", "limits": [5, 5, 1]})
    assert [i["code"] for i in degenerate] == ["degenerate_axis_limits"]

    ok_axis = {"scale_name": "linear", "limits": [-0.1, 6.1, 1.0]}
    assert client._axis_range_issues(0, "x", ok_axis) == []

    # z axis with no limits (common) must not be flagged
    empty_z = client._axis_range_issues(0, "z", {"scale_name": None, "limits": [None, None]})
    assert empty_z == []
