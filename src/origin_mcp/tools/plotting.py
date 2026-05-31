from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.models import (
    PlotKind,
    PlotStyleMode,
    PlotTableRequest,
)

from ._shared import (
    _export_inspection,
    _mcp_tool,
    _ok,
    _wrap,
    client,
)

PLOT_TYPE_ID_ROUTES: dict[str, tuple[int, str]] = {
    "area": (204, "area"),
    "stack_area": (214, "stackarea"),
    "fill_area": (249, "fillarea"),
    "bar": (215, "bar"),
    "stack_bar": (216, "bar"),
    "floating_bar": (207, "floatbar"),
    "column_stack": (213, "column"),
    "pie": (225, "pie"),
    "ternary": (245, "ternary"),
    "ternary_contour": (185, "TernaryContour"),
    "bubble": (193, "scatter"),
    "bubble_color_mapped": (248, "scatter"),
    "color_mapped": (247, "scatter"),
    "vector_xyam": (208, "vector"),
    "vector_xyxy": (218, "vectxyxy"),
    "vector_3d": (183, "gl3DVector"),
    "high_low_close": (205, "hclose"),
    "candlestick": (221, "Candlestick"),
    "waterfall": (210, "walls"),
    "ribbon_3d": (211, "ribbon"),
    "bars_3d": (212, "bar3d"),
    "errorbar_3d": (184, "gl3DError"),
    "polar_xr_ytheta": (186, "PolarXrYTheta"),
    "smith": (191, "SmithCht"),
    "dendrogram": (108, "Cluster"),
}

MATRIX_PLOT_TYPE_ID_ROUTES: dict[str, tuple[int, str]] = {
    "scatter_3d": (101, "gl3DScatterMat"),
    "surface_3d": (103, "glmesh"),
    "heatmap": (105, "heatmap"),
    "contour": (226, "contour"),
    "image": (220, "image"),
}


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


@_mcp_tool()
def origin_plot_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an area plot from table data."""

    return _pti(path, "area", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_stack_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a stacked area plot from table data."""

    return _pti(path, "stack_area", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_fill_area(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a fill area plot from table data."""

    return _pti(path, "fill_area", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a horizontal bar plot from table data."""

    return _pti(path, "bar", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_stack_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a stacked bar plot from table data."""

    return _pti(path, "stack_bar", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_floating_bar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a floating bar plot from table data."""

    return _pti(path, "floating_bar", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_column_stack(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a column stack plot from table data."""

    return _pti(path, "column_stack", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_pie(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a pie chart from table data."""

    return _pti(path, "pie", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_ternary(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a ternary plot from XYZ table data."""

    return _pti(path, "ternary", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_ternary_contour(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a ternary contour plot from table data."""

    return _pti(path, "ternary_contour", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_bubble(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a bubble plot from table data."""

    return _pti(path, "bubble", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_bubble_color_mapped(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a bubble and color-mapped plot from table data."""

    return _pti(path, "bubble_color_mapped", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_color_mapped(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a color-mapped scatter plot from table data."""

    return _pti(path, "color_mapped", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_vector_xyam(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an XYAM vector plot from table data."""

    return _pti(path, "vector_xyam", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_vector_xyxy(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an XYXY vector plot from table data."""

    return _pti(path, "vector_xyxy", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_3d_vector(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D vector plot from table data."""

    return _pti(path, "vector_3d", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_high_low_close(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a high-low-close plot from table data."""

    return _pti(path, "high_low_close", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_candlestick(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an OHLC/candlestick chart from table data."""

    return _pti(path, "candlestick", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_waterfall(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D waterfall/walls plot from table data."""

    return _pti(path, "waterfall", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_3d_ribbon(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D ribbon plot from table data."""

    return _pti(path, "ribbon_3d", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_3d_bars(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D bar plot from table data."""

    return _pti(path, "bars_3d", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_3d_errorbar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D scatter plot with error bars from table data."""

    return _pti(path, "errorbar_3d", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_polar_xr_ytheta(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a polar X(R) Y(Theta) plot from table data."""

    return _pti(path, "polar_xr_ytheta", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_smith(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a Smith chart from table data."""

    return _pti(path, "smith", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_dendrogram(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a dendrogram plot from table data."""

    return _pti(path, "dendrogram", selected_cols, graph_name, title, export_path)


@_mcp_tool()
def origin_plot_matrix_3d_scatter(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D scatter plot from an existing Origin matrix range."""

    return _plot_matrix_route(data_range, "scatter_3d", graph_name, title, export_path)


@_mcp_tool()
def origin_plot_matrix_3d_surface(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a 3D surface plot from an existing Origin matrix range."""

    return _plot_matrix_route(data_range, "surface_3d", graph_name, title, export_path)


@_mcp_tool()
def origin_plot_matrix_heatmap(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a heatmap from an existing Origin matrix range."""

    return _plot_matrix_route(data_range, "heatmap", graph_name, title, export_path)


@_mcp_tool()
def origin_plot_matrix_contour(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a contour plot from an existing Origin matrix range."""

    return _plot_matrix_route(data_range, "contour", graph_name, title, export_path)


@_mcp_tool()
def origin_plot_image(
    data_range: str,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create an image plot from an existing Origin matrix range."""

    return _plot_matrix_route(data_range, "image", graph_name, title, export_path)


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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
    palette_name: str | None = None,
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
                palette_name=palette_name,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )


@_mcp_tool()
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


@_mcp_tool()
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
    palette_name: str | None = None,
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
                palette_name=palette_name,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )


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
    bar_gap: float | None = None,
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
        if bar_gap is not None:
            client.set_plot_style(graph_name=graph.graph_name, bar_gap=bar_gap)
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
    palette_name: str | None = None,
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
            palette_name=palette_name,
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
    route: str,
    selected_cols: list[str | int] | None,
    graph_name: str | None,
    title: str | None,
    export_path: str | None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    plot_type_id, template = PLOT_TYPE_ID_ROUTES[route]
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


def _plot_matrix_route(
    data_range: str,
    route: str,
    graph_name: str | None,
    title: str | None,
    export_path: str | None,
) -> dict[str, Any]:
    plot_type_id, template = MATRIX_PLOT_TYPE_ID_ROUTES[route]
    return origin_plot_matrix_id(data_range, plot_type_id, template, graph_name, title, export_path)
