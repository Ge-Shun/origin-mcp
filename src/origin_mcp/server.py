from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .errors import OriginMcpError
from .models import (
    CsvImportRequest,
    GraphFormatRequest,
    PlotKind,
    PlotTableRequest,
    TableImportRequest,
    ToolResult,
)
from .origin_client import OriginClient

mcp = FastMCP("origin-mcp")
client = OriginClient()


def _ok(message: str, **data: Any) -> dict[str, Any]:
    return ToolResult(ok=True, message=message, data=data).model_dump()


def _error(exc: Exception) -> dict[str, Any]:
    return ToolResult(
        ok=False,
        message=str(exc),
        data={"error_type": type(exc).__name__},
    ).model_dump()


def _wrap(func: Any) -> dict[str, Any]:
    try:
        return func()
    except (OriginMcpError, ValidationError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def origin_ping(show: bool = True) -> dict[str, Any]:
    """Connect to Origin/OriginPro and report basic status."""

    return _wrap(lambda: _ok("Connected to Origin.", **client.connect(show=show)))


@mcp.tool()
def origin_new_project(show: bool = True) -> dict[str, Any]:
    """Create a new Origin project."""

    return _wrap(lambda: _ok("Created a new Origin project.", **client.new_project(show=show)))


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
) -> dict[str, Any]:
    """Import a CSV, TSV, TXT, DAT, XLS, or XLSX file into a new Origin worksheet."""

    def run() -> dict[str, Any]:
        req = TableImportRequest(
            path=Path(path),
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
        )
        worksheet = client.import_table(
            req.path,
            book_name=req.book_name,
            sheet_name=req.sheet_name,
            excel_sheet=req.excel_sheet,
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
def origin_plot_line(
    path: str,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
    graph_name: str | None = None,
    template: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    show_legend: bool = True,
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
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        show_legend=show_legend,
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
    graph_name: str | None = None,
    template: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    show_legend: bool = True,
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
        graph_name=graph_name,
        template=template,
        title=title,
        x_label=x_label,
        y_label=y_label,
        show_legend=show_legend,
        export_path=export_path,
    )


@mcp.tool()
def origin_export_graph(
    path: str,
    graph_name: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Export the active or named Origin graph to an image/PDF file."""

    return _wrap(
        lambda: _ok(
            "Exported Origin graph.",
            **client.export_graph(Path(path), graph_name=graph_name, overwrite=overwrite),
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
    """Set graph title, axis labels, legend visibility, and optional rescale."""

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
def origin_run_labtalk(script: str) -> dict[str, Any]:
    """Execute LabTalk script text inside Origin."""

    return _wrap(lambda: _ok("Executed LabTalk script.", **client.run_labtalk(script)))


@mcp.tool()
def origin_quit() -> dict[str, Any]:
    """Close Origin/OriginPro."""

    return _wrap(lambda: _ok("Closed Origin.", **client.quit()))


def _plot_csv(
    kind: PlotKind,
    path: str,
    x_col: str | int | None,
    y_cols: list[str | int] | None,
    book_name: str | None,
    sheet_name: str | None,
    excel_sheet: str | int | None,
    graph_name: str | None,
    template: str | None,
    title: str | None,
    x_label: str | None,
    y_label: str | None,
    show_legend: bool,
    export_path: str | None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        req = PlotTableRequest(
            path=Path(path),
            x_col=x_col,
            y_cols=y_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            graph_name=graph_name,
            template=template,
            title=title,
            x_label=x_label,
            y_label=y_label,
            show_legend=show_legend,
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
            graph_name=req.graph_name,
            template=req.template,
            title=req.title,
            x_label=req.x_label,
            y_label=req.y_label,
            show_legend=req.show_legend,
            export_path=req.export_path,
        )
        return _ok(
            f"Created {kind.value} plot from table data.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
        )

    return _wrap(run)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
