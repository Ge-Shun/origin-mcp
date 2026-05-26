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
