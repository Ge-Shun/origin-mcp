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
        output_dir=args.output_dir,
        project_path=args.project_path,
        show=args.show,
        detach=not args.no_detach,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


def run_smoke_test(
    data_path: Path | None = None,
    output_dir: Path | None = None,
    project_path: Path | None = None,
    show: bool = True,
    detach: bool = True,
) -> dict[str, Any]:
    repo_root = _default_repo_root()
    data_path = (data_path or repo_root / "examples" / "sample_data.csv").resolve()
    output_dir = (output_dir or repo_root / "output" / "smoke_test").resolve()
    project_path = (project_path or output_dir / "origin_mcp_smoke.opju").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    client = OriginClient()
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {}

    try:
        steps.append({"step": "connect", **client.connect(show=show)})
        steps.append({"step": "capabilities", **client.capabilities(show=show, refresh=True)})
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
        steps.append({"step": "save_project", **client.save_project(project_path)})

        result = {
            "ok": True,
            "data_path": str(data_path),
            "output_dir": str(output_dir),
            "project_path": str(project_path),
            "preview_path": preview["path"],
            "steps": steps,
        }
    except Exception as exc:
        result = {
            "ok": False,
            "data_path": str(data_path),
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
    parser.set_defaults(show=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
