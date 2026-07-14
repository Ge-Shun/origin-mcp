from __future__ import annotations

import math
from typing import Any

from ..errors import OriginOperationError
from .graph_formatting_helpers import _GraphFormattingHelperMixin


class _GraphFormattingMixin(_GraphFormattingHelperMixin):
    """Graph object lookup, layer / axis / legend editing methods."""

    def list_project(self) -> dict[str, Any]:
        self.ensure_feature("pages", "Project object listing")
        op = self.op
        pages = getattr(op, "pages", None)
        if not callable(pages):
            raise OriginOperationError("originpro.pages is not available.")

        workbooks: list[dict[str, Any]] = []
        matrixbooks: list[dict[str, Any]] = []
        graphs: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        for page in pages():
            item = {
                "name": self._object_name(page, default=""),
                "long_name": getattr(page, "lname", ""),
                "layers": len(page) if hasattr(page, "__len__") else None,
                "open": page.is_open() if hasattr(page, "is_open") else None,
            }
            cls_name = type(page).__name__.lower()
            if cls_name == "wbook":
                item["sheets"] = [
                    {
                        "name": self._object_name(sheet, default=""),
                        "rows": getattr(sheet, "rows", None),
                        "cols": getattr(sheet, "cols", None),
                    }
                    for sheet in page
                ]
                workbooks.append(item)
            elif cls_name == "mbook":
                matrixbooks.append(item)
            elif cls_name == "gpage":
                graphs.append(item)
            else:
                images.append(item)
        return {
            "workbooks": workbooks,
            "matrixbooks": matrixbooks,
            "graphs": graphs,
            "images": images,
        }

    def rename_object(self, name: str, new_name: str, object_type: str = "graph") -> dict[str, Any]:
        obj = self._find_object(name=name, object_type=object_type)
        obj.name = new_name
        return {"old_name": name, "new_name": self._object_name(obj, default=new_name)}

    def delete_object(self, name: str, object_type: str = "graph") -> dict[str, Any]:
        obj = self._find_object(name=name, object_type=object_type)
        destroy = getattr(obj, "destroy", None)
        if not callable(destroy):
            raise OriginOperationError(f"Object does not support delete: {name}")
        destroy()
        return {"deleted": True, "name": name, "object_type": object_type}

    def set_axis(
        self,
        graph_name: str | None = None,
        layer_index: int = 0,
        axis: str = "x",
        scale: str | int | None = None,
        start: float | None = None,
        end: float | None = None,
        step: float | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        ax = layer.axis(axis)
        if scale is not None:
            scale_value = self._axis_scale_value(scale)
            try:
                ax.scale = scale_value
            except Exception:
                if scale_value == scale:
                    raise
                ax.scale = scale
        if start is not None or end is not None or step is not None:
            ax.limits = (start, end, step)
        axis_title = self._label_text(title) if title is not None else None
        if axis_title is not None:
            ax.title = axis_title
        self._rescale(layer) if start is None and end is None else None
        axis_info = self._axis_info(ax)
        requested = {
            "scale": scale,
            "start": start,
            "end": end,
            "step": step,
            "title": axis_title,
        }
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "layer_index": layer_index,
            "axis": axis,
            "requested": {key: value for key, value in requested.items() if value is not None},
            "axis_info": axis_info,
            "verified": self._axis_settings_verified(requested, axis_info),
        }

    def set_axis_break(
        self,
        break_from: float | None = None,
        break_to: float | None = None,
        axis: str = "x",
        graph_name: str | None = None,
        layer_index: int = 0,
        position: float | None = None,
        post_break_increment: float | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        axis_l = axis.lower()
        if axis_l not in {"x", "y"}:
            raise OriginOperationError("axis must be 'x' or 'y'.", error_code="invalid_request")
        if enabled:
            if break_from is None or break_to is None:
                raise OriginOperationError(
                    "break_from and break_to are required when enabled.",
                    error_code="invalid_request",
                )
            if break_from >= break_to:
                raise OriginOperationError(
                    "break_from must be less than break_to.", error_code="invalid_request"
                )
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        self._activate_graph(graph, graph_name_actual)

        prefix = f"layer.{axis_l}"
        if not enabled:
            script = f"layer -s {layer_index + 1}; {prefix}.breaks.enable=0;"
        else:
            parts = [
                f"layer -s {layer_index + 1};",
                f"{prefix}.breaks.enable=1;",
                f"{prefix}.breaks.count=1;",
                f"{prefix}.break1.from={break_from};",
                f"{prefix}.break1.to={break_to};",
            ]
            if position is not None:
                parts.append(f"{prefix}.break1.pos={position};")
            if post_break_increment is not None:
                parts.append(f"{prefix}.break1.inc={post_break_increment};")
            script = " ".join(parts)
        result = self.run_labtalk(script)
        return {
            "graph_name": graph_name_actual,
            "layer_index": layer_index,
            "axis": axis_l,
            "enabled": enabled,
            "break_from": break_from if enabled else None,
            "break_to": break_to if enabled else None,
            "position": position,
            "script": script,
            **result,
        }

    def set_plot_style(
        self,
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
        colormap: str | None = None,
        contour_levels: list[float] | None = None,
        contour_minor_levels: int | None = None,
        color_scale_limits: tuple[float, float] | None = None,
        histogram_bin_width: float | None = None,
        errorbar_cap: float | None = None,
        box_width: float | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        layer = self._graph_layer(graph, layer_index)
        plots = layer.plot_list()
        selected_with_indexes = (
            list(enumerate(plots)) if plot_index is None else [(plot_index, plots[plot_index])]
        )
        for selected_index, plot in selected_with_indexes:
            if color is not None:
                plot.color = color
            if line_width is not None:
                self._set_plot_line_width(plot, line_width)
            if bar_gap is not None:
                self._set_plot_bar_gap(plot, bar_gap)
            if line_style is not None:
                plot.set_cmd(f"-d {line_style}")
            if symbol_kind is not None:
                plot.symbol_kind = symbol_kind
            if symbol_size is not None:
                plot.symbol_size = symbol_size
            if transparency is not None:
                plot.transparency = transparency
            if colormap is not None:
                plot.colormap = colormap
            if (
                contour_levels is not None
                or contour_minor_levels is not None
                or color_scale_limits is not None
            ):
                self._set_plot_z_levels(
                    plot,
                    contour_levels=contour_levels,
                    minor_levels=contour_minor_levels,
                    color_scale_limits=color_scale_limits,
                )
            if histogram_bin_width is not None:
                self._set_plot_command(plot, f"-hbs {histogram_bin_width:g}")
            if errorbar_cap is not None:
                self._set_plot_command(plot, f"-erwc {errorbar_cap:g}")
            if box_width is not None:
                self._set_box_chart_width(
                    graph=graph,
                    graph_name=graph_name_actual,
                    layer_index=layer_index,
                    plot_index=selected_index,
                    width=box_width,
                )
        applied = {
            "color": color,
            "line_width": line_width,
            "bar_gap": bar_gap,
            "line_style": line_style,
            "symbol_kind": symbol_kind,
            "symbol_size": symbol_size,
            "transparency": transparency,
            "colormap": colormap,
            "contour_levels": contour_levels,
            "contour_minor_levels": contour_minor_levels,
            "color_scale_limits": color_scale_limits,
            "histogram_bin_width": histogram_bin_width,
            "errorbar_cap": errorbar_cap,
            "box_width": box_width,
        }
        return {
            "graph_name": graph_name_actual,
            "layer_index": layer_index,
            "styled_plots": len(selected_with_indexes),
            "applied": {key: value for key, value in applied.items() if value is not None},
        }

    def add_plot_to_graph(
        self,
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
        if x_col is None or y_col is None:
            raise OriginOperationError("x_col and y_col are required.")
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        wks = self._find_sheet_from_ref(worksheet)
        ref = self._worksheet_ref(wks)
        columns = ref.columns
        x_name = self._resolve_column(columns, x_col, default_index=0)
        y_name = self._resolve_column(columns, y_col, default_index=1)
        z_name = (
            self._resolve_column(columns, z_col, default_index=2) if z_col is not None else None
        )
        yerr_name = (
            self._resolve_column(columns, y_error_col, default_index=2)
            if y_error_col is not None
            else None
        )
        xerr_name = (
            self._resolve_column(columns, x_error_col, default_index=2)
            if x_error_col is not None
            else None
        )
        self._add_plot(
            layer,
            wks,
            x_name=x_name,
            y_name=y_name,
            kind=plot_type,
            z_name=z_name,
            y_error_name=yerr_name,
            x_error_name=xerr_name,
        )
        self._rescale(layer)
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "layer_index": layer_index,
            "worksheet": ref.as_dict(),
            "x_col": x_name,
            "y_col": y_name,
            "plot_type": plot_type,
        }

    def add_uncertainty_band(
        self,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        lower_col: str | int | None = None,
        upper_col: str | int | None = None,
        graph_name: str | None = None,
        layer_index: int = 0,
        fill_color: str | int | tuple[int, int, int] | None = None,
        transparency: float | None = None,
    ) -> dict[str, Any]:
        if x_col is None or lower_col is None or upper_col is None:
            raise OriginOperationError(
                "x_col, lower_col, and upper_col are required.",
                error_code="invalid_request",
            )
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        wks = self._find_sheet_from_ref(worksheet)
        ref = self._worksheet_ref(wks)
        columns = ref.columns
        x_name = self._resolve_column(columns, x_col, default_index=0)
        lower_name = self._resolve_column(columns, lower_col, default_index=1)
        upper_name = self._resolve_column(columns, upper_col, default_index=2)
        start_index = len(layer.plot_list())

        data_range = self._worksheet_range_expr(wks, columns, [x_name, lower_name, upper_name])
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        safe_graph = self._escape_labtalk(graph_name_actual)
        plot_script = f"plotxy iy:={data_range} plot:=249 ogl:=[{safe_graph}]{layer_index + 1};"
        result = self.run_labtalk(plot_script)
        if result.get("result") is False:
            raise OriginOperationError(f"Origin rejected uncertainty-band script: {plot_script}")

        end_index = len(layer.plot_list())
        plot_index = start_index if end_index <= start_index else end_index - 1
        fill_color_index = fill_color if isinstance(fill_color, int) else 4
        fill_script = self._fill_area_script(
            graph_name=graph_name_actual,
            layer_index=layer_index,
            plot_index=plot_index,
            fill_color_index=fill_color_index,
            transparency=transparency,
        )
        fill_result = self.run_labtalk(fill_script)
        if fill_result.get("result") is False:
            raise OriginOperationError(f"Origin rejected fill-area script: {fill_script}")
        self._rescale(layer)
        return {
            "graph_name": graph_name_actual,
            "layer_index": layer_index,
            "worksheet": ref.as_dict(),
            "x_col": x_name,
            "lower_col": lower_name,
            "upper_col": upper_name,
            "plot_indices": list(range(start_index, max(start_index + 1, end_index))),
            "fill_color": fill_color,
            "transparency": transparency,
            "plot_script": plot_script,
            "fill_script": fill_script,
        }

    def add_inset_layer(
        self,
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
        if x_col is None or not y_cols:
            raise OriginOperationError(
                "x_col and y_cols are required.", error_code="invalid_request"
            )
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        self._activate_graph(graph, graph_name_actual)

        # A new layer added with layadd is appended at the end; size and position
        # it inside the existing layer(s) so it reads as an inset. left/top/width/
        # height are percentages of the page.
        before = len(graph) if hasattr(graph, "__len__") else 1
        self.run_labtalk("layadd;")
        inset_index = before
        inset_layer = self._graph_layer(graph, inset_index)
        self.run_labtalk(
            f"layer -s {inset_index + 1}; "
            f"layer.left={float(left)}; layer.top={float(top)}; "
            f"layer.width={float(width)}; layer.height={float(height)};"
        )

        wks = self._find_sheet_from_ref(worksheet)
        ref = self._worksheet_ref(wks)
        columns = ref.columns
        x_name = self._resolve_column(columns, x_col, default_index=0)
        y_names = [self._resolve_column(columns, col, default_index=1) for col in y_cols]
        for y_name in y_names:
            self._add_plot(inset_layer, wks, x_name=x_name, y_name=y_name, kind=plot_type)
        if len(y_names) > 1:
            self._group_layer_plots(
                inset_layer, graph_name=graph_name_actual, layer_index=inset_index
            )

        zoomed = False
        if x_start is not None and x_end is not None:
            inset_layer.axis("x").limits = (x_start, x_end, None)
            zoomed = True
        if y_start is not None and y_end is not None:
            inset_layer.axis("y").limits = (y_start, y_end, None)
            zoomed = True
        if not zoomed:
            self._rescale(inset_layer)

        return {
            "graph_name": graph_name_actual,
            "inset_layer_index": inset_index,
            "geometry": {"left": left, "top": top, "width": width, "height": height},
            "worksheet": ref.as_dict(),
            "x_col": x_name,
            "y_cols": y_names,
            "plot_type": plot_type,
        }

    def remove_plot_from_graph(
        self,
        plot_index: int,
        graph_name: str | None = None,
        layer_index: int = 0,
    ) -> dict[str, Any]:
        if plot_index < 0:
            raise OriginOperationError("plot_index must be non-negative.")
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        plots = self._layer_plots(layer)
        try:
            plot = plots[plot_index]
        except IndexError as exc:
            raise OriginOperationError(f"plot_index is out of range: {plot_index}") from exc
        remover = getattr(plot, "remove", None) or getattr(plot, "destroy", None)
        if callable(remover):
            remover()
            result = {"result": True}
        else:
            graph_name_actual = self._object_name(graph, default=graph_name or "")
            self._activate_graph(graph, graph_name_actual)
            result = self.run_labtalk(f"layer -s {layer_index + 1}; layer -d {plot_index + 1};")
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "layer_index": layer_index,
            "removed_plot_index": plot_index,
            **result,
        }

    def change_plot_type(
        self,
        plot_index: int,
        plot_type: str,
        graph_name: str | None = None,
        layer_index: int = 0,
    ) -> dict[str, Any]:
        if not plot_type.strip():
            raise OriginOperationError("plot_type is empty.")
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        plots = self._layer_plots(layer)
        try:
            plot = plots[plot_index]
        except IndexError as exc:
            raise OriginOperationError(f"plot_index is out of range: {plot_index}") from exc
        self._set_plot_command(plot, f"-c {plot_type}")
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "layer_index": layer_index,
            "plot_index": plot_index,
            "plot_type": plot_type,
        }

    def change_plot_data(
        self,
        plot_index: int,
        worksheet: str | None,
        x_col: str | int,
        y_col: str | int,
        graph_name: str | None = None,
        layer_index: int = 0,
    ) -> dict[str, Any]:
        self.remove_plot_from_graph(
            plot_index=plot_index,
            graph_name=graph_name,
            layer_index=layer_index,
        )
        return self.add_plot_to_graph(
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            graph_name=graph_name,
            layer_index=layer_index,
        )

    def _clear_graph_plots(
        self,
        graph: Any,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        removed = 0
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        for layer_index, layer in enumerate(self._graph_layers(graph)):
            plots = self._layer_plots(layer)
            for plot_index in range(len(plots) - 1, -1, -1):
                plot = plots[plot_index]
                remover = getattr(plot, "remove", None) or getattr(plot, "destroy", None)
                if callable(remover):
                    remover()
                    layer_plots = getattr(layer, "plots", None)
                    if isinstance(layer_plots, list) and plot in layer_plots:
                        layer_plots.remove(plot)
                else:
                    self._activate_graph(graph, graph_name_actual)
                    self.run_labtalk(f"layer -s {layer_index + 1}; layer -d {plot_index + 1};")
                removed += 1
        return {"graph_name": graph_name_actual, "removed_plots": removed}

    def set_graph_page(
        self,
        graph_name: str | None = None,
        width: float | None = None,
        height: float | None = None,
        unit: str = "inch",
        left: float | None = None,
        top: float | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        updates: dict[str, Any] = {}
        if width is not None:
            self._set_origin_property(graph, "width", width)
            updates["width"] = width
        if height is not None:
            self._set_origin_property(graph, "height", height)
            updates["height"] = height
        if left is not None:
            self._set_origin_property(graph, "left", left)
            updates["left"] = left
        if top is not None:
            self._set_origin_property(graph, "top", top)
            updates["top"] = top
        if unit:
            updates["unit"] = unit
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "page": updates,
        }

    def arrange_layers(
        self,
        graph_name: str | None = None,
        rows: int = 1,
        columns: int = 1,
        gap_x: float | None = None,
        gap_y: float | None = None,
        layer_geometries: list[dict[str, float | int]] | None = None,
    ) -> dict[str, Any]:
        if rows < 1 or columns < 1:
            raise OriginOperationError("rows and columns must be at least 1.")
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        self._activate_graph(graph, graph_name_actual)
        args = [f"row:={rows}", f"col:={columns}"]
        if gap_x is not None:
            args.append(f"xgap:={gap_x}")
        if gap_y is not None:
            args.append(f"ygap:={gap_y}")
        script = "layarrange " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        geometry_script = None
        geometry_result = None
        if layer_geometries:
            geometry_parts = []
            for item in layer_geometries:
                index = int(item["layer_index"])
                geometry_parts.append(
                    f"layer -s {index + 1}; "
                    f"layer.left={float(item['left'])}; "
                    f"layer.top={float(item['top'])}; "
                    f"layer.width={float(item['width'])}; "
                    f"layer.height={float(item['height'])};"
                )
            geometry_script = " ".join(geometry_parts)
            geometry_result = self.run_labtalk(geometry_script)
        return {
            "graph_name": graph_name_actual,
            "rows": rows,
            "columns": columns,
            "script": script,
            "layer_geometries": layer_geometries or [],
            "geometry_script": geometry_script,
            "geometry_result": geometry_result,
            **result,
        }

    def merge_graphs(
        self,
        graph_names: list[str],
        output_name: str | None = None,
        rows: int | None = None,
        columns: int | None = None,
        keep_sources: bool = True,
        arrange: bool = True,
        direction: str = "horizontal",
        gap_x: float = 2,
        gap_y: float = 2,
        margins: tuple[float, float, float, float] = (5, 5, 5, 5),
        unit: str = "percent",
        width: float | None = None,
        height: float | None = None,
        label_style: str = "none",
        custom_label: str | None = None,
        link_layers: bool = False,
        common_x_scale: bool = False,
        common_y_scale: bool = False,
    ) -> dict[str, Any]:
        """Merge existing graph pages into a publication-style multi-panel graph."""

        resolved = self._validated_graph_names(graph_names)
        rows, columns = self._panel_grid(len(resolved), rows, columns)
        unit_key = self._merge_unit(unit)
        if common_y_scale:
            self.ensure_feature(
                "origin_2026b_or_newer",
                "Common Y-scale sizing in merged graphs",
            )
        label_key = label_style.strip()
        if label_key not in {"none", "capitalA", "a", "custom"}:
            raise OriginOperationError("label_style must be none, capitalA, a, or custom.")
        if label_key == "custom" and not custom_label:
            raise OriginOperationError("custom_label is required for label_style='custom'.")

        graph_expr = "+char(10)$+".join(f'"{self._escape_labtalk(name)}"' for name in resolved)
        left, right, top, bottom = margins
        args = [
            "option:=specified",
            f"graphs:={graph_expr}",
            f"keep:={int(keep_sources)}",
            f"arrange:={int(arrange)}",
            f"row:={rows}",
            f"col:={columns}",
            f"dir:={'horz' if direction.strip().lower().startswith('h') else 'vert'}",
            f"xgap:={float(gap_x)}",
            f"ygap:={float(gap_y)}",
            f"leftmg:={float(left)}",
            f"rightmg:={float(right)}",
            f"topmg:={float(top)}",
            f"bottommg:={float(bottom)}",
            f"spaceunit:={unit_key}",
            f"labeltext:={label_key}",
            f"linkarrange:={int(link_layers)}",
        ]
        if common_x_scale:
            args.append("resizewidthbyscale:=1")
        if common_y_scale:
            args.append("resizeheightbyscale:=1")
        if width is not None:
            args.extend((f"width:={float(width)}", f"unit:={unit_key}"))
        if height is not None:
            args.extend((f"height:={float(height)}", f"unit:={unit_key}"))
        if custom_label:
            args.append(f'labelcustom:="{self._escape_labtalk(custom_label)}"')
        safe_output_name = self._safe_graph_name(output_name) if output_name else None

        before = self._graph_page_names()
        script = "merge_graph " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected merge_graph.", error_code="graph_merge_failed"
            )
        after = self._graph_page_names()
        created = sorted(after - before)
        created_name = created[0] if len(created) == 1 else None
        actual_name = created_name
        if safe_output_name and created_name:
            renamed = self.rename_object(created_name, safe_output_name, object_type="graph")
            actual_name = str(renamed["new_name"])
        elif safe_output_name:
            actual_name = safe_output_name
        if output_name and actual_name:
            self._remember_graph_alias(output_name, actual_name)
        return {
            "graph_names": resolved,
            "output_graph": actual_name,
            "created_graphs": created,
            "rows": rows,
            "columns": columns,
            "script": script,
            **result,
        }

    def create_graph_layout(
        self,
        graph_names: list[str],
        rows: int | None = None,
        columns: int | None = None,
        keep_aspect_ratio: bool = False,
        gap_x: float = 5,
        gap_y: float = 5,
        margins: tuple[float, float, float, float] = (15, 10, 10, 15),
        width: float | None = None,
        height: float | None = None,
        unit: str = "inch",
    ) -> dict[str, Any]:
        """Create an Origin Layout page containing linked existing graphs."""

        resolved = self._validated_graph_names(graph_names)
        rows, columns = self._panel_grid(len(resolved), rows, columns)
        graph_expr = "+char(10)$+".join(f'"{self._escape_labtalk(name)}"' for name in resolved)
        left, right, top, bottom = margins
        unit_key = self._merge_unit(unit)
        args = [
            "option:=specified",
            f"graphs:={graph_expr}",
            f"row:={rows}",
            f"col:={columns}",
            f"aspectratio:={int(keep_aspect_ratio)}",
            f"xgap:={float(gap_x)}",
            f"ygap:={float(gap_y)}",
            f"leftmg:={float(left)}",
            f"rightmg:={float(right)}",
            f"topmg:={float(top)}",
            f"bottommg:={float(bottom)}",
        ]
        if width is not None:
            args.append(f"width:={float(width)}")
        if height is not None:
            args.append(f"height:={float(height)}")
        if width is not None or height is not None:
            args.append(f"unit:={unit_key}")
        script = "g2layout " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected g2layout.", error_code="graph_layout_failed"
            )
        return {
            "graph_names": resolved,
            "rows": rows,
            "columns": columns,
            "script": script,
            **result,
        }

    def link_graph_layers(
        self,
        graph_name: str,
        source_layer: int,
        destination_layers: list[int],
        link_x: bool | None = True,
        link_y: bool | None = False,
        unit: str = "link",
    ) -> dict[str, Any]:
        """Link destination-layer scales and geometry to a source layer."""

        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name)
        self._validate_layer_indexes(graph, [source_layer, *destination_layers])
        if source_layer in destination_layers:
            raise OriginOperationError("source_layer cannot also be a destination layer.")
        if not destination_layers:
            raise OriginOperationError("destination_layers cannot be empty.")
        unit_key = self._merge_unit(unit, allow_link=True)
        selector = self._layer_selector(destination_layers)
        args = [
            f"igp:=[{self._safe_graph_name(graph_name_actual)}]",
            f"igl:=layer{source_layer + 1}",
            f'destlayers:="{selector}"',
            f"XAxis:={-1 if link_x is None else int(link_x)}",
            f"YAxis:={-1 if link_y is None else int(link_y)}",
            f"unit:={unit_key}",
        ]
        script = "laylink " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError("Origin rejected laylink.", error_code="graph_link_failed")
        return {
            "graph_name": graph_name_actual,
            "source_layer": source_layer,
            "destination_layers": sorted(destination_layers),
            "link_x": link_x,
            "link_y": link_y,
            "script": script,
            **result,
        }

    def copy_layer_scale(
        self,
        graph_name: str,
        source_layer: int,
        destination_layers: list[int],
        axis: int = 0,
    ) -> dict[str, Any]:
        """Copy Origin axis scale settings from one layer to other layers."""

        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name)
        self._validate_layer_indexes(graph, [source_layer, *destination_layers])
        if not destination_layers:
            raise OriginOperationError("destination_layers cannot be empty.")
        selector = self._layer_selector(destination_layers)
        script = (
            f"laycopyscale igp:=[{self._safe_graph_name(graph_name_actual)}] "
            f"igl:={source_layer + 1} dest:={selector} axis:={int(axis)};"
        )
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected laycopyscale.", error_code="graph_scale_copy_failed"
            )
        return {
            "graph_name": graph_name_actual,
            "source_layer": source_layer,
            "destination_layers": sorted(destination_layers),
            "axis": axis,
            "script": script,
            **result,
        }

    def extract_graph_layers(
        self,
        graph_name: str,
        layer_indexes: list[int],
        keep_source: bool = True,
        full_page: bool = True,
    ) -> dict[str, Any]:
        """Extract selected layers into separate graph pages."""

        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name)
        self._validate_layer_indexes(graph, layer_indexes)
        if not layer_indexes:
            raise OriginOperationError("layer_indexes cannot be empty.")
        before = self._graph_page_names()
        selector = self._layer_selector(layer_indexes)
        script = (
            f"layextract igp:=[{self._safe_graph_name(graph_name_actual)}] "
            f'layer:="{selector}" keep:={int(keep_source)} fullpage:={int(full_page)};'
        )
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected layextract.", error_code="graph_layer_extract_failed"
            )
        created = sorted(self._graph_page_names() - before)
        return {
            "graph_name": graph_name_actual,
            "layer_indexes": sorted(layer_indexes),
            "created_graphs": created,
            "script": script,
            **result,
        }

    def _validated_graph_names(self, graph_names: list[str]) -> list[str]:
        if not graph_names:
            raise OriginOperationError("graph_names cannot be empty.")
        resolved = []
        for name in graph_names:
            graph = self._find_or_active_graph(name)
            resolved.append(self._object_name(graph, default=name))
        if len(set(resolved)) != len(resolved):
            raise OriginOperationError("graph_names must not contain duplicates.")
        return resolved

    @staticmethod
    def _panel_grid(count: int, rows: int | None, columns: int | None) -> tuple[int, int]:
        if rows is None and columns is None:
            columns = max(1, math.ceil(math.sqrt(count)))
            rows = math.ceil(count / columns)
        elif rows is None:
            if columns is None or columns < 1:
                raise OriginOperationError("columns must be at least 1.")
            rows = math.ceil(count / columns)
        elif columns is None:
            if rows < 1:
                raise OriginOperationError("rows must be at least 1.")
            columns = math.ceil(count / rows)
        if rows < 1 or columns < 1 or rows * columns < count:
            raise OriginOperationError("rows * columns must fit every selected graph.")
        return rows, columns

    @staticmethod
    def _safe_graph_name(value: str) -> str:
        clean = value.strip()
        if not clean or any(char in clean for char in (";", '"', "[", "]", "\n", "\r")):
            raise OriginOperationError("Invalid graph page name.", error_code="invalid_request")
        return clean

    @staticmethod
    def _merge_unit(value: str, allow_link: bool = False) -> str:
        aliases = {"%": "percent", "page": "percent", "pixels": "pixel", "points": "point"}
        clean = aliases.get(value.strip().lower(), value.strip().lower())
        allowed = {"percent", "inch", "cm", "mm", "pixel", "point"}
        if allow_link:
            allowed.add("link")
        if clean not in allowed:
            raise OriginOperationError(f"Unsupported graph layout unit: {value}.")
        return clean

    @staticmethod
    def _layer_selector(indexes: list[int]) -> str:
        values = sorted(set(index + 1 for index in indexes))
        if any(value < 1 for value in values):
            raise OriginOperationError("Layer indexes must be non-negative.")
        runs: list[str] = []
        start = previous = values[0]
        for value in values[1:]:
            if value == previous + 1:
                previous = value
                continue
            runs.append(str(start) if start == previous else f"{start}:{previous}")
            start = previous = value
        runs.append(str(start) if start == previous else f"{start}:{previous}")
        return ",".join(runs)

    @staticmethod
    def _validate_layer_indexes(graph: Any, indexes: list[int]) -> None:
        count = len(graph) if hasattr(graph, "__len__") else 0
        for index in indexes:
            if index < 0 or index >= count:
                raise OriginOperationError(f"layer_index is out of range: {index}")

    def add_graph_label(
        self,
        text: str,
        graph_name: str | None = None,
        layer_index: int = 0,
        name: str | None = None,
        left: int | None = None,
        top: int | None = None,
        font_size: int | None = None,
    ) -> dict[str, Any]:
        if not text.strip():
            raise OriginOperationError("Label text is empty.")
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        add_label = getattr(layer, "add_label", None)
        if not callable(add_label):
            raise OriginOperationError("Graph layer does not support add_label().")
        formatted_text = self._label_text(text)
        label = add_label(formatted_text)
        if name:
            try:
                label.name = name
            except Exception:
                pass
        if left is not None:
            self._set_origin_property(label, "left", left)
        if top is not None:
            self._set_origin_property(label, "top", top)
        if font_size is not None:
            self._set_origin_property(label, "fsize", font_size)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        label_name = self._object_name(label, default=name or "")
        self._remember_graph_label(
            graph_name=graph_name_actual,
            layer_index=layer_index,
            name=label_name,
            text=formatted_text,
        )
        return {
            "graph_name": graph_name_actual,
            "layer_index": layer_index,
            "label_name": label_name,
            "text": text,
            "formatted_text": formatted_text,
        }

    def add_reference_line(
        self,
        value: float,
        axis: str = "y",
        graph_name: str | None = None,
        layer_index: int = 0,
        label: str | None = None,
    ) -> dict[str, Any]:
        if axis.lower() not in {"x", "y"}:
            raise OriginOperationError("Reference lines currently support only x or y axes.")
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        self._activate_graph(graph, graph_name_actual)
        orientation = "x" if axis.lower() == "x" else "y"
        line_name = f"ref_{orientation}_{str(value).replace('.', '_')}"
        script_parts = [
            f"layer -s {layer_index + 1};",
            f"draw -n {line_name} -l {orientation} {value};",
        ]
        if label:
            formatted_label = self._label_text(label)
            script_parts.append(
                f'label -s -sa -n ref_label "{self._escape_labtalk(formatted_label)}";'
            )
        script = " ".join(script_parts)
        result = self.run_labtalk(script)
        return {
            "graph_name": graph_name_actual,
            "layer_index": layer_index,
            "axis": axis.lower(),
            "value": value,
            "script": script,
            **result,
        }

    def format_legend(
        self,
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
        graph = self._find_or_active_graph(graph_name)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        legend = layer.label("Legend")
        if legend is None:
            self._set_legend(layer, show=True)
            legend = layer.label("Legend")
        if legend is None:
            raise OriginOperationError("Legend object was not found or created.")
        if text is not None:
            legend.text = text
        if font_size is not None:
            legend.set_int("fsize", font_size)
        # Re-assert the legend font here, after any legend (re)creation above. The
        # legend object is rebuilt by ``legend -r`` (losing its font), while axis
        # fonts are sticky, so the font must be applied as a final step to avoid the
        # legend reverting to the template default while the rest stays styled.
        if font_family is not None:
            self._set_legend_font(graph_name_actual, font_family)
        if show_frame is not None:
            legend.set_int("showframe", int(show_frame))
        position_result = self._position_legend(
            graph_name=graph_name_actual,
            layer_index=0,
            legend=legend,
            left=left,
            top=top,
            position=position,
            margin_percent=margin_percent,
            coordinate_mode=coordinate_mode,
        )
        return {
            "graph_name": graph_name_actual,
            "legend": True,
            "position": position_result,
        }

    def get_graph_info(self, graph_name: str | None = None) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        layers = []
        layer_count = len(graph) if hasattr(graph, "__len__") else 1
        for index in range(layer_count):
            layers.append(self._layer_info(graph, index, graph_name_actual))
        return {
            "graph_name": graph_name_actual,
            "long_name": getattr(graph, "lname", ""),
            "layers_count": layer_count,
            "layers": layers,
        }

    def get_layer_info(
        self,
        graph_name: str | None = None,
        layer_index: int = 0,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        return {
            "graph_name": graph_name_actual,
            "layer": self._layer_info(graph, layer_index, graph_name_actual),
        }

    def format_graph(
        self,
        graph_name: str | None = None,
        graph: Any | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        show_legend: bool | None = None,
        rescale: bool = True,
    ) -> dict[str, Any]:
        target = graph if graph is not None else self._find_or_active_graph(graph_name)
        layer = target[0] if hasattr(target, "__getitem__") else target

        if x_label:
            layer.axis("x").title = self._label_text(x_label)
        if y_label:
            layer.axis("y").title = self._label_text(y_label)
        if title:
            self._set_page_long_name(target, title, force_labtalk=graph_name is not None)

        if show_legend is not None:
            self._set_legend(layer, show=show_legend)
        if rescale:
            self._rescale(layer)
        object_graph_name = self._object_name(target, default="")
        graph_name_actual = object_graph_name or graph_name or "Graph"
        title_command_graph_name = None
        if graph_name is not None:
            title_command_graph_name = graph_name
        elif self._supports_graph_page_commands(target):
            title_command_graph_name = object_graph_name
        self._suppress_graph_title_text(
            graph=target,
            graph_name=title_command_graph_name,
            title=title,
        )

        return {
            "graph_name": graph_name_actual,
            "formatted": True,
        }
