from __future__ import annotations

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_peak_analyzer_runs_saved_theme_in_script_mode(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Spectrum", pd.DataFrame({"x": [1, 2, 3], "y": [0, 5, 0]}))

    result = fake_client.peak_analyzer(
        worksheet="Spectrum",
        x_col="x",
        y_col="y",
        theme="My Peak Fit",
    )

    assert result["input_range"] == "[Spectrum]Sheet1!(x,y)"
    assert 'theme:="My Peak Fit"' in result["script"]
    assert "smode:=1" in result["script"]


def test_peak_analyzer_script_mode_requires_theme(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Spectrum", pd.DataFrame({"x": [1], "y": [2]}))

    with pytest.raises(OriginOperationError):
        fake_client.peak_analyzer(
            worksheet="Spectrum", x_col="x", y_col="y", dialog_mode="no_dialog"
        )


def test_peak_baseline_prepares_anchor_output(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Spectrum", pd.DataFrame({"x": [1, 2, 3], "y": [2, 1, 2]}))

    result = fake_client.peak_baseline(
        worksheet="Spectrum",
        x_col="x",
        y_col="y",
        threshold=0.1,
        anchor_count=5,
        output_book="Baseline",
    )

    assert result["output_range"] == "[Baseline]Anchors!(1,2)"
    assert "blauto" in result["script"]
    assert "number:=5" in result["script"]


def test_peak_analyzer_batch_builds_contiguous_multi_y_range(
    fake_client: OriginClient,
) -> None:
    fake_client.op.add_book(
        "Spectra",
        pd.DataFrame({"x": [1], "a": [2], "b": [3], "c": [4]}),
    )

    result = fake_client.peak_analyzer_batch(
        theme="Integrate Peaks",
        worksheet="Spectra",
        x_col="x",
        y_cols=["a", "b", "c"],
        result_sheet="integrate",
        output_sheet="[Summary]Results!",
        sequential_initialization=True,
        background_instances=3,
    )

    assert result["input_range"] == "[Spectra]Sheet1!(1,2:4)"
    assert result["result_sheet"] == "integrate"
    assert "paMultiY" in result["script"]
    assert "append:=integrate" in result["script"]
    assert "initvalues:=1" in result["script"]
    assert "instance:=3" in result["script"]


def test_peak_analyzer_batch_rejects_script_in_range(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.peak_analyzer_batch(
            theme="Peaks",
            input_range="[Book]Sheet!(1,2); exit",
        )
