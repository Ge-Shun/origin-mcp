from pathlib import Path

from origin_mcp.compat import PLOT_TYPE_CATALOG
from origin_mcp.plot_matrix import (
    _safe_graph_structure,
    annotate_duplicate_exports,
    build_plot_matrix_cases,
    columns_for_input,
    ensure_plot_matrix_data,
    export_quality_issues,
    render_markdown_report,
    summarize_quality,
    summarize_results,
)


def test_build_plot_matrix_cases_covers_catalog() -> None:
    cases = build_plot_matrix_cases()

    assert len(cases) == len(PLOT_TYPE_CATALOG)
    assert {case.id for case in cases} == {int(item["id"]) for item in PLOT_TYPE_CATALOG}
    assert any(case.matrix_required for case in cases)


def test_columns_for_input_patterns() -> None:
    assert columns_for_input("XY Range") == ["x", "y"]
    assert columns_for_input("XYY Range") == ["x", "y", "y2"]
    assert columns_for_input("XYZXYZ Range/XYZdXdYdZ Range") == [
        "x",
        "y",
        "z",
        "dx",
        "dy",
        "dz",
    ]
    assert columns_for_input("OHLC Range") == ["date", "open", "high", "low", "close"]
    assert columns_for_input("Matrix Object") == []


def test_ensure_plot_matrix_data_writes_expected_columns(tmp_path: Path) -> None:
    path = ensure_plot_matrix_data(tmp_path / "matrix.csv")
    text = path.read_text(encoding="utf-8")

    assert text.startswith("x,y,y2,y3,x2,z,z2,dx,dy,dz,xerr,yerr,date,open,high,low,close")


def test_render_markdown_report_summarizes_results() -> None:
    report = {
        "capabilities": {
            "origin_version": 10.3,
            "originpro_version": "1.1.15",
            "originext_version": "1.2.5",
        },
        "backend": "mcp_server",
        "matrix_range": "[MBook1]MSheet1!1",
        "summary": summarize_results(
            [
                {"status": "passed"},
                {"status": "failed"},
                {"status": "skipped"},
            ]
        ),
        "results": [
            {
                "id": 200,
                "name": "Line",
                "status": "passed",
                "template": "line",
                "export_path": "line.png",
                "inspection": {"looks_nonempty": True},
            }
        ],
    }

    markdown = render_markdown_report(report)

    assert "Passed: 1" in markdown
    assert "Backend: mcp_server" in markdown
    assert "Matrix range: [MBook1]MSheet1!1" in markdown
    assert "| 200 | Line | passed | line | ok | line.png |  |" in markdown


def test_export_quality_issues_uses_visual_content() -> None:
    assert export_quality_issues({"exists": True, "size_bytes": 10, "looks_nonempty": True}) == []
    assert export_quality_issues({"exists": True, "size_bytes": 10, "looks_nonempty": False}) == [
        "blank_or_near_blank_export"
    ]
    assert export_quality_issues(
        {"exists": True, "size_bytes": 10, "looks_nonempty": True},
        {"layers_count": 1, "layers": [{"plots_count": 0}]},
    ) == ["graph_has_no_plots"]


def test_quality_summary_counts_decoded_issues_and_duplicates() -> None:
    results = [
        {
            "inspection": {
                "image_quality": {"decoded": True, "issues": ["low_color_complexity"]},
            },
            "quality_issues": ["export_dimensions_too_small"],
        },
        {
            "inspection": {
                "image_quality": {"decoded": True, "issues": ["blank_or_near_blank"]},
            },
            "quality_warnings": ["duplicate_export_sha256"],
        },
    ]

    summary = summarize_quality(results)

    assert summary["inspected"] == 2
    assert summary["issues"] == 1
    assert summary["decoded_png"] == 2
    assert summary["blank_or_near_blank"] == 1
    assert summary["low_color_complexity"] == 1
    assert summary["duplicates"] == 1


def test_annotate_duplicate_exports_marks_warnings() -> None:
    results = [
        {"id": 1, "name": "A", "inspection": {"sha256": "same"}},
        {"id": 2, "name": "B", "inspection": {"sha256": "same"}},
        {"id": 3, "name": "C", "inspection": {"sha256": "other"}},
    ]

    duplicates = annotate_duplicate_exports(results)

    assert duplicates == [
        {
            "sha256": "same",
            "cases": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
        }
    ]
    assert results[0]["quality_warnings"] == ["duplicate_export_sha256"]
    assert results[1]["quality_warnings"] == ["duplicate_export_sha256"]
    assert "quality_warnings" not in results[2]


def test_safe_graph_structure_falls_back_to_active_graph() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls = []

        def get_graph_info(self, graph_name: str | None) -> dict[str, object]:
            self.calls.append(graph_name)
            if graph_name:
                raise RuntimeError(f"Graph not found: {graph_name}")
            return {"graph_name": "Graph1", "layers_count": 1, "layers": [{"plots_count": 1}]}

    client = FakeClient()

    result = _safe_graph_structure(client, "requested")

    assert result is not None
    assert result["graph_name"] == "Graph1"
    assert "active graph" in str(result["warning"])
    assert client.calls == ["requested", None]
