from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.chart_palette import palette_catalog
from origin_mcp.models import (
    AxisSettingsRequest,
    GraphFormatRequest,
    PlotStyleRequest,
    ProjectObjectRequest,
)

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_palette_catalog() -> dict[str, Any]:
    """List built-in palette names, semantic roles, and source links."""

    return _wrap(lambda: _ok("Listed Origin MCP palettes.", palettes=palette_catalog()))


@_mcp_tool()
def origin_list_graph_templates(template_dir: str | None = None) -> dict[str, Any]:
    """List common graph template names and optional template files in a directory."""

    return _wrap(
        lambda: _ok(
            "Listed Origin graph templates.",
            **client.list_graph_templates(Path(template_dir) if template_dir else None),
        )
    )


@_mcp_tool()
def origin_get_graph_info(graph_name: str | None = None) -> dict[str, Any]:
    """Inspect a graph page, its layers, axes, and plots."""

    return _wrap(
        lambda: _ok(
            "Collected Origin graph information.",
            **client.get_graph_info(graph_name=graph_name),
        )
    )


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
def origin_inspect_export(path: str) -> dict[str, Any]:
    """Inspect an exported graph file for size, dimensions, hash, and image quality."""

    return _wrap(
        lambda: _ok(
            "Inspected exported graph file.",
            **client.inspect_export(Path(path)),
        )
    )


@_mcp_tool()
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


@_mcp_tool()
def origin_set_axis(
    graph_name: str | None = None,
    layer_index: int = 0,
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
            layer_index=layer_index,
            axis=axis,
            scale=scale,
            start=start,
            end=end,
            step=step,
            title=title,
        )
        return _ok("Updated Origin graph axis.", **client.set_axis(**req.model_dump()))

    return _wrap(run)


@_mcp_tool()
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


@_mcp_tool()
def origin_apply_nature_style(
    graph_name: str | None = None,
    layer_index: int | None = None,
    chart_type: str | None = None,
    page_width: float | None = None,
    page_height: float | None = None,
    font_family: str = "Arial",
    axis_title_size: int = 10,
    tick_label_size: int = 9,
    legend_font_size: int = 18,
    line_width: float = 3.0,
    symbol_size: float = 4.5,
    tick_length: int = 3,
    show_legend: bool = True,
    palette_role: str | None = None,
    palette_name: str | None = None,
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
                palette_name=palette_name,
                run_diagnostics=run_diagnostics,
            ),
        )
    )


@_mcp_tool()
def origin_diagnose_graph(
    graph_name: str | None = None,
    style: str | None = None,
    palette_role: str | None = None,
    palette_name: str | None = None,
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
                palette_name=palette_name,
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
def origin_list_project() -> dict[str, Any]:
    """List workbooks, worksheets, matrix books, graphs, and images in the project."""

    return _wrap(lambda: _ok("Listed Origin project objects.", **client.list_project()))


@_mcp_tool()
def origin_rename_object(name: str, new_name: str, object_type: str = "graph") -> dict[str, Any]:
    """Rename a graph, workbook, matrixbook, or worksheet."""

    def run() -> dict[str, Any]:
        req = ProjectObjectRequest(name=name, object_type=object_type)
        return _ok(
            "Renamed Origin object.",
            **client.rename_object(req.name, new_name=new_name, object_type=req.object_type),
        )

    return _wrap(run)


@_mcp_tool()
def origin_delete_object(name: str, object_type: str = "graph") -> dict[str, Any]:
    """Delete a graph, workbook, matrixbook, or worksheet."""

    def run() -> dict[str, Any]:
        req = ProjectObjectRequest(name=name, object_type=object_type)
        return _ok(
            "Deleted Origin object.",
            **client.delete_object(req.name, object_type=req.object_type),
        )

    return _wrap(run)
