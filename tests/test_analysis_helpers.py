"""Unit tests for the pure / near-pure helpers on ``_AnalysisMixin``.

These methods shape analysis output without driving Origin: some build LabTalk
variable-name maps (no originpro at all), and ``_structure_scalar_outputs`` only
needs ``op.lt_float`` to evaluate the variables. The latter is exercised by
injecting a tiny fake ``op`` onto ``client._op`` so the lazy ``op`` property
returns it instead of importing the real ``originpro`` package.

This file is the worked example for closing the client-mixin coverage gap; the
same ``_op`` injection pattern extends to the sheet-building helpers once a
reusable fake-worksheet fixture exists.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from origin_mcp.origin_client import OriginClient


def test_list_fit_functions_is_self_describing() -> None:
    result = OriginClient().list_fit_functions()

    assert result["count"] == len(result["functions"])
    names = {fn["name"] for fn in result["functions"]}
    assert {"Gauss", "Lorentz", "ExpDec1", "Boltzmann"} <= names
    for fn in result["functions"]:
        assert fn["parameters"], f"{fn['name']} has no parameters listed"


def test_polynomial_output_variables_are_unique_and_complete() -> None:
    variables = OriginClient._polynomial_output_variables()

    assert set(variables) == {"coef", "err", "N", "AdjRSq", "RSqCOD"}
    # Distinct LabTalk names with a shared per-call random prefix.
    assert len(set(variables.values())) == len(variables)
    prefixes = {name[:8] for name in variables.values()}
    assert len(prefixes) == 1
    # Two calls must not collide on the same prefix.
    assert OriginClient._polynomial_output_variables() != variables


def test_moments_output_variables_cover_descriptive_stats() -> None:
    variables = OriginClient._moments_output_variables()

    assert set(variables) == {
        "mean",
        "sd",
        "se",
        "n",
        "sum",
        "skewness",
        "kurtosis",
        "cv",
    }
    assert len(set(variables.values())) == len(variables)


def test_prepare_scalar_outputs_maps_each_name() -> None:
    names = ("stat", "prob", "df")
    variables = OriginClient._prepare_scalar_outputs(names)

    assert set(variables) == set(names)
    assert len(set(variables.values())) == len(names)


class _FakeOp:
    """Minimal originpro stand-in exposing only ``lt_float``."""

    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values

    def lt_float(self, expression: str) -> Any:
        # Mirror originpro: returns the LabTalk variable's float value.
        return self._values[expression]


def test_structure_scalar_outputs_renames_and_filters() -> None:
    client = OriginClient()
    variables = {"stat": "v_stat", "prob": "v_prob", "df": "v_df"}
    # ``prob`` evaluates to a non-finite/missing value and must be dropped.
    client._op = _FakeOp({"v_stat": 12.5, "v_prob": float("nan"), "v_df": 4.0})

    structured = client._structure_scalar_outputs(variables)

    # Known keys are renamed to their report labels; NaN ``prob`` is filtered out.
    assert structured["metrics"] == {"Statistic": 12.5, "DF": 4.0}
    # The raw variable map is preserved for traceability.
    assert structured["sections"]["scalar_variables"] == variables


def test_structure_scalar_outputs_keeps_unknown_keys_verbatim() -> None:
    client = OriginClient()
    client._op = _FakeOp({"v_custom": 7.0})

    structured = client._structure_scalar_outputs({"custom": "v_custom"})

    # Unmapped keys fall through unchanged rather than being dropped.
    assert structured["metrics"] == {"custom": 7.0}


# -- sheet-building helpers (need the fake worksheet surface) --------------


def test_analysis_output_reads_existing_sheet(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Result", pd.DataFrame({"a": [1, 2], "b": [3, 4]}))

    output = fake_client._analysis_output("Result", max_rows=10)

    assert output["total_rows"] == 2
    assert output["columns"] == ["a", "b"]


def test_analysis_output_reports_missing_sheet(fake_client: OriginClient) -> None:
    output = fake_client._analysis_output("DoesNotExist")

    assert output["found"] is False
    assert output["output_sheet"] == "DoesNotExist"


def test_prepare_report_output_creates_sheet(fake_client: OriginClient) -> None:
    prepared = fake_client._prepare_report_output("Stats")

    assert prepared["worksheet"].startswith("[")
    assert prepared["ref"].endswith("!")
    # A backing sheet now exists in the fake project.
    assert fake_client.op.books


def test_prepare_analysis_xy_output_passthrough_for_explicit_range(
    fake_client: OriginClient,
) -> None:
    # A range that already contains "!" is returned verbatim.
    assert fake_client._prepare_analysis_xy_output("[Book1]Sheet1!(1,2)") == "[Book1]Sheet1!(1,2)"


def test_prepare_peak_find_outputs_builds_columns(fake_client: OriginClient) -> None:
    prepared = fake_client._prepare_peak_find_outputs("Peaks")

    assert prepared["ocenter"].endswith("!(1)")
    assert prepared["ocenter_x"].endswith("!(2)")
    assert prepared["ocenter_y"].endswith("!(3)")
