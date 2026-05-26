from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .errors import OriginMcpError
from .models import (
    AnalysisRequest,
    AxisSettingsRequest,
    CsvImportRequest,
    GraphFormatRequest,
    PlotKind,
    PlotStyleRequest,
    PlotTableRequest,
    ProjectObjectRequest,
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
    except Exception as exc:
        return _error(exc)


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
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a heatmap graph."""

    return _plot_csv(
        kind=PlotKind.heatmap,
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
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a 3D scatter graph."""

    return _plot_csv(
        kind=PlotKind.scatter3d,
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
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import XYZ table data and create a 3D surface graph."""

    return _plot_csv(
        kind=PlotKind.surface3d,
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

    return _wrap(
        lambda: _ok(
            "Created Origin graph from range and Plot Type ID.",
            graph=client.plot_matrix_by_id(
                data_range=data_range,
                plot_type_id=plot_type_id,
                template=template,
                graph_name=graph_name,
                title=title,
                export_path=Path(export_path) if export_path else None,
            ).as_dict(),
        )
    )


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
        return _ok("Created graph from Origin range.", graph=graph.as_dict())

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

    return _wrap(
        lambda: _ok(
            "Exported Origin graph.",
            **client.export_graph(Path(path), graph_name=graph_name, overwrite=overwrite),
        )
    )


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
    """Inspect an exported graph file for size and image dimensions."""

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
) -> dict[str, Any]:
    """Format the graph legend text, font size, frame, and position."""

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
    """Force OriginExt to close Origin/OriginPro."""

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
            export_path=req.export_path,
        )
        return _ok(
            f"Created {kind.value} plot from table data.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
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
    export_path: str | None = None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
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
            export_path=Path(export_path) if export_path else None,
        )
        return _ok(
            "Created Origin graph from table data and Plot Type ID.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            command=command,
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
) -> dict[str, Any]:
    return _plot_table_id(
        path=path,
        plot_type_id=plot_type_id,
        template=template,
        selected_cols=selected_cols,
        graph_name=graph_name,
        title=title,
        export_path=export_path,
    )
def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
