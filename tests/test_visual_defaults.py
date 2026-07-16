from __future__ import annotations

import numpy as np

from origin_mcp.visual_defaults import (
    automatic_histogram_bin_width,
    decision_value,
    nice_datetime_scale,
    nice_numeric_scale,
    recommend_legend_placement,
    recommend_legend_position,
    resolve_visual_defaults,
    strict_datetime_values,
)


def test_automatic_histogram_bin_width_is_robust_and_bounded() -> None:
    values = np.linspace(0.0, 99.0, 100)

    width = automatic_histogram_bin_width(values)

    assert width is not None
    bins = int(np.ceil((values.max() - values.min()) / width))
    assert 5 <= bins <= 50


def test_automatic_histogram_bin_width_handles_degenerate_data() -> None:
    assert automatic_histogram_bin_width([1.0]) is None
    assert automatic_histogram_bin_width([2.0, 2.0, 2.0]) is None


def test_nice_numeric_scale_pads_extremes_without_clipping() -> None:
    scale = nice_numeric_scale(0.13, 0.87, 6)

    assert scale["from"] < 0.13
    assert scale["to"] > 0.87
    assert scale["step"] > 0
    assert np.isclose(
        (float(scale["to"]) - float(scale["from"])) / float(scale["step"]) + 1,
        scale["tick_count"],
    )


def test_nice_numeric_scale_handles_constant_and_zero_anchored_data() -> None:
    constant = nice_numeric_scale(5.0, 5.0, 6)
    bar = nice_numeric_scale(2.2, 9.7, 6, include_zero=True, anchor_zero=True)

    assert constant["from"] < 5.0 < constant["to"]
    assert bar["from"] == 0
    assert bar["to"] > 9.7


def test_strict_datetime_detection_accepts_iso_but_rejects_categories() -> None:
    parsed = strict_datetime_values(["2026-01-01", "2026-01-02 12:30"])

    assert parsed is not None
    assert parsed[1] is not None and parsed[1].hour == 12
    assert strict_datetime_values(["Stage 1", "Stage 2"]) is None
    assert strict_datetime_values(["01/02/2026", "02/02/2026"]) is None


def test_nice_datetime_scale_uses_aligned_ticks_and_safe_bounds() -> None:
    scale = nice_datetime_scale(["2026-01-03", "2026-04-17"], 6)

    assert scale is not None
    assert scale["from"] < "2026-01-03"
    assert scale["to"] > "2026-04-17"
    assert 3 <= scale["tick_count"] <= 9
    assert scale["label_type"] == "date"


def test_legend_position_avoids_increasing_series_upper_right() -> None:
    x = np.arange(10)
    assert recommend_legend_position(x, [x, x + 1]) == "inside_upper_left"


def test_legend_position_avoids_decreasing_series_upper_left() -> None:
    x = np.arange(10)
    assert recommend_legend_position(x, [10 - x, 9 - x]) == "inside_upper_right"


def test_smart_defaults_hide_redundant_legend_but_respect_override() -> None:
    automatic = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=10,
        x_values=np.arange(10),
        y_series=[np.arange(10)],
    )
    explicit = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=10,
        show_legend=True,
    )

    assert decision_value(automatic, "legend", "show") is False
    assert automatic["legend"]["show"]["reason"] == "single_series"
    assert decision_value(explicit, "legend", "show") is True
    assert explicit["legend"]["show"]["source"] == "user"


def test_smart_defaults_choose_installed_palette_for_nature_multi_series() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=3,
        row_count=20,
        x_values=np.arange(20),
        y_series=[np.arange(20), np.arange(20) + 1, np.arange(20) + 2],
        style_mode="nature",
    )

    assert decision_value(defaults, "palette_name") == "lcpmgh_auto"
    assert decision_value(defaults, "legend", "show") is True
    assert decision_value(defaults, "legend", "position") == "inside_upper_left"


def test_smart_defaults_explain_axis_titles_and_series_labels() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=2,
        row_count=20,
        x_values=np.arange(20),
        y_series=[np.arange(20), np.arange(20) + 1],
        x_name="time_s",
        y_names=["temperature_control_C", "temperature_treated_C"],
    )

    assert decision_value(defaults, "axes", "x_title") == "Time (s)"
    assert decision_value(defaults, "axes", "y_title") == r"Temperature (\x(00B0)C)"
    assert decision_value(defaults, "legend", "series_labels") == [
        "Control",
        "Treated",
    ]


def test_smart_defaults_move_large_legend_outside_and_widen_canvas() -> None:
    names = [f"response_condition_{index}" for index in range(8)]
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=len(names),
        row_count=20,
        x_values=np.arange(20),
        y_series=[np.arange(20) + index for index in range(len(names))],
        x_name="time_s",
        y_names=names,
    )

    assert decision_value(defaults, "legend", "position") == "outside_right"
    assert decision_value(defaults, "legend", "layout", "outside") is True
    assert decision_value(defaults, "canvas", "page_width_aspect_ratio") == 1.8
    assert decision_value(defaults, "canvas", "right_margin") == 0.28


def test_smart_defaults_reserve_external_legend_space_for_four_dual_y_series() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=4,
        row_count=20,
        x_values=np.arange(20),
        y_series=[np.arange(20) + index for index in range(4)],
        x_name="time_s",
        y_names=["temperature_control_C", "temperature_treated_C"],
        y2_names=["pressure_control_kPa", "pressure_treated_kPa"],
    )

    assert decision_value(defaults, "legend", "series_labels") == [
        "Temperature control",
        "Temperature treated",
        "Pressure control",
        "Pressure treated",
    ]
    assert decision_value(defaults, "legend", "position") == "inside_upper_left"
    assert decision_value(defaults, "legend", "layout", "outside") is False
    assert decision_value(defaults, "legend", "layout", "candidate_collision_fraction") == 0
    assert decision_value(defaults, "canvas", "page_width_aspect_ratio") is None


def test_smart_defaults_move_dual_y_legend_outside_when_all_corners_are_occupied() -> None:
    x = np.arange(20)
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=4,
        row_count=20,
        x_values=x,
        y_series=[
            np.zeros(20),
            np.ones(20),
            np.full(20, 100),
            np.full(20, 200),
        ],
        x_name="time_s",
        y_names=["temperature_low_C", "temperature_high_C"],
        y2_names=["pressure_low_kPa", "pressure_high_kPa"],
    )

    assert decision_value(defaults, "legend", "position") == "outside_right"
    assert decision_value(defaults, "legend", "layout", "outside") is True
    assert (
        defaults["legend"]["layout"]["outside"]["reason"]
        == "all_inside_legend_regions_intersect_data"
    )
    assert decision_value(defaults, "canvas", "page_width_aspect_ratio") == 1.8


def test_legend_placement_normalizes_dual_y_groups_independently() -> None:
    x = np.arange(13)
    placement = recommend_legend_placement(
        x,
        [20 + 0.4 * x, 21 + 0.5 * x, 98 + 1.2 * x, 101 + 1.5 * x],
        labels=[
            "Temperature control",
            "Temperature treated",
            "Pressure control",
            "Pressure treated",
        ],
        group_sizes=[2, 2],
    )

    assert placement["assessed"] is True
    assert placement["has_safe_inside"] is True
    assert placement["position"] == "inside_upper_left"
    assert placement["collision_fraction"] == 0


def test_smart_defaults_rotate_crowded_category_labels() -> None:
    labels = [f"Long category {index}" for index in range(12)]

    defaults = resolve_visual_defaults(
        chart_type="bar",
        series_count=1,
        row_count=len(labels),
        x_values=labels,
        y_series=[np.arange(len(labels))],
    )

    assert decision_value(defaults, "axes", "x_tick_rotation") == 45
    assert decision_value(defaults, "axes", "y_zero_baseline") is True
    assert decision_value(defaults, "canvas", "page_aspect_ratio") == 1.05
    assert decision_value(defaults, "canvas", "bottom_margin") == 0.25


def test_smart_defaults_add_more_height_for_vertical_category_labels() -> None:
    labels = [f"Exceptionally long category label {index}" for index in range(5)]

    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=len(labels),
        x_values=labels,
        y_series=[np.arange(len(labels))],
    )

    assert decision_value(defaults, "axes", "x_tick_rotation") == 90
    assert decision_value(defaults, "canvas", "page_aspect_ratio") == 0.9
    assert decision_value(defaults, "canvas", "bottom_margin") == 0.35


def test_smart_defaults_reduce_dense_scatter_marks() -> None:
    defaults = resolve_visual_defaults(
        chart_type="scatter",
        series_count=1,
        row_count=2500,
        x_values=np.arange(2500),
        y_series=[np.arange(2500)],
    )

    assert decision_value(defaults, "marks", "symbol_size") == 2.5
    assert decision_value(defaults, "marks", "transparency") == 55.0


def test_smart_defaults_use_scientific_notation_for_large_values() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=3,
        x_values=[1, 2, 3],
        y_series=[[100_000, 250_000, 500_000]],
    )

    assert decision_value(defaults, "axes", "y_number_format") == "scientific"
    assert decision_value(defaults, "axes", "y_decimal_places") == 2


def test_smart_defaults_choose_readable_numeric_ticks_and_quiet_grids() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=50,
        x_values=np.linspace(0, 100, 50),
        y_series=[np.linspace(0.125, 0.875, 50)],
    )

    x_scale = decision_value(defaults, "axes", "x_scale")
    assert decision_value(defaults, "axes", "x_major_ticks") == x_scale["tick_count"] == 8
    assert x_scale["from"] <= 0 and x_scale["to"] > 100
    y_scale = decision_value(defaults, "axes", "y_scale")
    assert decision_value(defaults, "axes", "y_major_ticks") == y_scale["tick_count"] == 7
    assert y_scale["from"] < 0.125 and y_scale["to"] > 0.875
    assert decision_value(defaults, "axes", "x_minor_ticks") == 1
    assert decision_value(defaults, "axes", "y_minor_ticks") == 1
    assert decision_value(defaults, "axes", "x_major_grid") is False
    assert decision_value(defaults, "axes", "y_major_grid") is True
    assert decision_value(defaults, "axes", "minor_grid") is False
    assert decision_value(defaults, "axes", "top_axis_ticks") is False


def test_smart_defaults_preserve_fractional_nice_step_labels() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=6,
        x_values=[0.13, 1.07, 2.91, 4.36, 6.88, 9.74],
        y_series=[[-2.37, -1.42, 0.18, 1.73, 3.09, 4.63]],
    )

    assert decision_value(defaults, "axes", "x_scale")["step"] == 1.5
    assert decision_value(defaults, "axes", "x_decimal_places") == 1


def test_smart_defaults_format_dual_y_axes_independently_and_align_ticks() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=2,
        row_count=4,
        x_values=[0, 1, 2, 3],
        y_series=[[20.1, 20.2, 20.3, 20.4], [100_000, 200_000, 300_000, 400_000]],
        y_names=["temperature_C"],
        y2_names=["pressure_Pa"],
    )

    assert decision_value(defaults, "axes", "y_number_format") == "decimal"
    assert decision_value(defaults, "axes", "y2_number_format") == "scientific"
    assert decision_value(defaults, "axes", "y_major_ticks") == 5
    assert decision_value(defaults, "axes", "y2_major_ticks") == 5
    left_scale = decision_value(defaults, "axes", "y_scale")
    right_scale = decision_value(defaults, "axes", "y2_scale")
    assert left_scale["tick_count"] == right_scale["tick_count"] == 5
    assert left_scale["step"] != right_scale["step"]
    assert left_scale["from"] < 20.1 and left_scale["to"] > 20.4
    assert right_scale["from"] < 100_000 and right_scale["to"] > 400_000
    assert decision_value(defaults, "axes", "y2_major_grid") is False
    assert decision_value(defaults, "canvas", "right_margin") == 0.12


def test_smart_defaults_preserve_datetime_labels_with_temporal_tick_density() -> None:
    dates = np.array(["2026-01-01", "2026-01-02", "2026-01-03"], dtype="datetime64[D]")

    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=3,
        x_values=dates,
        y_series=[[1, 2, 3]],
    )

    assert defaults["context"]["x_is_datetime"] is True
    assert defaults["context"]["x_is_categorical"] is False
    assert decision_value(defaults, "axes", "x_tick_rotation") == 0
    assert decision_value(defaults, "axes", "x_number_format") is None
    datetime_scale = decision_value(defaults, "axes", "x_datetime_scale")
    assert decision_value(defaults, "axes", "x_major_ticks") == datetime_scale["tick_count"]
    assert decision_value(defaults, "axes", "x_minor_ticks") == 0
    assert decision_value(defaults, "canvas", "left_margin") == 0.1
    assert decision_value(defaults, "canvas", "right_margin") == 0.1


def test_smart_defaults_recognize_iso_datetime_strings() -> None:
    defaults = resolve_visual_defaults(
        chart_type="line",
        series_count=1,
        row_count=3,
        x_values=["2026-01-01", "2026-02-01", "2026-03-01"],
        y_series=[[1, 2, 3]],
    )

    assert defaults["context"]["x_is_datetime"] is True
    assert decision_value(defaults, "axes", "x_datetime_scale") is not None


def test_smart_defaults_leave_specialized_chart_axes_and_grids_untouched() -> None:
    defaults = resolve_visual_defaults(
        chart_type="heatmap",
        series_count=1,
        row_count=9,
        x_values=np.arange(9),
        y_series=[np.arange(9)],
    )

    assert decision_value(defaults, "axes", "x_major_ticks") is None
    assert decision_value(defaults, "axes", "y_major_ticks") is None
    assert decision_value(defaults, "axes", "x_minor_ticks") is None
    assert decision_value(defaults, "axes", "y_minor_ticks") is None
    assert decision_value(defaults, "axes", "x_number_format") is None
    assert decision_value(defaults, "axes", "top_axis_ticks") is None
    assert decision_value(defaults, "axes", "x_major_grid") is False
    assert decision_value(defaults, "axes", "y_major_grid") is False


def test_histogram_count_axis_uses_integer_ticks_and_zero_baseline() -> None:
    defaults = resolve_visual_defaults(
        chart_type="histogram",
        series_count=1,
        row_count=5,
        x_values=[-3, -1, 0, 2, 4],
        y_series=[[-3, -1, 0, 2, 4]],
    )

    assert decision_value(defaults, "axes", "y_number_format") == "decimal"
    assert decision_value(defaults, "axes", "y_decimal_places") == 0
    assert decision_value(defaults, "axes", "y_zero_baseline") is True
