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
        "display_name": "Nature Skills Semantic",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": (
            "Nature-style method comparisons with hero, baseline, positive, "
            "and neutral roles."
        ),
        "palette": [
            "#0F4D92",
            "#8BCF8B",
            "#B64342",
            "#42949E",
            "#9A4D8E",
            "#CFCECE",
        ],
        "semantic": {
            "hero": "#0F4D92",
            "baseline": "#B64342",
            "positive": "#8BCF8B",
            "negative": "#B64342",
            "neutral": "#767676",
            "accent": "#42949E",
            "secondary": "#3775BA",
            "warning": "#FFD700",
            "background": "#CFCECE",
        },
    },
    "nmi_pastel": {
        "display_name": "Nature Machine Intelligence Pastel",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": "Dense method-family pages where related methods should stay visually unified.",
        "palette": [
            "#484878",
            "#7884B4",
            "#B4C0E4",
            "#E4E4F0",
            "#E4CCD8",
            "#F0C0CC",
        ],
        "semantic": {
            "hero": "#E4CCD8",
            "baseline": "#484878",
            "positive": "#2E9E44",
            "negative": "#E53935",
            "neutral": "#A8A8A8",
            "accent": "#7884B4",
            "secondary": "#F0C0CC",
            "warning": "#E53935",
            "background": "#E0E0F0",
        },
    },
    "nature_imaging": {
        "display_name": "Nature Skills Imaging",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": "Dark microscopy/image plates with grayscale context and fluorescent channels.",
        "palette": ["#22D7E6", "#FF2AD4", "#FFFFFF", "#B8B8B8", "#000000"],
        "semantic": {
            "hero": "#22D7E6",
            "baseline": "#B8B8B8",
            "positive": "#22D7E6",
            "negative": "#FF2AD4",
            "neutral": "#B8B8B8",
            "accent": "#FF2AD4",
            "secondary": "#FFFFFF",
            "warning": "#FF2AD4",
            "background": "#000000",
        },
    },
    "nature_material": {
        "display_name": "Nature Skills Material",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": "Materials and schematic-led scientific figure pages.",
        "palette": ["#77D7D1", "#33B5A5", "#B9A7E8", "#7C6CCF", "#E53935", "#D9D9D9"],
        "semantic": {
            "hero": "#33B5A5",
            "baseline": "#D9D9D9",
            "positive": "#77D7D1",
            "negative": "#E53935",
            "neutral": "#D9D9D9",
            "accent": "#7C6CCF",
            "secondary": "#B9A7E8",
            "warning": "#E53935",
        },
    },
    "nature_clinical": {
        "display_name": "Nature Skills Clinical",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": "Clinical composites and longitudinal follow-up plots.",
        "palette": ["#272727", "#E28E2C", "#D24B40", "#5B8FD6", "#7BAA5B", "#C45AD6"],
        "semantic": {
            "hero": "#5B8FD6",
            "baseline": "#272727",
            "positive": "#7BAA5B",
            "negative": "#D24B40",
            "neutral": "#F2E6D9",
            "accent": "#C45AD6",
            "secondary": "#E28E2C",
            "warning": "#D24B40",
        },
    },
    "nature_genomics": {
        "display_name": "Nature Skills Genomics",
        "source_url": "https://github.com/Yuan1z0825/nature-skills",
        "license": "MIT",
        "best_for": "Genomics, single-cell, and systems biology figures.",
        "palette": ["#D8D8D8", "#8F8F8F", "#D9544D", "#5B7FCA", "#B89BD9", "#4D4D4D"],
        "semantic": {
            "hero": "#5B7FCA",
            "baseline": "#8F8F8F",
            "positive": "#D9544D",
            "negative": "#5B7FCA",
            "neutral": "#D8D8D8",
            "accent": "#B89BD9",
            "secondary": "#4D4D4D",
            "warning": "#D9544D",
        },
    },
}

_PALETTE_ALIASES = {
    "default": "nature",
    "origin_mcp": "nature",
    "nmi": "nmi_pastel",
    "nmi-pastel": "nmi_pastel",
    "imaging": "nature_imaging",
    "material": "nature_material",
    "clinical": "nature_clinical",
    "genomics": "nature_genomics",
}


def normalize_palette_name(palette_name: str | None = None) -> str:
    value = (
        palette_name
        or os.environ.get("ORIGIN_MCP_NATURE_PALETTE")
        or os.environ.get("ORIGIN_MCP_PALETTE")
        or "nature"
    )
    normalized = str(value).strip().lower().replace(" ", "_")
    normalized = _PALETTE_ALIASES.get(normalized, normalized)
    if normalized not in _PALETTES:
        supported = ", ".join(sorted(_PALETTES))
        raise OriginOperationError(
            f"Unsupported palette_name: {palette_name!r}. Supported: {supported}."
        )
    return normalized


def palette_catalog() -> dict[str, dict[str, Any]]:
    catalog = {}
    for name, palette in _PALETTES.items():
        catalog[name] = {
            "name": name,
            "display_name": palette["display_name"],
            "source_url": palette.get("source_url"),
            "license": palette.get("license"),
            "best_for": palette.get("best_for"),
            "colors": list(palette["palette"]),
            "semantic_roles": dict(palette["semantic"]),
        }
    return catalog


def named_palette(palette_name: str | None = None) -> list[Rgb]:
    palette = _PALETTES[normalize_palette_name(palette_name)]
    return [_rgb(color) for color in palette["palette"]]


def named_semantic_palette(palette_name: str | None = None) -> dict[str, Rgb]:
    palette = _PALETTES[normalize_palette_name(palette_name)]
    return {role: _rgb(color) for role, color in palette["semantic"].items()}


def named_acceptable_palette(palette_name: str | None = None) -> set[Rgb]:
    return set(named_palette(palette_name)) | set(named_semantic_palette(palette_name).values())


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
