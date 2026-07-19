"""Pure helpers for readable, non-destructive plotting defaults.

The resolver in this module deliberately has no Origin dependency.  Plotting
code can therefore profile a table and explain every automatic visual choice
before the corresponding Origin properties are applied.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np

from .chart_palette import normalize_chart_type
from .nature_style_profiles import resolve_nature_style_profile
from .text_format import humanize_field_name, infer_axis_title, infer_series_labels

DEFAULT_HEATMAP_COLORMAP = "viridis"
DEFAULT_SMART_ANNOTATION_FONT_SIZE = 20
DEFAULT_SMART_LINE_WIDTH = 2.5

_ISO_DATETIME_PATTERN = re.compile(
    r"^\d{4}[-/]\d{2}[-/]\d{2}"
    r"(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
_NICE_MANTISSAS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)


@dataclass(frozen=True)
class VisualContext:
    raw_chart_type: str
    chart_variant: str
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
    chart_variant: str | None = None,
    series_count: int,
    row_count: int,
    x_values: Any = None,
    y_series: list[Any] | None = None,
    show_legend: bool | None = None,
    palette_name: str | None = None,
    mark_transparency: float | None = None,
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
        chart_variant=chart_variant,
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

    symbol_size, density_transparency = _density_defaults(context)
    transparency = _resolve_transparency_default(
        density_transparency,
        explicit=mark_transparency,
        style_mode=style_mode,
    )
    if context.chart_type == "line":
        line_width = _decision(
            (
                resolve_nature_style_profile("screen").line_width
                if style_mode == "nature"
                else DEFAULT_SMART_LINE_WIDTH
            ),
            (
                "nature_series_stroke"
                if style_mode == "nature"
                else "minimum_readable_series_stroke"
            ),
        )
    else:
        line_width = _decision(None, "chart_type_has_no_default_series_line")
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
    zero_baseline = context.raw_chart_type == "histogram" or (
        context.chart_type == "bar" and (y_min is None or y_min >= 0)
    )
    scalable = context.chart_type not in {"heatmap", "surface", "polar"}
    x_scale = None
    x_datetime_scale = None
    if scalable and context.x_is_datetime:
        x_datetime_scale = nice_datetime_scale(x_values, x_major_ticks or 6)
        if x_datetime_scale is not None:
            x_major_ticks = int(x_datetime_scale["tick_count"])
    elif scalable and not context.x_is_categorical and x_min is not None and x_major_ticks:
        x_upper = x_max if x_max is not None else x_min
        x_span = x_upper - x_min
        anchor_x_zero = x_min >= 0 and x_min <= max(x_span * 0.05, 1e-12)
        x_scale = nice_numeric_scale(
            x_min,
            x_upper,
            x_major_ticks,
            anchor_zero=anchor_x_zero,
        )
        x_major_ticks = int(x_scale["tick_count"])
        x_format, x_decimals = _numeric_format(
            float(x_scale["from"]),
            float(x_scale["to"]),
            float(x_scale["step"]),
        )
    y_scale = None
    if scalable and context.raw_chart_type != "histogram" and y_min is not None and y_major_ticks:
        y_scale = nice_numeric_scale(
            y_min,
            y_max if y_max is not None else y_min,
            y_major_ticks,
            include_zero=context.chart_type == "bar",
            anchor_zero=zero_baseline,
            strict_tick_count=bool(y2_names_actual),
        )
        y_major_ticks = int(y_scale["tick_count"])
        y_format, y_decimals = _numeric_format(
            float(y_scale["from"]),
            float(y_scale["to"]),
            float(y_scale["step"]),
        )
    y2_scale = None
    if scalable and y2_min is not None and y2_major_ticks:
        y2_scale = nice_numeric_scale(
            y2_min,
            y2_max if y2_max is not None else y2_min,
            y2_major_ticks,
            strict_tick_count=True,
        )
        y2_major_ticks = int(y2_scale["tick_count"])
        y2_format, y2_decimals = _numeric_format(
            float(y2_scale["from"]),
            float(y2_scale["to"]),
            float(y2_scale["step"]),
        )
    x_major_grid, y_major_grid = _grid_defaults(context)
    left_margin = _tick_label_margin(y_min, y_max, y_format, y_decimals)
    y2_margin = _tick_label_margin(y2_min, y2_max, y2_format, y2_decimals)
    temporal_endpoint_margin = 0.1 if context.x_is_datetime else None
    left_margin = _max_optional(left_margin, temporal_endpoint_margin)
    right_margin = _max_optional(
        decision_value(legend_layout, "right_margin"),
        y2_margin,
        temporal_endpoint_margin,
    )
    data_labels = _data_label_defaults(
        context,
        y_min=y_min,
        y_max=y_max,
        font_size=(
            resolve_nature_style_profile("screen").annotation_font_size
            if style_mode == "nature"
            else DEFAULT_SMART_ANNOTATION_FONT_SIZE
        ),
        font_reason=(
            "nature_annotation_typography"
            if style_mode == "nature"
            else "match_axis_tick_typography"
        ),
        layer_series_counts=[
            len(y_names_actual) or context.series_count,
            *([len(y2_names_actual)] if y2_names_actual else []),
        ],
        layer_formats=[
            _data_label_numeric_format(y_series_actual[:y_split]),
            *([_data_label_numeric_format(y_series_actual[y_split:])] if y2_names_actual else []),
        ],
    )
    if decision_value(data_labels, "show"):
        label_position = decision_value(data_labels, "position")
        if label_position == "right":
            right_margin = _max_optional(right_margin, 0.14)
            if x_scale is not None and x_min is not None and x_max is not None:
                x_span = max(x_max - x_min, 1e-12)
                padded_to = x_max + (x_span * 0.12)
                if float(x_scale["to"]) < padded_to:
                    x_scale = {**x_scale, "to": padded_to}
        top_margin = 0.1 if label_position == "above" else None
    else:
        top_margin = None
    reference_lines = _reference_line_defaults(
        context,
        y_min=y_min,
        y_max=y_max,
        y2_min=y2_min,
        y2_max=y2_max,
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
            "line_width": line_width,
            "symbol_size": symbol_size,
            "transparency": transparency,
        },
        "annotations": {
            "data_labels": data_labels,
            "reference_lines": _decision(
                reference_lines,
                (
                    "emphasize_zero_when_values_cross_sign"
                    if reference_lines
                    else "no_semantic_reference_line_inferred"
                ),
            ),
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
            "x_scale": _decision(
                x_scale,
                "tidy_numeric_bounds_with_extreme_padding"
                if x_scale is not None
                else "non_numeric_or_specialized_x_axis",
            ),
            "x_datetime_scale": _decision(
                x_datetime_scale,
                "calendar_aligned_ticks_with_extreme_padding"
                if x_datetime_scale is not None
                else "non_temporal_x_axis",
            ),
            "y_scale": _decision(
                y_scale,
                "tidy_numeric_bounds_with_extreme_padding"
                if y_scale is not None
                else "preserve_origin_scale_for_specialized_or_derived_axis",
            ),
            "y2_scale": _decision(
                y2_scale,
                "independent_tidy_bounds_with_shared_tick_count"
                if y2_scale is not None
                else "single_or_specialized_y_axis",
            ),
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
            "top_margin": _decision(
                top_margin,
                (
                    "reserve_space_for_above_mark_data_labels"
                    if top_margin is not None
                    else "default_top_margin_fits"
                ),
            ),
            "page_width_aspect_ratio": legend_layout["page_width_aspect_ratio"],
            "left_margin": _decision(
                left_margin,
                "reserve_space_for_axis_tick_labels"
                if left_margin is not None
                else "default_tick_labels_fit",
            ),
            "right_margin": _decision(
                right_margin,
                (
                    "reserve_external_legend_or_axis_tick_space"
                    if right_margin is not None
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


def strict_datetime_values(values: Any) -> list[datetime | None] | None:
    """Parse an entirely temporal sequence without guessing ambiguous strings.

    ISO-like year-first strings are accepted.  Missing entries are preserved,
    while any other text makes the whole sequence non-temporal so category
    labels such as ``Stage 1`` can never be silently converted.
    """

    try:
        array = np.asarray(values, dtype=object).reshape(-1)
    except Exception:
        return None
    parsed: list[datetime | None] = []
    present = 0
    for value in array:
        if _is_missing_value(value):
            parsed.append(None)
            continue
        converted = _strict_datetime_value(value)
        if converted is None:
            return None
        parsed.append(converted)
        present += 1
    return parsed if present else None


def nice_numeric_scale(
    lower: float,
    upper: float,
    tick_count: int,
    *,
    include_zero: bool = False,
    anchor_zero: bool = False,
    padding_fraction: float = 0.05,
    strict_tick_count: bool = False,
) -> dict[str, float | int]:
    """Return tidy fixed-count bounds that safely contain the data extent."""

    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise ValueError("Numeric scale bounds must be finite.")
    if lower > upper:
        lower, upper = upper, lower
    tick_count = max(2, int(tick_count))
    if not strict_tick_count:
        data_span = max(upper - lower, abs(lower) * 0.1, 1e-12)
        choices = []
        for candidate_count in range(max(3, tick_count - 1), tick_count + 3):
            scale = nice_numeric_scale(
                lower,
                upper,
                candidate_count,
                include_zero=include_zero,
                anchor_zero=anchor_zero,
                padding_fraction=padding_fraction,
                strict_tick_count=True,
            )
            excess = (float(scale["to"]) - float(scale["from"]) - (upper - lower)) / data_span
            score = excess + 0.02 * abs(candidate_count - tick_count)
            choices.append((score, candidate_count, scale))
        return min(choices, key=lambda item: (item[0], item[1]))[2]
    intervals = tick_count - 1
    span = upper - lower
    if span <= 0:
        half_span = max(abs(lower) * 0.05, 0.5)
        lower -= half_span
        upper += half_span
        span = upper - lower

    padding = max(0.0, float(padding_fraction)) * span
    padded_lower = lower - padding
    padded_upper = upper + padding
    zero_at_lower = (include_zero or anchor_zero) and lower >= 0
    zero_at_upper = include_zero and upper <= 0
    if zero_at_lower:
        padded_lower = 0.0
    elif zero_at_upper:
        padded_upper = 0.0
    elif include_zero:
        padded_lower = min(padded_lower, 0.0)
        padded_upper = max(padded_upper, 0.0)

    raw_step = max((padded_upper - padded_lower) / intervals, np.finfo(float).tiny)
    candidates = _nice_step_candidates(raw_step)
    best: tuple[float, float, float] | None = None
    for step in candidates:
        if zero_at_lower:
            starts: Any = [(0, step)]
        elif zero_at_upper:
            starts = [(-intervals, step)]
        else:
            quantum = step / 2.0
            first = math.ceil(((padded_upper - intervals * step) / quantum) - 1e-12)
            last = math.floor((padded_lower / quantum) + 1e-12)
            starts = ((start, quantum) for start in range(first, last + 1))
        for start, quantum in starts:
            axis_lower = start * quantum
            axis_upper = axis_lower + intervals * step
            tolerance = step * 1e-10
            if axis_lower > padded_lower + tolerance or axis_upper < padded_upper - tolerance:
                continue
            lower_slack = lower - axis_lower
            upper_slack = axis_upper - upper
            imbalance = abs(lower_slack - upper_slack) / max(span, step)
            excess = (axis_upper - axis_lower - span) / max(span, step)
            score = excess + 0.2 * imbalance + 0.01 * (step / raw_step)
            candidate = (score, axis_lower, step)
            if best is None or candidate < best:
                best = candidate
        if best is not None and step > raw_step * 2.5:
            break
    if best is None:  # Defensive fallback for extreme floating-point ranges.
        step = candidates[-1]
        axis_lower = math.floor(padded_lower / step) * step
    else:
        _, axis_lower, step = best
    axis_upper = axis_lower + intervals * step
    return {
        "from": _clean_float(axis_lower),
        "to": _clean_float(axis_upper),
        "step": _clean_float(step),
        "tick_count": tick_count,
    }


def nice_datetime_scale(values: Any, tick_count: int = 6) -> dict[str, Any] | None:
    """Return calendar-aligned temporal ticks with padded, non-clipping bounds."""

    parsed = strict_datetime_values(values)
    if parsed is None:
        return None
    actual = [value for value in parsed if value is not None]
    if not actual:
        return None
    lower = min(actual)
    upper = max(actual)
    if lower == upper:
        lower -= timedelta(hours=12)
        upper += timedelta(hours=12)
    target = max(3, int(tick_count))
    candidates: list[tuple[str, int]] = [
        *(("second", value) for value in (1, 2, 5, 10, 15, 30)),
        *(("minute", value) for value in (1, 2, 5, 10, 15, 30)),
        *(("hour", value) for value in (1, 2, 3, 4, 6, 12)),
        *(("day", value) for value in (1, 2, 3, 7, 14)),
        *(("month", value) for value in (1, 2, 3, 6)),
        *(("year", value) for value in (1, 2, 5, 10, 20, 50, 100)),
    ]
    best: tuple[float, list[datetime], str, int] | None = None
    for unit, amount in candidates:
        ticks = _calendar_ticks(lower, upper, unit, amount)
        if len(ticks) < 2 or len(ticks) > 12:
            continue
        coverage = (ticks[-1] - ticks[0]).total_seconds()
        data_span = max((upper - lower).total_seconds(), 1.0)
        score = abs(len(ticks) - target) + 0.15 * max(0.0, coverage / data_span - 1.0)
        candidate = (score, ticks, unit, amount)
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        return None
    _, ticks, unit, amount = best
    label_type = "time" if (upper - lower) < timedelta(days=1) else "date"
    return {
        "from": _datetime_iso(ticks[0]),
        "to": _datetime_iso(ticks[-1]),
        "ticks": [_datetime_iso(value) for value in ticks],
        "tick_count": len(ticks),
        "unit": unit,
        "step": amount,
        "label_type": label_type,
    }


def _decision(value: Any, reason: str, source: str = "smart_default") -> dict[str, Any]:
    return {"value": value, "source": source, "reason": reason}


def _visual_context(
    *,
    chart_type: str,
    chart_variant: str | None,
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
        chart_variant=str(chart_variant or chart_type or "generic")
        .strip()
        .lower()
        .replace("-", "_"),
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
    return strict_datetime_values(array) is not None


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, np.datetime64):
        return bool(np.isnat(value))
    try:
        missing = value != value
        return bool(missing) if isinstance(missing, (bool, np.bool_)) else False
    except Exception:
        return False


def _strict_datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        converted = value
    elif isinstance(value, date):
        converted = datetime(value.year, value.month, value.day)
    elif isinstance(value, np.datetime64):
        if np.isnat(value):
            return None
        text = np.datetime_as_string(value, unit="us")
        converted = datetime.fromisoformat(text)
    elif isinstance(value, str) and _ISO_DATETIME_PATTERN.fullmatch(value.strip()):
        text = value.strip().replace("/", "-")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            converted = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if converted.tzinfo is not None:
        converted = converted.astimezone(timezone.utc).replace(tzinfo=None)
    return converted


def _nice_step_candidates(raw_step: float) -> list[float]:
    exponent = math.floor(math.log10(raw_step))
    candidates = {
        mantissa * (10.0**power)
        for power in range(exponent - 1, exponent + 3)
        for mantissa in _NICE_MANTISSAS
        if mantissa * (10.0**power) >= raw_step * (1.0 - 1e-12)
    }
    return sorted(candidates)


def _clean_float(value: float) -> float:
    if abs(value) < 1e-14:
        return 0.0
    return float(f"{value:.14g}")


def _calendar_ticks(
    lower: datetime,
    upper: datetime,
    unit: str,
    amount: int,
) -> list[datetime]:
    start = _calendar_floor(lower, unit, amount)
    if start >= lower:
        start = _calendar_add(start, unit, -amount)
    ticks = [start]
    while ticks[-1] <= upper and len(ticks) <= 12:
        ticks.append(_calendar_add(ticks[-1], unit, amount))
    if ticks[-1] <= upper:
        ticks.append(_calendar_add(ticks[-1], unit, amount))
    return ticks


def _calendar_floor(value: datetime, unit: str, amount: int) -> datetime:
    if unit == "year":
        year = ((value.year - 1) // amount) * amount + 1
        return datetime(year, 1, 1)
    if unit == "month":
        month_index = value.year * 12 + value.month - 1
        floored = (month_index // amount) * amount
        return datetime(floored // 12, floored % 12 + 1, 1)
    seconds = {
        "second": amount,
        "minute": amount * 60,
        "hour": amount * 3600,
        "day": amount * 86400,
    }[unit]
    epoch = datetime(1970, 1, 1)
    elapsed = (value - epoch).total_seconds()
    return epoch + timedelta(seconds=math.floor(elapsed / seconds) * seconds)


def _calendar_add(value: datetime, unit: str, amount: int) -> datetime:
    if unit == "year":
        return value.replace(year=value.year + amount)
    if unit == "month":
        month_index = value.year * 12 + value.month - 1 + amount
        return value.replace(year=month_index // 12, month=month_index % 12 + 1)
    return (
        value
        + {
            "second": timedelta(seconds=amount),
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
        }[unit]
    )


def _datetime_iso(value: datetime) -> str:
    if value.microsecond:
        return value.isoformat(timespec="milliseconds")
    if value.second:
        return value.isoformat(timespec="seconds")
    if value.hour or value.minute:
        return value.isoformat(timespec="minutes")
    return value.date().isoformat()


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


def _resolve_transparency_default(
    density_default: dict[str, Any],
    *,
    explicit: float | None,
    style_mode: str,
) -> dict[str, Any]:
    """Resolve mark transparency once so themes, density rules, and QA agree."""

    if explicit is not None:
        value = float(explicit)
        if not 0 <= value <= 100:
            raise ValueError("mark_transparency must be between 0 and 100.")
        return _decision(value, "explicit_user_value", "user")
    if density_default.get("value") is not None:
        return density_default
    if style_mode == "nature":
        return _decision(0.0, "nature_theme_opaque_marks", "theme")
    return density_default


def _data_label_defaults(
    context: VisualContext,
    *,
    y_min: float | None,
    y_max: float | None,
    font_size: int,
    font_reason: str,
    layer_series_counts: list[int],
    layer_formats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Choose a sparse, cross-chart data-label policy.

    Labels intentionally show only numeric values.  Axis titles already carry
    the metric and unit while legends identify series, so repeating either in
    every mark label would add clutter rather than information.
    """

    show = False
    scope = "none"
    position = "above"
    reason = "chart_or_density_does_not_benefit_from_automatic_labels"

    if y_min is None or y_max is None:
        reason = "no_numeric_values_to_label"
    elif _is_3d_variant(context.chart_variant):
        reason = "three_dimensional_labels_require_view_specific_layout"
    elif context.raw_chart_type == "histogram":
        reason = "histogram_shape_is_clearer_without_bin_labels"
    elif context.chart_type == "bar":
        mark_count = context.row_count * max(1, context.series_count)
        crosses_zero = y_min < 0 < y_max
        if context.series_count != 1:
            reason = "grouped_or_stacked_bars_would_create_repeated_labels"
        elif mark_count > 12:
            reason = "too_many_bars_for_readable_value_labels"
        elif crosses_zero:
            reason = "mixed_sign_bars_need_per_mark_outside_end_positioning"
        else:
            show = True
            scope = "all"
            position = "right" if _is_horizontal_bar(context.chart_variant) else "above"
            reason = "compact_single_series_bar_comparison"
    elif context.chart_type == "line":
        if context.row_count < 2:
            reason = "single_point_is_not_a_trend"
        elif context.series_count > 4:
            reason = "too_many_line_endpoints_for_readable_labels"
        else:
            show = True
            scope = "end"
            position = "right"
            reason = "label_only_the_latest_value_for_each_line"
    elif context.chart_type == "scatter":
        if context.series_count != 1:
            reason = "multi_series_scatter_labels_would_compete_with_the_legend"
        elif context.row_count > 80:
            reason = "dense_scatter_should_rely_on_shape_and_outlier_inspection"
        else:
            show = True
            scope = "all" if context.row_count <= 8 else "extrema"
            position = "above"
            reason = (
                "small_scatter_supports_point_values"
                if scope == "all"
                else "label_only_scatter_extrema"
            )

    return {
        "show": _decision(show, reason),
        "scope": _decision(scope, reason),
        "position": _decision(position if show else None, reason),
        "font_size": _decision(
            font_size if show else None,
            font_reason,
        ),
        "value_source": _decision("y" if show else None, "axis_title_carries_metric_and_unit"),
        "layer_series_counts": _decision(
            layer_series_counts if show else [],
            "apply_labels_only_to_primary_data_series",
        ),
        "layer_formats": _decision(
            layer_formats if show else [],
            "preserve_source_value_precision_independently_from_axis_ticks",
        ),
    }


def _data_label_numeric_format(series: list[Any]) -> dict[str, Any]:
    """Choose a compact label format from source values, not axis tick steps."""

    finite_values: list[float] = []
    for values in series:
        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
        finite_values.extend(float(value) for value in array[np.isfinite(array)])
    if not finite_values:
        return {"number_format": "decimal", "decimal_places": 0}

    magnitude = max(abs(value) for value in finite_values)
    if magnitude >= 100_000 or (0 < magnitude < 0.0001):
        return {"number_format": "scientific", "decimal_places": 2}

    decimals = 3
    for candidate in range(4):
        if all(
            math.isclose(
                value,
                round(value, candidate),
                rel_tol=1e-10,
                abs_tol=1e-10,
            )
            for value in finite_values
        ):
            decimals = candidate
            break
    return {"number_format": "decimal", "decimal_places": decimals}


def _reference_line_defaults(
    context: VisualContext,
    *,
    y_min: float | None,
    y_max: float | None,
    y2_min: float | None,
    y2_max: float | None,
) -> list[dict[str, Any]]:
    if (
        context.raw_chart_type == "histogram"
        or _is_3d_variant(context.chart_variant)
        or context.chart_type
        not in {
            "line",
            "scatter",
            "bar",
        }
    ):
        return []
    lines = []
    for layer_index, (lower, upper) in enumerate(((y_min, y_max), (y2_min, y2_max))):
        if lower is not None and upper is not None and lower < 0 < upper:
            lines.append(
                {
                    "axis": "y",
                    "value": 0.0,
                    "layer_index": layer_index,
                    "role": "zero",
                    "color_index": 19,
                    "line_style": 0,
                    "line_width": 1.0,
                }
            )
    return lines


def _is_horizontal_bar(chart_variant: str) -> bool:
    value = chart_variant.strip().lower().replace("-", "_").replace(" ", "_")
    return value in {"bar", "stack_bar", "floating_bar"} or value.endswith("_bar")


def _is_3d_variant(chart_variant: str) -> bool:
    value = chart_variant.strip().lower().replace("-", "_").replace(" ", "_")
    return value == "3d" or "3d" in value or value.startswith("gl")


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


def _numeric_format(
    lower: float | None,
    upper: float | None,
    step: float | None = None,
) -> tuple[str, int]:
    if lower is None or upper is None:
        return "decimal", -1
    magnitude = max(abs(lower), abs(upper))
    if magnitude >= 100_000 or (0 < magnitude < 0.0001):
        return "scientific", 2
    span = abs(upper - lower)
    if span <= 0:
        return "decimal", -1
    approximate_step = abs(step) if step is not None and step != 0 else span / 5.0
    decimals = (
        _decimal_places_for_step(approximate_step)
        if step is not None
        else max(0, min(6, int(math.ceil(-math.log10(approximate_step)))))
    )
    return "decimal", decimals


def _decimal_places_for_step(step: float) -> int:
    for decimals in range(7):
        scaled = step * (10**decimals)
        if math.isclose(scaled, round(scaled), rel_tol=1e-10, abs_tol=1e-10):
            return decimals
    return 6


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
