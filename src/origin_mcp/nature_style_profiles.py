"""Reusable output profiles for Nature-style scientific figures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .errors import OriginOperationError


@dataclass(frozen=True)
class NatureStyleProfile:
    name: str
    display_name: str
    target_width_mm: float | None
    axis_title_size: int
    tick_label_size: int
    legend_font_size: int
    annotation_font_size: int
    line_width: float
    symbol_size: float
    tick_length: int
    best_for: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


NATURE_STYLE_PROFILES: dict[str, NatureStyleProfile] = {
    "screen": NatureStyleProfile(
        name="screen",
        display_name="Screen / interactive",
        target_width_mm=None,
        axis_title_size=20,
        tick_label_size=20,
        legend_font_size=20,
        annotation_font_size=20,
        line_width=3.0,
        symbol_size=10.0,
        tick_length=3,
        best_for="Interactive Origin use, previews, and large on-screen figures.",
    ),
    "journal_single_column": NatureStyleProfile(
        name="journal_single_column",
        display_name="Journal single column",
        target_width_mm=89.0,
        axis_title_size=20,
        tick_label_size=20,
        legend_font_size=20,
        annotation_font_size=20,
        line_width=3.0,
        symbol_size=10.0,
        tick_length=3,
        best_for=(
            "Compact publication figures near an 89 mm single-column width with "
            "large-format typography."
        ),
    ),
    "journal_double_column": NatureStyleProfile(
        name="journal_double_column",
        display_name="Journal double column",
        target_width_mm=183.0,
        axis_title_size=20,
        tick_label_size=20,
        legend_font_size=20,
        annotation_font_size=20,
        line_width=3.0,
        symbol_size=10.0,
        tick_length=3,
        best_for=(
            "Wide publication figures near a 183 mm double-column width with "
            "large-format typography."
        ),
    ),
    "presentation": NatureStyleProfile(
        name="presentation",
        display_name="Presentation",
        target_width_mm=None,
        axis_title_size=24,
        tick_label_size=20,
        legend_font_size=20,
        annotation_font_size=20,
        line_width=3.5,
        symbol_size=10.0,
        tick_length=4,
        best_for="Slides, projected figures, and distant viewing.",
    ),
}

_PROFILE_ALIASES = {
    "default": "screen",
    "interactive": "screen",
    "single": "journal_single_column",
    "single_column": "journal_single_column",
    "journal_single": "journal_single_column",
    "double": "journal_double_column",
    "double_column": "journal_double_column",
    "journal_double": "journal_double_column",
    "slides": "presentation",
    "slide": "presentation",
}


def normalize_nature_style_profile(name: str | None = None) -> str:
    value = str(name or "screen").strip().lower().replace("-", "_").replace(" ", "_")
    normalized = _PROFILE_ALIASES.get(value, value)
    if normalized not in NATURE_STYLE_PROFILES:
        supported = ", ".join(NATURE_STYLE_PROFILES)
        raise OriginOperationError(f"Unsupported output_profile: {name!r}. Supported: {supported}.")
    return normalized


def resolve_nature_style_profile(name: str | None = None) -> NatureStyleProfile:
    return NATURE_STYLE_PROFILES[normalize_nature_style_profile(name)]


def nature_style_profile_catalog() -> dict[str, dict[str, Any]]:
    return {name: profile.as_dict() for name, profile in NATURE_STYLE_PROFILES.items()}
