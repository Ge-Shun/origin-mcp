"""Pure helpers for readable, non-destructive plotting defaults.

The resolver in this module deliberately has no Origin dependency.  Plotting
code can therefore profile a table and explain every automatic visual choice
before the corresponding Origin properties are applied.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

import numpy as np

from .chart_palette import normalize_chart_type
from .text_format import humanize_field_name, infer_axis_title, infer_series_labels

DEFAULT_HEATMAP_COLORMAP = "viridis"


@dataclass(frozen=True)
class VisualContext:
    raw_chart_type: str
    chart_type: str
    series_count: int
    row_count: int
    x_is_categorical: bool
    x_is_datetime: bool
    x_unique_count: int
    longest_x_label: int
    y_min: float | None
    y_max: float | None


def resolve_visual_defaults(
    *,
    chart_type: str,
    series_count: int,
    row_count: int,
    x_values: Any = None,
    y_series: list[Any] | None = None,
    show_legend: bool | None = None,
    palette_name: str | None = None,
    style_mode: str = "origin_default",
    x_name: str | None = None,
    y_names: list[str] | None = None,
    y2_names: list[str] | None = None,
    table: Any = None,
    title_hint: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    y2_label: str | None = None,
) -> dict[str, Any]:
    """Resolve conservative cross-chart defaults and record their rationale.

    Explicit caller values always win.  Palette automation is activated only
    for the ``nature`` style so Origin/template styling remains untouched in
    ``origin_default`` mode.
    """

    context = _visual_context(
        chart_type=chart_type,
        series_count=series_count,
        row_count=row_count,
        x_values=x_values,
        y_series=y_series or [],
    )

    if show_legend is not None:
        legend_visible = _decision(bool(show_legend), "explicit_user_value", "user")
    elif context.series_count <= 1:
        legend_visible = _decision(False, "single_series")
    elif context.chart_type in {"heatmap", "surface"}:
        legend_visible = _decision(False, "color_scale_carries_the_value_encoding")
    elif context.chart_type == "box":
        legend_visible = _decision(False, "category_axis_identifies_the_groups")
    else:
        legend_visible = _decision(True, "multiple_series_require_identification")

    if palette_name is not None:
        palette = _decision(palette_name, "explicit_user_value", "user")
    elif style_mode == "nature":
        palette = _decision(
            "lcpmgh_auto",
            "match_an_installed_lcpmgh_palette_to_the_series_count",
        )
    else:
        palette = _decision(None, "preserve_origin_or_template_palette")

    y_names_actual = list(y_names or [])
    y2_names_actual = list(y2_names or [])
    all_series_names = [*y_names_actual, *y2_names_actual]
    series_labels = infer_series_labels(
        all_series_names,
        omit_units_when_metrics_differ=bool(y2_names_actual),
    )
    y_series_actual = list(y_series or [])
    legend_placement = None
    if (
        legend_visible["value"]
        and context.chart_type in {"line", "scatter"}
        and context.series_count > 1
    ):
        group_sizes = [len(y_names_actual)]
        if y2_names_actual:
            group_sizes.append(len(y2_names_actual))
        legend_placement = recommend_legend_placement(
            x_values,
            y_series_actual,
            labels=series_labels,
            group_sizes=group_sizes if sum(group_sizes) == len(y_series_actual) else None,
        )
    legend_layout = _legend_layout_defaults(
        visible=bool(legend_visible["value"]),
        series_count=context.series_count,
        labels=series_labels,
        placement=legend_placement,
    )

    legend_position: dict[str, Any]
    if not legend_visible["value"]:
        legend_position = _decision(None, "legend_hidden")
    elif legend_layout["outside"]["value"]:
        legend_position = _decision("outside_right", "legend_needs_dedicated_canvas_space")
    elif context.chart_type in {"line", "scatter"}:
        legend_position = _decision(
            (
                legend_placement["position"]
                if legend_placement is not None
                else recommend_legend_position(x_values, y_series_actual)
            ),
            "least_occupied_corner_with_sufficient_clearance",
        )
    else:
        legend_position = _decision("inside_upper_right", "stable_compact_anchor")

    symbol_size, transparency = _density_defaults(context)
    x_rotation = _x_tick_rotation(context)
    page_aspect_ratio, bottom_margin = _rotated_label_canvas(
        context,
        int(x_rotation["value"]),
    )
    x_title = infer_axis_title(
        [x_name] if x_name else [],
        explicit=x_label,
        fallback="X",
    )
    y_title = infer_axis_title(
        y_names_actual,
        explicit=y_label,
        table=table,
        title_hint=title_hint,
        x_name=x_name,
    )
    y2_title = (
        infer_axis_title(
            y2_names_actual,
            explicit=y2_label,
            table=table,
            title_hint=title_hint,
            x_name=x_name,
        )
        if y2_names_actual or y2_label is not None
        else None
    )
    y_split = len(y_names_actual) if y2_names_actual else len(y_series_actual)
    y_min, y_max = _numeric_extent(y_series_actual[:y_split])
    y2_min, y2_max = _numeric_extent(y_series_actual[y_split:])
    x_min, x_max = (
        (None, None)
        if context.x_is_categorical or context.x_is_datetime
        else _numeric_extent([x_values])
    )
    x_format, x_decimals = _numeric_format(x_min, x_max)
    y_format, y_decimals = _numeric_format(y_min, y_max)
    y2_format, y2_decimals = _numeric_format(y2_min, y2_max)
    if context.raw_chart_type == "histogram":
        y_format, y_decimals = "decimal", 0
    x_major_ticks = _major_tick_target(
        context,
        axis="x",
        number_format=x_format,
    )
    y_major_ticks = _major_tick_target(
        context,
        axis="y",
        number_format=y_format,
    )
    y2_major_ticks = None
    if y2_names_actual and y2_min is not None:
        right_target = _major_tick_target(
            context,
            axis="y",
            number_format=y2_format,
        )
        shared_targets = [target for target in (y_major_ticks, right_target) if target is not None]
        y_major_ticks = min(shared_targets) if shared_targets else None
        y2_major_ticks = y_major_ticks
    x_major_grid, y_major_grid = _grid_defaults(context)
    left_margin = _tick_label_margin(y_min, y_max, y_format, y_decimals)
    y2_margin = _tick_label_margin(y2_min, y2_max, y2_format, y2_decimals)
    zero_baseline = context.raw_chart_type == "histogram" or (
        context.chart_type == "bar" and (y_min is None or y_min >= 0)
    )

    aspect_ratios = {
        "line": 1.5,
        "scatter": 1.5,
        "bar": 1.35,
        "box": 1.35,
        "heatmap": 1.0,
        "surface": 1.0,
        "polar": 1.0,
        "generic": 1.4,
    }
    return {
        "mode": "conservative",
        "context": asdict(context),
        "legend": {
            "show": legend_visible,
            "position": legend_position,
            "series_labels": _decision(
                series_labels,
                _series_label_reason(all_series_names, series_labels),
            ),
            "layout": legend_layout,
        },
        "palette_name": palette,
        "marks": {
            "symbol_size": symbol_size,
            "transparency": transparency,
        },
        "axes": {
            "x_title": _decision(
                x_title.label,
                x_title.reason,
                x_title.source,
            ),
            "y_title": _decision(
                y_title.label,
                y_title.reason,
                y_title.source,
            ),
            "y2_title": _decision(
                y2_title.label if y2_title is not None else None,
                y2_title.reason if y2_title is not None else "single_y_axis",
                y2_title.source if y2_title is not None else "smart_default",
            ),
            "x_tick_rotation": x_rotation,
            "x_number_format": _decision(
                None if _preserve_specialized_x_axis(context) else x_format,
                (
                    "preserve_categorical_or_temporal_labels"
                    if _preserve_specialized_x_axis(context)
                    else "magnitude_and_range"
                ),
            ),
            "x_decimal_places": _decision(
                None if _preserve_specialized_x_axis(context) else x_decimals,
                (
                    "preserve_categorical_or_temporal_labels"
                    if _preserve_specialized_x_axis(context)
                    else "range_appropriate_precision"
                ),
            ),
            "y_number_format": _decision(y_format, "magnitude_and_range"),
            "y_decimal_places": _decision(y_decimals, "range_appropriate_precision"),
            "y2_number_format": _decision(
                y2_format if y2_min is not None else None,
                "independent_right_axis_magnitude_and_range"
                if y2_min is not None
                else "single_y_axis",
            ),
            "y2_decimal_places": _decision(
                y2_decimals if y2_min is not None else None,
                "independent_right_axis_precision" if y2_min is not None else "single_y_axis",
            ),
            "x_major_ticks": _decision(
                x_major_ticks,
                _major_tick_reason(context, axis="x", number_format=x_format),
            ),
            "y_major_ticks": _decision(
                y_major_ticks,
                _major_tick_reason(context, axis="y", number_format=y_format),
            ),
            "y2_major_ticks": _decision(
                y2_major_ticks,
                "align_dual_y_major_tick_counts" if y2_major_ticks is not None else "single_y_axis",
            ),
            "x_minor_ticks": _decision(
                _minor_tick_target(context, axis="x"),
                _minor_tick_reason(context, axis="x"),
            ),
            "y_minor_ticks": _decision(
                _minor_tick_target(context, axis="y"),
                _minor_tick_reason(context, axis="y"),
            ),
            "y2_minor_ticks": _decision(
                _minor_tick_target(context, axis="y") if y2_major_ticks is not None else None,
                "match_left_axis_minor_tick_density"
                if y2_major_ticks is not None
                else "single_y_axis",
            ),
            "x_major_grid": _decision(
                x_major_grid,
                "vertical_grid_adds_clutter" if not x_major_grid else "support_x_value_comparison",
            ),
            "y_major_grid": _decision(
                y_major_grid,
                "support_value_comparison"
                if y_major_grid
                else "non_cartesian_or_cell_encoded_chart",
            ),
            "y2_major_grid": _decision(False, "avoid_duplicate_dual_y_grid_lines"),
            "minor_grid": _decision(False, "keep_background_quiet"),
            "top_axis_ticks": _decision(
                None if context.chart_type in {"heatmap", "surface", "polar"} else False,
                (
                    "preserve_specialized_chart_axis_ticks"
                    if context.chart_type in {"heatmap", "surface", "polar"}
                    else "top_frame_does_not_need_duplicate_ticks"
                ),
            ),
            "y_zero_baseline": _decision(
                zero_baseline,
                "nonnegative_bar_like_chart" if zero_baseline else "preserve_data_range",
            ),
        },
        "canvas": {
            "aspect_ratio": _decision(
                aspect_ratios.get(context.chart_type, 1.4),
                f"{context.chart_type}_chart_footprint",
            ),
            "page_aspect_ratio": page_aspect_ratio,
            "bottom_margin": bottom_margin,
            "page_width_aspect_ratio": legend_layout["page_width_aspect_ratio"],
            "left_margin": _decision(
                left_margin,
                "reserve_space_for_long_y_tick_labels"
                if left_margin is not None
                else "default_tick_labels_fit",
            ),
            "right_margin": _decision(
                _max_optional(
                    decision_value(legend_layout, "right_margin"),
                    y2_margin,
                ),
                (
                    "reserve_external_legend_or_right_axis_tick_space"
                    if decision_value(legend_layout, "right_margin") is not None
                    or y2_margin is not None
                    else "default_tick_labels_fit"
                ),
            ),
        },
    }


def decision_value(defaults: dict[str, Any], *path: str) -> Any:
    """Return the value at a nested smart-default decision path."""

    current: Any = defaults
    for part in path:
        current = current[part]
    return current.get("value") if isinstance(current, dict) and "value" in current else current


def _decision(value: Any, reason: str, source: str = "smart_default") -> dict[str, Any]:
    return {"value": value, "source": source, "reason": reason}


def _visual_context(
    *,
    chart_type: str,
    series_count: int,
    row_count: int,
    x_values: Any,
    y_series: list[Any],
) -> VisualContext:
    raw_chart_type = str(chart_type or "generic").strip().lower().replace("-", "_")
    x_is_categorical, x_is_datetime, x_unique_count, longest_x_label = _x_profile(x_values)
    y_min, y_max = _numeric_extent(y_series)
    return VisualContext(
        raw_chart_type=raw_chart_type,
        chart_type=normalize_chart_type(chart_type),
        series_count=max(0, int(series_count)),
        row_count=max(0, int(row_count)),
        x_is_categorical=x_is_categorical,
        x_is_datetime=x_is_datetime,
        x_unique_count=x_unique_count,
        longest_x_label=longest_x_label,
        y_min=y_min,
        y_max=y_max,
    )


def _x_profile(values: Any) -> tuple[bool, bool, int, int]:
    if values is None:
        return False, False, 0, 0
    try:
        array = np.asarray(values).reshape(-1)
    except Exception:
        return False, False, 0, 0
    labels = [str(value) for value in array if value is not None and str(value) != "nan"]
    if not labels:
        return False, False, 0, 0
    is_datetime = _is_datetime_array(array)
    if is_datetime:
        return False, True, len(set(labels)), max(len(label) for label in labels)
    try:
        numeric = np.asarray(labels, dtype=float)
        is_categorical = not bool(np.all(np.isfinite(numeric)))
    except (TypeError, ValueError):
        is_categorical = True
    return is_categorical, False, len(set(labels)), max(len(label) for label in labels)


def _is_datetime_array(array: np.ndarray) -> bool:
    try:
        if np.issubdtype(array.dtype, np.datetime64):
            return True
    except TypeError:
        pass
    values = [value for value in array if value is not None]
    return bool(values) and all(
        isinstance(value, (date, datetime, np.datetime64)) for value in values
    )


def _numeric_extent(series: list[Any]) -> tuple[float | None, float | None]:
    arrays: list[np.ndarray] = []
    for values in series:
        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
        finite = array[np.isfinite(array)]
        if finite.size:
            arrays.append(finite)
    if not arrays:
        return None, None
    combined = np.concatenate(arrays)
    return float(np.min(combined)), float(np.max(combined))


def _density_defaults(context: VisualContext) -> tuple[dict[str, Any], dict[str, Any]]:
    if context.chart_type != "scatter" and context.raw_chart_type not in {
        "line_symbol",
        "linesymbol",
    }:
        return (
            _decision(None, "not_a_symbol_density_chart"),
            _decision(None, "not_a_symbol_density_chart"),
        )
    if context.row_count <= 40:
        return _decision(5.5, "sparse_points"), _decision(0.0, "sparse_points")
    if context.row_count <= 300:
        return _decision(4.5, "moderate_point_density"), _decision(10.0, "moderate_point_density")
    if context.row_count <= 2000:
        return _decision(3.5, "dense_points"), _decision(35.0, "dense_points")
    return _decision(2.5, "very_dense_points"), _decision(55.0, "very_dense_points")


def _x_tick_rotation(context: VisualContext) -> dict[str, Any]:
    if not context.x_is_categorical:
        return _decision(0, "numeric_or_temporal_axis")
    if context.x_unique_count > 20 or context.longest_x_label > 24:
        return _decision(90, "many_or_very_long_category_labels")
    if context.x_unique_count > 8 or context.longest_x_label > 10:
        return _decision(45, "crowded_category_labels")
    return _decision(0, "category_labels_fit_horizontally")


def _rotated_label_canvas(
    context: VisualContext,
    rotation: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reserve vertical page space for rotated category labels.

    The target page aspect ratio makes this rule idempotent: applying it more
    than once sets the same height instead of repeatedly multiplying it.
    """

    if rotation >= 90:
        return (
            _decision(0.9, "extra_page_height_for_vertical_category_labels"),
            _decision(0.35, "reserve_space_for_vertical_category_labels"),
        )
    if rotation >= 45:
        heavily_crowded = context.x_unique_count >= 12 or context.longest_x_label >= 18
        if heavily_crowded:
            return (
                _decision(1.05, "extra_page_height_for_long_rotated_category_labels"),
                _decision(0.25, "reserve_space_for_long_rotated_category_labels"),
            )
        return (
            _decision(1.2, "moderate_page_height_for_rotated_category_labels"),
            _decision(0.18, "reserve_space_for_rotated_category_labels"),
        )
    return (
        _decision(None, "no_rotated_category_labels"),
        _decision(None, "no_rotated_category_labels"),
    )


def _legend_layout_defaults(
    *,
    visible: bool,
    series_count: int,
    labels: list[str],
    placement: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    lengths = [len(label) for label in labels]
    longest = max(lengths, default=0)
    total = sum(lengths)
    fallback_outside = series_count >= 7 or longest > 24 or total > 90
    placement_assessed = bool(placement and placement["assessed"])
    if placement is not None and placement_assessed:
        needs_outside = not placement["has_safe_inside"]
    else:
        needs_outside = fallback_outside
    outside = visible and series_count > 1 and needs_outside
    occupancy_reason = (
        "all_inside_legend_regions_intersect_data"
        if placement_assessed
        else "legend_size_exceeds_safe_plot_overlay"
    )
    placement_fields = {
        "inside_candidate": _decision(
            placement["position"] if placement is not None else None,
            "lowest_curve_occupancy_candidate",
        ),
        "candidate_collision_fraction": _decision(
            placement["collision_fraction"] if placement is not None else None,
            "fraction_of_a_series_intersecting_the_candidate_legend_box",
        ),
        "estimated_width_fraction": _decision(
            placement["width"] if placement is not None else None,
            "legend_label_footprint_estimate",
        ),
        "estimated_height_fraction": _decision(
            placement["height"] if placement is not None else None,
            "legend_row_footprint_estimate",
        ),
    }
    if outside:
        wide = longest > 36 or total > 160
        return {
            "outside": _decision(True, occupancy_reason),
            "estimated_rows": _decision(series_count, "one_series_per_legend_row"),
            "max_label_length": _decision(longest, "inferred_series_labels"),
            "page_width_aspect_ratio": _decision(
                2.0 if wide else 1.8,
                "widen_canvas_for_external_legend",
            ),
            "right_margin": _decision(
                0.34 if wide else 0.28,
                "reserve_external_legend_column",
            ),
            **placement_fields,
        }
    return {
        "outside": _decision(
            False,
            (
                "data_free_inside_region_available"
                if placement_assessed
                else "legend_fits_inside_plot_area"
            ),
        ),
        "estimated_rows": _decision(series_count if visible else 0, "legend_visibility"),
        "max_label_length": _decision(longest, "inferred_series_labels"),
        "page_width_aspect_ratio": _decision(None, "no_external_legend"),
        "right_margin": _decision(None, "no_external_legend"),
        **placement_fields,
    }


def _series_label_reason(field_names: list[str], labels: list[str]) -> str:
    if labels and labels != [humanize_field_name(name) for name in field_names]:
        return "remove_axis_metric_and_unit_from_legend_series"
    return "humanized_field_names"


def _numeric_format(lower: float | None, upper: float | None) -> tuple[str, int]:
    if lower is None or upper is None:
        return "decimal", -1
    magnitude = max(abs(lower), abs(upper))
    if magnitude >= 100_000 or (0 < magnitude < 0.0001):
        return "scientific", 2
    span = abs(upper - lower)
    if span <= 0:
        return "decimal", -1
    approximate_step = span / 5.0
    decimals = max(0, min(6, int(math.ceil(-math.log10(approximate_step)))))
    return "decimal", decimals


def _major_tick_target(
    context: VisualContext,
    *,
    axis: str,
    number_format: str,
) -> int | None:
    if context.chart_type in {"heatmap", "surface", "polar"}:
        return None
    if axis == "x" and context.x_is_categorical:
        return None
    if axis == "x" and context.x_is_datetime:
        return 6
    if number_format == "scientific":
        return 5
    if axis == "x" and context.chart_type in {"line", "scatter"}:
        return 7
    return 6


def _major_tick_reason(
    context: VisualContext,
    *,
    axis: str,
    number_format: str,
) -> str:
    if context.chart_type in {"heatmap", "surface", "polar"}:
        return "preserve_specialized_chart_axis_scale"
    if axis == "x" and context.x_is_categorical:
        return "preserve_category_tick_positions"
    if axis == "x" and context.x_is_datetime:
        return "six_temporal_anchors"
    if number_format == "scientific":
        return "fewer_ticks_for_wide_scientific_labels"
    if axis == "x" and context.chart_type in {"line", "scatter"}:
        return "use_wide_canvas_for_seven_x_anchors"
    return "six_major_ticks_for_readable_comparison"


def _preserve_specialized_x_axis(context: VisualContext) -> bool:
    return (
        context.x_is_categorical
        or context.x_is_datetime
        or context.chart_type
        in {
            "heatmap",
            "surface",
            "polar",
        }
    )


def _minor_tick_target(context: VisualContext, *, axis: str) -> int | None:
    if context.chart_type in {"heatmap", "surface", "polar"}:
        return None
    if axis == "x" and (context.x_is_categorical or context.x_is_datetime):
        return 0
    return 1


def _minor_tick_reason(context: VisualContext, *, axis: str) -> str:
    if context.chart_type in {"heatmap", "surface", "polar"}:
        return "preserve_specialized_chart_axis_scale"
    if axis == "x" and (context.x_is_categorical or context.x_is_datetime):
        return "avoid_dense_category_or_temporal_subdivisions"
    return "one_subdivision_between_major_ticks"


def _grid_defaults(context: VisualContext) -> tuple[bool, bool]:
    if context.chart_type in {"heatmap", "surface", "polar"}:
        return False, False
    # Horizontal guides make value comparison easier. Vertical guides are
    # intentionally omitted because they compete with traces, bars and labels.
    return False, True


def _tick_label_margin(
    lower: float | None,
    upper: float | None,
    number_format: str,
    decimal_places: int,
) -> float | None:
    if lower is None or upper is None:
        return None
    if number_format == "scientific":
        return 0.12
    precision = max(0, decimal_places)
    longest = max(len(f"{value:.{precision}f}") for value in (lower, upper))
    if longest >= 10:
        return 0.12
    if longest >= 8:
        return 0.1
    return None


def _max_optional(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def automatic_histogram_bin_width(values: Any) -> float | None:
    """Return a robust bin width using Freedman-Diaconis with safe fallbacks.

    The result is clamped to a practical 5-50 bin range for non-trivial data so
    sparse inputs do not turn into a wall of one-observation bars.
    """

    try:
        data = np.asarray(values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None
    data = data[np.isfinite(data)]
    if data.size < 2:
        return None
    lower = float(np.min(data))
    upper = float(np.max(data))
    span = upper - lower
    if not math.isfinite(span) or span <= 0:
        return None

    count = int(data.size)
    q25, q75 = np.percentile(data, [25, 75])
    iqr = float(q75 - q25)
    width = 2.0 * iqr / math.pow(count, 1.0 / 3.0) if iqr > 0 else 0.0
    if not math.isfinite(width) or width <= 0:
        std = float(np.std(data, ddof=1)) if count > 1 else 0.0
        width = 3.5 * std / math.pow(count, 1.0 / 3.0) if std > 0 else 0.0
    if not math.isfinite(width) or width <= 0:
        width = span / max(1, math.ceil(math.sqrt(count)))

    bins = max(1, math.ceil(span / width))
    unique_count = int(np.unique(data).size)
    min_bins = min(5, unique_count)
    max_bins = max(min_bins, min(50, unique_count))
    bins = min(max(bins, min_bins), max_bins)
    return span / bins


def recommend_legend_position(x_values: Any, y_series: list[Any]) -> str:
    """Choose the quieter upper corner for a multi-series legend."""

    normalized = _normalized_points(x_values, y_series)
    if normalized is None:
        return "inside_upper_right"
    x_points, y_points = normalized
    left_score = _corner_density(x_points, y_points, x_anchor=0.12)
    right_score = _corner_density(x_points, y_points, x_anchor=0.88)
    return "inside_upper_left" if left_score <= right_score else "inside_upper_right"


def recommend_legend_placement(
    x_values: Any,
    y_series: list[Any],
    *,
    labels: list[str] | None = None,
    group_sizes: list[int] | None = None,
) -> dict[str, Any]:
    """Find an inside corner whose estimated legend rectangle is data-free.

    Each Y-axis group is normalized independently. This matters for dual-Y
    graphs because values with different units share screen coordinates even
    though their numeric ranges are unrelated.
    """

    series_count = len(y_series)
    longest = max((len(label) for label in labels or []), default=8)
    raw_width = 0.16 + 0.011 * longest
    raw_height = 0.05 + 0.065 * series_count
    width = min(0.58, max(0.22, raw_width))
    height = min(0.62, max(0.14, raw_height))
    curves = _normalized_curves(
        x_values,
        y_series,
        group_sizes=group_sizes,
    )
    if not curves:
        return {
            "position": "inside_upper_right",
            "has_safe_inside": False,
            "assessed": False,
            "collision_fraction": None,
            "width": width,
            "height": height,
        }

    margin = 0.025
    padding = 0.025
    candidates = [
        ("inside_upper_right", 1 - margin - width, 1 - margin, 1 - margin - height, 1 - margin),
        ("inside_upper_left", margin, margin + width, 1 - margin - height, 1 - margin),
        ("inside_lower_right", 1 - margin - width, 1 - margin, margin, margin + height),
        ("inside_lower_left", margin, margin + width, margin, margin + height),
    ]
    scored: list[tuple[float, float, str]] = []
    for position, x_min, x_max, y_min, y_max in candidates:
        collision = max(
            float(
                np.mean(
                    (curve_x >= x_min - padding)
                    & (curve_x <= x_max + padding)
                    & (curve_y >= y_min - padding)
                    & (curve_y <= y_max + padding)
                )
            )
            for curve_x, curve_y in curves
        )
        # Prefer upper corners when equally clear; lower legends more often
        # compete with the X axis and the beginning/end of a line trajectory.
        preference_penalty = 0.002 if "lower" in position else 0.0
        scored.append((collision + preference_penalty, collision, position))
    _effective_score, collision_fraction, position = min(scored)
    footprint_fits = raw_width <= 0.48 and raw_height <= 0.55
    return {
        "position": position,
        "has_safe_inside": footprint_fits and collision_fraction <= 0.002,
        "assessed": True,
        "collision_fraction": round(collision_fraction, 6),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def _normalized_curves(
    x_values: Any,
    y_series: list[Any],
    *,
    group_sizes: list[int] | None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if not y_series:
        return []
    try:
        arrays = [np.asarray(values, dtype=float).reshape(-1) for values in y_series]
    except (TypeError, ValueError):
        return []
    length = max((array.size for array in arrays), default=0)
    try:
        x_array = np.asarray(x_values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        x_array = np.arange(length, dtype=float)
    if x_array.size == 0:
        x_array = np.arange(length, dtype=float)

    groups = _series_groups(len(arrays), group_sizes)
    curves: list[tuple[np.ndarray, np.ndarray]] = []
    for indexes in groups:
        finite_y = [array[np.isfinite(array)] for array in (arrays[index] for index in indexes)]
        finite_y = [array for array in finite_y if array.size]
        if not finite_y:
            continue
        combined_y = np.concatenate(finite_y)
        y_min = float(np.min(combined_y))
        y_span = float(np.max(combined_y) - y_min)
        if y_span <= 0:
            continue
        for index in indexes:
            values = arrays[index]
            usable = min(x_array.size, values.size)
            if usable <= 1:
                continue
            x_part = x_array[:usable]
            y_part = values[:usable]
            mask = np.isfinite(x_part) & np.isfinite(y_part)
            if np.count_nonzero(mask) <= 1:
                continue
            x_valid = x_part[mask]
            y_valid = y_part[mask]
            x_min = float(np.min(x_valid))
            x_span = float(np.max(x_valid) - x_min)
            if x_span <= 0:
                continue
            x_normalized = (x_valid - x_min) / x_span
            y_normalized = (y_valid - y_min) / y_span
            order = np.argsort(x_normalized)
            unique_x, unique_indexes = np.unique(x_normalized[order], return_index=True)
            unique_y = y_normalized[order][unique_indexes]
            if unique_x.size <= 1:
                continue
            dense_x = np.linspace(float(unique_x[0]), float(unique_x[-1]), 200)
            dense_y = np.interp(dense_x, unique_x, unique_y)
            curves.append((dense_x, dense_y))
    return curves


def _series_groups(series_count: int, group_sizes: list[int] | None) -> list[list[int]]:
    if not group_sizes or any(size <= 0 for size in group_sizes):
        return [list(range(series_count))]
    groups: list[list[int]] = []
    start = 0
    for size in group_sizes:
        stop = min(series_count, start + size)
        if stop > start:
            groups.append(list(range(start, stop)))
        start = stop
    if start < series_count:
        groups.append(list(range(start, series_count)))
    return groups


def _normalized_points(x_values: Any, y_series: list[Any]) -> tuple[np.ndarray, np.ndarray] | None:
    if not y_series:
        return None
    try:
        y_arrays = [np.asarray(values, dtype=float).reshape(-1) for values in y_series]
    except (TypeError, ValueError):
        return None
    if not y_arrays:
        return None
    length = max(array.size for array in y_arrays)
    try:
        x_array = np.asarray(x_values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        x_array = np.arange(length, dtype=float)

    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for values in y_arrays:
        usable = min(x_array.size, values.size)
        if usable <= 0:
            continue
        x_part = x_array[:usable]
        y_part = values[:usable]
        mask = np.isfinite(x_part) & np.isfinite(y_part)
        if np.any(mask):
            xs.append(x_part[mask])
            ys.append(y_part[mask])
    if not xs:
        return None
    x_all = np.concatenate(xs)
    y_all = np.concatenate(ys)
    x_span = float(np.max(x_all) - np.min(x_all))
    y_span = float(np.max(y_all) - np.min(y_all))
    if x_span <= 0 or y_span <= 0:
        return None
    return (
        (x_all - np.min(x_all)) / x_span,
        (y_all - np.min(y_all)) / y_span,
    )


def _corner_density(x_values: np.ndarray, y_values: np.ndarray, *, x_anchor: float) -> float:
    distance_sq = np.square(x_values - x_anchor) + np.square(y_values - 0.88)
    return float(np.exp(-distance_sq / (2.0 * 0.22**2)).sum())
