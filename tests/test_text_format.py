from origin_mcp.text_format import origin_rich_text


def test_origin_rich_text_converts_unicode_super_and_subscripts() -> None:
    assert origin_rich_text("CO₂ flux (m⁻² s⁻¹)") == "CO\\-(2) flux (m\\+(-2) s\\+(-1))"


def test_origin_rich_text_converts_markup_and_braced_notation() -> None:
    assert origin_rich_text("E^{1/2} and x_{max}") == "E\\+(1/2) and x\\-(max)"
    assert origin_rich_text("H<sub>2</sub>O m<sup>2</sup>") == "H\\-(2)O m\\+(2)"


def test_origin_rich_text_converts_single_letter_subscripts() -> None:
    assert origin_rich_text("signal_a and CO_2") == "signal\\-(a) and CO\\-(2)"


def test_origin_rich_text_avoids_multi_letter_identifier_underscores() -> None:
    assert origin_rich_text("sample_id and run_a1") == "sample_id and run_a1"


def test_origin_rich_text_preserves_existing_origin_escape_sequences() -> None:
    assert origin_rich_text("CO\\-(2)") == "CO\\-(2)"
