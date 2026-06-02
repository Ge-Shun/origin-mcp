from __future__ import annotations

from typing import Any

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_filter_rows(
    conditions: list[dict[str, Any]],
    combine: str = "and",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Keep worksheet rows matching structured conditions.

    Each condition is {"column": name_or_index, "op": ..., "value": ...} where op
    is one of eq, ne, gt, ge, lt, le, in, not_in, contains, startswith, isna,
    notna. Conditions are joined by combine ("and" or "or"). Provide output_book
    or output_sheet to write the result to a new sheet; otherwise the source
    worksheet is overwritten in place.
    """

    return _wrap(
        lambda: _ok(
            "Filtered Origin worksheet rows.",
            **client.filter_rows(
                conditions=conditions,
                combine=combine,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_drop_duplicates(
    subset: list[str | int] | None = None,
    keep: str = "first",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Remove duplicate worksheet rows.

    subset limits the columns considered for duplication (default: all columns).
    keep is "first", "last", or "none" (drop every duplicated row). Provide
    output_book/output_sheet to write to a new sheet instead of in place.
    """

    return _wrap(
        lambda: _ok(
            "Dropped duplicate Origin worksheet rows.",
            **client.drop_duplicates(
                subset=subset,
                keep=keep,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_fill_missing(
    strategy: str = "value",
    value: Any = None,
    columns: list[str | int] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Handle missing worksheet values.

    strategy is one of: drop_rows, drop_columns, value (requires value),
    ffill, bfill, mean, median. columns limits which columns are affected
    (default: all). Provide output_book/output_sheet to write to a new sheet
    instead of in place.
    """

    return _wrap(
        lambda: _ok(
            "Handled missing Origin worksheet values.",
            **client.fill_missing(
                strategy=strategy,
                value=value,
                columns=columns,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_transpose_worksheet(
    label_column: str | int | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Transpose a worksheet so rows become columns.

    When label_column is given, that column's values become the new column
    headers; otherwise headers are R1, R2, .... The original column names become
    a leading "Field" column. Provide output_book/output_sheet to write to a new
    sheet instead of in place.
    """

    return _wrap(
        lambda: _ok(
            "Transposed Origin worksheet.",
            **client.transpose_worksheet(
                label_column=label_column,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_merge_worksheets(
    right_book: str | None = None,
    right_sheet: str | None = None,
    on: str | list[str] | None = None,
    left_on: str | list[str] | None = None,
    right_on: str | list[str] | None = None,
    how: str = "inner",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Join two worksheets on key columns (database-style merge).

    The left worksheet is book_name/sheet_name; the right is
    right_book/right_sheet. Specify the key with on (shared name) or with
    left_on plus right_on; when omitted, shared column names are used. how is
    inner, left, right, outer, or cross. Provide output_book/output_sheet to
    write to a new sheet instead of overwriting the left worksheet.
    """

    return _wrap(
        lambda: _ok(
            "Merged Origin worksheets.",
            **client.merge_worksheets(
                right_book=right_book,
                right_sheet=right_sheet,
                on=on,
                left_on=left_on,
                right_on=right_on,
                how=how,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_concat_worksheets(
    others: list[dict[str, str]],
    axis: str = "rows",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Concatenate the primary worksheet with one or more others.

    The primary worksheet is book_name/sheet_name; others is a list of
    {"book": ..., "sheet": ...}. axis="rows" stacks rows (a SQL UNION ALL,
    aligning by column name); axis="columns" places sheets side by side.
    Provide output_book/output_sheet to write to a new sheet instead of
    overwriting the primary worksheet.
    """

    return _wrap(
        lambda: _ok(
            "Concatenated Origin worksheets.",
            **client.concat_worksheets(
                others=others,
                axis=axis,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_pivot_worksheet(
    index: str | list[str],
    columns: str | list[str],
    values: str | list[str] | None = None,
    aggfunc: str = "mean",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Reshape long data into a wide pivot table.

    index columns stay as rows, the distinct values of columns become new
    column headers, and values are aggregated with aggfunc (mean, sum, count,
    min, max, median, std). Provide output_book/output_sheet to write to a new
    sheet instead of in place.
    """

    return _wrap(
        lambda: _ok(
            "Pivoted Origin worksheet.",
            **client.pivot_worksheet(
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_melt_worksheet(
    id_vars: list[str | int] | None = None,
    value_vars: list[str | int] | None = None,
    var_name: str = "variable",
    value_name: str = "value",
    book_name: str | None = None,
    sheet_name: str | None = None,
    output_book: str | None = None,
    output_sheet: str | None = None,
) -> dict[str, Any]:
    """Reshape wide data into long format (unpivot).

    id_vars columns are kept as identifiers; value_vars columns (default: all
    other columns) are unpivoted into a var_name/value_name column pair. Provide
    output_book/output_sheet to write to a new sheet instead of in place.
    """

    return _wrap(
        lambda: _ok(
            "Melted Origin worksheet.",
            **client.melt_worksheet(
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=var_name,
                value_name=value_name,
                book_name=book_name,
                sheet_name=sheet_name,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )
