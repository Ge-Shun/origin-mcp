from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .origin_client import OriginClient


def main() -> None:
    args = _parse_args()
    result = run_smoke_test(
        data_path=args.data,
        xyz_data_path=args.xyz_data,
        output_dir=args.output_dir,
        project_path=args.project_path,
        show=args.show,
        detach=not args.no_detach,
        gallery=args.gallery,
        analysis=args.analysis,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


def run_smoke_test(
    data_path: Path | None = None,
    xyz_data_path: Path | None = None,
    output_dir: Path | None = None,
    project_path: Path | None = None,
    show: bool = True,
    detach: bool = True,
    gallery: bool = False,
    analysis: bool = False,
) -> dict[str, Any]:
    repo_root = _default_repo_root()
    data_path = (data_path or repo_root / "examples" / "sample_data.csv").resolve()
    xyz_data_path = (xyz_data_path or repo_root / "examples" / "xyz_data.csv").resolve()
    output_dir = (output_dir or repo_root / "output" / "smoke_test").resolve()
    project_path = (project_path or output_dir / "origin_mcp_smoke.opju").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    client = OriginClient()
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {}

    try:
        steps.append({"step": "connect", **client.connect(show=show)})
        capabilities = client.capabilities(show=show, refresh=True)
        steps.append({"step": "capabilities", **capabilities})
        steps.append(
            {
                "step": "plot_type_coverage",
                **client.plot_type_coverage(
                    origin_version=capabilities.get("origin_version"),
                ),
            }
        )
        steps.append({"step": "new_project", **client.new_project(show=show)})

        worksheet, graph = client.plot_table(
            path=data_path,
            kind="line",
            x_col="time",
            y_cols=["signal_a", "signal_b"],
            book_name="OriginMcpSmoke",
            sheet_name="Signals",
            graph_name="Origin MCP Smoke",
            title="Origin MCP Smoke Test",
            x_label="Time",
            y_label="Signal",
            show_legend=True,
        )
        steps.append(
            {
                "step": "plot_table",
                "worksheet": worksheet.as_dict(),
                "graph": graph.as_dict(),
            }
        )

        steps.append(
            {
                "step": "publication_style",
                **client.apply_publication_style(graph_name=graph.graph_name),
            }
        )
        steps.append(
            {
                "step": "reference_line",
                **client.add_reference_line(
                    graph_name=graph.graph_name,
                    axis="y",
                    value=0,
                    label="baseline",
                ),
            }
        )
        steps.append(
            {
                "step": "graph_label",
                **client.add_graph_label(
                    graph_name=graph.graph_name,
                    text="Origin MCP smoke test",
                    name="smoke_label",
                    left=20,
                    top=10,
                    font_size=12,
                ),
            }
        )

        preview = client.export_preview(
            graph_name=graph.graph_name,
            output_dir=output_dir,
            file_type="png",
        )
        steps.append({"step": "export_preview", **preview})

        if analysis:
            steps.append(_run_analysis_check(client))

        gallery_results: list[dict[str, Any]] = []
        if gallery:
            gallery_results = _run_gallery(
                client=client,
                data_path=data_path,
                xyz_data_path=xyz_data_path,
                output_dir=output_dir / "gallery",
            )
            steps.append(
                {
                    "step": "gallery",
                    "ok": all(item.get("ok") for item in gallery_results),
                    "count": len(gallery_results),
                    "items": gallery_results,
                }
            )

        steps.append({"step": "save_project", **client.save_project(project_path)})

        result = {
            "ok": True,
            "data_path": str(data_path),
            "xyz_data_path": str(xyz_data_path),
            "output_dir": str(output_dir),
            "project_path": str(project_path),
            "preview_path": preview["path"],
            "gallery": gallery_results,
            "steps": steps,
        }
    except Exception as exc:
        result = {
            "ok": False,
            "data_path": str(data_path),
            "xyz_data_path": str(xyz_data_path),
            "output_dir": str(output_dir),
            "project_path": str(project_path),
            "steps": steps,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        if detach:
            try:
                result["detached"] = client.detach()
            except Exception as exc:
                result["detach_error"] = {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
    return result


def _run_analysis_check(client: OriginClient) -> dict[str, Any]:
    return {
        "step": "analysis_output",
        **client.run_analysis(
            analysis="smooth",
            worksheet="[OriginMcpSmoke]Signals",
            x_col="time",
            y_col="signal_a",
            output_sheet="SmokeSmooth",
            options={"method": "sg", "points": 3},
            include_output=True,
            output_max_rows=20,
        ),
    }


def _run_gallery(
    client: OriginClient,
    data_path: Path,
    xyz_data_path: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        {
            "name": "line",
            "path": data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="line",
                x_col="time",
                y_cols=["signal_a", "signal_b"],
                graph_name="Gallery Line",
                export_path=export,
            ),
        },
        {
            "name": "scatter",
            "path": data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="scatter",
                x_col="time",
                y_cols=["signal_a"],
                graph_name="Gallery Scatter",
                export_path=export,
            ),
        },
        {
            "name": "histogram",
            "path": data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="histogram",
                x_col="time",
                y_cols=["signal_a"],
                graph_name="Gallery Histogram",
                export_path=export,
            ),
        },
        {
            "name": "box",
            "path": data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="box",
                x_col="time",
                y_cols=["signal_a", "signal_b"],
                graph_name="Gallery Box",
                export_path=export,
            ),
        },
        {
            "name": "contour",
            "path": xyz_data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="contour",
                x_col="x",
                y_cols=["y"],
                z_col="z",
                graph_name="Gallery Contour",
                export_path=export,
            ),
        },
        {
            "name": "heatmap",
            "path": xyz_data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="heatmap",
                x_col="x",
                y_cols=["y"],
                z_col="z",
                graph_name="Gallery Heatmap",
                export_path=export,
            ),
        },
        {
            "name": "3d_scatter",
            "path": xyz_data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="scatter3d",
                x_col="x",
                y_cols=["y"],
                z_col="z",
                graph_name="Gallery 3D Scatter",
                export_path=export,
            ),
        },
        {
            "name": "polar",
            "path": data_path,
            "runner": lambda path, export: client.plot_table(
                path=path,
                kind="polar",
                x_col="time",
                y_cols=["signal_a"],
                graph_name="Gallery Polar",
                export_path=export,
            ),
        },
        {
            "name": "bubble",
            "path": xyz_data_path,
            "runner": lambda path, export: client.plot_table_by_id(
                path=path,
                plot_type_id=193,
                template="scatter",
                selected_cols=["x", "y", "z"],
                graph_name="Gallery Bubble",
                export_path=export,
            ),
        },
        {
            "name": "pie",
            "path": data_path,
            "runner": lambda path, export: client.plot_table_by_id(
                path=path,
                plot_type_id=225,
                template="pie",
                selected_cols=["time", "signal_a"],
                graph_name="Gallery Pie",
                export_path=export,
            ),
        },
    ]

    results = []
    for case in cases:
        export_path = output_dir / f"{case['name']}.png"
        try:
            value = case["runner"](case["path"], export_path)
            graph = value[1] if isinstance(value, tuple) else value
            results.append(
                {
                    "name": case["name"],
                    "ok": True,
                    "graph": graph.as_dict(),
                    "export_path": str(export_path),
                    "inspection": client.inspect_export(export_path),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "name": case["name"],
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    return results


def _default_repo_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "examples" / "sample_data.csv").exists():
        return source_root
    return Path.cwd().resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an end-to-end Origin smoke test for origin-mcp.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="CSV input path. Defaults to examples/sample_data.csv.",
    )
    parser.add_argument(
        "--xyz-data",
        type=Path,
        default=None,
        help="XYZ CSV input path for contour, heatmap, and 3D gallery plots.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for exported preview and project files.",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=None,
        help="OPJU path for the saved smoke-test project.",
    )
    parser.add_argument(
        "--hide",
        dest="show",
        action="store_false",
        help="Run Origin hidden when supported.",
    )
    parser.add_argument(
        "--no-detach",
        action="store_true",
        help="Leave the Origin automation connection attached after the test.",
    )
    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Run an analysis step and read the output worksheet back as JSON.",
    )
    parser.add_argument(
        "--gallery",
        action="store_true",
        help="Generate a multi-plot gallery under the output directory.",
    )
    parser.set_defaults(show=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
