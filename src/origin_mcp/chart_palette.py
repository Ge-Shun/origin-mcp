"""Pure chart-style data and chart-atlas route table.

These helpers carry no Origin/originpro dependency. They live outside the
mixin hierarchy so both ``_PlotMixin``-side code and ``_GraphStyleMixin``-side
code can share the same palette tables and chart-type normalisation rules.

``OriginClient`` exposes thin staticmethod shims that delegate here so the
historical ``self._nature_palette()`` access pattern keeps working.
"""

from __future__ import annotations

import os
from typing import Any

from .errors import OriginOperationError
from .lcpmgh_palettes import (
    LCMPGH_DEFAULT_NATURE_COLORS,
    LCMPGH_LICENSE,
    LCMPGH_SOURCE_URL,
    LCMPGH_WEB_URL,
    lcpmgh_palette_records,
)

Rgb = tuple[int, int, int]


def _rgb(hex_color: str) -> Rgb:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise OriginOperationError(f"Invalid palette color: {hex_color!r}.")
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError as exc:
        raise OriginOperationError(f"Invalid palette color: {hex_color!r}.") from exc


_PALETTES: dict[str, dict[str, Any]] = {
    "nature": {
        "display_name": "lcpmgh Nature Editorial",
        "source_url": LCMPGH_SOURCE_URL,
        "web_url": LCMPGH_WEB_URL,
        "license": LCMPGH_LICENSE,
        "family": "lcpmgh/colors",
        "best_for": (
            "Nature-style editorial scientific figures with balanced blue, red, "
            "ochre, and teal contrast."
        ),
        "palette": list(LCMPGH_DEFAULT_NATURE_COLORS),
        "semantic": {
            "hero": "#27447C",
            "secondary": "#4871B3",
            "baseline": "#E73C36",
            "negative": "#991F22",
            "accent": "#B88640",
            "warning": "#B88640",
            "positive": "#168676",
            "neutral": "#6B6B6B",
            "background": "#F4F3EE",
        },
    },
}


def _semantic_from_palette(colors: list[str]) -> dict[str, str]:
    if not colors:
        return {}
    return {
        "hero": colors[0],
        "secondary": colors[1] if len(colors) > 1 else colors[0],
        "baseline": colors[1] if len(colors) > 1 else colors[0],
        "positive": colors[2] if len(colors) > 2 else colors[0],
        "negative": colors[3] if len(colors) > 3 else colors[-1],
        "accent": colors[4] if len(colors) > 4 else colors[-1],
        "warning": colors[4] if len(colors) > 4 else colors[-1],
        "neutral": "#6B6B6B",
        "background": "#F4F3EE",
    }


for _record in lcpmgh_palette_records():
    _name = _record["name"]
    if _name in _PALETTES:
        continue
    _colors = list(_record["colors"])
    _ordinal = _name.rsplit("_", 1)[-1]
    _PALETTES[_name] = {
        "display_name": f"lcpmgh/colors {int(_record['colors_count'])}-color #{_ordinal}",
        "source_url": _record["source_url"],
        "web_url": _record["web_url"],
        "license": _record["license"],
        "family": _record["family"],
        "source_index": _record["source_index"],
        "derived_from": _record.get("derived_from"),
        "colors_count": _record["colors_count"],
        "best_for": f"lcpmgh/colors local snapshot palette with {_record['colors_count']} colors.",
        "palette": _colors,
        "semantic": _semantic_from_palette(_colors),
    }

_PALETTE_ALIASES = {
    "default": "nature",
    "origin_mcp": "nature",
    "lcpmgh": "nature",
    "lcpmgh_nature": "nature",
    "nature_lcpmgh": "nature",
}

_AUTO_PALETTE_NAMES = {"lcpmgh_auto"}


def normalize_palette_name(palette_name: str | None = None) -> str:
    value = (
        palette_name
        or os.environ.get("ORIGIN_MCP_NATURE_PALETTE")
        or os.environ.get("ORIGIN_MCP_PALETTE")
        or "nature"
    )
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    normalized = _PALETTE_ALIASES.get(normalized, normalized)
    if normalized in _AUTO_PALETTE_NAMES:
        return normalized
    if normalized not in _PALETTES:
        supported = ", ".join(sorted(_PALETTES))
        raise OriginOperationError(
            f"Unsupported palette_name: {palette_name!r}. Supported: {supported}."
        )
    return normalized


def _palette_colors_count(palette: dict[str, Any]) -> int:
    return int(palette.get("colors_count") or len(palette["palette"]))


def _catalog_entry(name: str, palette: dict[str, Any], *, include_colors: bool) -> dict[str, Any]:
    entry = {
        "name": name,
        "display_name": palette["display_name"],
        "source_url": palette.get("source_url"),
        "web_url": palette.get("web_url"),
        "license": palette.get("license"),
        "family": palette.get("family"),
        "source_index": palette.get("source_index"),
        "derived_from": palette.get("derived_from"),
        "best_for": palette.get("best_for"),
        "colors_count": _palette_colors_count(palette),
        "semantic_roles": dict(palette["semantic"]),
    }
    if include_colors:
        entry["colors"] = list(palette["palette"])
    return entry


def palette_catalog(
    palette_name: str | None = None,
    colors_count: int | None = None,
    min_colors: int | None = None,
    max_colors: int | None = None,
    family: str | None = None,
    include_colors: bool = False,
    limit: int | None = 50,
) -> dict[str, dict[str, Any]]:
    catalog = {}
    family_normalized = family.strip().lower() if family else None
    selected_name = normalize_palette_name(palette_name) if palette_name else None
    if selected_name in _AUTO_PALETTE_NAMES:
        selected_name = None
    for name, palette in _PALETTES.items():
        count = _palette_colors_count(palette)
        palette_family = str(palette.get("family") or "").lower()
        if selected_name and name != selected_name:
            continue
        if colors_count is not None and count != colors_count:
            continue
        if min_colors is not None and count < min_colors:
            continue
        if max_colors is not None and count > max_colors:
            continue
        if family_normalized and palette_family != family_normalized:
            continue
        catalog[name] = _catalog_entry(name, palette, include_colors=include_colors)
        if limit is not None and limit > 0 and len(catalog) >= limit:
            break
    return catalog


def named_palette(palette_name: str | None = None) -> list[Rgb]:
    normalized = normalize_palette_name(palette_name)
    if normalized in _AUTO_PALETTE_NAMES:
        normalized = "nature"
    palette = _PALETTES[normalized]
    return [_rgb(color) for color in palette["palette"]]


def named_semantic_palette(palette_name: str | None = None) -> dict[str, Rgb]:
    normalized = normalize_palette_name(palette_name)
    if normalized in _AUTO_PALETTE_NAMES:
        normalized = "nature"
    palette = _PALETTES[normalized]
    return {role: _rgb(color) for role, color in palette["semantic"].items()}


def named_acceptable_palette(palette_name: str | None = None) -> set[Rgb]:
    return set(named_palette(palette_name)) | set(named_semantic_palette(palette_name).values())


def select_palette_for_count(plot_count: int) -> tuple[str, dict[str, Any]]:
    if plot_count <= 1:
        target = 2
    elif plot_count > 16:
        target = 16
    else:
        target = plot_count
    matches = [
        (name, palette)
        for name, palette in _PALETTES.items()
        if name.startswith("lcpmgh_")
        and palette.get("family") == "lcpmgh/colors"
        and _palette_colors_count(palette) == target
    ]
    if not matches:
        raise OriginOperationError(f"No lcpmgh/colors palette is available for {target} colors.")
    matches.sort(key=lambda item: int(item[1].get("source_index") or 0))
    return matches[0]


def auto_palette_notice(plot_count: int, palette_name: str) -> dict[str, Any]:
    return {
        "requested_palette_name": "lcpmgh_auto",
        "resolved_palette_name": palette_name,
        "plot_count": plot_count,
        "colors_count": 2 if plot_count <= 1 else min(plot_count, 16),
        "warning": (
            "Plot count exceeds the recommended lcpmgh/colors range of 16; "
            "the selected 16-color palette is reused cyclically."
            if plot_count > 16
            else None
        ),
    }


def nature_palette() -> list[Rgb]:
    return named_palette("nature")


def nature_semantic_palette() -> dict[str, Rgb]:
    return named_semantic_palette("nature")


def nature_acceptable_palette() -> set[Rgb]:
    return named_acceptable_palette("nature")


def palette_roles(
    palette_role: str | list[str] | None,
    plot_count: int,
    palette_name: str | None = None,
) -> list[str]:
    if plot_count <= 0:
        return []
    if palette_role is None:
        return [""] * plot_count
    if isinstance(palette_role, str):
        raw_roles = [role.strip().lower() for role in palette_role.split(",")]
    else:
        raw_roles = [str(role).strip().lower() for role in palette_role]
    available = named_semantic_palette(palette_name)
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
    line_default = line_width == 3.0
    symbol_default = symbol_size == 4.5
    rules: dict[str, dict[str, float | None]] = {
        "line": {"line_width": 3.0, "symbol_size": 4.5},
        "scatter": {"line_width": 1.8, "symbol_size": 5.0},
        "bar": {"line_width": 1.8, "symbol_size": None},
        "box": {"line_width": 1.8, "symbol_size": None},
        "heatmap": {"line_width": None, "symbol_size": None},
        "surface": {"line_width": 1.8, "symbol_size": None},
        "polar": {"line_width": 2.2, "symbol_size": 4.5},
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
        "3d_scatter": {
            "plot_type_id": 240,
            "template": "3d",
            "chart_type": "scatter",
            "palette_role": "hero",
            "matrix_required": False,
            "rationale": "XYZ table data is routed to a 3D scatter plot.",
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
        "3d": "3d_scatter",
        "3d_scatter_xyz": "3d_scatter",
        "scatter_3d": "3d_scatter",
        "scatter_xyz": "3d_scatter",
        "xyz": "3d_scatter",
        "xyz_scatter": "3d_scatter",
    }
    normalized = aliases.get(value, value)
    if normalized not in chart_atlas_routes():
        supported = ", ".join(sorted(chart_atlas_routes()))
        raise OriginOperationError(
            f"Unsupported chart atlas intent: {intent!r}. Supported: {supported}."
        )
    return normalized
