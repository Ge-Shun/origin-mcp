"""Pure chart-style data and chart-atlas route table.

These helpers carry no Origin/originpro dependency. They live outside the
mixin hierarchy so both ``_PlotMixin``-side code and ``_GraphStyleMixin``-side
code can share the same palette tables and chart-type normalisation rules.

``OriginClient`` exposes thin staticmethod shims that delegate here so the
historical ``self._nature_palette()`` access pattern keeps working.
"""

from __future__ import annotations

from typing import Any

from .errors import OriginOperationError


def nature_palette() -> list[tuple[int, int, int]]:
    return [
        (0, 114, 178),
        (213, 94, 0),
        (0, 158, 115),
        (204, 121, 167),
        (230, 159, 0),
        (86, 180, 233),
        (240, 228, 66),
        (0, 0, 0),
    ]


def nature_semantic_palette() -> dict[str, tuple[int, int, int]]:
    return {
        "hero": (0, 114, 178),
        "baseline": (0, 0, 0),
        "positive": (0, 158, 115),
        "negative": (213, 94, 0),
        "neutral": (117, 117, 117),
        "accent": (204, 121, 167),
        "secondary": (86, 180, 233),
        "warning": (230, 159, 0),
    }


def nature_acceptable_palette() -> set[tuple[int, int, int]]:
    return set(nature_palette()) | set(nature_semantic_palette().values())


def palette_roles(
    palette_role: str | list[str] | None,
    plot_count: int,
) -> list[str]:
    if plot_count <= 0:
        return []
    if palette_role is None:
        return [""] * plot_count
    if isinstance(palette_role, str):
        raw_roles = [role.strip().lower() for role in palette_role.split(",")]
    else:
        raw_roles = [str(role).strip().lower() for role in palette_role]
    available = nature_semantic_palette()
    roles = [role for role in raw_roles if role in available]
    if not roles:
        return [""] * plot_count
    if len(roles) == 1 and plot_count > 1:
        return roles + ["neutral"] * (plot_count - 1)
    return [roles[index % len(roles)] for index in range(plot_count)]


def normalize_chart_type(chart_type: str | None) -> str:
    value = (chart_type or "generic").strip().lower().replace("-", "_").replace(" ", "_")
    if value in {"l", "line", "line_symbol", "linesymbol", "line_scatter"}:
        return "line"
    if value in {
        "s",
        "scatter",
        "scatter3d",
        "3dscatter",
        "3d_scatter",
        "bubble",
        "bubble_color_mapped",
        "color_mapped",
    }:
        return "scatter"
    if value in {
        "bar",
        "column",
        "histogram",
        "stack_bar",
        "floating_bar",
        "column_stack",
        "3d_bars",
    }:
        return "bar"
    if value in {"box", "boxplot"}:
        return "box"
    if value in {
        "heatmap",
        "contour",
        "image",
        "matrix_heatmap",
        "matrix_contour",
        "ternary_contour",
    }:
        return "heatmap"
    if value in {
        "surface",
        "surface3d",
        "3d_surface",
        "matrix_3d_surface",
        "waterfall",
        "3d_ribbon",
    }:
        return "surface"
    if value in {"polar", "polar_xr_ytheta", "ternary", "smith"}:
        return "polar"
    return "generic"


def nature_chart_style(
    chart_type: str | None,
    line_width: float,
    symbol_size: float,
) -> dict[str, Any]:
    normalized = normalize_chart_type(chart_type)
    line_default = line_width == 1.2
    symbol_default = symbol_size == 4.5
    rules: dict[str, dict[str, float | None]] = {
        "line": {"line_width": 1.2, "symbol_size": 4.5},
        "scatter": {"line_width": 0.8, "symbol_size": 5.0},
        "bar": {"line_width": 0.8, "symbol_size": None},
        "box": {"line_width": 0.9, "symbol_size": None},
        "heatmap": {"line_width": None, "symbol_size": None},
        "surface": {"line_width": 0.8, "symbol_size": None},
        "polar": {"line_width": 1.0, "symbol_size": 4.5},
        "generic": {"line_width": line_width, "symbol_size": symbol_size},
    }
    selected = rules.get(normalized, rules["generic"])
    return {
        "chart_type": normalized,
        "line_width": selected["line_width"] if line_default else line_width,
        "symbol_size": selected["symbol_size"] if symbol_default else symbol_size,
    }


def nature_chart_type_for_plot_id(plot_type_id: int, template: str) -> str:
    from_template = normalize_chart_type(template)
    if from_template != "generic":
        return from_template
    if plot_type_id in {200, 202, 205, 207}:
        return "line"
    if plot_type_id in {193, 201, 240, 242, 243, 245, 247}:
        return "scatter"
    if plot_type_id in {203, 215, 216, 217, 219}:
        return "bar"
    if plot_type_id in {101, 103, 105, 220, 226}:
        return "heatmap"
    if plot_type_id in {241, 242, 243}:
        return "surface"
    return "generic"


def chart_atlas_routes() -> dict[str, dict[str, Any]]:
    return {
        "correlation": {
            "kind": "scatter",
            "chart_type": "scatter",
            "template": "scatter",
            "palette_role": "hero",
            "regression": True,
            "matrix_required": False,
            "rationale": "Correlation is clearest as scatter with a linear-fit summary.",
        },
        "effect_size": {
            "plot_type_id": 231,
            "template": "Errbar",
            "chart_type": "line",
            "palette_role": "hero,neutral",
            "matrix_required": False,
            "rationale": "Effect sizes are best shown as interval/error-bar estimates.",
        },
        "composition": {
            "plot_type_id": 216,
            "template": "bar",
            "chart_type": "bar",
            "palette_role": "hero,secondary,accent,neutral",
            "matrix_required": False,
            "rationale": "Compositional comparisons are routed to stacked/grouped bars.",
        },
        "matrix": {
            "plot_type_id": 105,
            "template": "heatmap",
            "chart_type": "heatmap",
            "palette_role": "neutral",
            "matrix_required": True,
            "rationale": "Matrix-like values are best represented as a heatmap.",
        },
        "image_plate": {
            "plot_type_id": 220,
            "template": "image",
            "chart_type": "heatmap",
            "palette_role": "neutral",
            "matrix_required": True,
            "rationale": "Image plates should use image/heatmap plots plus panel metadata.",
        },
        "time_series": {
            "kind": "line",
            "chart_type": "line",
            "template": "line",
            "palette_role": "hero,baseline",
            "matrix_required": False,
            "rationale": "Ordered continuous values are routed to line plots.",
        },
        "distribution": {
            "kind": "box",
            "chart_type": "box",
            "template": "box",
            "palette_role": "hero,neutral",
            "matrix_required": False,
            "rationale": "Distribution summaries are routed to compact box plots.",
        },
    }


def normalize_chart_intent(intent: str) -> str:
    value = intent.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "corr": "correlation",
        "correlation_plot": "correlation",
        "regression": "correlation",
        "effect": "effect_size",
        "effectsize": "effect_size",
        "forest": "effect_size",
        "interval": "effect_size",
        "composition_plot": "composition",
        "stacked_bar": "composition",
        "grouped_bar": "composition",
        "heatmap": "matrix",
        "matrix_heatmap": "matrix",
        "image": "image_plate",
        "microscopy": "image_plate",
        "image_panel": "image_plate",
        "timeseries": "time_series",
        "time": "time_series",
        "histogram": "distribution",
        "box": "distribution",
    }
    normalized = aliases.get(value, value)
    if normalized not in chart_atlas_routes():
        supported = ", ".join(sorted(chart_atlas_routes()))
        raise OriginOperationError(
            f"Unsupported chart atlas intent: {intent!r}. Supported: {supported}."
        )
    return normalized
