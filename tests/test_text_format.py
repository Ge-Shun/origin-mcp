import pandas as pd

from origin_mcp.text_format import (
    humanize_field_name,
    infer_axis_title,
    infer_series_labels,
    origin_rich_text,
)


def test_origin_rich_text_converts_unicode_super_and_subscripts() -> None:
    assert origin_rich_text("CO₂ flux (m⁻² s⁻¹)") == "CO\\-(2) flux (m\\+(-2) s\\+(-1))"


def test_origin_rich_text_converts_markup_and_braced_notation() -> None:
    assert origin_rich_text("E^{1/2} and x_{max}") == "E\\+(1/2) and x\\-(max)"
    assert origin_rich_text("H<sub>2</sub>O m<sup>2</sup>") == "H\\-(2)O m\\+(2)"


def test_origin_rich_text_converts_single_letter_subscripts() -> None:
    assert origin_rich_text("signal_a and CO_2") == "signal\\-(a) and CO\\-(2)"


def test_origin_rich_text_avoids_multi_letter_identifier_underscores() -> None:
    assert origin_rich_text("sample_id and run_a1") == "sample_id and run_a1"


def test_origin_rich_text_preserves_existing_origin_escape_sequences() -> None:
    assert origin_rich_text("CO\\-(2)") == "CO\\-(2)"


def test_origin_rich_text_converts_common_unit_symbols_to_unicode_escapes() -> None:
    assert origin_rich_text("Dose (μM), 25 °C") == r"Dose (\x(00B5)M), 25 \x(00B0)C"


def test_humanize_field_name_formats_words_acronyms_and_units() -> None:
    assert humanize_field_name("measured_response") == "Measured response"
    assert humanize_field_name("origin_mcp_minutes") == "Origin MCP minutes"
    assert humanize_field_name("dose_uM") == r"Dose (\x(00B5)M)"
    assert humanize_field_name("duration_s") == "Duration (s)"
    assert humanize_field_name("temperature_C") == r"Temperature (\x(00B0)C)"
    assert humanize_field_name("glucose_mg_dL") == "Glucose (mg/dL)"


def test_axis_title_inference_extracts_shared_metric_and_unit() -> None:
    inferred = infer_axis_title(
        ["glucose_control_mg_dL", "glucose_treated_mg_dL"]
    )

    assert inferred.label == "Glucose (mg/dL)"
    assert inferred.unit == "mg/dL"
    assert infer_series_labels(
        ["glucose_control_mg_dL", "glucose_treated_mg_dL"]
    ) == ["Control", "Treated"]


def test_axis_title_inference_understands_statistics_and_temperature_unit() -> None:
    inferred = infer_axis_title(["temperature_mean_C", "temperature_std_C"])

    assert inferred.label == r"Temperature (\x(00B0)C)"
    assert infer_series_labels(["temperature_mean_C", "temperature_std_C"]) == [
        "Mean",
        "SD",
    ]


def test_axis_title_inference_uses_value_unit_table_structure() -> None:
    table = pd.DataFrame(
        {
            "sample": ["A", "B"],
            "metric": ["Temperature", "Temperature"],
            "value": [25.2, 26.1],
            "unit": ["C", "C"],
        }
    )

    inferred = infer_axis_title(["value"], table=table)

    assert inferred.label == r"Temperature (\x(00B0)C)"
    assert inferred.reason == "table_metric_unit_columns"


def test_axis_title_inference_uses_chart_title_when_fields_only_name_series() -> None:
    inferred = infer_axis_title(
        ["compound_a", "compound_b", "compound_c"],
        title_hint="Dose response comparison",
        x_name="dose_uM",
    )

    assert inferred.label == "Response"
    assert infer_series_labels(["compound_a", "compound_b", "compound_c"]) == [
        "Compound a",
        "Compound b",
        "Compound c",
    ]


def test_infer_series_labels_can_omit_units_for_dual_axis_legend() -> None:
    assert infer_series_labels(
        ["temperature_control_C", "pressure_control_kPa"],
        omit_units_when_metrics_differ=True,
    ) == ["Temperature control", "Pressure control"]
