from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from origin_mcp.bridge_client import OriginBridgeConfig, OriginBridgeProxy
from origin_mcp.errors import (
    OriginMcpError,
)
from origin_mcp.logging_config import get_tools_logger
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
        "origin_plan_figure_spec",
        "origin_execute_figure_spec",
        "origin_import_table",
        "origin_read_worksheet",
        "origin_write_worksheet",
        "origin_diagnose_worksheet",
        "origin_add_calculated_columns",
        "origin_filter_rows",
        "origin_drop_duplicates",
        "origin_fill_missing",
        "origin_transpose_worksheet",
        "origin_merge_worksheets",
        "origin_concat_worksheets",
        "origin_pivot_worksheet",
        "origin_melt_worksheet",
        "origin_recommend_chart",
        "origin_plot",
        "origin_plot_line",
        "origin_plot_scatter",
        "origin_plot_line_symbol",
        "origin_plot_column",
        "origin_plot_dual_y",
        "origin_plot_histogram",
        "origin_plot_box",
        "origin_plot_from_range",
        "origin_plot_auto",
        "origin_plot_chart_atlas",
        "origin_plot_table_id",
        "origin_add_plot_to_graph",
        "origin_add_inset",
        "origin_set_plot_style",
        "origin_set_axis",
        "origin_set_axis_break",
        "origin_get_graph_info",
        "origin_get_layer_info",
        "origin_save_graph_template",
        "origin_search_templates",
        "origin_list_user_templates",
        "origin_delete_template",
        "origin_rename_template",
        "origin_update_template_metadata",
        "origin_palette_catalog",
        "origin_plot_style_capabilities",
        "origin_plot_style_setter_coverage",
        "origin_set_plot_property",
        "origin_format_graph",
        "origin_export_graph",
        "origin_view_graph",
        # Analysis: the compact profile exposes the generic dispatcher plus the
        # two structured fits whose typed signatures are awkward to express
        # through run_analysis options. Every other named analysis
        # (polynomial_fit, smooth, descriptive_stats, differentiate, integrate,
        # peak_find, interpolate, normalize, the t-tests, fft/ifft, correlation,
        # plain nonlinear_fit) is reachable via
        # origin_run_analysis(analysis=..., options=...) and stays in the full
        # profile; see the analysis/workflow knowledge entry.
        "origin_run_analysis",
        "origin_linear_fit",
        "origin_nonlinear_fit_structured",
        "origin_list_fit_functions",
        "origin_run_labtalk",
        "origin_bridge_shutdown",
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


def _mcp_tool(**tool_kwargs: Any) -> Any:
    def decorate(func: Any) -> Any:
        if _should_register_tool(func.__name__):
            return mcp.tool(**tool_kwargs)(func)
        return func

    return decorate


class _BridgeOnlyClient:
    """Config-keyed singleton facade around an OriginBridgeProxy.

    The proxy holds a persistent TCP connection inside its OriginBridgeClient,
    so reusing it across tool calls avoids re-opening the socket. The cached
    proxy is rebuilt whenever the bridge configuration (host/port/token/
    timeout) changes — most importantly during tests that monkeypatch env vars.
    """

    def __init__(self) -> None:
        self._proxy: OriginBridgeProxy | None = None
        self._config: OriginBridgeConfig | None = None

    def _get_proxy(self) -> OriginBridgeProxy:
        config = OriginBridgeConfig.from_env()
        if self._proxy is None or self._config != config:
            self._config = config
            self._proxy = OriginBridgeProxy(config)
        return self._proxy

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._get_proxy(), name)


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
    if isinstance(exc, ValidationError):
        return "invalid_request"
    if isinstance(exc, OriginMcpError):
        return exc.error_code
    if isinstance(exc, ValueError):
        return "invalid_request"
    return "unexpected_error"


def _wrap(func: Any) -> dict[str, Any]:
    try:
        return func()
    except (OriginMcpError, ValidationError, ValueError) as exc:
        # Expected, classified failures: surface them without noisy logging.
        return _error(exc)
    except Exception as exc:
        # Unexpected failures lose their traceback once converted to a result
        # dict, which makes production issues hard to diagnose. Log it with the
        # full stack to server.log (the message/stack stays out of the tool
        # response). get_tools_logger() is cheap and idempotent.
        get_tools_logger().exception("Unexpected error in MCP tool call: %s", exc)
        return _error(exc)


def _export_inspection(graph: dict[str, Any]) -> dict[str, Any] | None:
    export_path = graph.get("export_path")
    if not export_path:
        return None
    try:
        return client.inspect_export(Path(str(export_path)))
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}
