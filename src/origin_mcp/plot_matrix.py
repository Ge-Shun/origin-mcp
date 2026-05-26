from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .compat import PLOT_TYPE_CATALOG
from .origin_client import OriginClient
from .runtime import python_runtime_profile

MATRIX_INPUTS = {"Matrix Object", "XYZ Range/Matrix Object", "Matrix Object/XYZ Range"}


@dataclass(frozen=True)
class PlotMatrixCase:
    id: int
    name: str
    category: str
    input: str
    template: str
    selected_columns: list[str]
    matrix_required: bool = False

    @property
    def slug(self) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in self.name)
        safe = "_".join(part for part in safe.split("_") if part)
        return f"{self.id}_{safe}"


def main() -> None:
    args = _parse_args()
    result = run_plot_matrix(
        output_dir=args.output_dir,
        project_path=args.project_path,
        data_path=args.data,
        matrix_range=args.matrix_range,
        show=args.show,
        detach=not args.no_detach,
        limit=args.limit,
        only=args.only,
        backend=args.backend,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


def run_plot_matrix(
    client: OriginClient | None = None,
    output_dir: Path | None = None,
    project_path: Path | None = None,
    data_path: Path | None = None,
    matrix_range: str | None = None,
    show: bool = True,
    detach: bool = True,
    limit: int | None = None,
    only: list[int] | None = None,
    backend: str = "originpro_external",
) -> dict[str, Any]:
    repo_root = _default_repo_root()
    output_dir = (output_dir or repo_root / "output" / "plot_matrix").resolve()
    export_dir = output_dir / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    data_path = (data_path or output_dir / "plot_matrix_data.csv").resolve()
    project_path = (project_path or output_dir / "origin_mcp_plot_matrix.opju").resolve()
    ensure_plot_matrix_data(data_path)

    client = client or OriginClient()
    cases = build_plot_matrix_cases()
    if only:
        allowed = set(only)
        cases = [case for case in cases if case.id in allowed]
    if limit is not None:
        cases = cases[:limit]

    results: list[dict[str, Any]] = []
    error_count = 0
    try:
        capabilities = client.capabilities(show=show, refresh=True)
        client.new_project(show=show)
        matrix_info = None
        if matrix_range is None and any(case.matrix_required for case in cases):
            matrix_info = client.create_sample_matrix_range()
            matrix_range = str(matrix_info["data_range"])
        for case in cases:
            result = _run_case(
                client=client,
                case=case,
                data_path=data_path,
                export_dir=export_dir,
                matrix_range=matrix_range,
            )
            results.append(result)
            if result["status"] == "failed":
                error_count += 1
        duplicate_exports = annotate_duplicate_exports(results)
        save_result = client.save_project(project_path)
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "python_runtime": python_runtime_profile().as_dict(),
            "output_dir": str(output_dir),
            "results": results,
        }
    finally:
        detach_result: dict[str, Any] | None = None
        if detach:
            try:
                detach_result = client.detach()
            except Exception as exc:
                detach_result = {"error_type": type(exc).__name__, "error": str(exc)}

    report = {
        "ok": error_count == 0,
        "output_dir": str(output_dir),
        "data_path": str(data_path),
        "project_path": str(project_path),
        "capabilities": capabilities,
        "backend": backend,
        "matrix_range": matrix_range,
        "matrix_info": matrix_info,
        "summary": summarize_results(results),
        "quality_summary": summarize_quality(results),
        "duplicate_exports": duplicate_exports,
        "results": results,
        "save_project": save_result,
        "detach": detach_result,
    }
    report_json = output_dir / "report.json"
    report_md = output_dir / "report.md"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_md.write_text(render_markdown_report(report), encoding="utf-8")
    report["report_json"] = str(report_json)
    report["report_markdown"] = str(report_md)
    return report


def build_plot_matrix_cases() -> list[PlotMatrixCase]:
    return [
        PlotMatrixCase(
            id=int(item["id"]),
            name=str(item["name"]),
            category=str(item["category"]),
            input=str(item["input"]),
            template=str(item["templates"][0]),
            selected_columns=columns_for_input(str(item["input"])),
            matrix_required=str(item["input"]) in MATRIX_INPUTS,
        )
        for item in PLOT_TYPE_CATALOG
    ]


def columns_for_input(input_spec: str) -> list[str]:
    if input_spec in MATRIX_INPUTS:
        return []
    if "XYZXYZ" in input_spec or "XYZdXdYdZ" in input_spec:
        return ["x", "y", "z", "dx", "dy", "dz"]
    if "OHLC" in input_spec:
        return ["date", "open", "high", "low", "close"]
    if "XYXY" in input_spec:
        return ["x", "y", "x2", "y2"]
    if "XYZZ" in input_spec:
        return ["x", "y", "z", "z2"]
    if "XYYY" in input_spec:
        return ["x", "y", "y2", "y3"]
    if "XYY" in input_spec:
        return ["x", "y", "y2"]
    if "XYZ" in input_spec:
        return ["x", "y", "z"]
    if "XYxErr" in input_spec:
        return ["x", "y", "xerr"]
    if "XYyErr" in input_spec:
        return ["x", "y", "yerr"]
    if input_spec.startswith("Y"):
        return ["y"]
    return ["x", "y"]


def ensure_plot_matrix_data(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    rows = []
    for index in range(1, 13):
        x = float(index)
        y = float(index * index) / 10.0
        rows.append(
            {
                "x": x,
                "y": y,
                "y2": y + 1.5,
                "y3": y + 3.0,
                "x2": x + 0.5,
                "z": float((index % 4) + 1),
                "z2": float((index % 5) + 2),
                "dx": 0.2,
                "dy": 0.3,
                "dz": 0.4,
                "xerr": 0.1,
                "yerr": 0.2,
                "date": index,
                "open": y,
                "high": y + 0.8,
                "low": y - 0.5,
                "close": y + 0.3,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def summarize_results(results: Iterable[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    for result in results:
        summary["total"] += 1
        status = result.get("status")
        if status in summary:
            summary[status] += 1
    return summary


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Origin Plot Matrix Report",
        "",
        f"- Origin version: {report['capabilities'].get('origin_version')}",
        f"- originpro: {report['capabilities'].get('originpro_version')}",
        f"- OriginExt: {report['capabilities'].get('originext_version')}",
        f"- Backend: {report.get('backend', '')}",
        f"- Matrix range: {report.get('matrix_range', '')}",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Skipped: {summary['skipped']}",
        f"- Quality issues: {report.get('quality_summary', {}).get('issues', 0)}",
        f"- Duplicate exports: {len(report.get('duplicate_exports', []))}",
        "",
        "| ID | Plot | Status | Template | Quality | Export | Error |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in report["results"]:
        export_path = result.get("export_path", "")
        error = result.get("error", result.get("reason", ""))
        quality = _result_quality_cell(result)
        lines.append(
            "| {id} | {name} | {status} | {template} | {quality} | {export} | {error} |".format(
                id=result.get("id", ""),
                name=_md_cell(str(result.get("name", ""))),
                status=result.get("status", ""),
                template=_md_cell(str(result.get("template", ""))),
                quality=_md_cell(quality),
                export=_md_cell(str(export_path)),
                error=_md_cell(str(error)),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _run_case(
    client: OriginClient,
    case: PlotMatrixCase,
    data_path: Path,
    export_dir: Path,
    matrix_range: str | None,
) -> dict[str, Any]:
    export_path = export_dir / f"{case.slug}.png"
    base = {
        "id": case.id,
        "name": case.name,
        "category": case.category,
        "input": case.input,
        "template": case.template,
        "selected_columns": case.selected_columns,
        "export_path": str(export_path),
    }
    try:
        if case.matrix_required and not matrix_range:
            return {
                **base,
                "status": "skipped",
                "reason": "Matrix input requires --matrix-range.",
            }
        if case.matrix_required:
            graph = client.plot_matrix_by_id(
                data_range=matrix_range or "",
                plot_type_id=case.id,
                template=case.template,
                graph_name=case.slug,
                export_path=export_path,
            )
            graph_info = graph.as_dict()
        else:
            _worksheet, graph, command = client.plot_table_by_id(
                path=data_path,
                plot_type_id=case.id,
                template=case.template,
                selected_cols=case.selected_columns,
                graph_name=case.slug,
                export_path=export_path,
            )
            graph_info = {**graph.as_dict(), "command": command}
        structure = _safe_graph_structure(client, graph_info.get("graph_name"))
        inspection = client.inspect_export(export_path)
        issues = export_quality_issues(inspection, structure)
        status = "passed" if not issues else "failed"
        return {
            **base,
            "status": status,
            "graph": graph_info,
            "graph_structure": structure,
            "inspection": inspection,
            "quality_issues": issues,
        }
    except Exception as exc:
        return {**base, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)}


def export_quality_issues(
    inspection: dict[str, Any],
    graph_structure: dict[str, Any] | None = None,
) -> list[str]:
    issues = []
    if not inspection.get("exists"):
        issues.append("missing_export")
    if int(inspection.get("size_bytes") or 0) <= 0:
        issues.append("empty_export")
    if not inspection.get("looks_nonempty"):
        issues.append("blank_or_near_blank_export")
    width = inspection.get("width")
    height = inspection.get("height")
    if isinstance(width, int) and isinstance(height, int) and (width < 64 or height < 64):
        issues.append("export_dimensions_too_small")
    if graph_structure and not graph_structure.get("error_type"):
        layers = graph_structure.get("layers", [])
        plot_count = sum(int(layer.get("plots_count") or 0) for layer in layers)
        if int(graph_structure.get("layers_count") or 0) <= 0:
            issues.append("graph_has_no_layers")
        if plot_count <= 0:
            issues.append("graph_has_no_plots")
    return _dedupe(issues)


def summarize_quality(results: Iterable[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "inspected": 0,
        "issues": 0,
        "decoded_png": 0,
        "blank_or_near_blank": 0,
        "low_color_complexity": 0,
        "duplicates": 0,
    }
    for result in results:
        inspection = result.get("inspection")
        if not isinstance(inspection, dict):
            continue
        summary["inspected"] += 1
        quality = inspection.get("image_quality")
        if isinstance(quality, dict) and quality.get("decoded"):
            summary["decoded_png"] += 1
            quality_issues = set(quality.get("issues", []))
            if "blank_or_near_blank" in quality_issues:
                summary["blank_or_near_blank"] += 1
            if "low_color_complexity" in quality_issues:
                summary["low_color_complexity"] += 1
        if result.get("quality_issues"):
            summary["issues"] += 1
        if result.get("quality_warnings"):
            summary["duplicates"] += 1
    return summary


def annotate_duplicate_exports(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        inspection = result.get("inspection")
        if not isinstance(inspection, dict):
            continue
        digest = inspection.get("sha256")
        if isinstance(digest, str) and digest:
            groups.setdefault(digest, []).append(result)
    duplicates = []
    for digest, members in groups.items():
        if len(members) < 2:
            continue
        case_refs = [{"id": item.get("id"), "name": item.get("name")} for item in members]
        duplicates.append({"sha256": digest, "cases": case_refs})
        for item in members:
            item.setdefault("quality_warnings", []).append("duplicate_export_sha256")
    return duplicates


def _safe_graph_structure(client: OriginClient, graph_name: Any) -> dict[str, Any] | None:
    if not isinstance(graph_name, str) or not graph_name:
        return None
    try:
        return client.get_graph_info(graph_name)
    except Exception as exc:
        if "Graph not found" in str(exc):
            try:
                info = client.get_graph_info(None)
                info["warning"] = (
                    f"Origin did not expose the plot command output as {graph_name!r}; "
                    "inspected the active graph instead."
                )
                return info
            except Exception:
                pass
        return {"error_type": type(exc).__name__, "error": str(exc)}


def _result_quality_cell(result: dict[str, Any]) -> str:
    parts = []
    issues = result.get("quality_issues") or []
    warnings = result.get("quality_warnings") or []
    if issues:
        parts.append("issues: " + ", ".join(str(issue) for issue in issues))
    elif result.get("inspection"):
        parts.append("ok")
    if warnings:
        parts.append("warnings: " + ", ".join(str(warning) for warning in warnings))
    return "; ".join(parts)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _default_repo_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "examples").exists():
        return source_root
    return Path.cwd().resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real-Origin plot type regression matrix.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--project-path", type=Path, default=None)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--matrix-range", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", type=int, nargs="*", default=None)
    parser.add_argument(
        "--backend",
        choices=["originpro_external", "mcp_server"],
        default="originpro_external",
        help=(
            "Execution backend label. CLI runs originpro_external; MCP tool calls use "
            "mcp_server inside the running server process."
        ),
    )
    parser.add_argument("--hide", dest="show", action="store_false")
    parser.add_argument("--no-detach", action="store_true")
    parser.set_defaults(show=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
