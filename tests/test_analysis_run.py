"""Behavioural tests for ``run_analysis`` dispatch and structured fits."""

from __future__ import annotations

import pandas as pd
import pytest
from fake_origin import FakeLinearFit

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def _seed(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]}))


def test_run_analysis_smooth_executes(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(
        analysis="smooth", worksheet="Data", x_col="x", y_col="y", output_sheet="Result"
    )

    assert result["analysis"] == "smooth"
    assert result["executed"] is True
    assert "script" in result


def test_run_analysis_descriptive_stats(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(analysis="descriptive_stats", worksheet="Data", y_col="y")

    assert result["analysis"] == "descriptive_stats"
    assert "metrics" in result


def test_run_analysis_ttest_scalar_path(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(
        analysis="ttest_one_sample", worksheet="Data", y_col="y", options={"mean": 0}
    )

    assert result["analysis"] == "ttest_one_sample"
    assert result["executed"] is True


def test_run_analysis_fft_report_path(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(
        analysis="fft", worksheet="Data", x_col="x", y_col="y", output_sheet="FFTOut"
    )

    assert result["analysis"] == "fft"
    assert result["executed"] is True


def test_run_analysis_correlation_report_path(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(
        analysis="correlation",
        worksheet="Data",
        output_sheet="Corr",
        options={"spearman": True},
    )

    assert result["analysis"] == "correlation"


def test_run_analysis_peak_find_path(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.run_analysis(
        analysis="peak_find", worksheet="Data", x_col="x", y_col="y", output_sheet="Peaks"
    )

    assert result["analysis"] == "peak_find"


def test_linear_fit_result_result_mode(fake_client: OriginClient) -> None:
    _seed(fake_client)
    fake_client.op.LinearFit = FakeLinearFit  # type: ignore[attr-defined]

    result = fake_client.linear_fit_result(worksheet="Data", x_col="x", y_col="y")

    assert result["mode"] == "result"
    names = {param["name"].lower() for param in result["result"]["parameters"]}
    assert "slope" in names and "intercept" in names


def test_linear_fit_result_report_mode(fake_client: OriginClient) -> None:
    _seed(fake_client)
    fake_client.op.LinearFit = FakeLinearFit  # type: ignore[attr-defined]

    result = fake_client.linear_fit_result(
        worksheet="Data", x_col="x", y_col="y", options={"report": True}
    )

    assert result["mode"] == "report"
    assert result["report_sheet"] == "FitReport"


def test_linear_fit_result_requires_api(fake_client: OriginClient) -> None:
    _seed(fake_client)
    # No LinearFit on the fake op -> ensure_feature raises.
    with pytest.raises(OriginOperationError):
        fake_client.linear_fit_result(worksheet="Data", x_col="x", y_col="y")


def test_nonlinear_fit_structured_delegates(fake_client: OriginClient) -> None:
    _seed(fake_client)

    result = fake_client.nonlinear_fit_structured(
        worksheet="Data",
        x_col="x",
        y_col="y",
        function="Gauss",
        initial_params={"A": 1.0},
        fixed_params=["y0"],
    )

    assert result["analysis"] == "nonlinear_fit"


def test_nonlinear_fit_structured_rejects_empty_function(fake_client: OriginClient) -> None:
    _seed(fake_client)
    with pytest.raises(OriginOperationError):
        fake_client.nonlinear_fit_structured(worksheet="Data", x_col="x", y_col="y", function="  ")
