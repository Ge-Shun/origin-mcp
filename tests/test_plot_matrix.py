import json
from pathlib import Path

from origin_mcp.compat import PLOT_TYPE_CATALOG
from origin_mcp.plot_matrix import (
    _safe_graph_structure,
    annotate_duplicate_exports,
    build_plot_matrix_cases,
    columns_for_input,
    columns_for_plot_type,
    ensure_plot_matrix_data,
    export_quality_issues,
    render_markdown_report,
    run_plot_matrix,
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


def test_columns_for_plot_type_uses_ternary_sample_columns() -> None:
    assert columns_for_plot_type(183, "XYZXYZ Range/XYZdXdYdZ Range") == [
        "vec_x",
        "vec_y",
        "vec_z",
        "vec_x2",
        "vec_y2",
        "vec_z2",
    ]
    assert columns_for_plot_type(184, "XYZZ Range") == [
        "err_x",
        "err_y",
        "err_z",
        "err_zerr",
    ]
    assert columns_for_plot_type(185, "XYZZ Range") == [
        "ternary_a",
        "ternary_b",
        "ternary_c",
        "ternary_value",
    ]
    assert columns_for_plot_type(245, "XYZ Range") == ["ternary_a", "ternary_b", "ternary_c"]


def test_ensure_plot_matrix_data_writes_expected_columns(tmp_path: Path) -> None:
    path = ensure_plot_matrix_data(tmp_path / "matrix.csv")
    text = path.read_text(encoding="utf-8")

    assert text.startswith("x,y,y2,y3,x2,z,z2,dx,dy,dz,xerr,yerr,date,open,high,low,close")
    assert "ternary_a,ternary_b,ternary_c,ternary_value" in text.splitlines()[0]
    assert "vec_x,vec_y,vec_z,vec_x2,vec_y2,vec_z2" in text.splitlines()[0]


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


def test_run_plot_matrix_exposes_top_level_summary(tmp_path: Path) -> None:
    class FakeGraph:
        def as_dict(self) -> dict[str, str]:
            return {"graph_name": "line", "export_path": str(tmp_path / "line.png")}

    class FakeWorksheet:
        def as_dict(self) -> dict[str, object]:
            return {"book_name": "Book1", "sheet_name": "Sheet1", "columns": [], "rows": 0}

    class FakeClient:
        def capabilities(self, show: bool, refresh: bool) -> dict[str, object]:
            return {
                "origin_version": 10.3,
                "originpro_version": "1.1.15",
                "originext_version": "1.2.5",
                "show": show,
                "refresh": refresh,
            }

        def new_project(self, show: bool) -> dict[str, bool]:
            return {"created": show}

        def plot_table_by_id(self, **_kwargs: object) -> tuple[FakeWorksheet, FakeGraph, str]:
            return FakeWorksheet(), FakeGraph(), "plotxy;"

        def get_graph_info(self, _graph_name: str | None) -> dict[str, object]:
            return {"layers_count": 1, "layers": [{"plots_count": 1}]}

        def inspect_export(self, _path: Path) -> dict[str, object]:
            return {
                "exists": True,
                "size_bytes": 128,
                "looks_nonempty": True,
                "width": 640,
                "height": 480,
                "sha256": "line-digest",
            }

        def save_project(self, path: Path) -> dict[str, str]:
            return {"path": str(path)}

        def detach(self) -> dict[str, bool]:
            return {"detached": True, "closed": False}

    result = run_plot_matrix(client=FakeClient(), output_dir=tmp_path, only=[200])

    assert result["ok"] is True
    assert result["total"] == 1
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 0
    assert result["summary"] == {"total": 1, "passed": 1, "failed": 0, "skipped": 0}

    report_json = Path(result["report_json"])
    persisted = json.loads(report_json.read_text(encoding="utf-8"))
    assert persisted["total"] == 1
    assert persisted["passed"] == 1


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
