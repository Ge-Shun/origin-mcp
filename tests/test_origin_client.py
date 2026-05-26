import struct
import zlib
from pathlib import Path

import pandas as pd
import pytest

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
    assert result["raw_result"] == {"result": False}


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
    assert {"name": "B1", "path": "coefVec[2]", "value": 2.0, "stderr": 0.2} in result[
        "parameters"
    ]
    assert result["metrics"]["RSquare"] == 0.99
    assert result["metrics"]["RSqCOD"] == 0.99


def test_structure_fit_result_extracts_parameters_and_metrics() -> None:
    client = OriginClient()

    structured = client._structure_fit_result(
        {
            "Parameters": {"Slope": 2.0, "Intercept": 1.0},
            "Statistics": {"RSquare": 0.99},
        }
    )

    assert {"name": "Slope", "path": "Parameters.Slope", "value": 2.0} in structured[
        "parameters"
    ]
    assert structured["metrics"]["RSquare"] == 0.99


def test_origin_name_matches_truncated_short_name() -> None:
    assert OriginClient._origin_name_matches("OfficialImport", {"OfficialImpor"})
    assert OriginClient._origin_name_matches("Book1", {"Book1"})
    assert not OriginClient._origin_name_matches("OtherBook", {"Book1"})


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

    def __init__(self, layer: "FakeLayer | None" = None) -> None:
        self.layer = layer

    def __len__(self) -> int:
        return 1 if self.layer is not None else 0

    def __getitem__(self, index: int) -> "FakeLayer":
        if index != 0 or self.layer is None:
            raise IndexError(index)
        return self.layer


class FakePlot:
    name = "Plot1"

    def __init__(self) -> None:
        self.commands = []
        self.removed = False
        self.symbol_size = 0

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


class FakeLayer:
    name = "Layer1"

    def __init__(self, plots: list[FakePlot] | None = None) -> None:
        self.plots = plots if plots is not None else []
        self.added = []
        self.labels = {}
        self.axes = {"x": FakeAxis(), "y": FakeAxis(), "z": FakeAxis()}

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
    graph = FakeGraph(FakeLayer([FakePlot()]))
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.get_graph_info("Graph1")

    assert result["layers_count"] == 1
    assert result["layers"][0]["plots_count"] == 1
    assert result["layers"][0]["axes"]["x"]["scale"] == "linear"


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


def test_format_graph_formats_axis_titles_and_title(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    layer = FakeLayer()
    graph = FakeGraph(layer)
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)

    client.format_graph(
        "Graph1",
        title="CO_2 response",
        x_label="time (s)",
        y_label="rate m^-2",
        rescale=True,
    )

    assert layer.axis("x").title == "time (s)"
    assert layer.axis("y").title == "rate m\\+(-2)"
    assert next(iter(layer.labels.values())).text == "CO\\-(2) response"


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
    assert 'win -a "Graph 1"; expGraph pages:="Graph 1" type:=png path:="' in scripts[0]
    assert 'filename:="graph" overwrite:=replace;' in scripts[0]


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
    publication_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(
        client,
        "apply_publication_style",
        lambda **kwargs: publication_calls.append(kwargs) or {"styled": True},
    )

    worksheet, graph_ref = client.plot_table(path=path, kind="scatter", show_legend=False)

    assert worksheet.rows == 1
    assert graph_ref.template == "scatter"
    assert graph_ref.style_mode == "origin_default"
    assert publication_calls == []


def test_plot_table_publication_style_applies_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n0,1\n", encoding="utf-8")
    client = OriginClient()
    wks = FakeWorksheet()
    graph = FakeGraph(FakeLayer())
    publication_calls = []
    monkeypatch.setattr(client, "_new_sheet", lambda **_kwargs: wks)
    monkeypatch.setattr(client, "_new_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(client, "_rescale", lambda _layer: None)
    monkeypatch.setattr(
        client,
        "apply_publication_style",
        lambda **kwargs: publication_calls.append(kwargs) or {"styled": True},
    )

    _, graph_ref = client.plot_table(
        path=path,
        kind="line",
        show_legend=False,
        style_mode="publication",
    )

    assert graph_ref.style_mode == "publication"
    assert publication_calls == [{"graph_name": "Graph1"}]


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
        lambda path_arg, graph_name: export_calls.append((path_arg, graph_name))
        or {"path": str(path_arg)},
    )

    _worksheet, graph_ref = client.plot_table(
        path=path,
        kind="line",
        graph_name="NamedLine",
        export_path=export_path,
    )

    assert graph_ref.export_path == str(export_path)
    assert export_calls == [(export_path, "Graph1")]


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


def test_apply_publication_style_updates_plots(monkeypatch: pytest.MonkeyPatch) -> None:
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

    result = client.apply_publication_style("Graph1", page_width=None, page_height=None)

    assert result["styled_plots"] == 1
    assert "-w 2.0" in plot.commands
    assert plot.symbol_size == 8.0
    assert "layer.x.label.pt=18;" in scripts[-1]


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
    assert "-w 1.2" in plot.commands
    assert plot.symbol_size == 4.5
    assert plot.color == (0, 114, 178)
    assert plot.transparency == 0
    assert 'layer.x.label.font$="Arial";' in scripts[-1]
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
    assert "-w 0.8" in plot.commands
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

    assert hero.color == (0, 114, 178)
    assert baseline.color == (0, 0, 0)
    assert result["applied_palette_roles"] == ["hero", "baseline"]
    assert result["diagnostics"]["checklist"][3]["name"] == "palette"
    assert result["diagnostics"]["checklist"][3]["passed"] is True


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
    plot.color = (213, 94, 0)
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


def test_chart_atlas_route_selects_correlation_scatter() -> None:
    client = OriginClient()

    route = client.chart_atlas_route("correlation", columns=["x", "y"])

    assert route["intent"] == "correlation"
    assert route["kind"] == "scatter"
    assert route["regression"] is True
    assert route["palette_role"] == "hero"


def test_plot_chart_atlas_applies_route_style_and_regression(
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
    assert calls["style"]["palette_role"] == "hero"
    assert calls["fit"]["worksheet"] == worksheet
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


def test_add_plot_supports_extended_plot_types() -> None:
    client = OriginClient()
    wks = FakeWorksheet(pd.DataFrame({"x": [0], "y": [1], "z": [2]}))
    layer = FakeLayer()

    client._add_plot(layer, wks, x_name="x", y_name="y", z_name="z", kind="surface3d")

    assert layer.added[0][1]["type"] == "surface"


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
    assert "plotxy iy:=[Book1]Sheet1!(1,2,3) plot:=193" in scripts[-1]


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
    assert "plotxyz iz:=[Book1]Sheet1!(1,2,3) plot:=240" in scripts[-1]


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
    assert "worksheet -s 1 0 6 0; worksheet -p 183 gl3DVector;" in scripts[-1]


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
    assert "plotm im:=[MBook1]MSheet1!1 plot:=105" in scripts[-1]


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
    assert "plotm im:=[MBook1]MSheet1!1 plot:=103" in scripts[-1]


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
