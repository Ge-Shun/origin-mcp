"""Behavioural tests for the pandas-backed data-transform methods."""

from __future__ import annotations

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_filter_rows_combines_and(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2, 3, 4], "g": ["a", "a", "b", "b"]}))

    result = fake_client.filter_rows(
        conditions=[{"column": "x", "op": "gt", "value": 1}, {"column": "g", "value": "a"}],
        combine="and",
    )

    assert result["matched_rows"] == 1
    assert result["total_rows"] == 4


def test_filter_rows_requires_conditions(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1]}))
    with pytest.raises(OriginOperationError):
        fake_client.filter_rows(conditions=[])


def test_drop_duplicates_removes_repeats(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 1, 2], "y": [9, 9, 8]}))

    result = fake_client.drop_duplicates()

    assert result["removed_rows"] == 1
    assert result["total_rows"] == 3


def test_fill_missing_with_value(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1.0, None, 3.0]}))

    result = fake_client.fill_missing(strategy="value", value=0)

    assert result["strategy"] == "value"
    sheet = fake_client.op.find_sheet("w", "Data")
    assert sheet is not None and sheet.to_df()["x"].tolist() == [1.0, 0.0, 3.0]


def test_fill_missing_value_requires_value(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1.0, None]}))
    with pytest.raises(OriginOperationError):
        fake_client.fill_missing(strategy="value", value=None)


def test_fill_missing_mean(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [2.0, None, 4.0]}))

    fake_client.fill_missing(strategy="mean")

    sheet = fake_client.op.find_sheet("w", "Data")
    assert sheet is not None and sheet.to_df()["x"].tolist() == [2.0, 3.0, 4.0]


def test_fill_missing_rejects_unknown_strategy(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1.0, None]}))
    with pytest.raises(OriginOperationError):
        fake_client.fill_missing(strategy="bogus")


def test_transpose_worksheet_with_label_column(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Data", pd.DataFrame({"name": ["m1", "m2"], "v1": [1, 2], "v2": [3, 4]})
    )

    result = fake_client.transpose_worksheet(label_column="name", output_sheet="T")

    cols = result["worksheet"]["columns"]
    assert cols[0] == "Field"
    assert "m1" in cols and "m2" in cols


def test_merge_worksheets_inner_join(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Left", pd.DataFrame({"id": [1, 2], "a": [10, 20]}))
    fake_client.op.add_book("Right", pd.DataFrame({"id": [2, 3], "b": [200, 300]}))

    result = fake_client.merge_worksheets(
        book_name="Left",
        right_book="Right",
        on="id",
        how="inner",
        output_book="Merged",
    )

    assert result["how"] == "inner"
    assert result["result_rows"] == 1


def test_merge_worksheets_rejects_bad_how(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Left", pd.DataFrame({"id": [1]}))
    fake_client.op.add_book("Right", pd.DataFrame({"id": [1]}))
    with pytest.raises(OriginOperationError):
        fake_client.merge_worksheets(book_name="Left", right_book="Right", on="id", how="diagonal")


def test_concat_worksheets_rows(fake_client: OriginClient) -> None:
    fake_client.op.add_book("A", pd.DataFrame({"x": [1, 2]}))
    fake_client.op.add_book("B", pd.DataFrame({"x": [3]}))

    result = fake_client.concat_worksheets(
        others=[{"book": "B"}],
        axis="rows",
        book_name="A",
        output_book="Combined",
    )

    assert result["result_rows"] == 3
    assert result["combined_sheets"] == 2


def test_concat_worksheets_rejects_bad_axis(fake_client: OriginClient) -> None:
    fake_client.op.add_book("A", pd.DataFrame({"x": [1]}))
    with pytest.raises(OriginOperationError):
        fake_client.concat_worksheets(others=[{"book": "A"}], axis="depth", book_name="A")


def test_pivot_worksheet(fake_client: OriginClient) -> None:
    df = pd.DataFrame(
        {
            "row": ["r1", "r1", "r2"],
            "col": ["c1", "c2", "c1"],
            "val": [1.0, 2.0, 3.0],
        }
    )
    fake_client.op.add_book("Data", df)

    result = fake_client.pivot_worksheet(
        index="row", columns="col", values="val", aggfunc="mean", output_sheet="P"
    )

    assert result["aggfunc"] == "mean"
    assert "row" in result["worksheet"]["columns"]


def test_melt_worksheet(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"id": [1, 2], "a": [10, 20], "b": [30, 40]}))

    result = fake_client.melt_worksheet(id_vars=["id"], value_vars=["a", "b"])

    assert set(result["worksheet"]["columns"]) == {"id", "variable", "value"}
    assert result["worksheet"]["rows"] == 4
