from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SAMPLE_CSV = ROOT / "examples" / "sample_data.csv"


def main() -> int:
    import origin_mcp.server as origin

    parser = argparse.ArgumentParser(
        description="Run an end-to-end Origin smoke test through the Origin GUI bridge."
    )
    parser.add_argument("--data", type=Path, default=SAMPLE_CSV, help="CSV file to import.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "origin-mcp-smoke",
        help="Directory for exported image and OPJU project.",
    )
    parser.add_argument(
        "--keep-origin-open",
        action="store_true",
        help="Detach instead of quitting Origin at the end of the smoke run.",
    )
    parser.add_argument(
        "--show-origin",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show the Origin GUI while running the smoke test.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    export_path = args.output_dir / "origin_mcp_bridge_smoke.png"
    project_path = args.output_dir / "origin_mcp_bridge_smoke.opju"

    print("backend: bridge")
    print(f"data: {args.data}")
    print(f"export: {export_path}")
    print(f"project: {project_path}")

    try:
        bridge_status = require_ok("origin_bridge_status", origin.origin_bridge_status())
        print_json("bridge_status", bridge_status)

        ping = require_ok("origin_ping", origin.origin_ping(show=args.show_origin))
        print_json("ping", ping)

        require_ok("origin_new_project", origin.origin_new_project(show=args.show_origin))

        imported = require_ok(
            "origin_import_table",
            origin.origin_import_table(
                path=str(args.data),
                book_name="SmokeBridge",
                sheet_name="Data",
            ),
        )
        print_json("imported", imported)

        info = require_ok(
            "origin_get_worksheet_info",
            origin.origin_get_worksheet_info(
                book_name="SmokeBridge",
                sheet_name="Data",
            ),
        )
        print_json("worksheet_info", info)

        rows = require_ok(
            "origin_read_worksheet",
            origin.origin_read_worksheet(
                book_name="SmokeBridge",
                sheet_name="Data",
                max_rows=3,
            ),
        )
        print_json("worksheet_rows", rows)

        plotted = require_ok(
            "origin_plot_line",
            origin.origin_plot_line(
                path=str(args.data),
                x_col="time",
                y_cols=["signal_a", "signal_b"],
                graph_name="SmokeGraphBridge",
                title="origin-mcp bridge smoke",
                x_label="time",
                y_label="signal",
                export_path=str(export_path),
            ),
        )
        print_json("plotted", plotted)

        inspection = require_ok(
            "origin_inspect_export",
            origin.origin_inspect_export(str(export_path)),
        )
        print_json("inspection", inspection)
        data = inspection["data"]
        if not data.get("looks_nonempty"):
            raise RuntimeError(f"Export did not pass non-empty inspection: {data}")

        saved = require_ok("origin_save_project", origin.origin_save_project(str(project_path)))
        print_json("saved", saved)

        if args.keep_origin_open:
            require_ok("origin_detach", origin.origin_detach())
        else:
            require_ok("origin_quit", origin.origin_quit())

    except Exception as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        try:
            print_json("doctor", origin.origin_doctor(ping_origin=False))
        except Exception as doctor_exc:
            print(f"DOCTOR FAILED: {doctor_exc}", file=sys.stderr)
        return 1

    print("SMOKE PASSED")
    return 0


def require_ok(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("ok"):
        raise RuntimeError(f"{name} failed: {json.dumps(result, indent=2, default=str)}")
    return result


def print_json(label: str, result: dict[str, Any]) -> None:
    print(f"{label}:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
