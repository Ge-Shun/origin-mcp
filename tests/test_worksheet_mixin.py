"""Behavioural tests for ``_WorksheetMixin`` against the in-memory fake Origin.

These exercise the pandas round-trip logic (read/write/sort/cells/transforms)
that previously only ran under live Origin validation.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest
from fake_origin import FakeOp

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient

# -- read / write ---------------------------------------------------------


def test_read_worksheet_windows_rows(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    result = fake_client.read_worksheet(start_row=1, max_rows=2)

    assert result["total_rows"] == 4
    assert result["returned_rows"] == 2
    assert result["columns"] == ["x", "y"]
    assert [row["x"] for row in result["rows"]] == [2, 3]


def test_read_worksheet_selects_columns(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    result = fake_client.read_worksheet(columns=["y"])

    assert result["columns"] == ["y"]
    assert all(set(row) == {"y"} for row in result["rows"])


@pytest.mark.parametrize("kwargs", [{"start_row": -1}, {"max_rows": 0}])
def test_read_worksheet_validates_bounds(
    fake_client: OriginClient, sample_df: pd.DataFrame, kwargs: dict[str, int]
) -> None:
    fake_client.op.add_book("Data", sample_df)
    with pytest.raises(OriginOperationError):
        fake_client.read_worksheet(**kwargs)


def test_write_worksheet_creates_and_trims(fake_client: OriginClient) -> None:
    # Seed a wider sheet so writing a narrower frame must trim trailing columns.
    fake_client.op.add_book("Out", pd.DataFrame({"a": [1], "b": [2], "c": [3]}))

    result = fake_client.write_worksheet(
        rows=[{"a": 1, "b": 2}, {"a": 3, "b": 4}],
        book_name="Out",
    )

    assert result["worksheet"]["columns"] == ["a", "b"]
    sheet = fake_client.op.find_sheet("w", "Out")
    assert sheet is not None and list(sheet.to_df().columns) == ["a", "b"]


def test_write_worksheet_rejects_empty(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.write_worksheet(rows=[], create=True)


def test_worksheet_info_reports_columns(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    info = fake_client.worksheet_info()

    assert info["columns_count"] == 2
    assert info["rows"] == 4
    assert info["labels"]["L"] == ["x", "y"]


def test_sort_worksheet_orders_descending(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [3, 1, 2], "y": [1, 2, 3]}))

    result = fake_client.sort_worksheet(by="x", ascending=False)

    assert result["sorted_by"] == "x"
    sheet = fake_client.op.find_sheet("w", "Data")
    assert sheet is not None and sheet.to_df()["x"].tolist() == [3, 2, 1]


# -- cells ----------------------------------------------------------------


def test_get_cell_value_reads(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    result = fake_client.get_cell_value(row=2, column="y")

    assert result["column"] == "y"
    assert result["value"] == 30.0


def test_get_cell_value_out_of_range(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)
    with pytest.raises(OriginOperationError):
        fake_client.get_cell_value(row=99, column=0)


def test_set_cell_value_writes(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    fake_client.set_cell_value(row=0, column="x", value=999)

    sheet = fake_client.op.find_sheet("w", "Data")
    assert sheet is not None and sheet.to_df()["x"].tolist()[0] == 999


def test_get_cell_value_returns_none_for_nan(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [math.nan, 2.0]}))

    result = fake_client.get_cell_value(row=0, column="x")

    assert result["value"] is None


# -- structural edits -----------------------------------------------------


def test_delete_columns_removes(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"a": [1], "b": [2], "c": [3]}))

    result = fake_client.delete_columns(columns=["b"])

    assert result["deleted_columns"] == ["b"]
    assert result["worksheet"]["columns"] == ["a", "c"]


def test_clear_worksheet_keeps_columns(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    result = fake_client.clear_worksheet(keep_columns=True)

    assert result["kept_columns"] is True
    assert result["worksheet"]["columns"] == ["x", "y"]
    assert result["worksheet"]["rows"] == 0


def test_clear_worksheet_drops_columns(fake_client: OriginClient, sample_df: pd.DataFrame) -> None:
    fake_client.op.add_book("Data", sample_df)

    result = fake_client.clear_worksheet(keep_columns=False)

    assert result["worksheet"]["columns"] == []


def test_diagnose_worksheet_flags_missing_and_constant(fake_client: OriginClient) -> None:
    df = pd.DataFrame(
        {
            "all_null": [math.nan, math.nan, math.nan],
            "constant": [5, 5, 5],
            "label": ["a", "b", "c"],
        }
    )
    fake_client.op.add_book("Data", df)

    report = fake_client.diagnose_worksheet()

    codes = {issue["code"] for issue in report["issues"]}
    assert "all_null_column" in codes
    assert "non_numeric_column" in codes


# -- export ---------------------------------------------------------------


def test_export_worksheet_csv(
    fake_client: OriginClient, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    fake_client.op.add_book("Data", sample_df)
    out = tmp_path / "export.csv"

    result = fake_client.export_worksheet_csv(path=out)

    assert Path(result["path"]).exists()
    assert result["rows"] == 4
    written = pd.read_csv(out)
    assert list(written.columns) == ["x", "y"]


def test_export_worksheet_csv_refuses_overwrite(
    fake_client: OriginClient, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    fake_client.op.add_book("Data", sample_df)
    out = tmp_path / "export.csv"
    out.write_text("existing", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.export_worksheet_csv(path=out, overwrite=False)


# -- import (file -> worksheet) ------------------------------------------


def test_import_table_loads_csv(fake_client: OriginClient, tmp_path: Path) -> None:
    csv = tmp_path / "in.csv"
    csv.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    ref = fake_client.import_table(path=csv, book_name="Imported")

    assert ref.columns == ["a", "b"]
    assert ref.rows == 2


def test_import_table_rejects_empty_file(fake_client: OriginClient, tmp_path: Path) -> None:
    csv = tmp_path / "empty.csv"
    csv.write_text("a,b\n", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.import_table(path=csv)


# -- worksheet_not_found path --------------------------------------------


def test_find_sheet_missing_raises() -> None:
    client = OriginClient()
    client._op = FakeOp()  # no books
    with pytest.raises(OriginOperationError) as excinfo:
        client.read_worksheet(book_name="Nope", sheet_name="Sheet1")
    assert excinfo.value.error_code == "worksheet_not_found"


# -- calculated columns & labels -----------------------------------------


def test_append_table_extends_sheet(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"a": [1], "b": [2]}))
    extra = tmp_path / "more.csv"
    extra.write_text("c,d\n5,6\n", encoding="utf-8")

    ref = fake_client.append_table(path=extra, book_name="Data", start_col=2)

    assert ref.columns == ["c", "d"]


def test_add_calculated_column(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2]}))

    result = fake_client.add_calculated_column(
        column_name="z", formula="col(x)*2", book_name="Data"
    )

    assert result["column_name"] == "z"
    assert result["formula"] == "col(x)*2"
    sheet = fake_client.op.find_sheet("w", "Data")
    assert sheet is not None and "z" in sheet.to_df().columns


def test_add_calculated_columns_validates_specs(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2]}))
    with pytest.raises(OriginOperationError):
        fake_client.add_calculated_columns(columns=[{"name": "z"}], book_name="Data")


def test_set_column_labels_records(fake_client: OriginClient) -> None:
    sheet = fake_client.op.add_book("Data", pd.DataFrame({"x": [1], "y": [2]}))

    fake_client.set_column_labels(labels=["Time", "Signal"], label_type="L", book_name="Data")

    assert sheet.label_calls
    applied_labels, label_type, _offset = sheet.label_calls[0]
    assert applied_labels == ["Time", "Signal"]
    assert label_type == "L"


def test_set_column_designations_records(fake_client: OriginClient) -> None:
    sheet = fake_client.op.add_book("Data", pd.DataFrame({"x": [1], "y": [2]}))

    fake_client.set_column_designations(spec="XY", book_name="Data")

    assert sheet.designation_calls
    assert sheet.designation_calls[0][0] == "XY"
