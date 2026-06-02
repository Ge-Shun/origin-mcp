from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Image

from origin_mcp.chart_palette import palette_catalog
from origin_mcp.client.graph_style import (
    NATURE_ANNOTATION_FONT_SIZE,
    NATURE_AXIS_TITLE_SIZE,
    NATURE_LEGEND_FONT_SIZE,
    NATURE_TICK_LABEL_SIZE,
)
from origin_mcp.models import (
    AxisSettingsRequest,
    GraphFormatRequest,
    PlotStyleRequest,
    ProjectObjectRequest,
)
from origin_mcp.plot_style_registry import (
    all_plot_style_capabilities,
    plot_style_capabilities,
    resolve_plot_style_capability,
)

from ._shared import (
    _error,
    _mcp_tool,
    _ok,
    _wrap,
    client,
)

_SET_PLOT_STYLE_PROPERTIES = {
    "color": "color",
    "line_width": "line_width",
    "bar_gap": "bar_gap",
    "line_style": "line_style",
    "symbol_kind": "symbol_kind",
    "symbol_size": "symbol_size",
    "transparency": "transparency",
    "bar_border_width": "line_width",
    "errorbar_width": "line_width",
    "three_d_symbol_size": "symbol_size",
}
_IMAGE_PANEL_STYLE_PROPERTIES = {
    "panel_label",
    "channel_label",
    "scale_bar_label",
    "dynamic_range_label",
    "dark_panel",
    "font_size",
    "run_diagnostics",
}


@_mcp_tool()
def origin_palette_catalog(
    palette_name: str | None = None,
    colors_count: int | None = None,
    min_colors: int | None = None,
    max_colors: int | None = None,
    family: str | None = None,
    include_colors: bool = False,
    limit: int | None = 50,
) -> dict[str, Any]:
    """List built-in palette names, semantic roles, and source links."""

    return _wrap(
        lambda: _ok(
            "Listed Origin MCP palettes.",
            palettes=palette_catalog(
                palette_name=palette_name,
                colors_count=colors_count,
                min_colors=min_colors,
                max_colors=max_colors,
                family=family,
                include_colors=include_colors,
                limit=limit,
            ),
        )
    )


@_mcp_tool()
def origin_plot_style_capabilities(
    chart_type: str | None = None,
    plot_type_id: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """List semantic plot style controls by chart type, Plot Type ID, or term."""

    return _wrap(
        lambda: _ok(
            "Listed Origin MCP plot style capabilities.",
            **plot_style_capabilities(
                chart_type=chart_type,
                plot_type_id=plot_type_id,
                query=query,
            ),
        )
    )


@_mcp_tool()
def origin_plot_style_setter_coverage(
    chart_type: str | None = None,
    plot_type_id: int | None = None,
) -> dict[str, Any]:
    """Report which implemented style registry entries have executable safe setters."""

    return _wrap(
        lambda: _ok(
            "Collected Origin MCP plot style setter coverage.",
            **_plot_style_setter_coverage(chart_type=chart_type, plot_type_id=plot_type_id),
        )
    )


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


@_mcp_tool(structured_output=False)
def origin_view_graph(graph_name: str | None = None, max_width: int = 1600) -> list[Any]:
    """Render an Origin graph and return it as an image the model can see.

    Unlike ``origin_export_graph`` this leaves no file behind: the graph is
    rendered to a temporary PNG, returned as an image content block alongside a
    small text summary, and the temp file is deleted. Use it to visually verify
    a plot and iterate on it. ``max_width`` bounds the rendered pixel width to
    keep the returned image (and its token cost) small. Requires a
    vision-capable client to be useful.
    """

    try:
        result = client.render_graph_png(graph_name=graph_name, max_width=max_width)
    except Exception as exc:  # noqa: BLE001 - classified and reported below
        return [_error(exc)]
    image_b64 = result.pop("image_base64", None)
    if not isinstance(image_b64, str) or not image_b64:
        return [_error(RuntimeError("Origin returned no preview image."))]
    try:
        png = base64.b64decode(image_b64)
    except (ValueError, TypeError) as exc:
        return [_error(exc)]
    summary = _ok("Rendered Origin graph preview.", **result)
    return [summary, Image(data=png, format="png")]


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
def origin_set_axis_break(
    break_from: float | None = None,
    break_to: float | None = None,
    axis: str = "x",
    graph_name: str | None = None,
    layer_index: int = 0,
    position: float | None = None,
    post_break_increment: float | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Add or remove an axis break on a graph axis.

    Hides the range between break_from and break_to on the chosen axis ("x" or
    "y"), so data on either side is shown closer together. position is the
    break location as a percent of the axis length; post_break_increment sets
    the tick spacing after the break. Pass enabled=false to remove the break.
    """

    return _wrap(
        lambda: _ok(
            "Updated Origin axis break.",
            **client.set_axis_break(
                break_from=break_from,
                break_to=break_to,
                axis=axis,
                graph_name=graph_name,
                layer_index=layer_index,
                position=position,
                post_break_increment=post_break_increment,
                enabled=enabled,
            ),
        )
    )


@_mcp_tool()
def origin_set_plot_style(
    graph_name: str | None = None,
    layer_index: int = 0,
    plot_index: int | None = None,
    color: str | tuple[int, int, int] | None = None,
    line_width: float | None = None,
    bar_gap: float | None = None,
    line_style: int | None = None,
    symbol_kind: int | None = None,
    symbol_size: float | None = None,
    transparency: float | None = None,
) -> dict[str, Any]:
    """Set line, color, symbol, column/bar gap, and transparency style on plots."""

    def run() -> dict[str, Any]:
        req = PlotStyleRequest(
            graph_name=graph_name,
            layer_index=layer_index,
            plot_index=plot_index,
            color=color,
            line_width=line_width,
            bar_gap=bar_gap,
            line_style=line_style,
            symbol_kind=symbol_kind,
            symbol_size=symbol_size,
            transparency=transparency,
        )
        return _ok("Updated Origin plot style.", **client.set_plot_style(**req.model_dump()))

    return _wrap(run)


@_mcp_tool()
def origin_set_plot_property(
    property_name: str,
    value: Any,
    graph_name: str | None = None,
    layer_index: int = 0,
    plot_index: int | None = None,
    chart_type: str | None = None,
    plot_type_id: int | None = None,
) -> dict[str, Any]:
    """Set one registry-backed plot style property if it is implemented."""

    def run() -> dict[str, Any]:
        resolved = resolve_plot_style_capability(
            property_name=property_name,
            chart_type=chart_type,
            plot_type_id=plot_type_id,
        )
        capability = resolved["capability"]
        route = _plot_style_dispatch_route(capability)
        if capability["status"] != "implemented" or route is None:
            alternatives = [
                item
                for item in resolved["capabilities"]
                if item["status"] == "implemented" and _plot_style_dispatch_route(item)
            ]
            return _ok(
                "Plot style property is known but not implemented as a safe setter.",
                applied=False,
                requested_property=property_name,
                value=value,
                capability=capability,
                alternatives=alternatives,
                chart_type=resolved["chart_type"],
                plot_type=resolved["plot_type"],
                loaded_sources=resolved["loaded_sources"],
            )
        result = _apply_plot_property_route(
            route=route,
            value=value,
            graph_name=graph_name,
            layer_index=layer_index,
            plot_index=plot_index,
            chart_type=resolved["chart_type"],
        )
        return _ok(
            "Updated Origin plot style property.",
            applied=True,
            requested_property=property_name,
            property_name=capability["name"],
            value=value,
            capability=capability,
            route=route,
            chart_type=resolved["chart_type"],
            plot_type=resolved["plot_type"],
            loaded_sources=resolved["loaded_sources"],
            result=result,
        )

    return _wrap(run)


def _plot_style_dispatch_route(capability: dict[str, Any]) -> dict[str, str] | None:
    if capability.get("status") != "implemented" or not capability.get("setter"):
        return None
    name = str(capability["name"])
    target_kwarg = _SET_PLOT_STYLE_PROPERTIES.get(name)
    if target_kwarg:
        return {"tool": "origin_set_plot_style", "kwarg": target_kwarg}
    if name == "palette_name":
        return {"tool": "origin_apply_nature_style", "kwarg": "palette_name"}
    if name == "image_panel_annotations":
        return {"tool": "origin_apply_image_panel_style", "kwarg": "annotations"}
    return None


def _apply_plot_property_route(
    route: dict[str, str],
    value: Any,
    graph_name: str | None,
    layer_index: int,
    plot_index: int | None,
    chart_type: str | None,
) -> dict[str, Any]:
    if route["tool"] == "origin_set_plot_style":
        return client.set_plot_style(
            graph_name=graph_name,
            layer_index=layer_index,
            plot_index=plot_index,
            **{route["kwarg"]: value},
        )
    if plot_index is not None:
        raise ValueError(f"plot_index is not supported by {route['tool']}.")
    if route["tool"] == "origin_apply_nature_style":
        return client.apply_nature_style(
            graph_name=graph_name,
            layer_index=layer_index,
            chart_type=chart_type,
            palette_name=value,
        )
    if route["tool"] == "origin_apply_image_panel_style":
        return client.apply_image_panel_style(
            graph_name=graph_name,
            layer_index=layer_index,
            **_image_panel_style_kwargs(value),
        )
    raise ValueError(f"Unsupported plot style route: {route['tool']}.")


def _image_panel_style_kwargs(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            "image_panel_annotations value must be an object with keys such as "
            "panel_label, channel_label, scale_bar_label, dynamic_range_label, "
            "dark_panel, or font_size."
        )
    unknown = sorted(str(key) for key in value if str(key) not in _IMAGE_PANEL_STYLE_PROPERTIES)
    if unknown:
        supported = ", ".join(sorted(_IMAGE_PANEL_STYLE_PROPERTIES))
        raise ValueError(
            f"Unsupported image panel annotation keys: {unknown}. Supported: {supported}."
        )
    if not value:
        raise ValueError("image_panel_annotations value must include at least one setting.")
    return {str(key): item for key, item in value.items()}


def _plot_style_setter_coverage(
    chart_type: str | None = None,
    plot_type_id: int | None = None,
) -> dict[str, Any]:
    if chart_type is None and plot_type_id is None:
        capabilities = [item.as_dict() for item in all_plot_style_capabilities()]
        loaded_sources: list[str] | None = None
        normalized_chart = None
        plot_type = None
    else:
        result = plot_style_capabilities(chart_type=chart_type, plot_type_id=plot_type_id)
        capabilities = result["capabilities"]
        loaded_sources = result["loaded_sources"]
        normalized_chart = result["chart_type"]
        plot_type = result["plot_type"]

    implemented = [
        item for item in capabilities if item["status"] == "implemented" and item.get("setter")
    ]
    executable = [
        {**item, "route": _plot_style_dispatch_route(item)}
        for item in implemented
        if _plot_style_dispatch_route(item) is not None
    ]
    unhandled = [item for item in implemented if _plot_style_dispatch_route(item) is None]
    planned = [item for item in capabilities if item["status"] == "planned"]
    return {
        "chart_type": normalized_chart,
        "plot_type": plot_type,
        "loaded_sources": loaded_sources,
        "total_capabilities": len(capabilities),
        "implemented_count": len(implemented),
        "executable_count": len(executable),
        "planned_count": len(planned),
        "unhandled_implemented_count": len(unhandled),
        "executable": executable,
        "unhandled_implemented": unhandled,
        "planned": planned,
    }


@_mcp_tool()
def origin_apply_nature_style(
    graph_name: str | None = None,
    layer_index: int | None = None,
    chart_type: str | None = None,
    page_width: float | None = None,
    page_height: float | None = None,
    font_family: str = "Arial",
    axis_title_size: int = NATURE_AXIS_TITLE_SIZE,
    tick_label_size: int = NATURE_TICK_LABEL_SIZE,
    legend_font_size: int = NATURE_LEGEND_FONT_SIZE,
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
    font_size: int = NATURE_ANNOTATION_FONT_SIZE,
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
def origin_add_inset(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    graph_name: str | None = None,
    left: float = 55.0,
    top: float = 12.0,
    width: float = 35.0,
    height: float = 35.0,
    plot_type: str = "line",
    x_start: float | None = None,
    x_end: float | None = None,
    y_start: float | None = None,
    y_end: float | None = None,
) -> dict[str, Any]:
    """Add an inset (small embedded layer) to an existing graph.

    A new layer is placed inside the graph at left/top with width/height (all
    percentages of the page) and the worksheet x_col/y_cols are plotted into it.
    Give x_start/x_end and/or y_start/y_end to zoom the inset to a sub-range
    (useful for a magnified detail view); otherwise the inset auto-scales.
    """

    return _wrap(
        lambda: _ok(
            "Added inset layer to Origin graph.",
            **client.add_inset_layer(
                worksheet=worksheet,
                x_col=x_col,
                y_cols=y_cols,
                graph_name=graph_name,
                left=left,
                top=top,
                width=width,
                height=height,
                plot_type=plot_type,
                x_start=x_start,
                x_end=x_end,
                y_start=y_start,
                y_end=y_end,
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
    font_family: str | None = None,
    show_frame: bool | None = None,
    left: int | None = None,
    top: int | None = None,
    position: str | None = None,
    margin_percent: float = 2.0,
    coordinate_mode: str = "auto",
) -> dict[str, Any]:
    """Format the graph legend text, font, font size, frame, and optional position."""

    return _wrap(
        lambda: _ok(
            "Formatted Origin graph legend.",
            **client.format_legend(
                graph_name=graph_name,
                text=text,
                font_size=font_size,
                font_family=font_family,
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
