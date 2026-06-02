from __future__ import annotations

from pathlib import Path
from typing import Any

from ._shared import (
    _export_inspection,
    _mcp_tool,
    _ok,
    _wrap,
    client,
)
from .plotting_shared import (
    MATRIX_PLOT_TYPE_ID_ROUTES,
    PLOT_TYPE_ID_ROUTES,
    _plot_table_id,
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
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a 3D vector plot from table data."""

    return _pti(path, "vector_3d", selected_cols, graph_name, title, export_path, style_mode)


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
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a 3D waterfall/walls plot from table data."""

    return _pti(path, "waterfall", selected_cols, graph_name, title, export_path, style_mode)


@_mcp_tool()
def origin_plot_3d_ribbon(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a 3D ribbon plot from table data."""

    return _pti(path, "ribbon_3d", selected_cols, graph_name, title, export_path, style_mode)


@_mcp_tool()
def origin_plot_3d_bars(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a 3D bar plot from table data."""

    return _pti(path, "bars_3d", selected_cols, graph_name, title, export_path, style_mode)


@_mcp_tool()
def origin_plot_3d_errorbar(
    path: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a 3D scatter plot with error bars from table data."""

    return _pti(path, "errorbar_3d", selected_cols, graph_name, title, export_path, style_mode)


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


@_mcp_tool()
def origin_plot(
    path: str,
    kind: str,
    selected_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    export_path: str | None = None,
    style_mode: str = "origin_default",
) -> dict[str, Any]:
    """Create a table-based plot selected by ``kind``.

    A single parameterized entry point for the table plot kinds that each also
    have a dedicated ``origin_plot_*`` tool, so the compact tool profile can
    reach every kind without enabling the full profile. ``kind`` must be one of:
    area, stack_area, fill_area, bar, stack_bar, floating_bar, column_stack,
    pie, ternary, ternary_contour, bubble, bubble_color_mapped, color_mapped,
    vector_xyam, vector_xyxy, vector_3d, high_low_close, candlestick, waterfall,
    ribbon_3d, bars_3d, errorbar_3d, polar_xr_ytheta, smith, dendrogram. For
    line/scatter/column/histogram/box use the dedicated tools; for matrix-range
    plots use origin_plot_matrix_id.
    """

    def run() -> dict[str, Any]:
        if kind not in PLOT_TYPE_ID_ROUTES:
            valid = ", ".join(sorted(PLOT_TYPE_ID_ROUTES))
            raise ValueError(f"Unknown plot kind: {kind!r}. Valid kinds: {valid}.")
        return _pti(path, kind, selected_cols, graph_name, title, export_path, style_mode)

    return _wrap(run)


def _plot_matrix_route(
    data_range: str,
    route: str,
    graph_name: str | None,
    title: str | None,
    export_path: str | None,
) -> dict[str, Any]:
    plot_type_id, template = MATRIX_PLOT_TYPE_ID_ROUTES[route]
    return origin_plot_matrix_id(data_range, plot_type_id, template, graph_name, title, export_path)
