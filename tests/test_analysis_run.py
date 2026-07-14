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


def test_get_analysis_results_reads_and_normalizes_result_tree(
    fake_client: OriginClient,
) -> None:
    fake_client.op.add_book(
        "Report",
        pd.DataFrame({"Parameter": ["Slope"], "Value": [2.5]}),
        sheet="FitNL1",
    )
    fake_client.op.default_result_tree = {
        "Summary": {"RSquare": 0.98, "PValue": 0.001},
        "Parameters": {"Slope": 2.5, "Intercept": 1.0},
    }

    result = fake_client.get_analysis_results("[Report]FitNL1", max_rows=10)

    assert result["report_sheet"] == "[Report]FitNL1"
    assert result["metrics"]["Summary.RSquare"] == 0.98
    assert result["result_tree"]["Parameters"]["Slope"] == 2.5
    assert fake_client.op.lt_trees == {}


def test_get_analysis_results_groups_origin_parameter_nodes(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Report", pd.DataFrame({"Value": [2.5]}), sheet="FitLinear1")
    fake_client.op.default_result_tree = {
        "Parameters": {
            "Intercept": {"Value": 1.0, "Error": 0.2, "tValue": 5.0, "Prob": 0.01},
            "Slope": {"Value": 2.5, "Error": 0.3, "tValue": 8.3, "Prob": 0.001},
        }
    }

    result = fake_client.get_analysis_results("[Report]FitLinear1")

    assert result["parameters"] == [
        {
            "name": "Intercept",
            "path": "Parameters.Intercept.Value",
            "value": 1.0,
            "stderr": 0.2,
            "t_value": 5.0,
            "p_value": 0.01,
        },
        {
            "name": "Slope",
            "path": "Parameters.Slope.Value",
            "value": 2.5,
            "stderr": 0.3,
            "t_value": 8.3,
            "p_value": 0.001,
        },
    ]


def test_analysis_operation_can_be_read_and_recalculated(fake_client: OriginClient) -> None:
    fake_client.op.default_operation_tree = {"xfGetN": {"npts": 5, "method": "sg"}}

    inspected = fake_client.get_analysis_operation("[Data]Result!col(1)")
    recalculated = fake_client.recalculate_analysis(
        "[Data]Result!col(1)", settings={"xfGetN": {"npts": 11, "method": "sg"}}
    )

    assert inspected["settings"]["xfGetN"]["npts"] == 5
    assert recalculated["recalculated"] is True
    assert fake_client.op.last_operation_tree == {"xfGetN": {"npts": 11, "method": "sg"}}
    assert "op:=run" in recalculated["script"]


def test_analysis_operation_rejects_script_delimiters(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.recalculate_analysis("col(1); exit")
