from types import SimpleNamespace

from origin_mcp.compat import collect_capabilities, is_origin_version_at_least, plot_type_coverage


def test_is_origin_version_at_least() -> None:
    assert is_origin_version_at_least(10.3, 10.15)
    assert is_origin_version_at_least("10.3", "10.15")
    assert not is_origin_version_at_least(10.15, 10.3)
    assert not is_origin_version_at_least(10.1, 10.15)
    assert not is_origin_version_at_least(None, 10.15)


def test_collect_capabilities_marks_missing_features() -> None:
    op = SimpleNamespace(lt_exec=lambda _script: True, save=lambda _path: True)

    data = collect_capabilities(op, 10.3)

    assert data["features"]["labtalk"]["available"] is True
    assert data["features"]["project_save"]["available"] is True
    assert data["features"]["project_open"]["available"] is False
    assert data["features"]["origin_2024_or_newer"]["available"] is True
    assert data["features"]["origin_2024_or_newer"]["note"] == (
        "Compatibility alias for origin_2024b_or_newer."
    )
    assert data["features"]["origin_2024b_or_newer"]["available"] is True
    assert data["features"]["origin_2026_or_newer"]["available"] is True
    assert "plot_type_coverage" in data


def test_plot_type_coverage_reports_direct_and_generic_support() -> None:
    coverage = plot_type_coverage(10.3)

    assert coverage["version_profile"]["recommended"] is True
    assert coverage["version_profile"]["name"] == "Origin 2026 or newer"
    assert coverage["summary"]["direct_tool_count"] == coverage["summary"]["catalog_count"]
    assert coverage["summary"]["not_wrapped_count"] == 0

    by_id = {item["id"]: item for item in coverage["items"]}
    assert by_id[200]["direct_tool"] == "origin_plot_line"
    assert by_id[204]["direct_tool"] == "origin_plot_area"
    assert by_id[220]["direct_tool"] == "origin_plot_image"


def test_plot_type_coverage_marks_2024b_as_not_guaranteed() -> None:
    coverage = plot_type_coverage(10.15)

    assert coverage["version_profile"]["name"] == "Origin 2024b to 2025"
    assert coverage["version_profile"]["recommended"] is False
