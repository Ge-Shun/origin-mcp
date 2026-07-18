import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.nature_style_profiles import (
    nature_style_profile_catalog,
    normalize_nature_style_profile,
    resolve_nature_style_profile,
)


def test_nature_style_profiles_cover_screen_journal_and_presentation_outputs() -> None:
    catalog = nature_style_profile_catalog()

    assert list(catalog) == [
        "screen",
        "journal_single_column",
        "journal_double_column",
        "presentation",
    ]
    assert catalog["screen"]["axis_title_size"] == 20
    assert catalog["journal_single_column"]["target_width_mm"] == 89.0
    assert catalog["journal_double_column"]["target_width_mm"] == 183.0
    assert all(profile["axis_title_size"] >= 20 for profile in catalog.values())
    assert all(profile["tick_label_size"] >= 20 for profile in catalog.values())
    assert all(profile["legend_font_size"] >= 20 for profile in catalog.values())
    assert all(profile["annotation_font_size"] >= 20 for profile in catalog.values())
    assert all(profile["line_width"] >= 3.0 for profile in catalog.values())
    assert all(profile["symbol_size"] == 10.0 for profile in catalog.values())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "screen"),
        ("interactive", "screen"),
        ("single-column", "journal_single_column"),
        ("double", "journal_double_column"),
        ("slides", "presentation"),
    ],
)
def test_nature_style_profile_aliases(value: str | None, expected: str) -> None:
    assert normalize_nature_style_profile(value) == expected
    assert resolve_nature_style_profile(value).name == expected


def test_nature_style_profile_rejects_unknown_output() -> None:
    with pytest.raises(OriginOperationError, match="Unsupported output_profile"):
        resolve_nature_style_profile("poster")
