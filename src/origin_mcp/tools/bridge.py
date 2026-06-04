from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from origin_mcp.bridge_client import OriginBridgeConfig, request_bridge
from origin_mcp.errors import OriginBridgeError
from origin_mcp.logging_config import active_log_path, tail_log

from ._shared import (
    COMPACT_TOOL_NAMES,
    _mcp_tool,
    _ok,
    _tool_profile,
    _wrap,
    client,
)


def _dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _status_file_candidates(status_path: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    for value in (status_path, os.environ.get("ORIGIN_MCP_BRIDGE_STATUS")):
        if value:
            candidates.append(Path(value).expanduser())
    candidates.extend(
        [
            Path.cwd() / "origin-bridge.status.txt",
            Path(__file__).resolve().parents[3] / "origin-bridge.status.txt",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _read_bridge_status(status_path: str | None = None) -> dict[str, Any]:
    candidates = _status_file_candidates(status_path)
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "path": str(candidate),
                "exists": True,
                "readable": False,
                "error": str(exc),
                "candidates": [str(path) for path in candidates],
            }
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        return {
            "path": str(candidate),
            "exists": True,
            "readable": True,
            "format": "json" if isinstance(data, dict) else "text",
            "data": data if isinstance(data, dict) else None,
            "raw_preview": None if isinstance(data, dict) else text[:1000],
            "candidates": [str(path) for path in candidates],
        }
    return {
        "path": str(candidates[0]) if candidates else None,
        "exists": False,
        "readable": False,
        "candidates": [str(path) for path in candidates],
    }


def _bridge_call(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = None,
    success: str,
) -> dict[str, Any]:
    """Shared scaffolding for ``origin_bridge_*`` MCP tools.

    Each tool builds a method name + params dict, forwards the standard
    ``host/port/token/timeout`` overrides, and reports the response under a
    success message. Centralising the wrapper avoids ~20 copies of the same
    ``_wrap(lambda: _ok(..., **request_bridge(...)))`` boilerplate.
    """

    def run() -> dict[str, Any]:
        if params is None:
            response = request_bridge(method, host=host, port=port, token=token, timeout=timeout)
        else:
            response = request_bridge(
                method, params, host=host, port=port, token=token, timeout=timeout
            )
        return _ok(success, **response)

    return _wrap(run)


@_mcp_tool()
def origin_ping(show: bool = True) -> dict[str, Any]:
    """Connect to Origin/OriginPro and report basic status."""

    return _wrap(lambda: _ok("Connected to Origin.", **client.connect(show=show)))


@_mcp_tool()
def origin_capabilities(show: bool = False, refresh: bool = False) -> dict[str, Any]:
    """Report Origin/originpro versions and runtime feature availability."""

    return _wrap(
        lambda: _ok(
            "Collected Origin compatibility information.",
            **client.capabilities(show=show, refresh=refresh),
        )
    )


@_mcp_tool()
def origin_bridge_status(
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 2.0,
) -> dict[str, Any]:
    """Check whether the Origin GUI bridge is reachable."""

    return _bridge_call(
        "ping",
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge responded.",
    )


@_mcp_tool()
def origin_bridge_shutdown(
    release_origin: bool = True,
    close_origin: bool = False,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 2.0,
) -> dict[str, Any]:
    """Ask the Origin GUI bridge to stop serving requests.

    By default this releases the Origin automation connection without closing
    Origin itself. Set ``close_origin=True`` to force-close Origin as part of
    shutdown.
    """

    return _bridge_call(
        "shutdown",
        {"release_origin": release_origin, "close_origin": close_origin},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge shutdown requested.",
    )


@_mcp_tool()
def origin_doctor(
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 2.0,
    status_path: str | None = None,
    ping_origin: bool = False,
) -> dict[str, Any]:
    """Diagnose Origin bridge configuration, status file, and connectivity."""

    def run() -> dict[str, Any]:
        config = OriginBridgeConfig.from_env(host=host, port=port, token=token, timeout=timeout)
        status_file = _read_bridge_status(status_path)
        bridge_check: dict[str, Any] = {"ok": False}
        origin_check: dict[str, Any] | None = None
        recommendations: list[str] = []

        try:
            response = request_bridge(
                "ping",
                host=config.host,
                port=config.port,
                token=config.token,
                timeout=config.timeout,
            )
            bridge_check = {"ok": True, "response": response}
        except OriginBridgeError as exc:
            bridge_check = {
                "ok": False,
                "error_code": exc.error_code,
                "message": str(exc),
            }
            recommendations.append(
                "Start Origin, open the Python Console, and run the root addon.py."
            )
            recommendations.append(
                "If addon.py is already running, compare ORIGIN_MCP_BRIDGE_HOST and "
                "ORIGIN_MCP_BRIDGE_PORT with the status file."
            )

        if ping_origin and bridge_check["ok"]:
            try:
                origin_check = {
                    "ok": True,
                    "response": request_bridge(
                        "origin_ping",
                        {"show": True},
                        host=config.host,
                        port=config.port,
                        token=config.token,
                        timeout=max(float(config.timeout), 10.0),
                    ),
                }
            except OriginBridgeError as exc:
                origin_check = {
                    "ok": False,
                    "error_code": exc.error_code,
                    "message": str(exc),
                }
                recommendations.append(
                    "The bridge responded, but Origin automation failed. Check the live Origin "
                    "session and the status file last_error field."
                )

        status_data = status_file.get("data")
        if isinstance(status_data, dict) and status_data.get("last_error"):
            recommendations.append(
                "addon.py recorded last_error in the status file; inspect that field first."
            )
        if not status_file.get("exists"):
            recommendations.append(
                "No bridge status file was found. Set ORIGIN_MCP_BRIDGE_STATUS or start addon.py "
                "from the checkout root."
            )

        log_path = active_log_path()
        log_info: dict[str, Any] = {
            "path": str(log_path) if log_path else None,
            "enabled": log_path is not None,
            "exists": bool(log_path and log_path.exists()),
            "recent": tail_log(20) if log_path and log_path.exists() else [],
        }

        return _ok(
            "Origin doctor completed.",
            config={
                "host": config.host,
                "port": config.port,
                "timeout": config.timeout,
                "token_configured": bool(config.token),
                "tool_profile": _tool_profile(),
                "compact_tool_count": len(COMPACT_TOOL_NAMES),
                "compact_tools": sorted(COMPACT_TOOL_NAMES),
                "env": {
                    "ORIGIN_MCP_BRIDGE_HOST": os.environ.get("ORIGIN_MCP_BRIDGE_HOST"),
                    "ORIGIN_MCP_BRIDGE_PORT": os.environ.get("ORIGIN_MCP_BRIDGE_PORT"),
                    "ORIGIN_MCP_BRIDGE_TIMEOUT": os.environ.get("ORIGIN_MCP_BRIDGE_TIMEOUT"),
                    "ORIGIN_MCP_BRIDGE_STATUS": os.environ.get("ORIGIN_MCP_BRIDGE_STATUS"),
                    "ORIGIN_MCP_BRIDGE_TOKEN": bool(os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN")),
                    "ORIGIN_MCP_TOOL_PROFILE": os.environ.get("ORIGIN_MCP_TOOL_PROFILE"),
                    "ORIGIN_MCP_LOG_FILE": os.environ.get("ORIGIN_MCP_LOG_FILE"),
                },
            },
            status_file=status_file,
            bridge=bridge_check,
            origin=origin_check,
            log=log_info,
            recommendations=_dedupe_strings(recommendations),
        )

    return _wrap(run)


@_mcp_tool()
def origin_bridge_ping_origin(
    show: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Ask the Origin GUI bridge to connect to Origin and report status."""

    return _bridge_call(
        "origin_ping",
        {"show": show},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge connected to Origin.",
    )


@_mcp_tool()
def origin_bridge_capabilities(
    show: bool = False,
    refresh: bool = False,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Ask the Origin GUI bridge for Origin/originpro capabilities."""

    return _bridge_call(
        "origin_capabilities",
        {"show": show, "refresh": refresh},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge collected capabilities.",
    )


@_mcp_tool()
def origin_bridge_run_labtalk(
    script: str,
    capture_log: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Execute LabTalk through the Origin GUI bridge."""

    return _bridge_call(
        "run_labtalk",
        {"script": script, "capture_log": capture_log},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge executed LabTalk script.",
    )


@_mcp_tool()
def origin_bridge_new_project(
    show: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Create a new Origin project through the Origin GUI bridge."""

    return _bridge_call(
        "new_project",
        {"show": show},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge created a new project.",
    )


@_mcp_tool()
def origin_bridge_open_project(
    path: str,
    readonly: bool = False,
    asksave: bool = False,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Open an Origin project through the Origin GUI bridge."""

    return _bridge_call(
        "open_project",
        {"path": path, "readonly": readonly, "asksave": asksave},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge opened project.",
    )


@_mcp_tool()
def origin_bridge_save_project(
    path: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Save the current Origin project through the Origin GUI bridge."""

    return _bridge_call(
        "save_project",
        {"path": path},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge saved project.",
    )


@_mcp_tool()
def origin_bridge_list_project(
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """List Origin project objects through the Origin GUI bridge."""

    return _bridge_call(
        "list_project",
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge listed project objects.",
    )


@_mcp_tool()
def origin_bridge_import_table(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Import table data through the Origin GUI bridge."""

    return _bridge_call(
        "import_table",
        {
            "path": path,
            "book_name": book_name,
            "sheet_name": sheet_name,
            "excel_sheet": excel_sheet,
            "delimiter": delimiter,
            "encoding": encoding,
            "header": header,
            "skiprows": skiprows,
            "nrows": nrows,
            "na_values": na_values,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge imported table data.",
    )


@_mcp_tool()
def origin_bridge_get_worksheet_info(
    book_name: str | None = None,
    sheet_name: str | None = None,
    label_types: list[str] | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Get worksheet information through the Origin GUI bridge."""

    return _bridge_call(
        "worksheet_info",
        {"book_name": book_name, "sheet_name": sheet_name, "label_types": label_types},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge collected worksheet information.",
    )


@_mcp_tool()
def origin_bridge_read_worksheet(
    book_name: str | None = None,
    sheet_name: str | None = None,
    start_row: int = 0,
    max_rows: int = 100,
    columns: list[str | int] | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Read worksheet data through the Origin GUI bridge."""

    return _bridge_call(
        "read_worksheet",
        {
            "book_name": book_name,
            "sheet_name": sheet_name,
            "start_row": start_row,
            "max_rows": max_rows,
            "columns": columns,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge read worksheet data.",
    )


@_mcp_tool()
def origin_bridge_write_worksheet(
    rows: list[dict[str, Any]] | list[list[Any]],
    columns: list[str] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    start_col: str | int = 0,
    create: bool = False,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Write worksheet data through the Origin GUI bridge."""

    return _bridge_call(
        "write_worksheet",
        {
            "rows": rows,
            "columns": columns,
            "book_name": book_name,
            "sheet_name": sheet_name,
            "start_col": start_col,
            "create": create,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge wrote worksheet data.",
    )


@_mcp_tool()
def origin_bridge_plot_table(
    path: str,
    kind: str = "line",
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
    graph_name: str | None = None,
    template: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    show_legend: bool = True,
    style_mode: str = "origin_default",
    palette_name: str | None = None,
    export_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 60.0,
) -> dict[str, Any]:
    """Create a table-backed plot through the Origin GUI bridge."""

    return _bridge_call(
        "plot_table",
        {
            "path": path,
            "kind": kind,
            "x_col": x_col,
            "y_cols": y_cols,
            "book_name": book_name,
            "sheet_name": sheet_name,
            "excel_sheet": excel_sheet,
            "delimiter": delimiter,
            "encoding": encoding,
            "header": header,
            "skiprows": skiprows,
            "nrows": nrows,
            "na_values": na_values,
            "graph_name": graph_name,
            "template": template,
            "title": title,
            "x_label": x_label,
            "y_label": y_label,
            "z_col": z_col,
            "y_error_col": y_error_col,
            "x_error_col": x_error_col,
            "show_legend": show_legend,
            "style_mode": style_mode,
            "palette_name": palette_name,
            "export_path": export_path,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge created table-backed plot.",
    )


@_mcp_tool()
def origin_bridge_export_graph(
    path: str,
    graph_name: str | None = None,
    overwrite: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Export a graph through the Origin GUI bridge."""

    return _bridge_call(
        "export_graph",
        {"path": path, "graph_name": graph_name, "overwrite": overwrite},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge exported graph.",
    )


@_mcp_tool()
def origin_bridge_run_analysis(
    analysis: str,
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 60.0,
) -> dict[str, Any]:
    """Run an Origin analysis through the Origin GUI bridge."""

    return _bridge_call(
        "run_analysis",
        {
            "analysis": analysis,
            "worksheet": worksheet,
            "x_col": x_col,
            "y_col": y_col,
            "output_sheet": output_sheet,
            "options": options or {},
            "include_output": include_output,
            "output_max_rows": output_max_rows,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Origin bridge ran analysis.",
    )


@_mcp_tool()
def origin_bridge_submit_task(
    method: str,
    params: dict[str, Any] | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Submit a supported Origin bridge method as a queued background task."""

    return _bridge_call(
        "submit_task",
        {"method": method, "params": params or {}},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Submitted Origin bridge task.",
    )


@_mcp_tool()
def origin_bridge_task_status(
    task_id: str,
    include_logs: bool = False,
    log_limit: int = 20,
    include_result: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Read status, result, or optional recent logs for an Origin bridge background task."""

    return _bridge_call(
        "task_status",
        {
            "task_id": task_id,
            "include_logs": include_logs,
            "log_limit": log_limit,
            "include_result": include_result,
        },
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Read Origin bridge task status.",
    )


@_mcp_tool()
def origin_bridge_cancel_task(
    task_id: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Cancel a queued Origin bridge task or mark a running task for cancellation."""

    return _bridge_call(
        "cancel_task",
        {"task_id": task_id},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Requested Origin bridge task cancellation.",
    )


@_mcp_tool()
def origin_bridge_list_tasks(
    limit: int = 20,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """List recent Origin bridge background tasks."""

    return _bridge_call(
        "list_tasks",
        {"limit": limit},
        host=host,
        port=port,
        token=token,
        timeout=timeout,
        success="Listed Origin bridge tasks.",
    )
