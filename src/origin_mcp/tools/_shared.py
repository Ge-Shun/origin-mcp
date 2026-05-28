from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from origin_mcp.bridge_client import OriginBridgeProxy
from origin_mcp.errors import (
    OriginBridgeError,
    OriginDependencyError,
    OriginMcpError,
    OriginOperationError,
)
from origin_mcp.models import ToolResult

mcp = FastMCP(
    "origin-mcp",
    instructions=(
        "Origin/OriginPro MCP server. The default compact tool profile exposes "
        "high-level diagnostics, knowledge, plotting, worksheet, analysis, export, "
        "LabTalk, and task tools. Set ORIGIN_MCP_TOOL_PROFILE=full to expose every "
        "specialized worksheet, graph, analysis, and plot-type wrapper."
    ),
)

COMPACT_TOOL_NAMES = frozenset(
    {
        "origin_doctor",
        "origin_ping",
        "origin_capabilities",
        "origin_browse_knowledge",
        "origin_query_knowledge",
        "origin_import_table",
        "origin_read_worksheet",
        "origin_write_worksheet",
        "origin_recommend_chart",
        "origin_plot_auto",
        "origin_plot_chart_atlas",
        "origin_plot_table_id",
        "origin_format_graph",
        "origin_export_graph",
        "origin_run_analysis",
        "origin_run_labtalk",
        "origin_bridge_submit_task",
        "origin_bridge_task_status",
        "origin_bridge_cancel_task",
        "origin_bridge_list_tasks",
    }
)
FULL_TOOL_PROFILE_VALUES = {"full", "expert", "all"}


def _tool_profile() -> str:
    return os.environ.get("ORIGIN_MCP_TOOL_PROFILE", "compact").strip().lower() or "compact"


def _should_register_tool(name: str) -> bool:
    profile = _tool_profile()
    return profile in FULL_TOOL_PROFILE_VALUES or name in COMPACT_TOOL_NAMES


def _mcp_tool() -> Any:
    def decorate(func: Any) -> Any:
        if _should_register_tool(func.__name__):
            return mcp.tool()(func)
        return func

    return decorate


class _BridgeOnlyClient:
    def __getattr__(self, name: str) -> Any:
        return getattr(OriginBridgeProxy(), name)


client = _BridgeOnlyClient()


def _ok(message: str, **data: Any) -> dict[str, Any]:
    return ToolResult(ok=True, message=message, data=_json_safe(data)).model_dump(exclude_none=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _error(exc: Exception) -> dict[str, Any]:
    error_code = _error_code(exc)
    return ToolResult(
        ok=False,
        message=str(exc),
        error_code=error_code,
        data={"error_type": type(exc).__name__, "error_code": error_code},
    ).model_dump(exclude_none=True)


def _error_code(exc: Exception) -> str:
    if isinstance(exc, OriginBridgeError):
        return exc.error_code
    if isinstance(exc, OriginDependencyError):
        return "origin_dependency_unavailable"
    if isinstance(exc, ValidationError):
        return "invalid_request"
    if isinstance(exc, ValueError):
        return "invalid_request"
    if isinstance(exc, OriginOperationError):
        message = str(exc).lower()
        if "outside origin_mcp_allowed_roots" in message:
            return "path_not_allowed"
        if "file does not exist" in message:
            return "file_not_found"
        if "path is not a file" in message:
            return "invalid_file_path"
        if "unsupported data file extension" in message:
            return "unsupported_file_type"
        if "unsupported analysis type" in message:
            return "unsupported_analysis_type"
        if "worksheet not found" in message:
            return "worksheet_not_found"
        if "graph not found" in message:
            return "graph_not_found"
        if "labtalk" in message and "not available" in message:
            return "labtalk_unavailable"
        if "requires origin >=" in message:
            return "unsupported_origin_version"
        if "not supported by this origin/originpro environment" in message:
            return "unsupported_origin_feature"
        return "origin_operation_failed"
    return "unexpected_error"


def _wrap(func: Any) -> dict[str, Any]:
    try:
        return func()
    except (OriginMcpError, ValidationError, ValueError) as exc:
        return _error(exc)
    except Exception as exc:
        return _error(exc)


def _export_inspection(graph: dict[str, Any]) -> dict[str, Any] | None:
    export_path = graph.get("export_path")
    if not export_path:
        return None
    try:
        return client.inspect_export(Path(str(export_path)))
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}
