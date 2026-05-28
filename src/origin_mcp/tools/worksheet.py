from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.models import (
    CsvImportRequest,
    TableImportRequest,
)

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
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


@_mcp_tool()
def origin_new_project(show: bool = True) -> dict[str, Any]:
    """Create a new Origin project."""

    return _wrap(lambda: _ok("Created a new Origin project.", **client.new_project(show=show)))


@_mcp_tool()
def origin_open_project(path: str, readonly: bool = False, asksave: bool = False) -> dict[str, Any]:
    """Open an existing Origin OPJU/OPJ project."""

    return _wrap(
        lambda: _ok(
            "Opened Origin project.",
            **client.open_project(Path(path), readonly=readonly, asksave=asksave),
        )
    )


@_mcp_tool()
def origin_save_project(path: str) -> dict[str, Any]:
    """Save the current Origin project to an OPJU/OPJ path."""

    return _wrap(lambda: _ok("Saved Origin project.", **client.save_project(Path(path))))


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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
