from __future__ import annotations

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_xfunction_catalog_is_schema_driven(fake_client: OriginClient) -> None:
    catalog = fake_client.list_xfunctions(category="signal")

    names = {item["name"] for item in catalog["xfunctions"]}
    assert {"smooth", "fft_filters", "stft", "hilbert", "envelope"} <= names
    fft = next(item for item in catalog["xfunctions"] if item["name"] == "fft_filters")
    assert fft["arguments"]["filter"]["choices"] == [
        "low",
        "high",
        "bandpass",
        "bandblock",
        "threshold",
        "lowpp",
    ]


def test_controlled_xfunction_validates_name_and_arguments(fake_client: OriginClient) -> None:
    result = fake_client.run_xfunction(
        "smooth",
        {"iy": "[Book]Sheet!(1,2)", "method": "sg", "npts": 7, "polyorder": 3},
    )
    assert result["script"] == ("smooth iy:=[Book]Sheet!(1,2) method:=sg npts:=7 polyorder:=3;")

    with pytest.raises(OriginOperationError) as excinfo:
        fake_client.run_xfunction("exit", {})
    assert excinfo.value.error_code == "xfunction_not_allowed"

    with pytest.raises(OriginOperationError):
        fake_client.run_xfunction("smooth", {"unexpected": 1})
    with pytest.raises(OriginOperationError):
        fake_client.run_xfunction("smooth", {"iy": "[Book]Sheet!1; exit"})
    with pytest.raises(OriginOperationError):
        fake_client.run_xfunction("smooth", {"method": "mystery"})


def test_fft_filter_builds_output_and_validates_cutoffs(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Signal", pd.DataFrame({"time": [0, 1, 2], "value": [1, 4, 1]}))

    result = fake_client.fft_filter(
        worksheet="Signal",
        x_col="time",
        y_col="value",
        filter_type="bandpass",
        lower_cutoff=1.0,
        upper_cutoff=5.0,
        output_book="FilteredBook",
    )

    assert "filter:=bandpass" in result["script"]
    assert "freq1:=1.0" in result["script"]
    assert "freq2:=5.0" in result["script"]
    assert result["output_worksheet"]["book_name"] == "FilteredBook"

    with pytest.raises(OriginOperationError):
        fake_client.fft_filter(
            worksheet="Signal",
            y_col="value",
            filter_type="bandpass",
            lower_cutoff=5,
            upper_cutoff=1,
        )


def test_pca_builds_range_from_columns(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Measurements",
        pd.DataFrame({"id": [1], "a": [2], "b": [3], "c": [4]}),
    )

    result = fake_client.principal_component_analysis(
        worksheet="Measurements",
        columns=["a", "b", "c"],
        matrix_type="cov",
        components=2,
        score_plot=True,
    )

    assert "irng:=[Measurements]Sheet1!(2:4)" in result["script"]
    assert "mtype:=cov" in result["script"]
    assert "splot:=1" in result["script"]
    assert result["originpro_only"] is True


def test_one_way_anova_uses_origin_operation_framework(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Groups", pd.DataFrame({"control": [1, 2], "drug_a": [2, 3], "drug_b": [4, 5]})
    )

    result = fake_client.one_way_anova(
        worksheet="Groups",
        group_columns=["control", "drug_a", "drug_b"],
    )

    assert result["group_columns"] == ["control", "drug_a", "drug_b"]
    assert "classname:=ANOVAOneWay" in result["script"]
    assert "InputData.Use=1" in result["script"]
    assert "xop execute:=cleanup" in result["script"]
