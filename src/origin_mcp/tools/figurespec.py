from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.client.graph_style import NATURE_ANNOTATION_FONT_SIZE
from origin_mcp.file_io import read_table
from origin_mcp.models import FigureExportFormatSpec, FigureSpec

from ._shared import _mcp_tool, _ok, _wrap, client

SUPPORTED_PLOT_TYPES = {
    "line",
    "scatter",
    "line_symbol",
    "column",
    "histogram",
    "box",
    "contour",
    "heatmap",
}
SUPPORTED_LAYOUTS = {"single", "grid", "custom", "inset", "dual_y"}
SUPPORTED_UNCERTAINTY_KEYS = {
    "error",
    "y_error",
    "y_error_col",
    "yerr",
    "x_error",
    "x_error_col",
    "xerr",
    "lower",
    "lower_col",
    "upper",
    "upper_col",
    "fill_color",
    "color",
    "transparency",
    "type",
    "kind",
}
SUPPORTED_UNCERTAINTY_KINDS = {
    "band",
    "confidence_band",
    "errorbar",
    "error_bar",
    "symmetric",
    "standard_error",
    "uncertainty_band",
}
GROUP_STYLE_SEQUENCE_KEYS = {
    "colors": "color",
    "line_widths": "line_width",
    "bar_gaps": "bar_gap",
    "line_styles": "line_style",
    "symbol_kinds": "symbol_kind",
    "symbol_sizes": "symbol_size",
    "transparencies": "transparency",
    "colormaps": "colormap",
    "contour_level_sets": "contour_levels",
    "contour_minor_level_counts": "contour_minor_levels",
    "color_scale_ranges": "color_scale_limits",
    "histogram_bin_widths": "histogram_bin_width",
    "errorbar_caps": "errorbar_cap",
    "box_widths": "box_width",
}
GROUP_STYLE_DIRECT_KEYS = {
    "color",
    "line_width",
    "bar_gap",
    "line_style",
    "symbol_kind",
    "symbol_size",
    "transparency",
    "colormap",
    "contour_minor_levels",
    "histogram_bin_width",
    "errorbar_cap",
    "box_width",
}
GROUP_STYLE_VECTOR_DIRECT_KEYS = {"contour_levels", "color_scale_limits"}
SUPPORTED_GROUP_STYLE_KEYS = {
    "series",
    *GROUP_STYLE_SEQUENCE_KEYS,
    *GROUP_STYLE_DIRECT_KEYS,
    *GROUP_STYLE_VECTOR_DIRECT_KEYS,
}


@_mcp_tool()
def origin_plan_figure_spec(spec: FigureSpec) -> dict[str, Any]:
    """Validate a declarative FigureSpec and return the planned Origin operations."""

    return _wrap(
        lambda: _ok("Planned FigureSpec.", **_plan_figure(FigureSpec.model_validate(spec)))
    )


@_mcp_tool()
def origin_execute_figure_spec(
    spec: FigureSpec,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute a declarative FigureSpec.

    The current executor supports worksheet-backed single-panel and grid
    multi-panel figures with common plot types. Unsupported features are
    reported in the plan instead of being guessed.
    """

    def run() -> dict[str, Any]:
        figure_spec = FigureSpec.model_validate(spec)
        plan = _plan_figure(figure_spec)
        if dry_run:
            return _ok("Planned FigureSpec.", **plan)
        if not plan["executor_executable"]:
            return _ok(
                "FigureSpec is valid but this executor cannot run it yet.",
                **plan,
                executed=False,
            )
        result = _execute_figure(figure_spec, plan)
        return _ok("Executed FigureSpec.", **result)

    return _wrap(run)


def _plan_figure(spec: FigureSpec) -> dict[str, Any]:
    data_validation = _validate_data_columns(spec)
    warning_details = _executor_warning_details(spec)
    warnings = _executor_warnings_from_details(warning_details)
    operations: list[dict[str, Any]] = []

    if spec.runtime.new_project:
        operations.append({"op": "new_project", "show_origin": spec.runtime.show_origin})

    for item in spec.data:
        operations.append(
            {
                "op": "load_data",
                "id": item.id,
                "source": str(item.source),
                "object": item.object,
                "roles": item.roles,
            }
        )

    if spec.page.layout == "dual_y":
        operations.append(_dual_y_plan(spec))

    for layer in spec.layers:
        operations.append(
            {
                "op": "configure_layer",
                "id": layer.id,
                "data_ref": layer.data_ref,
                "x": layer.x.model_dump(exclude_none=True),
                "y": layer.y.model_dump(exclude_none=True),
                "z": layer.z.model_dump(exclude_none=True),
                "panel_tag": layer.panel_tag,
                "grid_cell": layer.grid_cell,
                "grid_span": layer.grid_span,
                "position_mode": layer.position_mode,
                "position": layer.position,
            }
        )

    for plot in spec.plots:
        uncertainty_unsupported_keys = _unsupported_uncertainty_keys(plot.uncertainty)
        group_style_unsupported_keys = _unsupported_group_style_keys(plot.group_style)
        uncertainty_supported = not uncertainty_unsupported_keys and _band_executor_supported(
            spec, plot
        )
        operations.append(
            {
                "op": "plot",
                "id": plot.id,
                "type": _normalize_plot_type(plot.type),
                "layer": plot.layer,
                "data_ref": _plot_data_ref(spec, plot),
                "map": plot.map,
                "uncertainty": plot.uncertainty,
                "uncertainty_mapping": _uncertainty_mapping(plot),
                "uncertainty_style": _uncertainty_style(plot),
                "uncertainty_supported": uncertainty_supported,
                "uncertainty_unsupported_keys": uncertainty_unsupported_keys,
                "group_style": plot.group_style,
                "group_style_supported": not group_style_unsupported_keys
                and not bool(plot.map.get("group")),
                "group_style_supported_keys": sorted(SUPPORTED_GROUP_STYLE_KEYS),
                "group_style_unsupported_keys": group_style_unsupported_keys,
            }
        )

    page_setup = _page_setup_plan(spec)
    if page_setup:
        operations.append({"op": "set_graph_page", **page_setup})

    if spec.page.layout in {"grid", "custom", "inset"} and len(spec.layers) > 1:
        rows, columns = _grid_shape(spec)
        arrange_op = {"op": "arrange_layers", "rows": rows, "columns": columns}
        arrange_op.update(_layout_spacing_plan(spec))
        if spec.page.layout in {"custom", "inset"}:
            arrange_op["layer_geometries"] = _layer_geometries(spec, rows, columns)
        operations.append(arrange_op)

    for annotation in spec.annotations:
        operations.append(
            {
                "op": "annotate",
                "id": annotation.id,
                "type": annotation.type,
                "layer": annotation.layer,
                "text": annotation.text,
                "location": annotation.location,
            }
        )

    for path in _export_paths(spec):
        operations.append({"op": "export_graph", "path": str(path)})

    project_path = _project_path(spec)
    if spec.runtime.save_project or project_path:
        operations.append(
            {"op": "save_project", "path": str(project_path) if project_path else None}
        )

    qa = spec.export.qa
    if qa:
        operations.append({"op": "qa", "requirements": qa})

    executable = not warnings
    return {
        "figure_id": spec.figure.id,
        "title": spec.figure.title,
        "executor_executable": executable,
        "warnings": warnings,
        "warning_details": warning_details,
        "data_validation": data_validation,
        "operations": operations,
        "exports": [str(path) for path in _export_paths(spec)],
        "project_path": str(project_path) if project_path else None,
    }


def _execute_figure(spec: FigureSpec, plan: dict[str, Any]) -> dict[str, Any]:
    layer_indexes = {layer.id: index for index, layer in enumerate(spec.layers)}
    base_plot = _base_plot(spec)
    base_layer = _layer_by_id(spec, base_plot.layer)
    base_data = _data_by_id(spec, _plot_data_ref(spec, base_plot))
    worksheet_refs: dict[str, Any] = {}

    if spec.runtime.new_project:
        client.new_project(show=spec.runtime.show_origin)

    worksheet, graph, command = _create_base_graph(spec, base_data, base_layer, base_plot)
    if _uncertainty_band_mapping(base_plot):
        worksheet_refs[base_data.id] = client.import_table(**_import_kwargs(base_data))
    else:
        worksheet_refs[base_data.id] = worksheet
    graph_data = graph.as_dict()
    graph_name = graph_data.get("graph_name")

    for data in spec.data:
        if data.id not in worksheet_refs:
            worksheet_refs[data.id] = client.import_table(**_import_kwargs(data))

    if spec.page.layout == "dual_y":
        layer_setup = {
            "page": _apply_page_setup(spec, graph_name),
            "added_layers": 0,
            "arranged": {"layout": "dual_y", "template": "doubleY"},
        }
        band_updates: list[dict[str, Any]] = []
        added_plots = _dual_y_precreated_plots(spec)
    else:
        layer_setup = _ensure_layers_and_layout(spec, graph_name)
        band_updates = _add_uncertainty_bands(
            spec,
            graph_name,
            layer_indexes,
            worksheet_refs,
            base_plot,
        )
        added_plots, additional_band_updates = _add_remaining_plots(
            spec, graph_name, layer_indexes, worksheet_refs, base_plot
        )
        band_updates.extend(additional_band_updates)

    axis_updates = []
    for layer in spec.layers:
        axis_updates.extend(_apply_axis_specs(graph_name, layer, layer_indexes[layer.id]))
    style_updates = _apply_plot_styles(spec, graph_name, layer_indexes, base_plot)
    annotation_results = _apply_annotations(spec, graph_name, layer_indexes)
    export_inspections = _export_outputs(spec, graph_data, graph_name)
    saved_project = _save_project_if_requested(spec)
    diagnostics = _diagnose_if_requested(spec, graph_name)

    return {
        **plan,
        "executed": True,
        "worksheets": {data_id: ref.as_dict() for data_id, ref in worksheet_refs.items()},
        "worksheet": worksheet.as_dict(),
        "graph": graph_data,
        "command": command,
        "layer_setup": layer_setup,
        "band_updates": band_updates,
        "added_plots": added_plots,
        "axis_updates": axis_updates,
        "style_updates": style_updates,
        "annotations": annotation_results,
        "export_inspections": export_inspections,
        "saved_project": saved_project,
        "diagnostics": diagnostics,
    }


def _create_base_graph(
    spec: FigureSpec,
    data: Any,
    layer: Any,
    plot: Any,
) -> tuple[Any, Any, dict[str, Any] | None]:
    plot_type = _normalize_plot_type(plot.type)
    mapping = _plot_mapping(data, plot)

    if spec.page.layout == "dual_y":
        left_layer, right_layer = spec.layers
        left_plots = [item for item in spec.plots if item.layer == left_layer.id]
        right_plots = [item for item in spec.plots if item.layer == right_layer.id]
        left_y = _mapped_y_columns(spec, left_plots)
        right_y = _mapped_y_columns(spec, right_plots)
        worksheet, graph = client.plot_dual_y(
            path=data.source,
            x_col=mapping.get("x"),
            y1_cols=left_y,
            y2_cols=right_y,
            book_name=None,
            sheet_name=None,
            excel_sheet=data.excel_sheet,
            delimiter=data.delimiter,
            encoding=data.encoding,
            header=data.header,
            skiprows=data.skiprows,
            nrows=data.nrows,
            na_values=data.na_values,
            graph_name=spec.figure.id,
            title=spec.figure.title,
            x_label=left_layer.x.title,
            y1_label=left_layer.y.title,
            y2_label=right_layer.y.title,
            plot_type=plot_type,
            style_mode=_style_mode(spec),
            export_path=None,
        )
        return (
            worksheet,
            graph,
            {
                "layout": "dual_y",
                "template": "doubleY",
                "left_y": left_y,
                "right_y": right_y,
            },
        )

    if plot_type == "heatmap":
        worksheet, graph, command = client.plot_table_by_id(
            path=data.source,
            plot_type_id=243,
            template=spec.style.template or "Contour",
            selected_cols=_selected_xyz(mapping),
            book_name=None,
            sheet_name=None,
            excel_sheet=data.excel_sheet,
            delimiter=data.delimiter,
            encoding=data.encoding,
            header=data.header,
            skiprows=data.skiprows,
            nrows=data.nrows,
            na_values=data.na_values,
            graph_name=spec.figure.id,
            title=spec.figure.title or layer.title,
            x_label=layer.x.title,
            y_label=layer.y.title,
            style_mode=_style_mode(spec),
            palette_name=spec.style.palette_name,
            export_path=None,
        )
        return worksheet, graph, command

    band_mapping = _uncertainty_band_mapping(plot)
    if band_mapping:
        band_source, band_columns = _write_band_source(spec, data, plot, mapping, band_mapping)
        worksheet, graph, command = client.plot_table_by_id(
            path=band_source,
            plot_type_id=249,
            template=spec.style.template or "fillarea",
            selected_cols=band_columns[:3],
            book_name=None,
            sheet_name=None,
            excel_sheet=None,
            delimiter=None,
            encoding=None,
            header=data.header,
            skiprows=None,
            nrows=None,
            na_values=None,
            graph_name=spec.figure.id,
            title=spec.figure.title or layer.title,
            x_label=layer.x.title,
            y_label=layer.y.title,
            style_mode=_style_mode(spec),
            palette_name=spec.style.palette_name,
            export_path=None,
        )
        graph_name = graph.as_dict().get("graph_name")
        fill_result = client.run_labtalk(
            _fill_area_script(graph_name, layer_index=0, plot_index=0, **_uncertainty_style(plot))
        )
        y_col = band_columns[3]
        base_plot_result = client.add_plot_to_graph(
            worksheet=_worksheet_ref_expr(worksheet),
            x_col=band_columns[0],
            y_col=y_col,
            graph_name=graph_name,
            layer_index=0,
            plot_type=plot_type,
            z_col=mapping.get("z"),
            y_error_col=mapping.get("error") or mapping.get("y_error"),
            x_error_col=mapping.get("x_error"),
        )
        return (
            worksheet,
            graph,
            {
                **(command or {}),
                "band_fill": fill_result,
                "base_plot": base_plot_result,
            },
        )

    worksheet, graph = client.plot_table(
        path=data.source,
        kind=plot_type,
        x_col=mapping.get("x"),
        y_cols=_y_columns(mapping),
        z_col=mapping.get("z"),
        y_error_col=mapping.get("error") or mapping.get("y_error"),
        x_error_col=mapping.get("x_error"),
        book_name=None,
        sheet_name=None,
        excel_sheet=data.excel_sheet,
        delimiter=data.delimiter,
        encoding=data.encoding,
        header=data.header,
        skiprows=data.skiprows,
        nrows=data.nrows,
        na_values=data.na_values,
        graph_name=spec.figure.id,
        template=spec.style.template,
        title=spec.figure.title or layer.title,
        x_label=layer.x.title,
        y_label=layer.y.title,
        show_legend=_show_legend(spec),
        style_mode=_style_mode(spec),
        palette_name=spec.style.palette_name,
        export_path=None,
    )
    return worksheet, graph, None


def _mapped_y_columns(spec: FigureSpec, plots: list[Any]) -> list[str | int]:
    columns: list[str | int] = []
    for plot in plots:
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        columns.extend(_y_columns(_plot_mapping(data, plot)) or [])
    return columns


def _dual_y_precreated_plots(spec: FigureSpec) -> list[dict[str, Any]]:
    results = []
    for layer_index, layer in enumerate(spec.layers):
        for plot in (item for item in spec.plots if item.layer == layer.id):
            data = _data_by_id(spec, _plot_data_ref(spec, plot))
            for y_col in _y_columns(_plot_mapping(data, plot)) or []:
                results.append(
                    {
                        "plot_id": plot.id,
                        "y_col": y_col,
                        "layer_index": layer_index,
                        "plot_type": _normalize_plot_type(plot.type),
                        "precreated": True,
                    }
                )
    return results


def _dual_y_plan(spec: FigureSpec) -> dict[str, Any]:
    layers = list(spec.layers[:2])
    sides = []
    for side, layer in zip(("left", "right"), layers, strict=False):
        plots = [item for item in spec.plots if item.layer == layer.id]
        sides.append(
            {
                "side": side,
                "layer": layer.id,
                "plots": [item.id for item in plots],
                "y": _mapped_y_columns(spec, plots),
            }
        )
    return {
        "op": "create_dual_y",
        "template": "doubleY",
        "sides": sides,
    }


def _add_remaining_plots(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
    worksheet_refs: dict[str, Any],
    base_plot: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    added = []
    band_updates = []
    for plot in spec.plots:
        if plot.id == base_plot.id:
            continue
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
        band_mapping = _uncertainty_band_mapping(plot)
        if band_mapping:
            result = client.add_uncertainty_band(
                worksheet=_worksheet_ref_expr(worksheet_refs[data.id]),
                x_col=mapping.get("x"),
                lower_col=band_mapping["lower"],
                upper_col=band_mapping["upper"],
                graph_name=graph_name,
                layer_index=layer_indexes[plot.layer],
                **_uncertainty_style(plot),
            )
            band_updates.append({"plot_id": plot.id, **result})
        y_options: list[Any] = list(_y_columns(mapping) or []) or [None]
        for y_col in y_options:
            result = client.add_plot_to_graph(
                worksheet=_worksheet_ref_expr(worksheet_refs[data.id]),
                x_col=mapping.get("x"),
                y_col=y_col,
                graph_name=graph_name,
                layer_index=layer_indexes[plot.layer],
                plot_type=_normalize_plot_type(plot.type),
                z_col=mapping.get("z"),
                y_error_col=mapping.get("error") or mapping.get("y_error"),
                x_error_col=mapping.get("x_error"),
            )
            added.append({"plot_id": plot.id, "y_col": y_col, **result})
    return added, band_updates


def _add_uncertainty_bands(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
    worksheet_refs: dict[str, Any],
    base_plot: Any,
) -> list[dict[str, Any]]:
    updates = []
    for plot in spec.plots:
        band_mapping = _uncertainty_band_mapping(plot)
        if not band_mapping:
            continue
        if plot.id != base_plot.id:
            continue
        if plot.id == base_plot.id:
            updates.append(
                {
                    "plot_id": plot.id,
                    "graph_name": graph_name,
                    "layer_index": layer_indexes[plot.layer],
                    "mode": "native_fillarea_base",
                    "lower_col": band_mapping["lower"],
                    "upper_col": band_mapping["upper"],
                    "plot_indices": [0, 1],
                    **_uncertainty_style(plot),
                }
            )
            continue
    return updates


def _ensure_layers_and_layout(spec: FigureSpec, graph_name: str | None) -> dict[str, Any]:
    layer_count = len(spec.layers)
    page_setup = _apply_page_setup(spec, graph_name)
    added_layers = 0
    if layer_count > 1:
        script = _add_layers_script(graph_name, layer_count - 1)
        if script:
            client.run_labtalk(script)
            added_layers = layer_count - 1

    arranged = None
    if spec.page.layout in {"grid", "custom", "inset"} and layer_count > 1:
        rows, columns = _grid_shape(spec)
        arrange_kwargs: dict[str, Any] = {
            "graph_name": graph_name,
            "rows": rows,
            "columns": columns,
            **_layout_spacing_plan(spec),
        }
        if spec.page.layout in {"custom", "inset"}:
            arrange_kwargs["layer_geometries"] = _layer_geometries(spec, rows, columns)
        arranged = client.arrange_layers(**arrange_kwargs)
        if spec.page.layout == "inset":
            graph_prefix = f'win -a "{_escape_labtalk(graph_name)}"; ' if graph_name else ""
            drawing_order = client.run_labtalk(graph_prefix + "page.cntrl=page.cntrl|4;")
            arranged["draw_layers_sequentially"] = drawing_order
    return {"page": page_setup, "added_layers": added_layers, "arranged": arranged}


def _add_layers_script(graph_name: str | None, count: int) -> str:
    if count <= 0:
        return ""
    parts = []
    if graph_name:
        parts.append(f'win -a "{_escape_labtalk(graph_name)}";')
    parts.extend("layadd;" for _ in range(count))
    return " ".join(parts)


def _fill_area_script(
    graph_name: str | None,
    layer_index: int,
    plot_index: int,
    fill_color: str | int | tuple[int, int, int] | None = None,
    transparency: float | None = None,
) -> str:
    fill_color_index = fill_color if isinstance(fill_color, int) else 4
    parts = []
    if graph_name:
        parts.append(f'win -a "{_escape_labtalk(graph_name)}";')
    parts.append(f"layer -s {layer_index + 1};")
    parts.extend(
        [
            f"range __origin_mcp_band_plot = !{plot_index + 1};",
            "set __origin_mcp_band_plot -pf 1;",
            "set __origin_mcp_band_plot -pfv 9;",
            f"set __origin_mcp_band_plot -pfb {fill_color_index};",
            f"set __origin_mcp_band_plot -p2fb {fill_color_index};",
        ]
    )
    if transparency is not None:
        parts.append(f"set __origin_mcp_band_plot -paap {transparency:g};")
    parts.append("rescale;")
    return " ".join(parts)


def _write_band_source(
    spec: FigureSpec,
    data: Any,
    plot: Any,
    mapping: dict[str, Any],
    band_mapping: dict[str, Any],
) -> tuple[Path, list[str]]:
    y_columns = _y_columns(mapping) or []
    if len(y_columns) != 1:
        raise ValueError("FigureSpec band uncertainty currently requires exactly one y column.")
    x_col = mapping.get("x")
    y_col = y_columns[0]
    lower_col = band_mapping["lower"]
    upper_col = band_mapping["upper"]
    if not all(isinstance(value, str) for value in (x_col, y_col, lower_col, upper_col)):
        raise ValueError("FigureSpec band uncertainty currently requires named columns.")

    df = read_table(
        data.source,
        excel_sheet=data.excel_sheet,
        delimiter=data.delimiter,
        encoding=data.encoding,
        header=data.header,
        skiprows=data.skiprows,
        nrows=data.nrows,
        na_values=data.na_values,
    )
    columns = [
        "__origin_mcp_band_x",
        "__origin_mcp_band_lower",
        "__origin_mcp_band_upper",
        "__origin_mcp_band_y",
    ]
    band_df = df[[x_col, lower_col, upper_col, y_col]].copy()
    band_df.columns = columns
    output_dir = spec.export.dir_figures or data.source.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{spec.figure.id}_{plot.id}_band.csv"
    band_df.to_csv(path, index=False)
    return path, columns


def _validate_data_columns(spec: FigureSpec) -> dict[str, Any]:
    datasets = []
    missing: list[dict[str, Any]] = []
    data_by_id = {item.id: item for item in spec.data}
    columns_by_id: dict[str, list[str]] = {}

    for data in spec.data:
        df = read_table(
            data.source,
            excel_sheet=data.excel_sheet,
            delimiter=data.delimiter,
            encoding=data.encoding,
            header=data.header,
            skiprows=data.skiprows,
            nrows=0,
            na_values=data.na_values,
        )
        columns = [str(column) for column in df.columns]
        columns_by_id[data.id] = columns
        datasets.append(
            {
                "id": data.id,
                "source": str(data.source),
                "columns": columns,
                "column_count": len(columns),
            }
        )

    for data in spec.data:
        missing.extend(
            _missing_mapping_columns(data.id, "roles", data.roles, columns_by_id[data.id])
        )

    for plot in spec.plots:
        data_id = _plot_data_ref(spec, plot)
        data = data_by_id[data_id]
        mapping = _plot_mapping(data, plot)
        missing.extend(
            _missing_mapping_columns(data_id, f"plot:{plot.id}", mapping, columns_by_id[data_id])
        )

    if missing:
        details = "; ".join(
            f"{item['scope']} {item['channel']}={item['value']!r} not in {item['columns']}"
            for item in missing
        )
        raise ValueError(f"FigureSpec data column validation failed: {details}")

    return {"ok": True, "datasets": datasets}


def _missing_mapping_columns(
    data_id: str,
    scope: str,
    mapping: dict[str, Any],
    columns: list[str],
) -> list[dict[str, Any]]:
    missing = []
    for channel, value in mapping.items():
        for item in _as_column_values(value):
            if isinstance(item, int):
                if item < 0 or item >= len(columns):
                    missing.append(
                        {
                            "data_id": data_id,
                            "scope": scope,
                            "channel": channel,
                            "value": item,
                            "columns": columns,
                        }
                    )
                continue
            if isinstance(item, str) and item not in columns:
                missing.append(
                    {
                        "data_id": data_id,
                        "scope": scope,
                        "channel": channel,
                        "value": item,
                        "columns": columns,
                    }
                )
    return missing


def _executor_warnings_from_details(details: list[dict[str, Any]]) -> list[str]:
    return sorted({str(item["code"]) for item in details})


def _executor_warning_details(spec: FigureSpec) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if spec.page.layout == "dual_y":
        warnings.extend(_dual_y_warning_details(spec))
    if any(item.object != "worksheet" for item in spec.data):
        warnings.append(
            {
                "code": "executor_supports_only_worksheet_data",
                "field": "data.object",
                "supported_values": ["worksheet"],
            }
        )
    for plot in spec.plots:
        plot_type = _normalize_plot_type(plot.type)
        mapping = _plot_mapping(_data_by_id(spec, _plot_data_ref(spec, plot)), plot)
        if plot_type not in SUPPORTED_PLOT_TYPES:
            warnings.append(
                {
                    "code": f"unsupported_executor_plot_type:{plot.type}",
                    "plot_id": plot.id,
                    "field": "type",
                    "value": plot.type,
                    "supported_values": sorted(SUPPORTED_PLOT_TYPES),
                }
            )
        if plot.id != _base_plot(spec).id and plot_type != "histogram" and mapping.get("y") is None:
            warnings.append(
                {
                    "code": "executor_requires_y_mapping_for_additional_plots",
                    "plot_id": plot.id,
                    "field": "map.y",
                }
            )
        if plot.map.get("group"):
            warnings.append(
                {
                    "code": "executor_does_not_apply_group_style",
                    "plot_id": plot.id,
                    "field": "map.group",
                    "unsupported_keys": ["group"],
                    "supported_keys": sorted(SUPPORTED_GROUP_STYLE_KEYS),
                    "supported_alternatives": ["group_style.colors", "group_style.series"],
                }
            )
        group_style_unsupported_keys = _unsupported_group_style_keys(plot.group_style)
        if group_style_unsupported_keys:
            warnings.append(
                {
                    "code": "executor_does_not_apply_group_style",
                    "plot_id": plot.id,
                    "field": "group_style",
                    "unsupported_keys": group_style_unsupported_keys,
                    "supported_keys": sorted(SUPPORTED_GROUP_STYLE_KEYS),
                }
            )
        style_unsupported_values = _unsupported_style_values(plot)
        if style_unsupported_values:
            warnings.append(
                {
                    "code": "executor_does_not_apply_plot_style",
                    "plot_id": plot.id,
                    "field": "style",
                    "unsupported_values": style_unsupported_values,
                    "supported_alternatives": [
                        "style.symbol_kind as an Origin integer symbol code",
                    ],
                }
            )
        uncertainty_unsupported_keys = _unsupported_uncertainty_keys(plot.uncertainty)
        if uncertainty_unsupported_keys:
            warnings.append(
                {
                    "code": "executor_does_not_apply_uncertainty_bands",
                    "plot_id": plot.id,
                    "field": "uncertainty",
                    "unsupported_keys": uncertainty_unsupported_keys,
                    "supported_alternatives": ["uncertainty.y_error", "uncertainty.x_error"],
                }
            )
        if _uncertainty_band_mapping(plot) and not _band_executor_supported(spec, plot):
            warnings.append(
                {
                    "code": "executor_does_not_apply_uncertainty_bands",
                    "plot_id": plot.id,
                    "field": "uncertainty",
                    "unsupported_keys": _unsupported_band_executor_features(spec, plot),
                    "supported_alternatives": [
                        "use exactly one y column per banded plot",
                        "use named x/y/lower/upper columns",
                    ],
                }
            )
    if spec.page.layout not in SUPPORTED_LAYOUTS:
        warnings.append(
            {
                "code": "executor_does_not_support_layout",
                "field": "page.layout",
                "value": spec.page.layout,
                "supported_values": sorted(SUPPORTED_LAYOUTS),
            }
        )
    for layer in spec.layers:
        if layer.z.breaks:
            warnings.append(
                {
                    "code": "executor_axis_break_supports_only_x_or_y",
                    "layer_id": layer.id,
                    "field": "layers.z.breaks",
                    "supported_values": ["x", "y"],
                }
            )
        if layer.position_mode == "absolute" and _missing_absolute_position_keys(layer):
            warnings.append(
                {
                    "code": "executor_requires_absolute_layer_position",
                    "layer_id": layer.id,
                    "field": "layers.position",
                    "missing_keys": _missing_absolute_position_keys(layer),
                    "required_keys": ["left", "top", "width", "height"],
                    "supported_alternatives": [
                        "page.layout=custom",
                        "layers.grid_cell",
                        "layers.grid_span",
                        "page.margins_mm",
                        "page.panel_spacing_mm",
                    ],
                }
            )
    if len(spec.layers) > 1 and not any(plot.layer == spec.layers[0].id for plot in spec.plots):
        warnings.append(
            {
                "code": "executor_requires_at_least_one_plot_on_first_layer",
                "field": "plots.layer",
                "layer": spec.layers[0].id,
            }
        )
    if any(_normalize_plot_type(plot.type) == "histogram" for plot in spec.plots[1:]):
        warnings.append(
            {
                "code": "executor_supports_histogram_only_as_first_plot",
                "field": "plots.type",
            }
        )
    return warnings


def _dual_y_warning_details(spec: FigureSpec) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if len(spec.layers) != 2:
        return [
            {
                "code": "executor_dual_y_requires_two_layers",
                "field": "layers",
                "value": len(spec.layers),
                "required": 2,
            }
        ]

    layer_plots = [[plot for plot in spec.plots if plot.layer == layer.id] for layer in spec.layers]
    for side, layer, plots in zip(("left", "right"), spec.layers, layer_plots, strict=True):
        if not plots:
            warnings.append(
                {
                    "code": "executor_dual_y_requires_plots_on_both_axes",
                    "field": "plots.layer",
                    "side": side,
                    "layer": layer.id,
                }
            )

    plots = [plot for side_plots in layer_plots for plot in side_plots]
    data_refs = {_plot_data_ref(spec, plot) for plot in plots}
    if len(data_refs) > 1:
        warnings.append(
            {
                "code": "executor_dual_y_requires_one_data_source",
                "field": "plots.data_ref",
                "values": sorted(data_refs),
            }
        )

    mappings = [
        _plot_mapping(_data_by_id(spec, _plot_data_ref(spec, plot)), plot) for plot in plots
    ]
    x_mappings = {str(mapping.get("x")) for mapping in mappings}
    if len(x_mappings) > 1:
        warnings.append(
            {
                "code": "executor_dual_y_requires_shared_x",
                "field": "plots.map.x",
                "values": sorted(x_mappings),
            }
        )
    if any(not _y_columns(mapping) for mapping in mappings):
        warnings.append(
            {
                "code": "executor_dual_y_requires_y_mapping",
                "field": "plots.map.y",
            }
        )

    plot_types = {_normalize_plot_type(plot.type) for plot in plots}
    supported_types = {"line", "scatter", "line_symbol"}
    if len(plot_types) > 1 or not plot_types.issubset(supported_types):
        warnings.append(
            {
                "code": "executor_dual_y_requires_one_supported_plot_type",
                "field": "plots.type",
                "values": sorted(plot_types),
                "supported_values": sorted(supported_types),
            }
        )
    if any(plot.uncertainty for plot in plots):
        warnings.append(
            {
                "code": "executor_dual_y_does_not_support_uncertainty",
                "field": "plots.uncertainty",
            }
        )
    if spec.style.template and spec.style.template.lower() != "doubley":
        warnings.append(
            {
                "code": "executor_dual_y_requires_doubley_template",
                "field": "style.template",
                "value": spec.style.template,
                "supported_values": ["doubleY"],
            }
        )
    return warnings


def _base_plot(spec: FigureSpec) -> Any:
    first_layer_id = spec.layers[0].id
    return next((plot for plot in spec.plots if plot.layer == first_layer_id), spec.plots[0])


def _plot_data_ref(spec: FigureSpec, plot: Any) -> str:
    if plot.data_ref:
        return plot.data_ref
    layer = next((item for item in spec.layers if item.id == plot.layer), None)
    if layer and layer.data_ref:
        return layer.data_ref
    return spec.data[0].id


def _data_by_id(spec: FigureSpec, data_id: str | None) -> Any:
    for data in spec.data:
        if data.id == data_id:
            return data
    raise ValueError(f"Unknown data id: {data_id!r}")


def _layer_by_id(spec: FigureSpec, layer_id: str) -> Any:
    for layer in spec.layers:
        if layer.id == layer_id:
            return layer
    raise ValueError(f"Unknown layer id: {layer_id!r}")


def _plot_mapping(data: Any, plot: Any) -> dict[str, Any]:
    return {**data.roles, **_uncertainty_mapping(plot), **plot.map}


def _normalize_plot_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _style_mode(spec: FigureSpec) -> str:
    if spec.style.template and spec.style.theme in {"origin_default", "template"}:
        return "template"
    return spec.style.theme


def _legend_font(spec: FigureSpec) -> str | None:
    """Font to assert on the legend so it matches the styled axes.

    An explicit ``font_family`` always wins. Otherwise the Nature theme forces
    Arial (matching ``apply_nature_style``); other themes return None to preserve
    the Origin template defaults rather than overriding the legend font.
    """
    if spec.style.font_family:
        return spec.style.font_family
    if spec.style.theme == "nature":
        return "Arial"
    return None


def _show_legend(spec: FigureSpec) -> bool:
    for item in spec.annotations:
        if item.type.strip().lower() == "legend":
            return True
    return True


def _y_columns(mapping: dict[str, Any]) -> list[str | int] | None:
    y_value = mapping.get("y")
    if y_value is None:
        return None
    if isinstance(y_value, list):
        return y_value
    return [y_value]


def _selected_xyz(mapping: dict[str, Any]) -> list[str | int]:
    return [mapping.get("x", 0), mapping.get("y", 1), mapping.get("z", 2)]


def _apply_axis_specs(
    graph_name: str | None,
    layer: Any,
    layer_index: int,
) -> list[dict[str, Any]]:
    updates = []
    for axis_name, axis_spec in (("x", layer.x), ("y", layer.y), ("z", layer.z)):
        start = end = None
        limits = axis_spec.limits
        if isinstance(limits, list):
            start = limits[0] if len(limits) > 0 else None
            end = limits[1] if len(limits) > 1 else None
        has_axis_format = not (
            axis_spec.scale is None
            and start is None
            and end is None
            and axis_spec.step is None
            and axis_spec.title is None
        )
        if has_axis_format:
            updates.append(
                {
                    "layer_index": layer_index,
                    **client.set_axis(
                        graph_name=graph_name,
                        layer_index=layer_index,
                        axis=axis_name,
                        scale=axis_spec.scale,
                        start=start,
                        end=end,
                        step=axis_spec.step,
                        title=axis_spec.title,
                    ),
                }
            )
        for axis_break in axis_spec.breaks:
            updates.append(
                {
                    "layer_index": layer_index,
                    **client.set_axis_break(
                        graph_name=graph_name,
                        layer_index=layer_index,
                        axis=axis_name,
                        break_from=axis_break.start,
                        break_to=axis_break.end,
                        position=axis_break.position,
                        post_break_increment=axis_break.post_break_increment,
                        enabled=axis_break.enabled,
                    ),
                }
            )
    return updates


def _apply_plot_styles(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
    base_plot: Any,
) -> list[dict[str, Any]]:
    updates = []
    primary_indices = _plot_primary_indices(spec, base_plot)
    for plot in _plot_execution_order(spec, base_plot):
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
        y_count = len(_y_columns(mapping) or [None])
        layer_index = layer_indexes[plot.layer]
        for offset in range(y_count):
            style = _plot_style_kwargs(_plot_series_style(plot, offset))
            if style:
                updates.append(
                    {
                        "plot_id": plot.id,
                        "series_index": offset,
                        **client.set_plot_style(
                            graph_name=graph_name,
                            layer_index=layer_index,
                            plot_index=primary_indices[plot.id][offset],
                            **style,
                        ),
                    }
                )
    return updates


def _plot_execution_order(spec: FigureSpec, base_plot: Any) -> list[Any]:
    return [base_plot, *(plot for plot in spec.plots if plot.id != base_plot.id)]


def _plot_primary_indices(spec: FigureSpec, base_plot: Any) -> dict[str, list[int]]:
    next_plot_index = {layer.id: 0 for layer in spec.layers}
    indices: dict[str, list[int]] = {}
    for plot in _plot_execution_order(spec, base_plot):
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
        y_count = len(_y_columns(mapping) or [None])
        start_index = next_plot_index[plot.layer]
        band_slots = 2 if _uncertainty_band_mapping(plot) else 0
        primary_start = start_index + band_slots
        indices[plot.id] = [primary_start + offset for offset in range(y_count)]
        next_plot_index[plot.layer] = primary_start + y_count
    return indices


def _plot_series_style(plot: Any, series_index: int) -> dict[str, Any]:
    style = dict(plot.style)
    group_style = plot.group_style
    if not group_style:
        return style

    series = group_style.get("series")
    if (
        isinstance(series, list)
        and series_index < len(series)
        and isinstance(series[series_index], dict)
    ):
        style.update(series[series_index])

    for source_key, target_key in GROUP_STYLE_SEQUENCE_KEYS.items():
        value = _series_value(group_style.get(source_key), series_index)
        if value is not None:
            style[target_key] = value

    for key in GROUP_STYLE_DIRECT_KEYS:
        value = _series_value(group_style.get(key), series_index)
        if value is not None:
            style[key] = value

    for key in GROUP_STYLE_VECTOR_DIRECT_KEYS:
        value = group_style.get(key)
        if value is not None:
            style[key] = value

    return style


def _series_value(value: Any, index: int) -> Any:
    if isinstance(value, list):
        return value[index] if index < len(value) else None
    return value


def _plot_style_kwargs(style: dict[str, Any]) -> dict[str, Any]:
    supported = {
        "color",
        "line_width",
        "bar_gap",
        "line_style",
        "symbol_kind",
        "symbol_size",
        "transparency",
        "colormap",
        "contour_levels",
        "contour_minor_levels",
        "color_scale_limits",
        "histogram_bin_width",
        "errorbar_cap",
        "box_width",
    }
    kwargs = {key: value for key, value in style.items() if key in supported and value is not None}
    if "symbol_kind" in kwargs and not isinstance(kwargs["symbol_kind"], int):
        kwargs.pop("symbol_kind")
    if isinstance(kwargs.get("color_scale_limits"), list):
        kwargs["color_scale_limits"] = tuple(kwargs["color_scale_limits"])
    return kwargs


def _unsupported_style_values(plot: Any) -> list[dict[str, Any]]:
    issues = []
    style = plot.style
    symbol_kind = style.get("symbol_kind")
    if symbol_kind is not None and not isinstance(symbol_kind, int):
        issues.append(
            {
                "key": "symbol_kind",
                "value": symbol_kind,
                "expected": "Origin integer symbol code",
            }
        )
    contour_levels = style.get("contour_levels")
    if contour_levels is not None and (
        not isinstance(contour_levels, list)
        or len(contour_levels) < 2
        or not all(isinstance(item, (int, float)) for item in contour_levels)
        or any(
            right <= left for left, right in zip(contour_levels, contour_levels[1:], strict=False)
        )
    ):
        issues.append(
            {
                "key": "contour_levels",
                "value": contour_levels,
                "expected": "at least two strictly increasing numbers",
            }
        )
    color_limits = style.get("color_scale_limits")
    if color_limits is not None and (
        not isinstance(color_limits, (list, tuple))
        or len(color_limits) != 2
        or not all(isinstance(item, (int, float)) for item in color_limits)
        or color_limits[0] >= color_limits[1]
    ):
        issues.append(
            {
                "key": "color_scale_limits",
                "value": color_limits,
                "expected": "two increasing numbers",
            }
        )
    for key in (
        "line_width",
        "symbol_size",
        "histogram_bin_width",
        "errorbar_cap",
        "box_width",
    ):
        value = style.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value <= 0):
            issues.append({"key": key, "value": value, "expected": "a positive number"})
    transparency = style.get("transparency")
    if transparency is not None and (
        not isinstance(transparency, (int, float)) or not 0 <= transparency <= 100
    ):
        issues.append(
            {
                "key": "transparency",
                "value": transparency,
                "expected": "a number from 0 to 100",
            }
        )
    minor_levels = style.get("contour_minor_levels")
    if minor_levels is not None and (
        not isinstance(minor_levels, int) or isinstance(minor_levels, bool) or minor_levels < 0
    ):
        issues.append(
            {
                "key": "contour_minor_levels",
                "value": minor_levels,
                "expected": "a non-negative integer",
            }
        )
    colormap = style.get("colormap")
    if colormap is not None and (not isinstance(colormap, str) or not colormap.strip()):
        issues.append(
            {"key": "colormap", "value": colormap, "expected": "a non-empty palette name"}
        )
    return issues


def _uncertainty_mapping(plot: Any) -> dict[str, Any]:
    uncertainty = plot.uncertainty
    if not uncertainty:
        return {}
    band_mapping = _uncertainty_band_mapping(plot)
    if band_mapping:
        return band_mapping
    mapping: dict[str, Any] = {}
    y_error = (
        uncertainty.get("y_error")
        or uncertainty.get("y_error_col")
        or uncertainty.get("error")
        or uncertainty.get("yerr")
    )
    x_error = (
        uncertainty.get("x_error") or uncertainty.get("x_error_col") or uncertainty.get("xerr")
    )
    if y_error is not None:
        mapping["y_error"] = y_error
    if x_error is not None:
        mapping["x_error"] = x_error
    return mapping


def _uncertainty_band_mapping(plot: Any) -> dict[str, Any]:
    uncertainty = plot.uncertainty
    if not uncertainty or _uncertainty_kind(uncertainty) not in {
        "band",
        "confidence_band",
        "uncertainty_band",
    }:
        return {}
    lower = uncertainty.get("lower") or uncertainty.get("lower_col")
    upper = uncertainty.get("upper") or uncertainty.get("upper_col")
    if lower is None or upper is None:
        return {}
    mapping: dict[str, Any] = {
        "lower": lower,
        "upper": upper,
    }
    return mapping


def _uncertainty_style(plot: Any) -> dict[str, Any]:
    uncertainty = plot.uncertainty
    if not uncertainty:
        return {}
    mapping: dict[str, Any] = {}
    fill_color = uncertainty.get("fill_color") or uncertainty.get("color")
    transparency = uncertainty.get("transparency")
    if fill_color is not None:
        mapping["fill_color"] = fill_color
    if transparency is not None:
        mapping["transparency"] = transparency
    return mapping


def _uncertainty_kind(uncertainty: dict[str, Any]) -> str | None:
    kind = uncertainty.get("type", uncertainty.get("kind"))
    if kind is None:
        return None
    return str(kind).strip().lower()


def _unsupported_uncertainty_keys(uncertainty: dict[str, Any]) -> list[str]:
    unsupported = [key for key in uncertainty if key not in SUPPORTED_UNCERTAINTY_KEYS]
    kind = _uncertainty_kind(uncertainty)
    if kind is not None and kind not in SUPPORTED_UNCERTAINTY_KINDS:
        unsupported.append("type")
    if kind in {"band", "confidence_band", "uncertainty_band"}:
        if uncertainty.get("lower") is None and uncertainty.get("lower_col") is None:
            unsupported.append("lower")
        if uncertainty.get("upper") is None and uncertainty.get("upper_col") is None:
            unsupported.append("upper")
    return sorted(set(unsupported))


def _unsupported_group_style_keys(group_style: dict[str, Any]) -> list[str]:
    return sorted(key for key in group_style if key not in SUPPORTED_GROUP_STYLE_KEYS)


def _band_executor_supported(spec: FigureSpec, plot: Any) -> bool:
    if not _uncertainty_band_mapping(plot):
        return True
    return not _unsupported_band_executor_features(spec, plot)


def _unsupported_band_executor_features(spec: FigureSpec, plot: Any) -> list[str]:
    if not _uncertainty_band_mapping(plot):
        return []
    unsupported = []
    data = _data_by_id(spec, _plot_data_ref(spec, plot))
    mapping = _plot_mapping(data, plot)
    y_columns = _y_columns(mapping) or []
    if len(y_columns) != 1:
        unsupported.append("multiple_y_columns")
    band_mapping = _uncertainty_band_mapping(plot)
    required = [
        mapping.get("x"),
        *(y_columns[:1]),
        band_mapping.get("lower"),
        band_mapping.get("upper"),
    ]
    if not all(isinstance(value, str) for value in required):
        unsupported.append("non_named_columns")
    return sorted(set(unsupported))


def _apply_annotations(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
) -> list[dict[str, Any]]:
    results = []
    annotation_font_size = spec.style.annotation_font_size or NATURE_ANNOTATION_FONT_SIZE
    for layer in spec.layers:
        if layer.panel_tag:
            results.append(
                client.add_graph_label(
                    text=layer.panel_tag,
                    graph_name=graph_name,
                    layer_index=layer_indexes[layer.id],
                    name=f"{layer.id}_panel_tag",
                    font_size=annotation_font_size,
                )
            )
    for annotation in spec.annotations:
        kind = annotation.type.strip().lower()
        layer_index = layer_indexes.get(annotation.layer or spec.layers[0].id, 0)
        if kind == "legend":
            text = annotation.text or _legend_text(spec)
            results.append(
                client.format_legend(
                    graph_name=graph_name,
                    text=text,
                    font_family=_legend_font(spec),
                    show_frame=annotation.frame,
                    position=annotation.location,
                )
            )
        elif kind in {"panel_tag", "text"} and annotation.text:
            results.append(
                client.add_graph_label(
                    text=annotation.text,
                    graph_name=graph_name,
                    layer_index=layer_index,
                    name=annotation.id,
                    font_size=int(annotation.style.get("font_size") or annotation_font_size),
                )
            )
        elif kind == "reference_line" and annotation.value is not None:
            axis = "x" if (annotation.orientation or "").lower().startswith("v") else "y"
            results.append(
                client.add_reference_line(
                    value=annotation.value,
                    axis=axis,
                    graph_name=graph_name,
                    layer_index=layer_index,
                    label=annotation.text,
                )
            )
    return results


def _legend_text(spec: FigureSpec) -> str | None:
    base_plot = _base_plot(spec)
    if not any(_uncertainty_band_mapping(plot) for plot in spec.plots):
        return None
    entries = []
    primary_indices = _plot_primary_indices(spec, base_plot)
    for plot in _plot_execution_order(spec, base_plot):
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
        y_columns = _y_columns(mapping) or []
        if not y_columns:
            continue
        for index, y_col in zip(primary_indices[plot.id], y_columns, strict=False):
            entries.append(f"\\l({index + 1}) {y_col}")
    if not entries:
        return None
    return "\n".join(entries)


def _export_outputs(
    spec: FigureSpec,
    graph_data: dict[str, Any],
    graph_name: str | None,
) -> list[dict[str, Any]]:
    export_paths = _export_paths(spec)
    exported = []
    first_export = export_paths[0] if export_paths else None
    if first_export and graph_data.get("export_path"):
        exported.append(client.inspect_export(Path(graph_data["export_path"])))
    elif first_export:
        item = client.export_graph(
            first_export,
            graph_name=graph_name,
            overwrite=True,
            width=_export_width_px(spec, first_export),
        )
        exported.append(client.inspect_export(Path(item["path"])))
    for path in export_paths[1:]:
        item = client.export_graph(
            path,
            graph_name=graph_name,
            overwrite=True,
            width=_export_width_px(spec, path),
        )
        exported.append(client.inspect_export(Path(item["path"])))
    return exported


def _export_width_px(spec: FigureSpec, path: Path) -> int:
    suffix = path.suffix.lower().lstrip(".")
    item = getattr(spec.export, suffix, None)
    if isinstance(item, FigureExportFormatSpec) and item.width_px:
        return int(item.width_px)
    if suffix in {"png", "jpg", "jpeg", "tif", "tiff"}:
        return 1600
    return 0


def _save_project_if_requested(spec: FigureSpec) -> dict[str, Any] | None:
    project_path = _project_path(spec)
    if not spec.runtime.save_project and not project_path:
        return None
    if project_path is None:
        project_path = Path(f"{spec.figure.id}.opju")
    return client.save_project(project_path)


def _diagnose_if_requested(spec: FigureSpec, graph_name: str | None) -> dict[str, Any] | None:
    if not spec.export.qa:
        return None
    return client.diagnose_graph(
        graph_name=graph_name,
        style=spec.style.theme,
        palette_role=spec.style.palette_role,
        palette_name=spec.style.palette_name,
        require_axis_titles=bool(spec.export.qa.get("require_axis_titles", True)),
        require_plots=bool(spec.export.qa.get("require_plots", True)),
        require_legend=bool(spec.export.qa.get("require_legend", False)),
        require_panel_label=bool(spec.export.qa.get("require_panel_label", False)),
    )


def _export_paths(spec: FigureSpec) -> list[Path]:
    paths = []
    for suffix in ("png", "pdf", "svg", "tiff"):
        item = getattr(spec.export, suffix)
        if not _export_enabled(item):
            continue
        path = item.path if isinstance(item, FigureExportFormatSpec) else None
        if path is None:
            output_dir = spec.export.dir_figures or Path("output") / "figures"
            path = output_dir / f"{spec.figure.id}.{suffix}"
        paths.append(path)
    return paths


def _export_enabled(item: FigureExportFormatSpec | bool | None) -> bool:
    if isinstance(item, bool):
        return item
    if item is None:
        return False
    return item.enabled


def _project_path(spec: FigureSpec) -> Path | None:
    if spec.runtime.project_path:
        return spec.runtime.project_path
    if spec.export.dir_opju and (spec.runtime.save_project or spec.export.qa.get("require_opju")):
        return spec.export.dir_opju / f"{spec.figure.id}.opju"
    return None


def _apply_page_setup(spec: FigureSpec, graph_name: str | None) -> dict[str, Any] | None:
    page_setup = _page_setup_plan(spec)
    if not page_setup:
        return None
    return client.set_graph_page(graph_name=graph_name, **page_setup)


def _page_setup_plan(spec: FigureSpec) -> dict[str, Any]:
    if not spec.page.size_mm:
        return {}
    width = float(spec.page.size_mm[0]) / 25.4 if len(spec.page.size_mm) > 0 else None
    height = float(spec.page.size_mm[1]) / 25.4 if len(spec.page.size_mm) > 1 else None
    plan: dict[str, Any] = {"unit": "inch"}
    if width is not None:
        plan["width"] = width
    if height is not None:
        plan["height"] = height
    return plan


def _grid_shape(spec: FigureSpec) -> tuple[int, int]:
    if spec.page.layout == "inset":
        return 1, 1
    rows = 1
    columns = 1 if any(layer.grid_cell for layer in spec.layers) else max(1, len(spec.layers))
    for index, layer in enumerate(spec.layers):
        cell = layer.grid_cell or [index // columns, index % columns]
        span = layer.grid_span or [1, 1]
        rows = max(rows, int(cell[0]) + int(span[0]))
        columns = max(columns, int(cell[1]) + int(span[1]))
    if any(layer.grid_cell for layer in spec.layers):
        return rows, columns
    if spec.page.layout == "grid" and len(spec.layers) > 1:
        columns = 2 if len(spec.layers) > 2 else len(spec.layers)
        rows = (len(spec.layers) + columns - 1) // columns
    return rows, columns


def _layout_spacing_plan(spec: FigureSpec) -> dict[str, float]:
    if not spec.page.panel_spacing_mm:
        return {}
    spacing = spec.page.panel_spacing_mm
    page_size = spec.page.size_mm or []
    plan: dict[str, float] = {}
    if len(spacing) > 0 and len(page_size) > 0 and float(page_size[0]) > 0:
        plan["gap_x"] = float(spacing[0]) / float(page_size[0]) * 100.0
    if len(spacing) > 1 and len(page_size) > 1 and float(page_size[1]) > 0:
        plan["gap_y"] = float(spacing[1]) / float(page_size[1]) * 100.0
    return plan


def _layer_geometries(spec: FigureSpec, rows: int, columns: int) -> list[dict[str, float | int]]:
    if spec.page.layout == "inset":
        return _inset_layer_geometries(spec)
    width_mm, height_mm = _page_size_mm(spec)
    margins = _page_margins_mm(spec)
    spacing_x, spacing_y = _panel_spacing_mm(spec)
    usable_width = max(1.0, width_mm - margins[0] - margins[2] - spacing_x * (columns - 1))
    usable_height = max(1.0, height_mm - margins[1] - margins[3] - spacing_y * (rows - 1))
    cell_width = usable_width / columns
    cell_height = usable_height / rows
    geometries = []
    for index, layer in enumerate(spec.layers):
        if layer.position_mode == "absolute":
            position = layer.position
            geometries.append(
                {
                    "layer_index": index,
                    "left": float(position["left"]),
                    "top": float(position["top"]),
                    "width": float(position["width"]),
                    "height": float(position["height"]),
                }
            )
            continue
        cell = layer.grid_cell or [index // columns, index % columns]
        span = layer.grid_span or [1, 1]
        row = int(cell[0])
        column = int(cell[1])
        row_span = max(1, int(span[0]))
        col_span = max(1, int(span[1]))
        left_mm = margins[0] + column * (cell_width + spacing_x)
        top_mm = margins[1] + row * (cell_height + spacing_y)
        panel_width = cell_width * col_span + spacing_x * (col_span - 1)
        panel_height = cell_height * row_span + spacing_y * (row_span - 1)
        geometries.append(
            {
                "layer_index": index,
                "left": left_mm / width_mm * 100.0,
                "top": top_mm / height_mm * 100.0,
                "width": panel_width / width_mm * 100.0,
                "height": panel_height / height_mm * 100.0,
            }
        )
    return geometries


def _inset_layer_geometries(spec: FigureSpec) -> list[dict[str, float | int]]:
    geometries: list[dict[str, float | int]] = []
    for index, layer in enumerate(spec.layers):
        if layer.position_mode == "absolute":
            position = layer.position
            geometries.append(
                {
                    "layer_index": index,
                    "left": float(position["left"]),
                    "top": float(position["top"]),
                    "width": float(position["width"]),
                    "height": float(position["height"]),
                }
            )
            continue
        if index == 0:
            geometries.append(
                {"layer_index": 0, "left": 10.0, "top": 8.0, "width": 82.0, "height": 82.0}
            )
            continue
        inset_offset = float((index - 1) * 4)
        geometries.append(
            {
                "layer_index": index,
                "left": max(12.0, 60.0 - inset_offset),
                "top": min(54.0, 12.0 + inset_offset),
                "width": 30.0,
                "height": 30.0,
            }
        )
    return geometries


def _missing_absolute_position_keys(layer: Any) -> list[str]:
    required = ["left", "top", "width", "height"]
    position = getattr(layer, "position", {}) or {}
    return [key for key in required if position.get(key) is None]


def _page_size_mm(spec: FigureSpec) -> tuple[float, float]:
    if spec.page.size_mm and len(spec.page.size_mm) >= 2:
        return max(1.0, float(spec.page.size_mm[0])), max(1.0, float(spec.page.size_mm[1]))
    return 180.0, 120.0


def _page_margins_mm(spec: FigureSpec) -> tuple[float, float, float, float]:
    margins = [float(item) for item in (spec.page.margins_mm or [])]
    if len(margins) == 1:
        margins *= 4
    elif len(margins) == 2:
        margins = [margins[0], margins[1], margins[0], margins[1]]
    elif len(margins) == 3:
        margins = [margins[0], margins[1], margins[2], margins[1]]
    elif len(margins) < 4:
        margins = [12.0, 10.0, 8.0, 10.0]
    return tuple(margins[:4])  # type: ignore[return-value]


def _panel_spacing_mm(spec: FigureSpec) -> tuple[float, float]:
    spacing = [float(item) for item in (spec.page.panel_spacing_mm or [])]
    if len(spacing) == 1:
        return spacing[0], spacing[0]
    if len(spacing) >= 2:
        return spacing[0], spacing[1]
    return 6.0, 6.0


def _import_kwargs(data: Any) -> dict[str, Any]:
    return {
        "path": data.source,
        "book_name": None,
        "sheet_name": None,
        "excel_sheet": data.excel_sheet,
        "delimiter": data.delimiter,
        "encoding": data.encoding,
        "header": data.header,
        "skiprows": data.skiprows,
        "nrows": data.nrows,
        "na_values": data.na_values,
    }


def _worksheet_ref_expr(ref: Any) -> str:
    return f"[{ref.book_name}]{ref.sheet_name}"


def _as_column_values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _escape_labtalk(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
