from __future__ import annotations

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
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        layer = self._graph_layer(graph, layer_index)
        plots = layer.plot_list()
        selected = plots if plot_index is None else [plots[plot_index]]
        for plot in selected:
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
        return {
            "graph_name": self._object_name(graph, default=graph_name or ""),
            "layer_index": layer_index,
            "styled_plots": len(selected),
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
    ) -> dict[str, Any]:
        if rows < 1 or columns < 1:
            raise OriginOperationError("rows and columns must be at least 1.")
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        self._activate_graph(graph, graph_name_actual)
        args = [f"row:={rows}", f"col:={columns}"]
        if gap_x is not None:
            args.append(f"vgap:={gap_x}")
        if gap_y is not None:
            args.append(f"hgap:={gap_y}")
        script = "layarrange " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        return {
            "graph_name": graph_name_actual,
            "rows": rows,
            "columns": columns,
            "script": script,
            **result,
        }

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
