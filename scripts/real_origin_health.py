"""Run a lightweight real-Origin bridge health gate.

Start the Origin bridge first, then run this script from the repository root.
The gate intentionally avoids graphing, export, OPJU save, and Origin shutdown.
It only checks the automation path needed before running heavier FigureSpec or
release smoke tests: ping, new project, table import, and worksheet info.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "health"
DEFAULT_DATA = ROOT / "examples" / "sample_data.csv"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    import origin_mcp.server as origin

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the JSON health report.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="CSV file to import for the worksheet health check.",
    )
    parser.add_argument(
        "--show-origin",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Ask Origin to show its GUI during the health check.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    report_path = output_dir / "health-report.json"
    report = run_health(
        origin,
        data_path=args.data.resolve(),
        output_dir=output_dir,
        report_path=report_path,
        show_origin=args.show_origin,
    )
    print_report(report)
    return 0 if report["ok"] else 1


def run_health(
    origin: Any,
    *,
    data_path: Path = DEFAULT_DATA,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    show_origin: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_path or (output_dir / "health-report.json")
    report: dict[str, Any] = {
        "ok": False,
        "started_at": _utc_timestamp(),
        "finished_at": None,
        "duration_sec": None,
        "backend": "bridge",
        "paths": {
            "data": str(data_path),
            "output_dir": str(output_dir),
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
        new_project = _run_step(
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
                    book_name="HealthBridge",
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
                    book_name="HealthBridge",
                    sheet_name="Data",
                ),
            ),
        )
        report["artifacts"] = {
            "bridge_status": _tool_data(bridge_status),
            "ping": _tool_data(ping),
            "new_project": _tool_data(new_project),
            "worksheet": _tool_data(imported).get("worksheet"),
            "worksheet_info": _tool_data(worksheet_info),
        }
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001 - health report should capture all failures
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
        message = result.get("message") or result.get("error_code") or "unknown error"
        raise RuntimeError(f"{name} failed: {message}")
    return result


def _tool_data(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data")
    return data if isinstance(data, dict) else {}


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def print_report(report: dict[str, Any]) -> None:
    print("Real Origin health gate:", "PASS" if report["ok"] else "FAIL")
    print(f"Report: {report['paths']['report']}")
    print(f"Duration: {report['duration_sec']}s")
    if not report["ok"]:
        print("Error:", (report.get("error") or {}).get("message"))


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    raise SystemExit(main())
