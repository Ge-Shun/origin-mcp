from __future__ import annotations

import pytest

from origin_mcp.official_docs import (
    OfficialDocRecord,
    build_version_diff_overlay,
    classify_originlab_doc_url,
    diff_record_sets,
    discover_originpro_members_from_html,
    discover_records_from_html,
    merge_records,
    records_for_version,
    validate_records,
)


def test_classify_xfunction_function_page() -> None:
    record = classify_originlab_doc_url(
        "https://docs.originlab.com/x-function/ref/plotting/plotxy",
        "plotxy",
    )

    assert record is not None
    assert record.path == "x-function/plotting/plotxy"
    assert record.doc_family == "x_function"
    assert record.doc_kind == "xfunction"


def test_classify_xfunction_keeps_function_name_underscores() -> None:
    record = classify_originlab_doc_url(
        "https://docs.originlab.com/x-function/ref/plotting/plot_windrose",
        "plot_windrose",
    )

    assert record is not None
    assert record.path == "x-function/plotting/plot_windrose"


def test_classify_labtalk_command_page() -> None:
    record = classify_originlab_doc_url(
        "https://docs.originlab.com/labtalk/ref/display-control/legend",
        "legend",
    )

    assert record is not None
    assert record.path == "labtalk/commands/display-control/legend"
    assert record.doc_family == "labtalk"
    assert record.doc_kind == "command"


def test_classify_originpro_class_page() -> None:
    record = classify_originlab_doc_url(
        "https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1Axis.html",
        "Axis",
    )

    assert record is not None
    assert record.path == "python/originpro-api/graph/Axis"
    assert record.title == "originpro.graph.Axis"
    assert record.doc_kind == "class"


def test_discover_records_from_html_fixture() -> None:
    html = """
    <html><body>
      <a href="/x-function/ref/plotting/plotxy">plotxy</a>
      <a href="/labtalk/ref/display-control/axis">axis</a>
      <a href="/originpro/classoriginpro_1_1worksheet_1_1WSheet.html">WSheet</a>
      <a href="https://example.com/not-origin">ignore</a>
    </body></html>
    """

    records = discover_records_from_html(html, "https://docs.originlab.com/x-function/ref/")
    paths = {record.path for record in records}

    assert "x-function/plotting/plotxy" in paths
    assert "labtalk/commands/display-control/axis" in paths
    assert "python/originpro-api/worksheet/WSheet" in paths


def test_discover_xfunction_category_page_places_functions_under_category() -> None:
    html = '<html><body><a href="/x-function/ref/plotxy/">plotxy</a></body></html>'

    records = discover_records_from_html(
        html, "https://docs.originlab.com/x-function/ref/plotting/"
    )

    assert records[0].path == "x-function/plotting/plotxy"
    assert records[0].doc_kind == "xfunction"


def test_discover_labtalk_category_page_places_commands_under_category() -> None:
    html = '<html><body><a href="/labtalk/ref/legend-cmd/">legend</a></body></html>'

    records = discover_records_from_html(
        html, "https://docs.originlab.com/labtalk/ref/display-control/"
    )

    assert records[0].path == "labtalk/commands/display-control/legend"
    assert records[0].doc_kind == "command"


def test_discover_originpro_members_from_doxygen_rows() -> None:
    class_record = OfficialDocRecord(
        path="python/originpro-api/graph/Axis",
        title="originpro.graph.Axis",
        summary="summary",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1Axis.html",
        doc_family="originpro_api",
        doc_kind="class",
    )
    html = """
    <table>
      <tr>
        <td class="memItemLeft">int&nbsp;</td>
        <td class="memItemRight"><a class="el">scale</a>(self)</td>
      </tr>
      <tr>
        <td class="memItemLeft">&nbsp;</td>
        <td class="memItemRight"><a class="el">limits</a>(self)</td>
      </tr>
    </table>
    """

    records = discover_originpro_members_from_html(html, class_record)

    assert {record.path for record in records} == {
        "python/originpro-api/graph/Axis/scale",
        "python/originpro-api/graph/Axis/limits",
    }
    assert {record.doc_kind for record in records} == {"member"}


def test_validate_records_rejects_duplicate_path() -> None:
    record = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="summary",
        url="https://docs.originlab.com/x-function/ref/plotting/plotxy",
        doc_family="x_function",
        doc_kind="xfunction",
    )

    with pytest.raises(ValueError, match="Duplicate official docs path"):
        validate_records([record, record])


def test_merge_records_allows_generated_records_to_override_seed() -> None:
    seed = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="old",
        summary="summary",
        url="https://docs.originlab.com/x-function/ref/plotting/plotxy",
        doc_family="x_function",
        doc_kind="xfunction",
    )
    generated = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="updated",
        url="https://docs.originlab.com/x-function/ref/plotting/plotxy",
        doc_family="x_function",
        doc_kind="xfunction",
    )

    merged = merge_records([seed], [generated])

    assert merged == [generated]


def test_diff_record_sets_reports_added_removed_and_changed() -> None:
    old_common = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="old summary",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
        versions=("2025",),
    )
    new_common = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="new summary",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
        versions=("2026",),
    )
    removed = OfficialDocRecord(
        path="x-function/plotting/old",
        title="old",
        summary="summary",
        url="https://docs.originlab.com/x-function/ref/old/",
        doc_family="x_function",
        doc_kind="xfunction",
    )
    added = OfficialDocRecord(
        path="x-function/plotting/new",
        title="new",
        summary="summary",
        url="https://docs.originlab.com/x-function/ref/new/",
        doc_family="x_function",
        doc_kind="xfunction",
    )

    diff = diff_record_sets([old_common, removed], [new_common, added])

    assert [item["path"] for item in diff["added"]] == ["x-function/plotting/new"]
    assert [item["path"] for item in diff["removed"]] == ["x-function/plotting/old"]
    assert [item["path"] for item in diff["changed"]] == ["x-function/plotting/plotxy"]


def test_records_for_version_applies_delta_without_copying_base_index() -> None:
    base = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="baseline",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
    )
    changed = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="2025 behavior",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
        versions=("2025",),
    )
    added = OfficialDocRecord(
        path="x-function/plotting/new",
        title="new",
        summary="new in old source",
        url="https://docs.originlab.com/x-function/ref/new/",
        doc_family="x_function",
        doc_kind="xfunction",
        versions=("2025",),
    )
    diff_data = {
        "base_version": "2026",
        "diffs": {
            "2025": {
                "added": [added.as_json_dict()],
                "changed": [changed.as_json_dict()],
                "removed": [],
            }
        },
    }

    records = records_for_version([base], "2025", diff_data)
    by_path = {record.path: record for record in records}

    assert by_path["x-function/plotting/plotxy"].summary == "2025 behavior"
    assert by_path["x-function/plotting/plotxy"].version_status == "changed"
    assert by_path["x-function/plotting/new"].version_status == "added"


def test_build_version_diff_overlay_stores_only_differences() -> None:
    base = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="baseline",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
    )
    version = OfficialDocRecord(
        path="x-function/plotting/plotxy",
        title="plotxy",
        summary="changed",
        url="https://docs.originlab.com/x-function/ref/plotxy/",
        doc_family="x_function",
        doc_kind="xfunction",
        versions=("2025",),
    )

    overlay = build_version_diff_overlay([base], [version])

    assert overlay["added"] == []
    assert overlay["removed"] == []
    assert [item["path"] for item in overlay["changed"]] == ["x-function/plotting/plotxy"]
