from pathlib import Path

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


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


def test_origin_name_matches_truncated_short_name() -> None:
    assert OriginClient._origin_name_matches("OfficialImport", {"OfficialImpor"})
    assert OriginClient._origin_name_matches("Book1", {"Book1"})
    assert not OriginClient._origin_name_matches("OtherBook", {"Book1"})


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


def test_set_graph_page_updates_fake_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OriginClient()
    graph = FakeGraph()
    monkeypatch.setattr(client, "_find_or_active_graph", lambda _name: graph)

    result = client.set_graph_page(graph_name="Graph1", width=6.0, height=4.0)

    assert result["page"]["width"] == 6.0
    assert graph.width == 6.0
    assert graph.height == 4.0


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
