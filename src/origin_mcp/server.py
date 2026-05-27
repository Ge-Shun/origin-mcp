from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .bridge_client import OriginBridgeProxy, request_bridge
from .errors import OriginBridgeError, OriginDependencyError, OriginMcpError, OriginOperationError
from .knowledge import browse_knowledge, query_knowledge
from .models import (
    AnalysisRequest,
    AxisSettingsRequest,
    CsvImportRequest,
    GraphFormatRequest,
    PlotKind,
    PlotStyleMode,
    PlotStyleRequest,
    PlotTableRequest,
    ProjectObjectRequest,
    TableImportRequest,
    ToolResult,
)

mcp = FastMCP("origin-mcp")


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


@mcp.tool()
def origin_ping(show: bool = True) -> dict[str, Any]:
    """Connect to Origin/OriginPro and report basic status."""

    return _wrap(lambda: _ok("Connected to Origin.", **client.connect(show=show)))


@mcp.tool()
def origin_capabilities(show: bool = False, refresh: bool = False) -> dict[str, Any]:
    """Report Origin/originpro versions and runtime feature availability."""

    return _wrap(
        lambda: _ok(
            "Collected Origin compatibility information.",
            **client.capabilities(show=show, refresh=refresh),
        )
    )


@mcp.tool()
def origin_bridge_status(
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 2.0,
) -> dict[str, Any]:
    """Check whether the Origin GUI bridge is reachable."""

    return _wrap(
        lambda: _ok(
            "Origin bridge responded.",
            **request_bridge(
                "ping",
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_ping_origin(
    show: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Ask the Origin GUI bridge to connect to Origin and report status."""

    return _wrap(
        lambda: _ok(
            "Origin bridge connected to Origin.",
            **request_bridge(
                "origin_ping",
                {"show": show},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_capabilities(
    show: bool = False,
    refresh: bool = False,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Ask the Origin GUI bridge for Origin/originpro capabilities."""

    return _wrap(
        lambda: _ok(
            "Origin bridge collected capabilities.",
            **request_bridge(
                "origin_capabilities",
                {"show": show, "refresh": refresh},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_run_labtalk(
    script: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Execute LabTalk through the Origin GUI bridge."""

    return _wrap(
        lambda: _ok(
            "Origin bridge executed LabTalk script.",
            **request_bridge(
                "run_labtalk",
                {"script": script},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_new_project(
    show: bool = True,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Create a new Origin project through the Origin GUI bridge."""

    return _wrap(
        lambda: _ok(
            "Origin bridge created a new project.",
            **request_bridge(
                "new_project",
                {"show": show},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge opened project.",
            **request_bridge(
                "open_project",
                {"path": path, "readonly": readonly, "asksave": asksave},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_save_project(
    path: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """Save the current Origin project through the Origin GUI bridge."""

    return _wrap(
        lambda: _ok(
            "Origin bridge saved project.",
            **request_bridge(
                "save_project",
                {"path": path},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_list_project(
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 30.0,
) -> dict[str, Any]:
    """List Origin project objects through the Origin GUI bridge."""

    return _wrap(
        lambda: _ok(
            "Origin bridge listed project objects.",
            **request_bridge(
                "list_project",
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge imported table data.",
            **request_bridge(
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
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge collected worksheet information.",
            **request_bridge(
                "worksheet_info",
                {"book_name": book_name, "sheet_name": sheet_name, "label_types": label_types},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge read worksheet data.",
            **request_bridge(
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
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge wrote worksheet data.",
            **request_bridge(
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
            ),
        )
    )


@mcp.tool()
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
    export_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 60.0,
) -> dict[str, Any]:
    """Create a table-backed plot through the Origin GUI bridge."""

    return _wrap(
        lambda: _ok(
            "Origin bridge created table-backed plot.",
            **request_bridge(
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
                    "export_path": export_path,
                },
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge exported graph.",
            **request_bridge(
                "export_graph",
                {"path": path, "graph_name": graph_name, "overwrite": overwrite},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
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

    return _wrap(
        lambda: _ok(
            "Origin bridge ran analysis.",
            **request_bridge(
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
            ),
        )
    )


@mcp.tool()
def origin_bridge_submit_task(
    method: str,
    params: dict[str, Any] | None = None,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Submit a supported Origin bridge method as a queued background task."""

    return _wrap(
        lambda: _ok(
            "Submitted Origin bridge task.",
            **request_bridge(
                "submit_task",
                {"method": method, "params": params or {}},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_task_status(
    task_id: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Read status, result, or error for an Origin bridge background task."""

    return _wrap(
        lambda: _ok(
            "Read Origin bridge task status.",
            **request_bridge(
                "task_status",
                {"task_id": task_id},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_cancel_task(
    task_id: str,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """Cancel a queued Origin bridge task or mark a running task for cancellation."""

    return _wrap(
        lambda: _ok(
            "Requested Origin bridge task cancellation.",
            **request_bridge(
                "cancel_task",
                {"task_id": task_id},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_bridge_list_tasks(
    limit: int = 20,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 10.0,
) -> dict[str, Any]:
    """List recent Origin bridge background tasks."""

    return _wrap(
        lambda: _ok(
            "Listed Origin bridge tasks.",
            **request_bridge(
                "list_tasks",
                {"limit": limit},
                host=host,
                port=port,
                token=token,
                timeout=timeout,
            ),
        )
    )


@mcp.tool()
def origin_plot_type_coverage(
    origin_version: float | None = None,
    show: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    """Report documented Origin plot type coverage by Origin version and MCP support."""

    return _wrap(
        lambda: _ok(
            "Collected Origin plot type coverage information.",
            **client.plot_type_coverage(
                origin_version=origin_version,
                show=show,
                refresh=refresh,
            ),
        )
    )


@mcp.tool()
def origin_browse_knowledge(
    collection: str | None = None,
    topic: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Browse the local Origin knowledge base by collection and path."""

    return _wrap(
        lambda: _ok(
            "Browsed Origin knowledge base.",
            **browse_knowledge(collection=collection, path=topic, version=version),
        )
    )


@mcp.tool()
def origin_query_knowledge(
    query: str,
    collection: str | None = None,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search the local Origin knowledge base by keyword."""

    return _wrap(
        lambda: _ok(
            "Searched Origin knowledge base.",
            **query_knowledge(query=query, collection=collection, version=version, limit=limit),
        )
    )


@mcp.tool()
def origin_browse_reference(topic: str | None = None, version: str | None = None) -> dict[str, Any]:
    """Browse Origin workflow reference notes, plot IDs, styles, and analysis adapters."""

    return _wrap(
        lambda: _ok(
            "Browsed Origin reference knowledge.",
            **browse_knowledge(collection="reference", path=topic, version=version),
        )
    )


@mcp.tool()
def origin_query_reference(
    query: str,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Origin workflow reference notes, plot IDs, styles, and analysis adapters."""

    return _wrap(
        lambda: _ok(
            "Searched Origin reference knowledge.",
            **query_knowledge(query=query, collection="reference", version=version, limit=limit),
        )
    )


@mcp.tool()
def origin_browse_python_api(api: str | None = None) -> dict[str, Any]:
    """Browse OriginPro Python API usage notes by dot path."""

    return _wrap(
        lambda: _ok(
            "Browsed OriginPro Python API knowledge.",
            **browse_knowledge(collection="python_api", path=api),
        )
    )


@mcp.tool()
def origin_query_python_api(query: str, limit: int = 10) -> dict[str, Any]:
    """Search OriginPro Python API usage notes."""

    return _wrap(
        lambda: _ok(
            "Searched OriginPro Python API knowledge.",
            **query_knowledge(query=query, collection="python_api", limit=limit),
        )
    )


@mcp.tool()
def origin_browse_labtalk(command: str | None = None, version: str | None = None) -> dict[str, Any]:
    """Browse LabTalk and X-Function knowledge used by origin-mcp."""

    return _wrap(
        lambda: _ok(
            "Browsed LabTalk knowledge.",
            **browse_knowledge(collection="labtalk", path=command, version=version),
        )
    )


@mcp.tool()
def origin_query_labtalk(query: str, version: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Search LabTalk and X-Function knowledge used by origin-mcp."""

    return _wrap(
        lambda: _ok(
            "Searched LabTalk knowledge.",
            **query_knowledge(query=query, collection="labtalk", version=version, limit=limit),
        )
    )


@mcp.tool()
def origin_browse_mcp_tools(tool: str | None = None) -> dict[str, Any]:
    """Browse origin-mcp tools by workflow group or tool path."""

    return _wrap(
        lambda: _ok(
            "Browsed origin-mcp tool knowledge.",
            **browse_knowledge(collection="mcp_tools", path=tool),
        )
    )


@mcp.tool()
def origin_query_mcp_tools(query: str, limit: int = 10) -> dict[str, Any]:
    """Search origin-mcp tool knowledge."""

    return _wrap(
        lambda: _ok(
            "Searched origin-mcp tool knowledge.",
            **query_knowledge(query=query, collection="mcp_tools", limit=limit),
        )
    )


@mcp.tool()
def origin_browse_official_docs(topic: str | None = None) -> dict[str, Any]:
    """Browse indexed official OriginLab documentation entry points."""

    return _wrap(
        lambda: _ok(
            "Browsed official OriginLab documentation index.",
            **browse_knowledge(collection="official_docs", path=topic),
        )
    )


@mcp.tool()
def origin_query_official_docs(query: str, limit: int = 10) -> dict[str, Any]:
    """Search indexed official OriginLab documentation entry points."""

    return _wrap(
        lambda: _ok(
            "Searched official OriginLab documentation index.",
            **query_knowledge(query=query, collection="official_docs", limit=limit),
        )
    )


@mcp.tool()
def origin_get_default_plot_config(
    template_dir: str | None = None,
    max_templates: int = 200,
) -> dict[str, Any]:
    """Inspect Origin default plot template/style settings visible to origin-mcp."""

    return _wrap(
        lambda: _ok(
            "Collected Origin default plot configuration.",
            **client.default_plot_config(
                template_dir=Path(template_dir) if template_dir else None,
                max_templates=max_templates,
            ),
        )
    )


@mcp.tool()
def origin_new_project(show: bool = True) -> dict[str, Any]:
    """Create a new Origin project."""

    return _wrap(lambda: _ok("Created a new Origin project.", **client.new_project(show=show)))


@mcp.tool()
def origin_open_project(path: str, readonly: bool = False, asksave: bool = False) -> dict[str, Any]:
    """Open an existing Origin OPJU/OPJ project."""

    return _wrap(
        lambda: _ok(
            "Opened Origin project.",
            **client.open_project(Path(path), readonly=readonly, asksave=asksave),
        )
    )


@mcp.tool()
def origin_save_project(path: str) -> dict[str, Any]:
    """Save the current Origin project to an OPJU/OPJ path."""

    return _wrap(lambda: _ok("Saved Origin project.", **client.save_project(Path(path))))


@mcp.tool()
def origin_import_csv(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Import a CSV file into a new Origin worksheet."""

    def run() -> dict[str, Any]:
        req = CsvImportRequest(path=Path(path), book_name=book_name, sheet_name=sheet_name)
        worksheet = client.import_csv(req.path, req.book_name, req.sheet_name)
        return _ok("Imported CSV into Origin worksheet.", worksheet=worksheet.as_dict())

    return _wrap(run)


@mcp.tool()
def origin_import_table(
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
) -> dict[str, Any]:
    """Import a CSV, TSV, TXT, DAT, XLS, or XLSX file into a new Origin worksheet."""

    def run() -> dict[str, Any]:
        req = TableImportRequest(
            path=Path(path),
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        worksheet = client.import_table(
            req.path,
            book_name=req.book_name,
            sheet_name=req.sheet_name,
            excel_sheet=req.excel_sheet,
            delimiter=req.delimiter,
            encoding=req.encoding,
            header=req.header,
            skiprows=req.skiprows,
            nrows=req.nrows,
            na_values=req.na_values,
        )
        return _ok("Imported table data into Origin worksheet.", worksheet=worksheet.as_dict())

    return _wrap(run)


@mcp.tool()
def origin_import_excel(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
) -> dict[str, Any]:
    """Import an Excel workbook sheet into a new Origin worksheet."""

    return origin_import_table(
        path=path,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
    )


@mcp.tool()
def origin_import_file(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    keep_dc: bool = True,
    dctype: str = "",
    sel: str = "",
    sparks: bool = False,
) -> dict[str, Any]:
    """Import a file using Origin's official Data Connector/from_file path."""

    def run() -> dict[str, Any]:
        worksheet = client.import_file_connector(
            Path(path),
            book_name=book_name,
            sheet_name=sheet_name,
            keep_dc=keep_dc,
            dctype=dctype,
            sel=sel,
            sparks=sparks,
        )
        return _ok("Imported file with Origin Data Connector.", worksheet=worksheet.as_dict())

    return _wrap(run)


@mcp.tool()
def origin_append_table(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
    start_col: str | int = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
) -> dict[str, Any]:
    """Append table data into an existing Origin worksheet starting at a column."""

    def run() -> dict[str, Any]:
        req = TableImportRequest(
            path=Path(path),
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        worksheet = client.append_table(
            req.path,
            book_name=req.book_name,
            sheet_name=req.sheet_name,
            excel_sheet=req.excel_sheet,
            start_col=start_col,
            delimiter=req.delimiter,
            encoding=req.encoding,
            header=req.header,
            skiprows=req.skiprows,
            nrows=req.nrows,
            na_values=req.na_values,
        )
        return _ok("Appended table data into Origin worksheet.", worksheet=worksheet.as_dict())

    return _wrap(run)


@mcp.tool()
def origin_get_worksheet_info(
    book_name: str | None = None,
    sheet_name: str | None = None,
    label_types: list[str] | None = None,
) -> dict[str, Any]:
    """Get worksheet row/column counts and column label rows."""

    return _wrap(
        lambda: _ok(
            "Collected Origin worksheet information.",
            **client.worksheet_info(
                book_name=book_name,
                sheet_name=sheet_name,
                label_types=label_types,
            ),
        )
    )


@mcp.tool()
def origin_read_worksheet(
    book_name: str | None = None,
    sheet_name: str | None = None,
    start_row: int = 0,
    max_rows: int = 100,
    columns: list[str | int] | None = None,
) -> dict[str, Any]:
    """Read a window of Origin worksheet data as structured rows."""

    return _wrap(
        lambda: _ok(
            "Read Origin worksheet data.",
            **client.read_worksheet(
                book_name=book_name,
                sheet_name=sheet_name,
                start_row=start_row,
                max_rows=max_rows,
                columns=columns,
            ),
        )
    )


@mcp.tool()
def origin_write_worksheet(
    rows: list[dict[str, Any]] | list[list[Any]],
    columns: list[str] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    start_col: str | int = 0,
    create: bool = False,
) -> dict[str, Any]:
    """Write structured rows into a new or existing Origin worksheet."""

    return _wrap(
        lambda: _ok(
            "Wrote Origin worksheet data.",
            **client.write_worksheet(
                rows=rows,
                columns=columns,
                book_name=book_name,
                sheet_name=sheet_name,
                start_col=start_col,
                create=create,
            ),
        )
    )


@mcp.tool()
def origin_add_calculated_column(
    column_name: str,
    formula: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Add a worksheet column and fill it with a LabTalk column formula."""

    return _wrap(
        lambda: _ok(
            "Added calculated Origin worksheet column.",
            **client.add_calculated_column(
                column_name=column_name,
                formula=formula,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@mcp.tool()
def origin_sort_worksheet(
    by: str | int,
    ascending: bool = True,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Sort worksheet rows by a column through a pandas round trip."""

    return _wrap(
        lambda: _ok(
            "Sorted Origin worksheet data.",
            **client.sort_worksheet(
                by=by,
                ascending=ascending,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@mcp.tool()
def origin_get_cell_value(
    row: int,
    column: str | int,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Read one worksheet cell value by zero-based row and column name/index."""

    return _wrap(
        lambda: _ok(
            "Read Origin worksheet cell value.",
            **client.get_cell_value(
                row=row,
                column=column,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@mcp.tool()
def origin_set_cell_value(
    row: int,
    column: str | int,
    value: Any,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Set one worksheet cell value by zero-based row and column name/index."""

    return _wrap(
        lambda: _ok(
            "Updated Origin worksheet cell value.",
            **client.set_cell_value(
                row=row,
                column=column,
                value=value,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@mcp.tool()
def origin_delete_columns(
    columns: list[str | int],
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Delete worksheet columns by name or zero-based index."""

    return _wrap(
        lambda: _ok(
            "Deleted Origin worksheet columns.",
            **client.delete_columns(
                columns=columns,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@mcp.tool()
def origin_clear_worksheet(
    book_name: str | None = None,
    sheet_name: str | None = None,
    keep_columns: bool = True,
) -> dict[str, Any]:
    """Clear worksheet data, optionally preserving column headers."""

    return _wrap(
        lambda: _ok(
            "Cleared Origin worksheet.",
            **client.clear_worksheet(
                book_name=book_name,
                sheet_name=sheet_name,
                keep_columns=keep_columns,
            ),
        )
    )


@mcp.tool()
def origin_export_worksheet_csv(
    path: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Export an Origin worksheet to a CSV file."""

    return _wrap(
        lambda: _ok(
            "Exported Origin worksheet to CSV.",
            **client.export_worksheet_csv(
                Path(path),
                book_name=book_name,
                sheet_name=sheet_name,
                overwrite=overwrite,
            ),
        )
    )


@mcp.tool()
def origin_plot_line(
    path: str,
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
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a line graph."""

    return _plot_csv(
        kind=PlotKind.line,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        y_error_col=y_error_col,
        x_error_col=x_error_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_scatter(
    path: str,
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
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a scatter graph."""

    return _plot_csv(
        kind=PlotKind.scatter,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        y_error_col=y_error_col,
        x_error_col=x_error_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_line_symbol(
    path: str,
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
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a line+symbol graph."""

    return _plot_csv(
        kind=PlotKind.line_symbol,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        y_error_col=y_error_col,
        x_error_col=x_error_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_column(
    path: str,
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
    y_error_col: str | int | None = None,
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a column/bar-style graph."""

    return _plot_csv(
        kind=PlotKind.column,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        y_error_col=y_error_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_contour(
    path: str,
    x_col: str | int,
    y_col: str | int,
    z_col: str | int,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a contour graph."""

    return _plot_csv(
        kind=PlotKind.contour,
        path=path,
        x_col=x_col,
        y_cols=[y_col],
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        z_col=z_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_errorbar(
    path: str,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a line+symbol plot with error bars."""

    return _plot_csv(
        kind=PlotKind.line_symbol,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        y_error_col=y_error_col,
        x_error_col=x_error_col,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_histogram(
    path: str,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a histogram graph."""

    return _plot_csv(
        kind=PlotKind.histogram,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_box(
    path: str,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a box plot."""

    return _plot_csv(
        kind=PlotKind.box,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_heatmap(
    path: str,
    x_col: str | int,
    y_col: str | int,
    z_col: str | int,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a heatmap graph."""

    return _plot_table_id(
        path=path,
        plot_type_id=243,
        template=template or "Contour",
        selected_cols=[x_col, y_col, z_col],
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        title=title,
        x_label=x_label,
        y_label=y_label,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_3d_scatter(
    path: str,
    x_col: str | int,
    y_col: str | int,
    z_col: str | int,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a 3D scatter graph."""

    return _plot_table_id(
        path=path,
        plot_type_id=240,
        template=template or "3d",
        selected_cols=[x_col, y_col, z_col],
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        title=title,
        x_label=x_label,
        y_label=y_label,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_3d_surface(
    path: str,
    x_col: str | int,
    y_col: str | int,
    z_col: str | int,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a 3D surface graph."""

    return _plot_table_id(
        path=path,
        plot_type_id=242,
        template=template or "glmesh",
        selected_cols=[x_col, y_col, z_col],
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        title=title,
        x_label=x_label,
        y_label=y_label,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_polar(
    path: str,
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
    show_legend: bool = True,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a polar graph."""

    return _plot_csv(
        kind=PlotKind.polar,
        path=path,
        x_col=x_col,
        y_cols=y_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_table_id(
    path: str,
    plot_type_id: int,
    template: str,
    selected_cols: list[str | int] | None = None,
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
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a graph from table data using an Origin Plot Type ID and template."""

    return _plot_table_id(
        path=path,
        plot_type_id=plot_type_id,
        template=template,
        selected_cols=selected_cols,
        book_name=book_name,
        sheet_name=sheet_name,
        excel_sheet=excel_sheet,
        delimiter=delimiter,
        encoding=encoding,
        header=header,
        skiprows=skiprows,
        nrows=nrows,
        na_values=na_values,
        graph_name=graph_name,
        title=title,
        x_label=x_label,
        y_label=y_label,
        style_mode=style_mode,
        export_path=export_path,
    )


@mcp.tool()
def origin_plot_matrix_id(
    data_range: str,
    plot_type_id: int,
    template: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a graph from an existing matrix/XYZ Origin range using a Plot Type ID."""

    def run() -> dict[str, Any]:
        graph = client.plot_matrix_by_id(
            data_range=data_range,
            plot_type_id=plot_type_id,
            template=template,
            graph_name=graph_name,
            title=title,
            export_path=Path(export_path) if export_path else None,
        )
        graph_data = graph.as_dict()
        return _ok(
            "Created Origin graph from range and Plot Type ID.",
            graph=graph_data,
            export_inspection=_export_inspection(graph_data),
        )

    return _wrap(run)


@mcp.tool()
def origin_plot_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an area plot from table data."""

    return _pti(path, 204, "area", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_stack_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a stacked area plot from table data."""

    return _pti(path, 214, "stackarea", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_fill_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a fill area plot from table data."""

    return _pti(path, 249, "fillarea", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a horizontal bar plot from table data."""

    return _pti(path, 215, "bar", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_stack_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a stacked bar plot from table data."""

    return _pti(path, 216, "bar", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_floating_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a floating bar plot from table data."""

    return _pti(path, 207, "floatbar", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_column_stack(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a column stack plot from table data."""

    return _pti(path, 213, "column", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_pie(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a pie chart from table data."""

    return _pti(path, 225, "pie", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_ternary(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a ternary plot from XYZ table data."""

    return _pti(path, 245, "ternary", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_ternary_contour(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a ternary contour plot from table data."""

    return _pti(path, 185, "TernaryContour", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_bubble(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a bubble plot from table data."""

    return _pti(path, 193, "scatter", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_bubble_color_mapped(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a bubble and color-mapped plot from table data."""

    return _pti(path, 248, "scatter", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_color_mapped(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a color-mapped scatter plot from table data."""

    return _pti(path, 247, "scatter", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_vector_xyam(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an XYAM vector plot from table data."""

    return _pti(path, 208, "vector", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_vector_xyxy(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an XYXY vector plot from table data."""

    return _pti(path, 218, "vectxyxy", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_3d_vector(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D vector plot from table data."""

    return _pti(path, 183, "gl3DVector", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_high_low_close(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a high-low-close plot from table data."""

    return _pti(path, 205, "hclose", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_candlestick(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an OHLC/candlestick chart from table data."""

    return _pti(path, 221, "Candlestick", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_waterfall(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D waterfall/walls plot from table data."""

    return _pti(path, 210, "walls", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_3d_ribbon(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D ribbon plot from table data."""

    return _pti(path, 211, "ribbon", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_3d_bars(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D bar plot from table data."""

    return _pti(path, 212, "bar3d", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_3d_errorbar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D scatter plot with error bars from table data."""

    return _pti(path, 184, "gl3DError", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_polar_xr_ytheta(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a polar X(R) Y(Theta) plot from table data."""

    return _pti(path, 186, "PolarXrYTheta", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_smith(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a Smith chart from table data."""

    return _pti(path, 191, "SmithCht", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_dendrogram(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a dendrogram plot from table data."""

    return _pti(path, 108, "Cluster", selected_cols, graph_name, title, export_path)


@mcp.tool()
def origin_plot_matrix_3d_scatter(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D scatter plot from an existing Origin matrix range."""

    return origin_plot_matrix_id(data_range, 101, "gl3DScatterMat", graph_name, title, export_path)


@mcp.tool()
def origin_plot_matrix_3d_surface(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D surface plot from an existing Origin matrix range."""

    return origin_plot_matrix_id(data_range, 103, "glmesh", graph_name, title, export_path)


@mcp.tool()
def origin_plot_matrix_heatmap(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a heatmap from an existing Origin matrix range."""

    return origin_plot_matrix_id(data_range, 105, "heatmap", graph_name, title, export_path)


@mcp.tool()
def origin_plot_matrix_contour(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a contour plot from an existing Origin matrix range."""

    return origin_plot_matrix_id(data_range, 226, "contour", graph_name, title, export_path)


@mcp.tool()
def origin_plot_image(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an image plot from an existing Origin matrix range."""

    return origin_plot_matrix_id(data_range, 220, "image", graph_name, title, export_path)


@mcp.tool()
def origin_plot_from_range(
    data_range: str,
    template: str = "line",
    plot_type: str = "?",
    graph_name: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a graph from an existing Origin range and template."""

    def run() -> dict[str, Any]:
        graph = client.plot_range(
            data_range=data_range,
            template=template,
            plot_type=plot_type,
            graph_name=graph_name,
            title=title,
            x_label=x_label,
            y_label=y_label,
            export_path=Path(export_path) if export_path else None,
        )
        graph_data = graph.as_dict()
        return _ok(
            "Created graph from Origin range.",
            graph=graph_data,
            export_inspection=_export_inspection(graph_data),
        )

    return _wrap(run)


@mcp.tool()
def origin_batch_plot_from_template(
    data_ranges: list[str],
    template: str,
    output_dir: str | None = None,
    file_type: str = "png",
    plot_type: str = "?",
) -> dict[str, Any]:
    """Create multiple graphs from existing Origin ranges using one template."""

    return _wrap(
        lambda: _ok(
            "Created batch template plots.",
            **client.batch_plot_from_template(
                data_ranges=data_ranges,
                template=template,
                output_dir=Path(output_dir) if output_dir else None,
                file_type=file_type,
                plot_type=plot_type,
            ),
        )
    )


@mcp.tool()
def origin_list_graph_templates(template_dir: str | None = None) -> dict[str, Any]:
    """List common graph template names and optional template files in a directory."""

    return _wrap(
        lambda: _ok(
            "Listed Origin graph templates.",
            **client.list_graph_templates(Path(template_dir) if template_dir else None),
        )
    )


@mcp.tool()
def origin_get_graph_info(graph_name: str | None = None) -> dict[str, Any]:
    """Inspect a graph page, its layers, axes, and plots."""

    return _wrap(
        lambda: _ok(
            "Collected Origin graph information.",
            **client.get_graph_info(graph_name=graph_name),
        )
    )


@mcp.tool()
def origin_get_layer_info(
    graph_name: str | None = None,
    layer_index: int = 0,
) -> dict[str, Any]:
    """Inspect one graph layer, its axes, and plots."""

    return _wrap(
        lambda: _ok(
            "Collected Origin graph layer information.",
            **client.get_layer_info(graph_name=graph_name, layer_index=layer_index),
        )
    )


@mcp.tool()
def origin_export_graph(
    path: str,
    graph_name: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Export the active or named Origin graph to an image/PDF file."""

    def run() -> dict[str, Any]:
        exported = client.export_graph(Path(path), graph_name=graph_name, overwrite=overwrite)
        return _ok(
            "Exported Origin graph.",
            **exported,
            inspection=client.inspect_export(Path(exported["path"])),
        )

    return _wrap(run)


@mcp.tool()
def origin_export_all_graphs(
    output_dir: str,
    file_type: str = "png",
    overwrite: bool = True,
    width: int = 0,
) -> dict[str, Any]:
    """Export all graphs in the current Origin project."""

    return _wrap(
        lambda: _ok(
            "Exported all Origin graphs.",
            **client.export_all_graphs(
                Path(output_dir),
                file_type=file_type,
                overwrite=overwrite,
                width=width,
            ),
        )
    )


@mcp.tool()
def origin_export_preview(
    graph_name: str | None = None,
    output_dir: str | None = None,
    file_type: str = "png",
    overwrite: bool = True,
) -> dict[str, Any]:
    """Export a graph preview image and return file diagnostics."""

    return _wrap(
        lambda: _ok(
            "Exported Origin graph preview.",
            **client.export_preview(
                graph_name=graph_name,
                output_dir=Path(output_dir) if output_dir else None,
                file_type=file_type,
                overwrite=overwrite,
            ),
        )
    )


@mcp.tool()
def origin_inspect_export(path: str) -> dict[str, Any]:
    """Inspect an exported graph file for size, dimensions, hash, and image quality."""

    return _wrap(
        lambda: _ok(
            "Inspected exported graph file.",
            **client.inspect_export(Path(path)),
        )
    )


@mcp.tool()
def origin_format_graph(
    graph_name: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    show_legend: bool | None = None,
    rescale: bool = True,
) -> dict[str, Any]:
    """Set graph long name, axis labels, legend visibility, and optional rescale."""

    def run() -> dict[str, Any]:
        req = GraphFormatRequest(
            graph_name=graph_name,
            title=title,
            x_label=x_label,
            y_label=y_label,
            show_legend=show_legend,
            rescale=rescale,
        )
        return _ok(
            "Formatted Origin graph.",
            **client.format_graph(
                graph_name=req.graph_name,
                title=req.title,
                x_label=req.x_label,
                y_label=req.y_label,
                show_legend=req.show_legend,
                rescale=req.rescale,
            ),
        )

    return _wrap(run)


@mcp.tool()
def origin_set_axis(
    graph_name: str | None = None,
    axis: str = "x",
    scale: str | int | None = None,
    start: float | None = None,
    end: float | None = None,
    step: float | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Set axis scale, limits, tick step, and title."""

    def run() -> dict[str, Any]:
        req = AxisSettingsRequest(
            graph_name=graph_name,
            axis=axis,
            scale=scale,
            start=start,
            end=end,
            step=step,
            title=title,
        )
        return _ok("Updated Origin graph axis.", **client.set_axis(**req.model_dump()))

    return _wrap(run)


@mcp.tool()
def origin_set_plot_style(
    graph_name: str | None = None,
    plot_index: int | None = None,
    color: str | tuple[int, int, int] | None = None,
    line_width: float | None = None,
    line_style: int | None = None,
    symbol_kind: int | None = None,
    symbol_size: float | None = None,
    transparency: float | None = None,
) -> dict[str, Any]:
    """Set line, color, symbol, and transparency style on one or all plots."""

    def run() -> dict[str, Any]:
        req = PlotStyleRequest(
            graph_name=graph_name,
            plot_index=plot_index,
            color=color,
            line_width=line_width,
            line_style=line_style,
            symbol_kind=symbol_kind,
            symbol_size=symbol_size,
            transparency=transparency,
        )
        return _ok("Updated Origin plot style.", **client.set_plot_style(**req.model_dump()))

    return _wrap(run)


@mcp.tool()
def origin_apply_publication_style(
    graph_name: str | None = None,
    layer_index: int | None = None,
    page_width: float | None = 6.0,
    page_height: float | None = 4.0,
    axis_title_size: int = 18,
    tick_label_size: int = 14,
    legend_font_size: int = 12,
    line_width: float = 2.0,
    symbol_size: float = 8.0,
    tick_length: int = 6,
    show_legend: bool = True,
) -> dict[str, Any]:
    """Apply a compact publication-style graph format."""

    return _wrap(
        lambda: _ok(
            "Applied Origin publication style.",
            **client.apply_publication_style(
                graph_name=graph_name,
                layer_index=layer_index,
                page_width=page_width,
                page_height=page_height,
                axis_title_size=axis_title_size,
                tick_label_size=tick_label_size,
                legend_font_size=legend_font_size,
                line_width=line_width,
                symbol_size=symbol_size,
                tick_length=tick_length,
                show_legend=show_legend,
            ),
        )
    )


@mcp.tool()
def origin_apply_nature_style(
    graph_name: str | None = None,
    layer_index: int | None = None,
    chart_type: str | None = None,
    page_width: float | None = None,
    page_height: float | None = None,
    font_family: str = "Arial",
    axis_title_size: int = 8,
    tick_label_size: int = 7,
    legend_font_size: int = 6,
    line_width: float = 1.2,
    symbol_size: float = 4.5,
    tick_length: int = 3,
    show_legend: bool = True,
    palette_role: str | None = None,
    run_diagnostics: bool = True,
) -> dict[str, Any]:
    """Apply a compact Nature-style scientific figure preset."""

    return _wrap(
        lambda: _ok(
            "Applied Origin Nature-style figure preset.",
            **client.apply_nature_style(
                graph_name=graph_name,
                layer_index=layer_index,
                chart_type=chart_type,
                page_width=page_width,
                page_height=page_height,
                font_family=font_family,
                axis_title_size=axis_title_size,
                tick_label_size=tick_label_size,
                legend_font_size=legend_font_size,
                line_width=line_width,
                symbol_size=symbol_size,
                tick_length=tick_length,
                show_legend=show_legend,
                palette_role=palette_role,
                run_diagnostics=run_diagnostics,
            ),
        )
    )


@mcp.tool()
def origin_diagnose_graph(
    graph_name: str | None = None,
    style: str | None = None,
    palette_role: str | None = None,
    require_axis_titles: bool = True,
    require_plots: bool = True,
    require_legend: bool = False,
    require_panel_label: bool = False,
    require_scale_bar: bool = False,
    require_channel_label: bool = False,
    require_dynamic_range: bool = False,
    export_path: str | None = None,
    min_export_width: int = 600,
    min_export_height: int = 400,
) -> dict[str, Any]:
    """Diagnose graph readiness issues such as empty layers or missing axis titles."""

    return _wrap(
        lambda: _ok(
            "Diagnosed Origin graph.",
            **client.diagnose_graph(
                graph_name=graph_name,
                style=style,
                palette_role=palette_role,
                require_axis_titles=require_axis_titles,
                require_plots=require_plots,
                require_legend=require_legend,
                require_panel_label=require_panel_label,
                require_scale_bar=require_scale_bar,
                require_channel_label=require_channel_label,
                require_dynamic_range=require_dynamic_range,
                export_path=Path(export_path) if export_path else None,
                min_export_width=min_export_width,
                min_export_height=min_export_height,
            ),
        )
    )


@mcp.tool()
def origin_recommend_chart(
    path: str,
    intent: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
    max_recommendations: int = 5,
) -> dict[str, Any]:
    """Recommend chart types from table shape, column semantics, and optional intent."""

    return _wrap(
        lambda: _ok(
            "Recommended chart route.",
            **client.recommend_chart(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                max_recommendations=max_recommendations,
            ),
        )
    )


@mcp.tool()
def origin_plot_auto(
    path: str,
    intent: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
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
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Choose a chart route from table data and create the plot."""

    return _wrap(
        lambda: _ok(
            "Created automatically routed plot.",
            **client.plot_auto(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                style_mode=style_mode,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )


@mcp.tool()
def origin_chart_atlas_route(
    intent: str,
    columns: list[str] | None = None,
    matrix: bool = False,
) -> dict[str, Any]:
    """Choose the recommended plot route for a semantic chart intent."""

    return _wrap(
        lambda: _ok(
            "Selected chart atlas route.",
            **client.chart_atlas_route(intent=intent, columns=columns, matrix=matrix),
        )
    )


@mcp.tool()
def origin_plot_chart_atlas(
    path: str,
    intent: str,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
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
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    style_mode: str = "origin_default",
    palette_role: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a plot using chart-atlas intent routing."""

    return _wrap(
        lambda: _ok(
            "Created chart atlas plot.",
            **client.plot_chart_atlas(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                style_mode=style_mode,
                palette_role=palette_role,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )


@mcp.tool()
def origin_apply_image_panel_style(
    graph_name: str | None = None,
    layer_index: int | None = None,
    panel_label: str | None = None,
    channel_label: str | None = None,
    scale_bar_label: str | None = None,
    dynamic_range_label: str | None = None,
    dark_panel: bool = False,
    font_size: int = 8,
    run_diagnostics: bool = True,
) -> dict[str, Any]:
    """Apply heatmap/image panel labels and optional dark panel layout."""

    return _wrap(
        lambda: _ok(
            "Applied Origin image panel style.",
            **client.apply_image_panel_style(
                graph_name=graph_name,
                layer_index=layer_index,
                panel_label=panel_label,
                channel_label=channel_label,
                scale_bar_label=scale_bar_label,
                dynamic_range_label=dynamic_range_label,
                dark_panel=dark_panel,
                font_size=font_size,
                run_diagnostics=run_diagnostics,
            ),
        )
    )


@mcp.tool()
def origin_add_plot_to_graph(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    graph_name: str | None = None,
    layer_index: int = 0,
    plot_type: str = "l",
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
) -> dict[str, Any]:
    """Add a worksheet X/Y plot to an existing graph layer."""

    return _wrap(
        lambda: _ok(
            "Added plot to Origin graph.",
            **client.add_plot_to_graph(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                graph_name=graph_name,
                layer_index=layer_index,
                plot_type=plot_type,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
            ),
        )
    )


@mcp.tool()
def origin_remove_plot_from_graph(
    plot_index: int,
    graph_name: str | None = None,
    layer_index: int = 0,
) -> dict[str, Any]:
    """Remove a plot from an existing graph layer."""

    return _wrap(
        lambda: _ok(
            "Removed plot from Origin graph.",
            **client.remove_plot_from_graph(
                plot_index=plot_index,
                graph_name=graph_name,
                layer_index=layer_index,
            ),
        )
    )


@mcp.tool()
def origin_change_plot_type(
    plot_index: int,
    plot_type: str,
    graph_name: str | None = None,
    layer_index: int = 0,
) -> dict[str, Any]:
    """Change an existing graph plot type."""

    return _wrap(
        lambda: _ok(
            "Changed Origin plot type.",
            **client.change_plot_type(
                plot_index=plot_index,
                plot_type=plot_type,
                graph_name=graph_name,
                layer_index=layer_index,
            ),
        )
    )


@mcp.tool()
def origin_change_plot_data(
    plot_index: int,
    worksheet: str | None,
    x_col: str | int,
    y_col: str | int,
    graph_name: str | None = None,
    layer_index: int = 0,
) -> dict[str, Any]:
    """Replace a plot by removing it and adding new worksheet X/Y data."""

    return _wrap(
        lambda: _ok(
            "Changed Origin plot data.",
            **client.change_plot_data(
                plot_index=plot_index,
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                graph_name=graph_name,
                layer_index=layer_index,
            ),
        )
    )


@mcp.tool()
def origin_set_graph_page(
    graph_name: str | None = None,
    width: float | None = None,
    height: float | None = None,
    unit: str = "inch",
    left: float | None = None,
    top: float | None = None,
) -> dict[str, Any]:
    """Set graph page size and page placement properties."""

    return _wrap(
        lambda: _ok(
            "Updated Origin graph page.",
            **client.set_graph_page(
                graph_name=graph_name,
                width=width,
                height=height,
                unit=unit,
                left=left,
                top=top,
            ),
        )
    )


@mcp.tool()
def origin_arrange_layers(
    graph_name: str | None = None,
    rows: int = 1,
    columns: int = 1,
    gap_x: float | None = None,
    gap_y: float | None = None,
) -> dict[str, Any]:
    """Arrange graph layers into a panel layout."""

    return _wrap(
        lambda: _ok(
            "Arranged Origin graph layers.",
            **client.arrange_layers(
                graph_name=graph_name,
                rows=rows,
                columns=columns,
                gap_x=gap_x,
                gap_y=gap_y,
            ),
        )
    )


@mcp.tool()
def origin_add_graph_label(
    text: str,
    graph_name: str | None = None,
    layer_index: int = 0,
    name: str | None = None,
    left: int | None = None,
    top: int | None = None,
    font_size: int | None = None,
) -> dict[str, Any]:
    """Add a text label to a graph layer."""

    return _wrap(
        lambda: _ok(
            "Added Origin graph label.",
            **client.add_graph_label(
                text=text,
                graph_name=graph_name,
                layer_index=layer_index,
                name=name,
                left=left,
                top=top,
                font_size=font_size,
            ),
        )
    )


@mcp.tool()
def origin_add_reference_line(
    value: float,
    axis: str = "y",
    graph_name: str | None = None,
    layer_index: int = 0,
    label: str | None = None,
) -> dict[str, Any]:
    """Add a horizontal or vertical reference line to a graph layer."""

    return _wrap(
        lambda: _ok(
            "Added Origin graph reference line.",
            **client.add_reference_line(
                value=value,
                axis=axis,
                graph_name=graph_name,
                layer_index=layer_index,
                label=label,
            ),
        )
    )


@mcp.tool()
def origin_set_column_labels(
    labels: list[str],
    label_type: str = "L",
    book_name: str | None = None,
    sheet_name: str | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Set Origin worksheet column label rows such as Long Name, Units, or Comments."""

    return _wrap(
        lambda: _ok(
            "Updated Origin worksheet column labels.",
            worksheet=client.set_column_labels(
                labels=labels,
                label_type=label_type,
                book_name=book_name,
                sheet_name=sheet_name,
                offset=offset,
            ),
        )
    )


@mcp.tool()
def origin_set_column_designations(
    spec: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
    c1: int = 0,
    c2: int = -1,
    repeat: bool = True,
) -> dict[str, Any]:
    """Set worksheet column plot designations, for example XYY or XY."""

    return _wrap(
        lambda: _ok(
            "Updated Origin worksheet column designations.",
            worksheet=client.set_column_designations(
                spec=spec,
                book_name=book_name,
                sheet_name=sheet_name,
                c1=c1,
                c2=c2,
                repeat=repeat,
            ),
        )
    )


@mcp.tool()
def origin_format_legend(
    graph_name: str | None = None,
    text: str | None = None,
    font_size: int | None = None,
    show_frame: bool | None = None,
    left: int | None = None,
    top: int | None = None,
    position: str | None = None,
    margin_percent: float = 2.0,
    coordinate_mode: str = "auto",
) -> dict[str, Any]:
    """Format the graph legend text, font size, frame, and optional position."""

    return _wrap(
        lambda: _ok(
            "Formatted Origin graph legend.",
            **client.format_legend(
                graph_name=graph_name,
                text=text,
                font_size=font_size,
                show_frame=show_frame,
                left=left,
                top=top,
                position=position,
                margin_percent=margin_percent,
                coordinate_mode=coordinate_mode,
            ),
        )
    )


@mcp.tool()
def origin_list_project() -> dict[str, Any]:
    """List workbooks, worksheets, matrix books, graphs, and images in the project."""

    return _wrap(lambda: _ok("Listed Origin project objects.", **client.list_project()))


@mcp.tool()
def origin_rename_object(name: str, new_name: str, object_type: str = "graph") -> dict[str, Any]:
    """Rename a graph, workbook, matrixbook, or worksheet."""

    def run() -> dict[str, Any]:
        req = ProjectObjectRequest(name=name, object_type=object_type)
        return _ok(
            "Renamed Origin object.",
            **client.rename_object(req.name, new_name=new_name, object_type=req.object_type),
        )

    return _wrap(run)


@mcp.tool()
def origin_delete_object(name: str, object_type: str = "graph") -> dict[str, Any]:
    """Delete a graph, workbook, matrixbook, or worksheet."""

    def run() -> dict[str, Any]:
        req = ProjectObjectRequest(name=name, object_type=object_type)
        return _ok(
            "Deleted Origin object.",
            **client.delete_object(req.name, object_type=req.object_type),
        )

    return _wrap(run)


@mcp.tool()
def origin_run_analysis(
    analysis: str,
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run a named Origin analysis X-Function through LabTalk."""

    def run() -> dict[str, Any]:
        req = AnalysisRequest(
            analysis=analysis,
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_sheet,
            options=options or {},
            include_output=include_output,
            output_max_rows=output_max_rows,
        )
        return _ok("Ran Origin analysis.", **client.run_analysis(**req.model_dump()))

    return _wrap(run)


@mcp.tool()
def origin_linear_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin linear fitting."""

    if x_col is not None and y_col is not None:
        return _wrap(
            lambda: _ok(
                "Ran Origin linear fitting.",
                **client.linear_fit_result(
                    worksheet=worksheet,
                    x_col=x_col,
                    y_col=y_col,
                    y_error_col=(options or {}).get("y_error_col"),
                    options=options,
                ),
            )
        )
    return origin_run_analysis(
        "linear_fit",
        worksheet,
        x_col,
        y_col,
        output_sheet,
        options,
        include_output,
        output_max_rows,
    )


@mcp.tool()
def origin_polynomial_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin polynomial fitting."""

    return origin_run_analysis(
        "polynomial_fit",
        worksheet,
        x_col,
        y_col,
        output_sheet,
        options,
        include_output,
        output_max_rows,
    )


@mcp.tool()
def origin_smooth(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin smoothing."""

    return origin_run_analysis(
        "smooth", worksheet, x_col, y_col, output_sheet, options, include_output, output_max_rows
    )


@mcp.tool()
def origin_peak_find(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin peak finding."""

    return origin_run_analysis(
        "peak_find", worksheet, x_col, y_col, output_sheet, options, include_output, output_max_rows
    )


@mcp.tool()
def origin_differentiate(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin differentiation."""

    return origin_run_analysis(
        "differentiate",
        worksheet,
        x_col,
        y_col,
        output_sheet,
        options,
        include_output,
        output_max_rows,
    )


@mcp.tool()
def origin_integrate(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin integration."""

    return origin_run_analysis(
        "integrate", worksheet, x_col, y_col, output_sheet, options, include_output, output_max_rows
    )


@mcp.tool()
def origin_descriptive_stats(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin descriptive statistics."""

    return origin_run_analysis(
        "descriptive_stats",
        worksheet,
        x_col,
        y_col,
        output_sheet,
        options,
        include_output,
        output_max_rows,
    )


@mcp.tool()
def origin_nonlinear_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin nonlinear fitting."""

    return origin_run_analysis(
        "nonlinear_fit",
        worksheet,
        x_col,
        y_col,
        output_sheet,
        options,
        include_output,
        output_max_rows,
    )


@mcp.tool()
def origin_list_fit_functions() -> dict[str, Any]:
    """List common Origin nonlinear fit function names and parameters."""

    return _wrap(lambda: _ok("Listed Origin fit functions.", **client.list_fit_functions()))


@mcp.tool()
def origin_nonlinear_fit_structured(
    worksheet: str | None,
    x_col: str | int,
    y_col: str | int,
    function: str,
    output_sheet: str | None = None,
    initial_params: dict[str, float] | None = None,
    fixed_params: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run nonlinear fitting with explicit function and parameter hints."""

    return _wrap(
        lambda: _ok(
            "Ran structured Origin nonlinear fitting.",
            **client.nonlinear_fit_structured(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                function=function,
                output_sheet=output_sheet,
                initial_params=initial_params,
                fixed_params=fixed_params,
                options=options,
            ),
        )
    )


@mcp.tool()
def origin_run_labtalk(script: str) -> dict[str, Any]:
    """Execute LabTalk script text inside Origin."""

    return _wrap(lambda: _ok("Executed LabTalk script.", **client.run_labtalk(script)))


@mcp.tool()
def origin_quit() -> dict[str, Any]:
    """Close Origin/OriginPro."""

    return _wrap(lambda: _ok("Closed Origin.", **client.quit()))


@mcp.tool()
def origin_detach() -> dict[str, Any]:
    """Release the external Origin automation connection without closing Origin."""

    return _wrap(lambda: _ok("Released Origin automation connection.", **client.detach()))


@mcp.tool()
def origin_release() -> dict[str, Any]:
    """Alias for origin_detach."""

    return origin_detach()


@mcp.tool()
def origin_force_quit() -> dict[str, Any]:
    """Ask the bridge to force-close Origin/OriginPro."""

    return _wrap(lambda: _ok("Force-closed Origin.", **client.force_quit()))


def _plot_csv(
    kind: PlotKind,
    path: str,
    x_col: str | int | None,
    y_cols: list[str | int] | None,
    book_name: str | None,
    sheet_name: str | None,
    excel_sheet: str | int | None,
    delimiter: str | None,
    encoding: str | None,
    header: int | None,
    skiprows: int | list[int] | None,
    nrows: int | None,
    na_values: str | list[str] | None,
    graph_name: str | None,
    template: str | None,
    title: str | None,
    x_label: str | None,
    y_label: str | None,
    show_legend: bool,
    style_mode: str,
    export_path: str | None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        req = PlotTableRequest(
            path=Path(path),
            x_col=x_col,
            y_cols=y_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
            graph_name=graph_name,
            template=template,
            title=title,
            x_label=x_label,
            y_label=y_label,
            z_col=z_col,
            y_error_col=y_error_col,
            x_error_col=x_error_col,
            show_legend=show_legend,
            style_mode=PlotStyleMode(style_mode),
            export_path=Path(export_path) if export_path else None,
        )
        worksheet, graph = client.plot_table(
            path=req.path,
            kind=kind.value,
            x_col=req.x_col,
            y_cols=req.y_cols,
            book_name=req.book_name,
            sheet_name=req.sheet_name,
            excel_sheet=req.excel_sheet,
            delimiter=req.delimiter,
            encoding=req.encoding,
            header=req.header,
            skiprows=req.skiprows,
            nrows=req.nrows,
            na_values=req.na_values,
            graph_name=req.graph_name,
            template=req.template,
            title=req.title,
            x_label=req.x_label,
            y_label=req.y_label,
            z_col=req.z_col,
            y_error_col=req.y_error_col,
            x_error_col=req.x_error_col,
            show_legend=req.show_legend,
            style_mode=req.style_mode.value,
            export_path=req.export_path,
        )
        return _ok(
            f"Created {kind.value} plot from table data.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            export_inspection=_export_inspection(graph.as_dict()),
        )

    return _wrap(run)


def _plot_table_id(
    path: str,
    plot_type_id: int,
    template: str,
    selected_cols: list[str | int] | None = None,
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
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        style_mode_actual = PlotStyleMode(style_mode).value
        worksheet, graph, command = client.plot_table_by_id(
            path=Path(path),
            plot_type_id=plot_type_id,
            template=template,
            selected_cols=selected_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
            graph_name=graph_name,
            title=title,
            x_label=x_label,
            y_label=y_label,
            style_mode=style_mode_actual,
            export_path=Path(export_path) if export_path else None,
        )
        return _ok(
            "Created Origin graph from table data and Plot Type ID.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            command=command,
            export_inspection=_export_inspection(graph.as_dict()),
        )

    return _wrap(run)


def _pti(
    path: str,
    plot_type_id: int,
    template: str,
    selected_cols: list[str | int] | None,
    graph_name: str | None,
    title: str | None,
    export_path: str | None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    return _plot_table_id(
        path=path,
        plot_type_id=plot_type_id,
        template=template,
        selected_cols=selected_cols,
        graph_name=graph_name,
        title=title,
        style_mode=style_mode,
        export_path=export_path,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
