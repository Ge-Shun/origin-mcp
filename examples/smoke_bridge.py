from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
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
        help="Directory for exported image, OPJU project, and JSON report.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="JSON report path. Defaults to <output-dir>/smoke-report.json.",
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

    report = run_smoke(
        origin,
        data_path=args.data,
        output_dir=args.output_dir,
        report_path=args.report,
        keep_origin_open=args.keep_origin_open,
        show_origin=args.show_origin,
    )
    print_report(report)
    return 0 if report["ok"] else 1


def run_smoke(
    origin: Any,
    *,
    data_path: Path = SAMPLE_CSV,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    keep_origin_open: bool = False,
    show_origin: bool = True,
) -> dict[str, Any]:
    """Run the bridge smoke workflow and return a structured report."""

    output_dir = output_dir or (Path(tempfile.gettempdir()) / "origin-mcp-smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_path or (output_dir / "smoke-report.json")
    export_path = output_dir / "origin_mcp_bridge_smoke.png"
    project_path = output_dir / "origin_mcp_bridge_smoke.opju"

    report: dict[str, Any] = {
        "ok": False,
        "started_at": _utc_timestamp(),
        "finished_at": None,
        "duration_sec": None,
        "backend": "bridge",
        "paths": {
            "data": str(data_path),
            "output_dir": str(output_dir),
            "export": str(export_path),
            "project": str(project_path),
            "report": str(report_path),
        },
        "steps": [],
        "artifacts": {},
        "error": None,
        "doctor": None,
    }
    started = time.monotonic()

    try:
        bridge_status = _run_step(
            report,
            "origin_bridge_status",
            lambda: require_ok("origin_bridge_status", origin.origin_bridge_status()),
        )
        ping = _run_step(
            report,
            "origin_ping",
            lambda: require_ok("origin_ping", origin.origin_ping(show=show_origin)),
        )
        _run_step(
            report,
            "origin_new_project",
            lambda: require_ok(
                "origin_new_project",
                origin.origin_new_project(show=show_origin),
            ),
        )
        imported = _run_step(
            report,
            "origin_import_table",
            lambda: require_ok(
                "origin_import_table",
                origin.origin_import_table(
                    path=str(data_path),
                    book_name="SmokeBridge",
                    sheet_name="Data",
                ),
            ),
        )
        worksheet_info = _run_step(
            report,
            "origin_get_worksheet_info",
            lambda: require_ok(
                "origin_get_worksheet_info",
                origin.origin_get_worksheet_info(
                    book_name="SmokeBridge",
                    sheet_name="Data",
                ),
            ),
        )
        worksheet_rows = _run_step(
            report,
            "origin_read_worksheet",
            lambda: require_ok(
                "origin_read_worksheet",
                origin.origin_read_worksheet(
                    book_name="SmokeBridge",
                    sheet_name="Data",
                    max_rows=3,
                ),
            ),
        )
        plotted = _run_step(
            report,
            "origin_plot_line",
            lambda: require_ok(
                "origin_plot_line",
                origin.origin_plot_line(
                    path=str(data_path),
                    x_col="time",
                    y_cols=["signal_a", "signal_b"],
                    graph_name="SmokeGraphBridge",
                    title="origin-mcp bridge smoke",
                    x_label="time",
                    y_label="signal",
                    export_path=str(export_path),
                ),
            ),
        )
        inspection = _run_step(
            report,
            "origin_inspect_export",
            lambda: require_ok(
                "origin_inspect_export",
                origin.origin_inspect_export(str(export_path)),
            ),
        )
        inspection_data = inspection["data"]
        if not inspection_data.get("looks_nonempty"):
            raise RuntimeError(f"Export did not pass non-empty inspection: {inspection_data}")

        saved = _run_step(
            report,
            "origin_save_project",
            lambda: require_ok(
                "origin_save_project",
                origin.origin_save_project(str(project_path)),
            ),
        )
        close_step = "origin_detach" if keep_origin_open else "origin_quit"
        close_result = _run_step(
            report,
            close_step,
            lambda: (
                require_ok(close_step, origin.origin_detach())
                if keep_origin_open
                else require_ok(close_step, origin.origin_quit())
            ),
        )

        report["artifacts"] = {
            "bridge_status": _tool_data(bridge_status),
            "ping": _tool_data(ping),
            "worksheet": _tool_data(imported).get("worksheet"),
            "worksheet_info": _tool_data(worksheet_info),
            "worksheet_rows": _tool_data(worksheet_rows),
            "plot": _tool_data(plotted).get("graph"),
            "export_inspection": inspection_data,
            "saved_project": _tool_data(saved),
            "close": _tool_data(close_result),
        }
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001 - smoke report should capture all failures
        report["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        try:
            report["doctor"] = origin.origin_doctor(ping_origin=False)
        except Exception as doctor_exc:  # noqa: BLE001 - preserve original failure
            report["doctor"] = {
                "ok": False,
                "error": {
                    "type": type(doctor_exc).__name__,
                    "message": str(doctor_exc),
                },
            }
    finally:
        report["finished_at"] = _utc_timestamp()
        report["duration_sec"] = round(time.monotonic() - started, 3)
        write_report(report, report_path)

    return report


def _run_step(report: dict[str, Any], name: str, func: Any) -> dict[str, Any]:
    started = time.monotonic()
    step: dict[str, Any] = {
        "name": name,
        "ok": False,
        "duration_sec": None,
        "result": None,
        "error": None,
    }
    report["steps"].append(step)
    try:
        result = func()
    except Exception as exc:
        step["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    else:
        step["ok"] = True
        step["result"] = result
        return result
    finally:
        step["duration_sec"] = round(time.monotonic() - started, 3)


def require_ok(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("ok"):
        raise RuntimeError(f"{name} failed: {json.dumps(result, indent=2, default=str)}")
    return result


def write_report(report: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def print_report(report: dict[str, Any]) -> None:
    paths = report["paths"]
    print("backend: bridge")
    print(f"data: {paths['data']}")
    print(f"export: {paths['export']}")
    print(f"project: {paths['project']}")
    print(f"report: {paths['report']}")
    for step in report["steps"]:
        status = "ok" if step["ok"] else "failed"
        print(f"{step['name']}: {status} ({step['duration_sec']}s)")
    if report["ok"]:
        print("SMOKE PASSED")
    else:
        error = report.get("error") or {}
        print(f"SMOKE FAILED: {error.get('message', 'unknown error')}", file=sys.stderr)
        doctor = report.get("doctor")
        if doctor is not None:
            print_json("doctor", doctor)


def print_json(label: str, result: dict[str, Any]) -> None:
    print(f"{label}:")
    print(json.dumps(result, indent=2, default=str))


def _tool_data(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data")
    return data if isinstance(data, dict) else {}


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    raise SystemExit(main())
