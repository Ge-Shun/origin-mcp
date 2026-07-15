"""Command-line entry point for the MCP server, setup, and diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from .diagnostics import (
    EXIT_DIAGNOSTIC_ERROR,
    classify_diagnostics,
    collect_diagnostics,
)


def _add_diagnostic_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_timeout: float,
) -> None:
    parser.add_argument("--host", help="override the Origin bridge host")
    parser.add_argument("--port", type=int, help="override the Origin bridge port")
    parser.add_argument(
        "--timeout",
        type=float,
        default=default_timeout,
        help=f"bridge probe timeout in seconds (default: {default_timeout:g})",
    )
    parser.add_argument("--status-path", help="override the bridge status-file path")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="origin-mcp",
        description=(
            "Run the origin-mcp server or inspect the local Origin bridge. "
            "With no arguments, the MCP server runs over stdio."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser(
        "install-origin-app",
        help="install the Origin MCP Bridge Start/Stop Apps for the current user",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="replace an existing Origin MCP Bridge App installation",
    )
    install.add_argument(
        "--destination",
        help="override the Origin Apps directory (primarily for testing)",
    )

    status = subparsers.add_parser(
        "status",
        help="show whether the local Origin bridge is running",
    )
    _add_diagnostic_arguments(status, default_timeout=1.0)

    doctor = subparsers.add_parser(
        "doctor",
        help="diagnose bridge configuration, status, logs, and connectivity",
    )
    _add_diagnostic_arguments(doctor, default_timeout=2.0)
    doctor.add_argument(
        "--ping-origin",
        action="store_true",
        help="also ask the bridge to connect to Origin (may show the Origin window)",
    )
    return parser


def _json_payload(report: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": assessment["state"],
        "exit_code": assessment["exit_code"],
        "status_age_seconds": assessment["status_age_seconds"],
        "status_stale": assessment["status_stale"],
        "diagnostics": report,
    }


def _write_json(payload: dict[str, Any], stream: TextIO | None = None) -> None:
    print(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        file=stream or sys.stdout,
    )


def _state_label(state: str) -> str:
    return state.replace("_", " ").upper()


def _format_age(age_seconds: Any) -> str | None:
    if not isinstance(age_seconds, (int, float)):
        return None
    if age_seconds < 60:
        return f"{age_seconds:.0f}s ago"
    if age_seconds < 3600:
        return f"{age_seconds / 60:.0f}m ago"
    if age_seconds < 86400:
        return f"{age_seconds / 3600:.1f}h ago"
    return f"{age_seconds / 86400:.1f}d ago"


def _dict_value(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def _write_human_report(
    report: dict[str, Any],
    assessment: dict[str, Any],
    *,
    detailed: bool,
    stream: TextIO | None = None,
) -> None:
    output = stream or sys.stdout
    label = "Origin MCP doctor" if detailed else "Origin MCP bridge"
    print(f"{label}: {_state_label(str(assessment['state']))}", file=output)

    config = _dict_value(report, "config")
    print(f"Address: {config.get('host')}:{config.get('port')}", file=output)

    bridge = _dict_value(report, "bridge")
    if bridge.get("ok"):
        print("Bridge: reachable", file=output)
    else:
        error_code = bridge.get("error_code") or "unavailable"
        print(f"Bridge: unreachable ({error_code})", file=output)
        if bridge.get("message"):
            print(f"  {bridge['message']}", file=output)

    status_file = _dict_value(report, "status_file")
    if status_file.get("exists"):
        suffix: list[str] = []
        age = _format_age(assessment.get("status_age_seconds"))
        if age:
            suffix.append(age)
        if assessment.get("status_stale"):
            suffix.append("stale")
        detail = f" ({', '.join(suffix)})" if suffix else ""
        print(f"Status file: {status_file.get('path')}{detail}", file=output)
    else:
        print(f"Status file: not found ({status_file.get('path')})", file=output)

    status = _dict_value(report, "status_diagnostics")
    if status.get("install_phase") and assessment.get("state") not in {"running", "stopped"}:
        print(f"Install phase: {status['install_phase']}", file=output)
    if status.get("last_error"):
        error_type = status.get("last_error_type")
        prefix = f"{error_type}: " if error_type else ""
        print(f"Last error: {prefix}{status['last_error']}", file=output)

    if detailed:
        origin = report.get("origin")
        if origin is None:
            print("Origin: not checked (use --ping-origin)", file=output)
        elif isinstance(origin, dict) and origin.get("ok"):
            print("Origin: reachable", file=output)
        elif isinstance(origin, dict):
            print(f"Origin: failed ({origin.get('error_code') or 'unknown'})", file=output)
            if origin.get("message"):
                print(f"  {origin['message']}", file=output)

        log = _dict_value(report, "log")
        if log.get("enabled"):
            availability = "exists" if log.get("exists") else "no records yet"
            print(f"Log: {log.get('path')} ({availability})", file=output)
        else:
            print("Log: disabled", file=output)

    recommendations = report.get("next_actions", report.get("recommendations"))
    if isinstance(recommendations, list) and recommendations:
        print("Next actions:", file=output)
        limit = None if detailed else 3
        for item in recommendations[:limit]:
            print(f"  - {item}", file=output)


def _run_diagnostics(parsed: argparse.Namespace, *, detailed: bool) -> int:
    json_output = bool(parsed.json_output)
    try:
        report = collect_diagnostics(
            host=parsed.host,
            port=parsed.port,
            timeout=parsed.timeout,
            status_path=parsed.status_path,
            ping_origin=bool(getattr(parsed, "ping_origin", False)),
        )
        assessment = classify_diagnostics(report)
    except Exception as exc:
        payload = {
            "state": "diagnostic_error",
            "exit_code": EXIT_DIAGNOSTIC_ERROR,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        if json_output:
            _write_json(payload)
        else:
            print(f"Origin MCP diagnostics failed: {exc}", file=sys.stderr)
        return EXIT_DIAGNOSTIC_ERROR

    if json_output:
        _write_json(_json_payload(report, assessment))
    else:
        _write_human_report(report, assessment, detailed=detailed)
    return int(assessment["exit_code"])


def main(argv: Sequence[str] | None = None) -> int:
    """Run the MCP server by default, or an explicitly requested CLI command."""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        from .server import main as server_main

        server_main()
        return 0

    parsed = _build_parser().parse_args(args)
    if parsed.command == "install-origin-app":
        from .app_installer import install_origin_apps

        installed = install_origin_apps(
            force=parsed.force,
            destination=parsed.destination,
        )
        print("Staged Origin App sources:")
        for path in installed:
            print(f"  {path}")
        print("In Origin's Command Window, pack the Apps with:")
        for path in installed:
            opx = path.with_suffix(".opx")
            print(f'mkOPX app:="{path.name}" opx:="{opx}";')
        print("Then drag both OPX files into Origin to register the Apps.")
        return 0
    if parsed.command == "status":
        return _run_diagnostics(parsed, detailed=False)
    if parsed.command == "doctor":
        return _run_diagnostics(parsed, detailed=True)
    raise RuntimeError(f"Unhandled command: {parsed.command}")
