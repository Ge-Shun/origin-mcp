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
SUPPORTED_LAYOUTS = {"single", "grid"}


@_mcp_tool()
def origin_plan_figure_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate a declarative FigureSpec and return the planned Origin operations."""

    return _wrap(
        lambda: _ok("Planned FigureSpec.", **_plan_figure(FigureSpec.model_validate(spec)))
    )


@_mcp_tool()
def origin_execute_figure_spec(
    spec: dict[str, Any],
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
    warnings = _executor_warnings(spec)
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

    for layer in spec.layers:
        operations.append(
            {
                "op": "configure_layer",
                "id": layer.id,
                "data_ref": layer.data_ref,
                "x": layer.x.model_dump(exclude_none=True),
                "y": layer.y.model_dump(exclude_none=True),
                "panel_tag": layer.panel_tag,
                "grid_cell": layer.grid_cell,
            }
        )

    for plot in spec.plots:
        operations.append(
            {
                "op": "plot",
                "id": plot.id,
                "type": _normalize_plot_type(plot.type),
                "layer": plot.layer,
                "data_ref": _plot_data_ref(spec, plot),
                "map": plot.map,
            }
        )

    if spec.page.layout == "grid" and len(spec.layers) > 1:
        rows, columns = _grid_shape(spec)
        operations.append({"op": "arrange_layers", "rows": rows, "columns": columns})

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
    worksheet_refs[base_data.id] = worksheet
    graph_data = graph.as_dict()
    graph_name = graph_data.get("graph_name")

    for data in spec.data:
        if data.id not in worksheet_refs:
            worksheet_refs[data.id] = client.import_table(**_import_kwargs(data))

    layer_setup = _ensure_layers_and_layout(spec, graph_name)
    added_plots = _add_remaining_plots(spec, graph_name, layer_indexes, worksheet_refs, base_plot)

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
    export_paths = _export_paths(spec)
    first_export = export_paths[0] if export_paths else None

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
            export_path=first_export,
        )
        return worksheet, graph, command

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
        export_path=first_export,
    )
    return worksheet, graph, None


def _add_remaining_plots(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
    worksheet_refs: dict[str, Any],
    base_plot: Any,
) -> list[dict[str, Any]]:
    added = []
    for plot in spec.plots:
        if plot.id == base_plot.id:
            continue
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
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
    return added


def _ensure_layers_and_layout(spec: FigureSpec, graph_name: str | None) -> dict[str, Any]:
    layer_count = len(spec.layers)
    added_layers = 0
    if layer_count > 1:
        script = _add_layers_script(graph_name, layer_count - 1)
        if script:
            client.run_labtalk(script)
            added_layers = layer_count - 1

    arranged = None
    if spec.page.layout == "grid" and layer_count > 1:
        rows, columns = _grid_shape(spec)
        arranged = client.arrange_layers(graph_name=graph_name, rows=rows, columns=columns)
    return {"added_layers": added_layers, "arranged": arranged}


def _add_layers_script(graph_name: str | None, count: int) -> str:
    if count <= 0:
        return ""
    parts = []
    if graph_name:
        parts.append(f'win -a "{_escape_labtalk(graph_name)}";')
    parts.extend("layadd;" for _ in range(count))
    return " ".join(parts)


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


def _executor_warnings(spec: FigureSpec) -> list[str]:
    warnings: list[str] = []
    if any(item.object != "worksheet" for item in spec.data):
        warnings.append("executor_supports_only_worksheet_data")
    for plot in spec.plots:
        plot_type = _normalize_plot_type(plot.type)
        mapping = _plot_mapping(_data_by_id(spec, _plot_data_ref(spec, plot)), plot)
        if plot_type not in SUPPORTED_PLOT_TYPES:
            warnings.append(f"unsupported_executor_plot_type:{plot.type}")
        if plot.id != _base_plot(spec).id and plot_type != "histogram" and mapping.get("y") is None:
            warnings.append("executor_requires_y_mapping_for_additional_plots")
        if plot.map.get("group") or plot.group_style:
            warnings.append("executor_does_not_apply_group_style")
        if plot.uncertainty:
            warnings.append("executor_does_not_apply_uncertainty_bands")
    if spec.page.layout not in SUPPORTED_LAYOUTS:
        warnings.append("executor_supports_only_single_or_grid_layout")
    if len(spec.layers) > 1 and not any(plot.layer == spec.layers[0].id for plot in spec.plots):
        warnings.append("executor_requires_at_least_one_plot_on_first_layer")
    if any(_normalize_plot_type(plot.type) == "histogram" for plot in spec.plots[1:]):
        warnings.append("executor_supports_histogram_only_as_first_plot")
    return sorted(set(warnings))


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
    return {**data.roles, **plot.map}


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
    for axis_name, axis_spec in (("x", layer.x), ("y", layer.y)):
        start = end = None
        limits = axis_spec.limits
        if isinstance(limits, list):
            start = limits[0] if len(limits) > 0 else None
            end = limits[1] if len(limits) > 1 else None
        if (
            axis_spec.scale is None
            and start is None
            and end is None
            and axis_spec.step is None
            and axis_spec.title is None
        ):
            continue
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
    return updates


def _apply_plot_styles(
    spec: FigureSpec,
    graph_name: str | None,
    layer_indexes: dict[str, int],
    base_plot: Any,
) -> list[dict[str, Any]]:
    updates = []
    next_plot_index = {layer.id: 0 for layer in spec.layers}
    execution_order = [base_plot, *(plot for plot in spec.plots if plot.id != base_plot.id)]
    for plot in execution_order:
        data = _data_by_id(spec, _plot_data_ref(spec, plot))
        mapping = _plot_mapping(data, plot)
        y_count = len(_y_columns(mapping) or [None])
        style = _plot_style_kwargs(plot.style)
        layer_index = layer_indexes[plot.layer]
        start_index = next_plot_index[plot.layer]
        if style:
            for offset in range(y_count):
                updates.append(
                    {
                        "plot_id": plot.id,
                        **client.set_plot_style(
                            graph_name=graph_name,
                            layer_index=layer_index,
                            plot_index=start_index + offset,
                            **style,
                        ),
                    }
                )
        next_plot_index[plot.layer] = start_index + y_count
    return updates


def _plot_style_kwargs(style: dict[str, Any]) -> dict[str, Any]:
    supported = {
        "color",
        "line_width",
        "bar_gap",
        "line_style",
        "symbol_kind",
        "symbol_size",
        "transparency",
    }
    return {key: value for key, value in style.items() if key in supported and value is not None}


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
            results.append(
                client.format_legend(
                    graph_name=graph_name,
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
    for path in export_paths[1:]:
        item = client.export_graph(path, graph_name=graph_name, overwrite=True)
        exported.append(client.inspect_export(Path(item["path"])))
    return exported


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


def _grid_shape(spec: FigureSpec) -> tuple[int, int]:
    rows = 1
    columns = max(1, len(spec.layers))
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
