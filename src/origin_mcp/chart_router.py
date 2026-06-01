from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd
from pandas.api import types as pd_types


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    kind: str
    missing_ratio: float
    unique_count: int
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChartProfile:
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    numeric_columns: list[str]
    date_columns: list[str]
    categorical_columns: list[str]
    error_columns: list[str]
    lower_columns: list[str]
    upper_columns: list[str]
    group_columns: list[str]
    x_candidates: list[str]
    y_candidates: list[str]
    z_candidates: list[str]
    ohlc_columns: dict[str, str]
    ternary_columns: list[str]
    source_target_columns: dict[str, str]
    regular_xyz_grid: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChartRecommendation:
    chart_family: str
    chart: str
    score: float
    rationale: str
    kind: str | None = None
    plot_type_id: int | None = None
    template: str | None = None
    selected_cols: list[str] | None = None
    x_col: str | None = None
    y_cols: list[str] | None = None
    z_col: str | None = None
    y_error_col: str | None = None
    x_error_col: str | None = None
    palette_role: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value not in (None, [], {})}


def profile_table(df: pd.DataFrame) -> ChartProfile:
    columns: list[ColumnProfile] = []
    numeric_columns: list[str] = []
    date_columns: list[str] = []
    categorical_columns: list[str] = []
    error_columns: list[str] = []
    lower_columns: list[str] = []
    upper_columns: list[str] = []
    group_columns: list[str] = []
    x_candidates: list[str] = []
    y_candidates: list[str] = []
    z_candidates: list[str] = []

    row_count = len(df)
    for raw_name in df.columns:
        name = str(raw_name)
        series = df[raw_name]
        tags = _semantic_tags(name)
        kind = _column_kind(series, name)
        missing_ratio = float(series.isna().mean()) if row_count else 0.0
        unique_count = int(series.nunique(dropna=True))
        columns.append(
            ColumnProfile(
                name=name,
                kind=kind,
                missing_ratio=round(missing_ratio, 6),
                unique_count=unique_count,
                tags=tags,
            )
        )
        if kind == "numeric":
            numeric_columns.append(name)
        elif kind == "date":
            date_columns.append(name)
        elif kind == "categorical":
            categorical_columns.append(name)
        if "error" in tags:
            error_columns.append(name)
        if "lower" in tags:
            lower_columns.append(name)
        if "upper" in tags:
            upper_columns.append(name)
        if "group" in tags:
            group_columns.append(name)
        if "x" in tags:
            x_candidates.append(name)
        if "y" in tags:
            y_candidates.append(name)
        if "z" in tags:
            z_candidates.append(name)

    ohlc_columns = _detect_ohlc(df)
    ternary_columns = _detect_ternary_columns(df, numeric_columns)
    source_target_columns = _detect_source_target_columns(df)
    regular_xyz_grid = _detect_regular_xyz_grid(df, x_candidates, y_candidates, z_candidates)

    return ChartProfile(
        row_count=row_count,
        column_count=len(df.columns),
        columns=columns,
        numeric_columns=numeric_columns,
        date_columns=date_columns,
        categorical_columns=categorical_columns,
        error_columns=error_columns,
        lower_columns=lower_columns,
        upper_columns=upper_columns,
        group_columns=group_columns,
        x_candidates=x_candidates,
        y_candidates=y_candidates,
        z_candidates=z_candidates,
        ohlc_columns=ohlc_columns,
        ternary_columns=ternary_columns,
        source_target_columns=source_target_columns,
        regular_xyz_grid=regular_xyz_grid,
    )


def recommend_chart(
    profile: ChartProfile,
    intent: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    max_recommendations: int = 5,
) -> dict[str, Any]:
    normalized_intent = _normalize_intent(intent)
    columns = [column.name for column in profile.columns]
    x_name = _resolve_requested_column(columns, x_col)
    y_names = [_resolve_requested_column(columns, col) for col in y_cols or []]
    z_name = _resolve_requested_column(columns, z_col)
    yerr_name = _resolve_requested_column(columns, y_error_col)
    xerr_name = _resolve_requested_column(columns, x_error_col)

    candidates = _recommendation_candidates(
        profile=profile,
        intent=normalized_intent,
        x_col=x_name,
        y_cols=[name for name in y_names if name],
        z_col=z_name,
        y_error_col=yerr_name,
        x_error_col=xerr_name,
    )
    if not candidates:
        candidates = [
            ChartRecommendation(
                chart_family="line",
                chart="line",
                kind="line",
                template="line",
                score=10,
                rationale="Fallback route when the table shape is ambiguous.",
                x_col=profile.numeric_columns[0] if profile.numeric_columns else None,
                y_cols=profile.numeric_columns[1:2] if len(profile.numeric_columns) > 1 else None,
                warnings=["ambiguous_table_shape"],
            )
        ]

    ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
    selected = ranked[0]
    return {
        "intent": normalized_intent,
        "profile": profile.as_dict(),
        "selected": selected.as_dict(),
        "candidates": [item.as_dict() for item in ranked[:max_recommendations]],
    }


def _recommendation_candidates(
    profile: ChartProfile,
    intent: str | None,
    x_col: str | None,
    y_cols: list[str],
    z_col: str | None,
    y_error_col: str | None,
    x_error_col: str | None,
) -> list[ChartRecommendation]:
    candidates: list[ChartRecommendation] = []
    numeric = profile.numeric_columns
    categorical = profile.categorical_columns
    dates = profile.date_columns
    x = x_col or _first_existing(profile.x_candidates, numeric, dates)
    y_values = y_cols or _default_y_columns(profile, x)
    y = y_values[0] if y_values else None
    z = z_col or _first_existing(profile.z_candidates)
    yerr = y_error_col or _first_existing(profile.error_columns)
    xerr = x_error_col
    category_axis = _category_axis(profile, intent, explicit_x=x_col is not None)
    if category_axis:
        x = category_axis
        y_values = y_cols or _default_y_columns(profile, x)
        y = y_values[0] if y_values else None

    if profile.source_target_columns:
        candidates.append(
            ChartRecommendation(
                chart_family="network_matrix",
                chart="network_matrix",
                kind="heatmap",
                template="heatmap",
                score=_score(88, intent, {"network", "matrix"}),
                rationale=(
                    "Source/target columns indicate relational data; route to a matrix-style "
                    "view because origin-mcp does not yet expose a dedicated network graph."
                ),
                selected_cols=list(profile.source_target_columns.values()),
                warnings=["network_graph_not_yet_wrapped"],
            )
        )

    if profile.ohlc_columns:
        selected = [profile.ohlc_columns[key] for key in ("date", "open", "high", "low", "close")]
        candidates.append(
            ChartRecommendation(
                chart_family="financial",
                chart="candlestick",
                plot_type_id=221,
                template="Candlestick",
                score=_score(96, intent, {"candlestick", "ohlc", "time_series"}),
                rationale="Detected OHLC columns, which map directly to a candlestick chart.",
                selected_cols=selected,
            )
        )

    if len(profile.ternary_columns) >= 3:
        candidates.append(
            ChartRecommendation(
                chart_family="radar_polar",
                chart="ternary",
                plot_type_id=245,
                template="ternary",
                score=_score(94, intent, {"ternary", "composition", "radar_polar"}),
                rationale=(
                    "Detected three numeric composition columns whose row sums resemble 1 or 100."
                ),
                selected_cols=profile.ternary_columns[:3],
            )
        )

    if x and y and x in numeric and y in numeric:
        extra_numeric = [column for column in numeric if column not in {x, y}]
        if extra_numeric and intent in {"bubble", "color_mapped", "bubble_color_mapped"}:
            if len(extra_numeric) >= 2 and intent in {"color_mapped", "bubble_color_mapped"}:
                selected = [x, y, extra_numeric[0], extra_numeric[1]]
                candidates.append(
                    ChartRecommendation(
                        chart_family="scatter_bubble",
                        chart="bubble_color_mapped",
                        plot_type_id=248,
                        template="scatter",
                        score=_score(92, intent, {"bubble_color_mapped", "color_mapped"}),
                        rationale=(
                            "Detected paired numeric variables with size and color columns; "
                            "bubble plus color-mapped scatter preserves both encodings."
                        ),
                        selected_cols=selected,
                        x_col=x,
                        y_cols=[y],
                        palette_role="hero,secondary,accent",
                    )
                )
            else:
                selected = [x, y, extra_numeric[0]]
                chart = "color_mapped" if intent == "color_mapped" else "bubble"
                candidates.append(
                    ChartRecommendation(
                        chart_family="scatter_bubble",
                        chart=chart,
                        plot_type_id=247 if chart == "color_mapped" else 193,
                        template="scatter",
                        score=_score(90, intent, {"bubble", "color_mapped", "relationship"}),
                        rationale=(
                            "Detected paired numeric variables plus an additional numeric "
                            "encoding column."
                        ),
                        selected_cols=selected,
                        x_col=x,
                        y_cols=[y],
                        palette_role="hero,secondary",
                    )
                )

    if x and y and z:
        prefer_3d_scatter = intent in {"3d", "3d_scatter", "scatter3d", "xyz", "xyz_scatter"}
        if profile.regular_xyz_grid or intent in {"matrix", "heatmap"}:
            candidates.append(
                ChartRecommendation(
                    chart_family="heatmap_matrix",
                    chart="contour",
                    plot_type_id=243,
                    template="Contour",
                    score=_score(
                        70 if prefer_3d_scatter else 90,
                        intent,
                        {"matrix", "heatmap", "contour"},
                    ),
                    rationale=(
                        "Detected x/y/z values with a grid-like structure; "
                        "contour/heatmap is appropriate."
                    ),
                    selected_cols=[x, y, z],
                    x_col=x,
                    y_cols=[y],
                    z_col=z,
                )
            )
        candidates.append(
            ChartRecommendation(
                chart_family="scatter_bubble",
                chart="3d_scatter",
                plot_type_id=240,
                template="3d",
                score=_score(
                    94 if prefer_3d_scatter else 78,
                    intent,
                    {"scatter", "3d", "3d_scatter", "xyz_scatter", "relationship"},
                ),
                rationale=(
                    "Detected x/y/z numeric columns; 3D scatter preserves "
                    "point-level relationships."
                ),
                selected_cols=[x, y, z],
                x_col=x,
                y_cols=[y],
                z_col=z,
            )
        )

    if x and y and (yerr or xerr):
        selected = [x, y]
        if yerr:
            selected.append(yerr)
        if xerr:
            selected.append(xerr)
        candidates.append(
            ChartRecommendation(
                chart_family="forest_interval",
                chart="error_bar",
                plot_type_id=231 if yerr else 233,
                template="Errbar",
                score=_score(92, intent, {"effect_size", "interval", "error_bar", "forest"}),
                rationale=(
                    "Detected explicit error or interval columns; interval/error-bar "
                    "plot is appropriate."
                ),
                selected_cols=selected,
                x_col=x,
                y_cols=[y],
                y_error_col=yerr,
                x_error_col=xerr,
                palette_role="hero,neutral",
            )
        )

    if dates and y:
        date_x = x if x in dates else dates[0]
        candidates.append(
            ChartRecommendation(
                chart_family="line_trend",
                chart="time_series",
                kind="line",
                template="line",
                score=_score(88, intent, {"time_series", "line", "trend"}),
                rationale=(
                    "Detected a date/time column with numeric measurements; "
                    "line chart shows temporal trend."
                ),
                x_col=date_x,
                y_cols=y_values,
                palette_role="hero,baseline",
            )
        )

    if x and y and x in numeric and y in numeric:
        warnings = []
        base_score = 82
        if profile.row_count > 2000:
            base_score -= 8
            warnings.append("dense_scatter_consider_heatmap_or_binning")
        candidates.append(
            ChartRecommendation(
                chart_family="scatter_bubble",
                chart="scatter",
                kind="scatter",
                template="scatter",
                score=_score(base_score, intent, {"correlation", "scatter", "relationship"}),
                rationale=(
                    "Detected paired numeric variables; scatter shows relationship and outliers."
                ),
                x_col=x,
                y_cols=[y],
                palette_role="hero",
                warnings=warnings,
            )
        )

    if categorical and y:
        category = x if x in categorical else categorical[0]
        if profile.row_count > max(30, len(categorical) * 10) or intent == "distribution":
            candidates.append(
                ChartRecommendation(
                    chart_family="distribution",
                    chart="box",
                    plot_type_id=206,
                    template="box",
                    score=_score(82, intent, {"distribution", "box"}),
                    rationale=(
                        "Detected categorical groups with numeric observations; "
                        "box plot summarizes distributions."
                    ),
                    selected_cols=[y],
                    x_col=category,
                    y_cols=[y],
                    palette_role="hero,neutral",
                )
            )
        candidates.append(
            ChartRecommendation(
                chart_family="bar",
                chart="column",
                kind="column",
                template="column",
                score=_score(70, intent, {"bar", "comparison"}),
                rationale=(
                    "Detected categorical labels with numeric values; "
                    "column chart supports simple comparison."
                ),
                x_col=category,
                y_cols=[y],
                warnings=["bar_chart_assumes_values_are_summaries"],
            )
        )

    if len(y_values) >= 2 and x:
        if intent in {"composition", "stacked", "area"}:
            candidates.append(
                ChartRecommendation(
                    chart_family="area_stacked",
                    chart="stacked_bar",
                    plot_type_id=216,
                    template="bar",
                    score=_score(86, intent, {"composition", "stacked", "area"}),
                    rationale=(
                        "Detected multiple value series and a composition intent; "
                        "stacked bars show part-to-whole comparison."
                    ),
                    selected_cols=[x, *y_values],
                    x_col=x,
                    y_cols=y_values,
                    palette_role="hero,secondary,accent,neutral",
                )
            )
        candidates.append(
            ChartRecommendation(
                chart_family="line_trend",
                chart="multi_series_line",
                kind="line",
                template="line",
                score=_score(76, intent, {"time_series", "line", "trend"}),
                rationale=(
                    "Detected multiple y-series sharing one x column; "
                    "line chart compares trajectories."
                ),
                x_col=x,
                y_cols=y_values,
                palette_role="hero,baseline",
            )
        )

    if len(numeric) == 1:
        candidates.append(
            ChartRecommendation(
                chart_family="distribution",
                chart="histogram",
                plot_type_id=219,
                template="hist",
                score=_score(80, intent, {"distribution", "histogram"}),
                rationale="Detected a single numeric variable; histogram shows its distribution.",
                selected_cols=[numeric[0]],
                y_cols=[numeric[0]],
            )
        )

    return candidates


def _column_kind(series: pd.Series, name: str) -> str:
    if pd_types.is_numeric_dtype(series):
        return "numeric"
    if pd_types.is_datetime64_any_dtype(series):
        return "date"
    lower = name.strip().lower()
    if any(token in lower for token in ("date", "time", "year", "month", "day")):
        parsed = pd.to_datetime(series.dropna().head(50), errors="coerce")
        if len(parsed) and parsed.notna().mean() >= 0.8:
            return "date"
    unique_count = int(series.nunique(dropna=True))
    if unique_count <= max(20, len(series) // 5):
        return "categorical"
    return "text"


def _semantic_tags(name: str) -> list[str]:
    value = name.strip().lower().replace("-", "_").replace(" ", "_")
    tags = []
    if value in {"x", "time", "date", "year", "month"} or value.endswith("_x"):
        tags.append("x")
    if value in {"y", "value", "signal", "response"} or value.endswith("_y"):
        tags.append("y")
    if value in {"z", "intensity", "height"} or value.endswith("_z"):
        tags.append("z")
    if any(token in value for token in ("err", "error", "stderr", "std", "sem", "ci")):
        tags.append("error")
    if any(token in value for token in ("lower", "lo", "lcl", "ci_low", "ci_lower")):
        tags.append("lower")
    if any(token in value for token in ("upper", "hi", "ucl", "ci_high", "ci_upper")):
        tags.append("upper")
    if value in {"group", "category", "class", "condition", "treatment", "sample"}:
        tags.append("group")
    return tags


def _detect_ohlc(df: pd.DataFrame) -> dict[str, str]:
    lookup = {str(column).strip().lower(): str(column) for column in df.columns}
    mapping = {
        "date": lookup.get("date") or lookup.get("time") or lookup.get("year"),
        "open": lookup.get("open"),
        "high": lookup.get("high"),
        "low": lookup.get("low"),
        "close": lookup.get("close"),
    }
    return {key: value for key, value in mapping.items() if value} if all(mapping.values()) else {}


def _detect_ternary_columns(df: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    if len(numeric_columns) < 3 or df.empty:
        return []
    preferred_sets = [
        ("a", "b", "c"),
        ("ternary_a", "ternary_b", "ternary_c"),
        ("component_a", "component_b", "component_c"),
    ]
    lowered = {column.lower(): column for column in numeric_columns}
    for names in preferred_sets:
        cols = [lowered.get(name) for name in names]
        if all(cols) and _row_sums_look_compositional(df, [str(col) for col in cols]):
            return [str(col) for col in cols]
    for index in range(0, len(numeric_columns) - 2):
        window = numeric_columns[index : index + 3]
        if _row_sums_look_compositional(df, window):
            return window
    return []


def _row_sums_look_compositional(df: pd.DataFrame, columns: list[str]) -> bool:
    values = df[columns].dropna()
    if values.empty:
        return False
    sums = values.sum(axis=1)
    close_to_one = ((sums - 1.0).abs() < 0.05).mean()
    close_to_hundred = ((sums - 100.0).abs() < 1.0).mean()
    return bool(max(close_to_one, close_to_hundred) >= 0.8)


def _detect_source_target_columns(df: pd.DataFrame) -> dict[str, str]:
    lookup = {str(column).strip().lower(): str(column) for column in df.columns}
    source = lookup.get("source") or lookup.get("from")
    target = lookup.get("target") or lookup.get("to")
    if not source or not target:
        return {}
    result = {"source": source, "target": target}
    weight = lookup.get("weight") or lookup.get("value")
    if weight:
        result["weight"] = weight
    return result


def _detect_regular_xyz_grid(
    df: pd.DataFrame,
    x_candidates: list[str],
    y_candidates: list[str],
    z_candidates: list[str],
) -> bool:
    if df.empty or not x_candidates or not y_candidates or not z_candidates:
        return False
    x = x_candidates[0]
    y = y_candidates[0]
    pairs = df[[x, y]].dropna()
    if pairs.empty:
        return False
    unique_x = pairs[x].nunique(dropna=True)
    unique_y = pairs[y].nunique(dropna=True)
    unique_pairs = pairs.drop_duplicates().shape[0]
    return unique_pairs == len(pairs) and unique_x * unique_y == unique_pairs


def _normalize_intent(intent: str | None) -> str | None:
    if not intent:
        return None
    value = intent.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "corr": "correlation",
        "regression": "correlation",
        "effect": "effect_size",
        "forest": "effect_size",
        "interval": "effect_size",
        "hist": "histogram",
        "boxplot": "distribution",
        "stacked_bar": "composition",
        "grouped_bar": "composition",
        "timeseries": "time_series",
        "time": "time_series",
        "matrix_heatmap": "matrix",
        "image": "image_plate",
        "bubble_color": "bubble_color_mapped",
        "bubble_colormap": "bubble_color_mapped",
        "colormap": "color_mapped",
        "colour_mapped": "color_mapped",
        "3d_scatter_xyz": "3d_scatter",
        "scatter_3d": "3d_scatter",
        "scatter_xyz": "xyz_scatter",
        "xyz_3d": "3d_scatter",
    }
    return aliases.get(value, value)


def _category_axis(profile: ChartProfile, intent: str | None, explicit_x: bool) -> str | None:
    if explicit_x or not profile.categorical_columns or not profile.numeric_columns:
        return None
    first = profile.columns[0] if profile.columns else None
    if first and first.kind == "categorical":
        return first.name
    if intent in {"comparison", "bar", "distribution", "composition", "stacked", "area"}:
        return profile.categorical_columns[0]
    return None


def _score(base: float, intent: str | None, matches: set[str]) -> float:
    if intent is None:
        return base
    if intent in matches:
        return base + 15
    if intent == "correlation" and "relationship" in matches:
        return base + 12
    if intent == "distribution" and "histogram" in matches:
        return base + 12
    if intent == "time_series" and "trend" in matches:
        return base + 12
    return base - 5


def _resolve_requested_column(columns: list[str], value: str | int | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return columns[value] if 0 <= value < len(columns) else None
    return value if value in columns else None


def _first_existing(*groups: list[str]) -> str | None:
    for group in groups:
        if group:
            return group[0]
    return None


def _default_y_columns(profile: ChartProfile, x: str | None) -> list[str]:
    values = [column for column in profile.numeric_columns if column != x]
    if values:
        return values
    return [column for column in profile.numeric_columns[:1] if column != x]
