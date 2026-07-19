from __future__ import annotations

import math
import os
from inspect import signature
from pathlib import Path
from typing import Annotated, Any, get_type_hints

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

from origin_mcp.bridge_client import OriginBridgeConfig, OriginBridgeProxy
from origin_mcp.errors import (
    OriginMcpError,
)
from origin_mcp.logging_config import get_tools_logger
from origin_mcp.models import ToolResult
from origin_mcp.recovery import recovery_guidance

mcp = FastMCP(
    "origin-mcp",
    instructions=(
        "Origin/OriginPro MCP server. The default compact profile exposes a focused "
        "high-level surface. Use data, plot, analysis, or standard for a broader "
        "workflow-specific surface, and full for every specialized wrapper."
    ),
)

STANDARD_TOOL_NAMES = frozenset(
    {
        "origin_doctor",
        "origin_ping",
        "origin_capabilities",
        "origin_browse_knowledge",
        "origin_query_knowledge",
        "origin_plan_figure_spec",
        "origin_execute_figure_spec",
        "origin_import_table",
        "origin_import_file",
        "origin_connect_data_source",
        "origin_get_connector",
        "origin_update_connector",
        "origin_refresh_connector",
        "origin_connect_selection",
        "origin_disconnect_connector",
        "origin_refresh_all_connectors",
        "origin_create_matrix",
        "origin_get_matrix_info",
        "origin_read_matrix",
        "origin_write_matrix",
        "origin_set_matrix_properties",
        "origin_transform_matrix",
        "origin_import_image",
        "origin_create_image",
        "origin_get_image_info",
        "origin_read_image",
        "origin_process_image",
        "origin_image_to_matrix",
        "origin_create_note",
        "origin_get_note",
        "origin_write_note",
        "origin_load_note",
        "origin_export_note_html",
        "origin_delete_note",
        "origin_list_project_folder",
        "origin_set_project_folder",
        "origin_create_project_folder",
        "origin_move_project_item",
        "origin_rename_project_item",
        "origin_delete_project_folder",
        "origin_save_analysis_template",
        "origin_open_analysis_template",
        "origin_batch_process",
        "origin_clone_import",
        "origin_peak_analyzer",
        "origin_peak_baseline",
        "origin_peak_analyzer_batch",
        "origin_list_xfunctions",
        "origin_run_xfunction",
        "origin_fft_filter",
        "origin_principal_component_analysis",
        "origin_one_way_anova",
        "origin_multivariate_analysis",
        "origin_nonparametric_test",
        "origin_survival_analysis",
        "origin_get_analysis_results",
        "origin_get_analysis_operation",
        "origin_recalculate_analysis",
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
        "origin_merge_graphs",
        "origin_create_graph_layout",
        "origin_link_graph_layers",
        "origin_copy_layer_scale",
        "origin_extract_graph_layers",
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
        # Analysis: the standard profile exposes the generic dispatcher plus the
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
        "origin_recommend_chart",
        "origin_plot",
        "origin_plot_auto",
        "origin_get_graph_info",
        "origin_format_graph",
        "origin_export_graph",
        "origin_view_graph",
        "origin_run_analysis",
        "origin_run_labtalk",
        "origin_bridge_shutdown",
        "origin_bridge_submit_task",
        "origin_bridge_task_status",
        "origin_bridge_cancel_task",
        "origin_bridge_list_tasks",
    }
)
DATA_TOOL_NAMES = COMPACT_TOOL_NAMES | frozenset(
    {
        "origin_import_file",
        "origin_connect_data_source",
        "origin_get_connector",
        "origin_update_connector",
        "origin_refresh_connector",
        "origin_connect_selection",
        "origin_disconnect_connector",
        "origin_refresh_all_connectors",
        "origin_export_worksheet_csv",
        "origin_create_matrix",
        "origin_get_matrix_info",
        "origin_read_matrix",
        "origin_write_matrix",
        "origin_set_matrix_properties",
        "origin_transform_matrix",
        "origin_import_image",
        "origin_create_image",
        "origin_get_image_info",
        "origin_read_image",
        "origin_process_image",
        "origin_image_to_matrix",
        "origin_save_analysis_template",
        "origin_open_analysis_template",
        "origin_batch_process",
        "origin_clone_import",
        "origin_add_calculated_columns",
        "origin_filter_rows",
        "origin_drop_duplicates",
        "origin_fill_missing",
        "origin_transpose_worksheet",
        "origin_merge_worksheets",
        "origin_concat_worksheets",
        "origin_pivot_worksheet",
        "origin_melt_worksheet",
    }
)
PLOT_TOOL_NAMES = COMPACT_TOOL_NAMES | frozenset(
    name
    for name in STANDARD_TOOL_NAMES
    if name.startswith("origin_plot_")
    or name
    in {
        "origin_add_inset",
        "origin_add_plot_to_graph",
        "origin_merge_graphs",
        "origin_create_graph_layout",
        "origin_link_graph_layers",
        "origin_copy_layer_scale",
        "origin_extract_graph_layers",
        "origin_delete_template",
        "origin_get_layer_info",
        "origin_list_user_templates",
        "origin_palette_catalog",
        "origin_rename_template",
        "origin_save_graph_template",
        "origin_search_templates",
        "origin_set_axis",
        "origin_set_axis_break",
        "origin_set_plot_property",
        "origin_set_plot_style",
        "origin_update_template_metadata",
    }
)
ANALYSIS_TOOL_NAMES = COMPACT_TOOL_NAMES | frozenset(
    {
        "origin_save_analysis_template",
        "origin_open_analysis_template",
        "origin_batch_process",
        "origin_clone_import",
        "origin_peak_analyzer",
        "origin_peak_baseline",
        "origin_peak_analyzer_batch",
        "origin_list_xfunctions",
        "origin_run_xfunction",
        "origin_fft_filter",
        "origin_principal_component_analysis",
        "origin_one_way_anova",
        "origin_multivariate_analysis",
        "origin_nonparametric_test",
        "origin_survival_analysis",
        "origin_get_analysis_results",
        "origin_get_analysis_operation",
        "origin_recalculate_analysis",
        "origin_linear_fit",
        "origin_list_fit_functions",
        "origin_nonlinear_fit_structured",
    }
)
PROFILE_TOOL_NAMES = {
    "compact": COMPACT_TOOL_NAMES,
    "data": DATA_TOOL_NAMES,
    "plot": PLOT_TOOL_NAMES,
    "analysis": ANALYSIS_TOOL_NAMES,
    "standard": STANDARD_TOOL_NAMES,
    "legacy": STANDARD_TOOL_NAMES,
}
FULL_TOOL_PROFILE_VALUES = {"full", "expert", "all"}


_COMMON_PARAMETER_DESCRIPTIONS = {
    "book_name": "Origin workbook name. Omit to use the active workbook or the tool default.",
    "capture_log": "Whether to capture and return LabTalk output produced by the script.",
    "close_origin": "Whether bridge shutdown should also force-close the Origin application.",
    "collection": "Knowledge collection to browse or search. Omit to include all collections.",
    "columns": "Column names or zero-based column indexes selected for this operation.",
    "create": "Whether to create the target Origin object when it does not already exist.",
    "delimiter": "Text-file delimiter. Omit to use the format default or automatic detection.",
    "dry_run": "Validate and plan the operation without changing the Origin project.",
    "encoding": "Text-file character encoding. Omit to use automatic/default decoding.",
    "excel_sheet": "Excel sheet name or zero-based sheet index; ignored for text files.",
    "export_path": "Optional output path for exporting the created graph.",
    "graph_name": "Origin graph page name. Omit to use the active graph or create a new page.",
    "header": "Zero-based input row to use as column names; null means no header row.",
    "host": "Optional Origin bridge host override. Normally omit to use configured localhost.",
    "include_logs": "Whether to include recent background-task log records in the response.",
    "include_output": "Whether to read generated worksheet rows back into the tool response.",
    "include_result": "Whether to include a completed background task's result payload.",
    "intent": "Optional natural-language chart intent used to guide automatic routing.",
    "limit": "Maximum number of matching or recent records to return.",
    "log_limit": "Maximum number of recent background-task log records to return.",
    "max_recommendations": "Maximum number of ranked chart recommendations to return.",
    "max_rows": "Maximum number of worksheet rows to return.",
    "max_width": "Maximum rendered image width in pixels.",
    "method": "Allowlisted Origin bridge method to run as a background task.",
    "na_values": "Additional string value or values to interpret as missing data.",
    "nrows": "Maximum number of input data rows to read; omit to read all rows.",
    "options": "Operation-specific options. Use only keys documented for the selected operation.",
    "output_max_rows": "Maximum number of generated worksheet rows to include in the response.",
    "output_sheet": "Optional Origin output worksheet name or range hint.",
    "overwrite": "Whether an existing output file may be replaced.",
    "palette_name": "Optional registered color palette name used by the selected style mode.",
    "params": "Keyword arguments passed to the selected allowlisted bridge method.",
    "path": "Filesystem path consumed or produced by this tool; see the tool description.",
    "ping_origin": "Whether diagnostics should also make a live request to Origin.",
    "port": "Optional Origin bridge TCP port override. Normally omit to use the handshake value.",
    "query": "Keyword query matched against local knowledge titles, summaries, and bodies.",
    "refresh": "Whether to bypass cached capability data and query Origin again.",
    "release_origin": "Whether bridge shutdown should release its Origin automation connection.",
    "rescale": "Whether to rescale graph axes after applying formatting.",
    "rows": "Rows to write, as objects keyed by column name or arrays matching columns.",
    "script": "LabTalk script text to execute inside the connected Origin application.",
    "selected_cols": "Column names or zero-based indexes to include in the plot.",
    "sheet_name": "Origin worksheet name. Omit to use the active sheet or the tool default.",
    "show": "Whether Origin should be visible after connecting or querying capabilities.",
    "show_legend": (
        "Legend visibility override; null uses cross-chart rules based on series count "
        "and chart type."
    ),
    "skiprows": "Zero-based input row index or indexes to skip while reading the file.",
    "spec": "Declarative FigureSpec describing data, layout, plots, style, export, and QA.",
    "start_col": "Column name or zero-based column index at which writing begins.",
    "start_row": "Zero-based worksheet row at which reading begins.",
    "status_path": "Optional bridge status-file path override used by diagnostics.",
    "style_mode": (
        "Graph styling policy: origin_default preserves the Origin template; nature applies "
        "the origin-mcp scientific preset."
    ),
    "task_id": "Background task identifier returned by origin_bridge_submit_task.",
    "timeout": "Bridge request timeout in seconds; null uses the configured default.",
    "title": "Optional Origin page long name or graph title.",
    "token": "Optional bridge authentication token override. Normally omit to use the handshake.",
    "topic": "Knowledge entry path within the selected collection; omit to list its children.",
    "version": "Optional Origin documentation version filter, such as 2026b.",
    "width": "Export width in pixels; zero preserves Origin's default export width.",
    "worksheet": "Origin worksheet range or book/sheet reference. Omit to use the active sheet.",
    "x_col": "Column name or zero-based index to use as X data.",
    "x_error_col": "Optional column name or zero-based index containing X errors.",
    "x_label": "Optional X-axis title.",
    "y_col": "Column name or zero-based index to use as Y data.",
    "y_cols": "Column names or zero-based indexes to use as Y series.",
    "y_error_col": "Optional column name or zero-based index containing Y errors.",
    "y_label": "Optional Y-axis title.",
    "z_col": "Optional column name or zero-based index to use as Z data.",
}

_JSON_SCHEMA_CONSTRAINTS = {
    "minimum": "ge",
    "exclusiveMinimum": "gt",
    "maximum": "le",
    "exclusiveMaximum": "lt",
    "minLength": "min_length",
    "maxLength": "max_length",
    "minItems": "min_length",
    "maxItems": "max_length",
}


def _model_schema_value(schema: dict[str, Any], key: str, root: dict[str, Any]) -> Any:
    if key in schema:
        return schema[key]
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        target = root.get("$defs", {}).get(reference.removeprefix("#/$defs/"), {})
        value = _model_schema_value(target, key, root)
        if value is not None:
            return value
    for branch_key in ("anyOf", "oneOf", "allOf"):
        for branch in schema.get(branch_key, []):
            value = _model_schema_value(branch, key, root)
            if value is not None:
                return value
    return None


def _tool_profile() -> str:
    return os.environ.get("ORIGIN_MCP_TOOL_PROFILE", "compact").strip().lower() or "compact"


def _should_register_tool(name: str) -> bool:
    profile = _tool_profile()
    if profile in FULL_TOOL_PROFILE_VALUES:
        return True
    return name in PROFILE_TOOL_NAMES.get(profile, COMPACT_TOOL_NAMES)


def _enrich_tool_schema(
    func: Any,
    *,
    schema_model: type[BaseModel] | None = None,
    parameter_descriptions: dict[str, str] | None = None,
    parameter_choices: dict[str, tuple[Any, ...] | list[Any] | set[Any]] | None = None,
    parameter_constraints: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Attach MCP-facing field metadata without changing the flat call signature."""

    descriptions = parameter_descriptions or {}
    choices = parameter_choices or {}
    constraints = parameter_constraints or {}
    root_model_schema = schema_model.model_json_schema() if schema_model is not None else {}
    model_properties = root_model_schema.get("properties", {})
    try:
        resolved_annotations = get_type_hints(func, include_extras=True)
    except (NameError, TypeError):
        resolved_annotations = dict(func.__annotations__)

    for name in signature(func).parameters:
        annotation = resolved_annotations.get(name)
        if annotation is None:
            continue
        property_schema = model_properties.get(name, {})
        description = (
            descriptions.get(name)
            or property_schema.get("description")
            or _COMMON_PARAMETER_DESCRIPTIONS.get(name)
        )
        field_kwargs = {}
        for source, target in _JSON_SCHEMA_CONSTRAINTS.items():
            value = _model_schema_value(property_schema, source, root_model_schema)
            if value is not None:
                field_kwargs[target] = value
        field_kwargs.update(constraints.get(name, {}))
        if description:
            field_kwargs["description"] = description

        enum_values = choices.get(name) or _model_schema_value(
            property_schema, "enum", root_model_schema
        )
        if enum_values:
            field_kwargs["json_schema_extra"] = {"enum": list(enum_values)}
        if not field_kwargs:
            continue
        func.__annotations__[name] = Annotated[annotation, Field(**field_kwargs)]


def _mcp_tool(
    *,
    schema_model: type[BaseModel] | None = None,
    parameter_descriptions: dict[str, str] | None = None,
    parameter_choices: dict[str, tuple[Any, ...] | list[Any] | set[Any]] | None = None,
    parameter_constraints: dict[str, dict[str, Any]] | None = None,
    **tool_kwargs: Any,
) -> Any:
    def decorate(func: Any) -> Any:
        if _should_register_tool(func.__name__):
            _enrich_tool_schema(
                func,
                schema_model=schema_model,
                parameter_descriptions=parameter_descriptions,
                parameter_choices=parameter_choices,
                parameter_constraints=parameter_constraints,
            )
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
    guidance = recovery_guidance(error_code)
    return ToolResult(
        ok=False,
        message=str(exc),
        error_code=error_code,
        recoverable=guidance.recoverable,
        next_actions=list(guidance.next_actions),
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
