from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.models import PlotKind

from ._shared import _export_inspection, _mcp_tool, _ok, _wrap, client
from .plotting_shared import _plot_csv, _plot_table_id


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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
    bar_gap: float | None = None,
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
        bar_gap=bar_gap,
        show_legend=show_legend,
        style_mode=style_mode,
        export_path=export_path,
    )


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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

    def run() -> dict[str, Any]:
        result = _plot_table_id(
            path=path,
            plot_type_id=219,
            template=template or "hist",
            selected_cols=y_cols or ([x_col] if x_col is not None else None),
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
        _apply_plot_id_legend_visibility(result, show_legend)
        return result

    return run()


def _apply_plot_id_legend_visibility(result: dict[str, Any], show_legend: bool) -> None:
    if not result.get("ok"):
        return
    graph_data = result.get("data", {}).get("graph", {})
    graph_name = graph_data.get("graph_name")
    if graph_name:
        client.format_graph(graph_name=graph_name, show_legend=show_legend, rescale=False)


@_mcp_tool()
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

    result = _plot_table_id(
        path=path,
        plot_type_id=206,
        template=template or "box",
        selected_cols=y_cols or ([x_col] if x_col is not None else None),
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
    _apply_plot_id_legend_visibility(result, show_legend)
    return result


@_mcp_tool()
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
    palette_name: str | None = None,
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
        palette_name=palette_name,
        export_path=export_path,
    )


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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
    palette_name: str | None = None,
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


@_mcp_tool()
def origin_plot_dual_y(
    path: str,
    x_col: str | int | None = None,
    y1_cols: list[str | int] | None = None,
    y2_cols: list[str | int] | None = None,
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
    y1_label: str | None = None,
    y2_label: str | None = None,
    plot_type: str = "line",
    style_mode: str = "origin_default",
    export_path: str | None = None,
) -> dict[str, Any]:
    """Import table data and create a double-Y (two Y axes) graph.

    y1_cols are plotted against the left Y axis (layer 1) and y2_cols against
    the right Y axis (layer 2), sharing one X axis. Both lists are required.
    plot_type is "line", "scatter", "line_symbol", or "column".
    """

    def run() -> dict[str, Any]:
        worksheet, graph = client.plot_dual_y(
            path=Path(path),
            x_col=x_col,
            y1_cols=y1_cols,
            y2_cols=y2_cols,
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
            y1_label=y1_label,
            y2_label=y2_label,
            plot_type=plot_type,
            style_mode=style_mode,
            export_path=Path(export_path) if export_path else None,
        )
        return _ok(
            "Created double-Y plot from table data.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            export_inspection=_export_inspection(graph.as_dict()),
        )

    return _wrap(run)
