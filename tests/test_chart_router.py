from __future__ import annotations

from pathlib import Path

import pandas as pd

from origin_mcp.chart_router import profile_table, recommend_chart
from origin_mcp.origin_client import OriginClient


def _selected(df: pd.DataFrame, intent: str | None = None) -> dict[str, object]:
    return recommend_chart(profile_table(df), intent=intent)["selected"]


def test_recommends_time_series_for_date_and_numeric_values() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "signal": [1.0, 1.5, 2.0],
        }
    )

    selected = _selected(df)

    assert selected["chart"] == "time_series"
    assert selected["kind"] == "line"
    assert selected["x_col"] == "date"


def test_recommends_scatter_for_paired_numeric_relationship() -> None:
    df = pd.DataFrame({"dose": [0, 1, 2, 3], "response": [0.1, 0.4, 0.7, 0.9]})

    selected = _selected(df, intent="correlation")

    assert selected["chart"] == "scatter"
    assert selected["kind"] == "scatter"
    assert selected["x_col"] == "dose"
    assert selected["y_cols"] == ["response"]


def test_recommends_error_bar_when_error_column_is_present() -> None:
    df = pd.DataFrame(
        {
            "dose": [0, 1, 2],
            "mean": [0.2, 0.5, 0.8],
            "stderr": [0.03, 0.04, 0.05],
        }
    )

    selected = recommend_chart(
        profile_table(df),
        intent="effect_size",
        x_col="dose",
        y_cols=["mean"],
        y_error_col="stderr",
    )["selected"]

    assert selected["chart"] == "error_bar"
    assert selected["plot_type_id"] == 231
    assert selected["selected_cols"] == ["dose", "mean", "stderr"]


def test_recommends_candlestick_for_ohlc_columns() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "open": [10.0, 11.0],
            "high": [12.0, 13.0],
            "low": [9.0, 10.0],
            "close": [11.0, 12.0],
        }
    )

    selected = _selected(df)

    assert selected["chart"] == "candlestick"
    assert selected["plot_type_id"] == 221
    assert selected["selected_cols"] == ["date", "open", "high", "low", "close"]


def test_recommends_ternary_for_compositional_triplets() -> None:
    df = pd.DataFrame(
        {
            "ternary_a": [0.6, 0.5, 0.3],
            "ternary_b": [0.3, 0.2, 0.4],
            "ternary_c": [0.1, 0.3, 0.3],
        }
    )

    selected = _selected(df, intent="composition")

    assert selected["chart"] == "ternary"
    assert selected["plot_type_id"] == 245


def test_recommends_histogram_for_single_numeric_column() -> None:
    df = pd.DataFrame({"value": [1, 2, 2, 3, 5, 8]})

    selected = _selected(df, intent="histogram")

    assert selected["chart"] == "histogram"
    assert selected["plot_type_id"] == 219


def test_recommends_contour_for_regular_xyz_grid() -> None:
    df = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "y": [0, 1, 0, 1],
            "z": [0.1, 0.2, 0.3, 0.4],
        }
    )

    selected = _selected(df, intent="matrix")

    assert selected["chart"] == "contour"
    assert selected["plot_type_id"] == 243
    assert selected["selected_cols"] == ["x", "y", "z"]


def test_origin_client_recommend_chart_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "signals.csv"
    path.write_text("time,signal_a,signal_b\n0,0.1,0.2\n1,0.4,0.5\n", encoding="utf-8")

    result = OriginClient().recommend_chart(path, intent="time_series")

    assert result["selected"]["chart"] == "multi_series_line"
    assert result["selected"]["kind"] == "line"
    assert result["profile"]["row_count"] == 2
