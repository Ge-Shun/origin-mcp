from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .compat import is_origin_version_at_least
from .errors import OriginOperationError


@dataclass(frozen=True)
class AnalysisAdapter:
    name: str
    x_function: str
    aliases: tuple[str, ...] = ()
    minimum_origin_version: float | None = None
    range_required: bool = False
    input_option: str = "iy"
    output_option: str = "oy"
    option_aliases: dict[str, str] = field(default_factory=dict)
    symbol_options: tuple[str, ...] = ()
    note: str = ""

    def supports(self, origin_version: float | int | None) -> bool:
        if self.minimum_origin_version is None:
            return True
        return is_origin_version_at_least(origin_version, self.minimum_origin_version)

    def normalize_options(self, options: dict[str, Any]) -> dict[str, Any]:
        normalized = {}
        for key, value in options.items():
            normalized[self.option_aliases.get(key, key)] = value
        return normalized

    def command(self, range_expr: str, output_sheet: str | None, options: dict[str, Any]) -> str:
        parts = [self.x_function]
        if range_expr:
            parts.append(f"{self.input_option}:={range_expr}")
        if output_sheet:
            parts.append(f"{self.output_option}:={output_sheet}")
        option_text = xf_options(self.normalize_options(options), self.symbol_options)
        if option_text:
            parts.append(option_text)
        return " ".join(parts) + ";"


ANALYSIS_ADAPTERS = {
    "linear_fit": AnalysisAdapter(
        name="linear_fit",
        x_function="fitlr",
        aliases=("fitlr", "linear-fit"),
        range_required=True,
        option_aliases={"intercept": "fixintercept", "slope": "fixslope"},
    ),
    "polynomial_fit": AnalysisAdapter(
        name="polynomial_fit",
        x_function="fitpoly",
        aliases=("fitpoly", "polynomial-fit"),
        minimum_origin_version=9.0,
        range_required=True,
        symbol_options=("coef", "err", "N", "AdjRSq", "RSqCOD"),
        option_aliases={
            "order": "polyorder",
            "degree": "polyorder",
            "fix_intercept": "fixint",
            "fixed_intercept": "intercept",
            "coefficients": "coef",
        },
    ),
    "nonlinear_fit": AnalysisAdapter(
        name="nonlinear_fit",
        x_function="nlfit",
        aliases=("nlfit", "nonlinear-fit"),
        range_required=True,
        note="For structured nonlinear fitting prefer originpro.NLFit in future adapters.",
    ),
    "smooth": AnalysisAdapter(
        name="smooth",
        x_function="smooth",
        aliases=("smoothing",),
        range_required=True,
        option_aliases={
            "points": "npts",
            "window_points": "npts",
            "polynomial_order": "polyorder",
            "percentile": "percent",
        },
        symbol_options=("method", "boundary", "prop"),
    ),
    "differentiate": AnalysisAdapter(
        name="differentiate",
        x_function="differentiate",
        aliases=("diff", "derivative"),
        range_required=True,
    ),
    "integrate": AnalysisAdapter(
        name="integrate",
        x_function="integ1",
        aliases=("integration", "integ1"),
        range_required=True,
    ),
    "peak_find": AnalysisAdapter(
        name="peak_find",
        x_function="pkFind",
        aliases=("pkfind", "find_peaks", "peak-find"),
        range_required=True,
        option_aliases={
            "smooth_points": "smooth",
            "direction": "dir",
            "local_points": "npts",
            "size_option": "option",
            "threshold": "value",
            "max_peaks": "value",
            "filter_by": "filter",
            "max_half_width": "hwidth",
            "foot_height": "fheight",
            "center_indices": "ocenter",
            "center_x": "ocenter_x",
            "center_y": "ocenter_y",
            "left_indices": "oleft",
            "right_indices": "oright",
        },
        symbol_options=("method", "dir", "option", "filter"),
    ),
    "descriptive_stats": AnalysisAdapter(
        name="descriptive_stats",
        x_function="moments",
        aliases=("moments", "statistics", "stats"),
        range_required=True,
    ),
}


def resolve_analysis_adapter(name: str, origin_version: float | int | None) -> AnalysisAdapter:
    normalized = name.lower().replace("-", "_")
    adapter = ANALYSIS_ADAPTERS.get(normalized)
    if adapter is None:
        adapter = next(
            (
                item
                for item in ANALYSIS_ADAPTERS.values()
                if normalized in {alias.replace("-", "_") for alias in item.aliases}
            ),
            None,
        )
    if adapter is None:
        supported = ", ".join(sorted(ANALYSIS_ADAPTERS))
        raise OriginOperationError(f"Unsupported analysis type: {name}. Supported: {supported}")
    if not adapter.supports(origin_version):
        raise OriginOperationError(
            f"Analysis '{adapter.name}' requires Origin >= {adapter.minimum_origin_version}; "
            f"detected {origin_version}."
        )
    return adapter


def xf_options(options: dict[str, Any], symbol_options: tuple[str, ...] = ()) -> str:
    parts = []
    for key, value in options.items():
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, str) and key in symbol_options:
            parts.append(f"{key}:={value}")
        elif isinstance(value, str):
            escaped = value.replace('"', r"\"")
            parts.append(f'{key}:="{escaped}"')
        else:
            parts.append(f"{key}:={value}")
    return " ".join(parts)
