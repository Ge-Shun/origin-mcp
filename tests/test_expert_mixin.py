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


def test_multivariate_analysis_builds_controlled_ranges(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Measurements",
        pd.DataFrame({"group": [1, 2], "a": [2, 3], "b": [4, 5], "response": [6, 7]}),
    )

    clustered = fake_client.multivariate_analysis(
        method="kmeans",
        worksheet="Measurements",
        columns=["a", "b"],
        options={"num": 3, "std": "snd", "anova": True},
        output_book="ClusterReport",
    )
    discriminant = fake_client.multivariate_analysis(
        method="discrim",
        worksheet="Measurements",
        columns=["a", "b"],
        group_col="group",
    )

    assert clustered["script"].startswith("kmeans ")
    assert "ir:=[Measurements]Sheet1!(2:3)" in clustered["script"]
    assert "num:=3" in clustered["script"]
    assert "rt:=[ClusterReport]<new>" in clustered["script"]
    assert "group:=[Measurements]Sheet1!(group)" in discriminant["script"]
    assert "var:=[Measurements]Sheet1!(2:3)" in discriminant["script"]


def test_nonparametric_and_survival_dispatchers(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Study",
        pd.DataFrame(
            {
                "time": [1, 2],
                "censor": [0, 1],
                "group": [1, 2],
                "value_a": [3, 4],
                "value_b": [5, 6],
            }
        ),
    )

    nonparametric = fake_client.nonparametric_test(
        test="mann_whitney",
        worksheet="Study",
        columns=["value_a", "value_b"],
        tail="upper",
        exact=True,
    )
    survival = fake_client.survival_analysis(
        method="kaplan_meier",
        worksheet="Study",
        time_col="time",
        censor_col="censor",
        group_col="group",
        censor_values=[0, -1],
        options={"logrank": True, "sfci": True},
    )

    assert nonparametric["script"].startswith("mwtest ")
    assert "type:=1" in nonparametric["script"]
    assert "tail:=upper" in nonparametric["script"]
    assert "exact:=1" in nonparametric["script"]
    assert survival["script"].startswith("kaplanmeier ")
    assert "irng:=[Study]Sheet1!(1,2,3)" in survival["script"]
    assert "censor:={0.0,-1.0}" in survival["script"]
    assert "logrank:=1" in survival["script"]

    single_censor = fake_client.survival_analysis(
        method="kaplan_meier",
        worksheet="Study",
        time_col="time",
        censor_col="censor",
        censor_values=[0],
    )
    assert "censor:=0.0" in single_censor["script"]
    assert "censor:={" not in single_censor["script"]


def test_advanced_statistics_reject_unknown_options(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"a": [1], "b": [2]}))

    with pytest.raises(OriginOperationError):
        fake_client.multivariate_analysis(
            method="kmeans",
            worksheet="Data",
            columns=["a", "b"],
            options={"script": "exit"},
        )
