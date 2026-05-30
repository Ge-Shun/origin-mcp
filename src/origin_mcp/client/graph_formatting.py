from __future__ import annotations

from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase


class _GraphFormattingMixin(_OriginClientBase):
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
        axis: str = "x",
        scale: str | int | None = None,
        start: float | None = None,
        end: float | None = None,
        step: float | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph
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
            "axis": axis,
            "requested": {key: value for key, value in requested.items() if value is not None},
            "axis_info": axis_info,
            "verified": self._axis_settings_verified(requested, axis_info),
        }

    def set_plot_style(
        self,
        graph_name: str | None = None,
        plot_index: int | None = None,
        color: str | tuple[int, int, int] | None = None,
        line_width: float | None = None,
        line_style: int | None = None,
        symbol_kind: int | None = None,
        symbol_size: float | None = None,
        transparency: float | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph
        plots = layer.plot_list()
        selected = plots if plot_index is None else [plots[plot_index]]
        for plot in selected:
            if color is not None:
                plot.color = color
            if line_width is not None:
                plot.set_cmd(f"-w {line_width}")
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

    def _find_or_active_graph(self, graph_name: str | None) -> Any:
        op = self.op
        if hasattr(op, "find_graph"):
            graph = op.find_graph(graph_name or "")
            if graph is not None:
                return graph
            alias = self._graph_aliases.get(graph_name or "")
            if alias:
                graph = op.find_graph(alias)
                if graph is not None:
                    return graph
        if graph_name:
            graph = self._find_graph_by_long_name(graph_name)
            if graph is not None:
                return graph

        if graph_name:
            raise OriginOperationError(
                f"Graph not found: {graph_name}",
                error_code="graph_not_found",
            )

        raise OriginOperationError("No active graph found. Create or name a graph first.")

    def _find_graph_by_long_name(self, graph_name: str) -> Any | None:
        op = self._op
        if op is None:
            return None
        pages = getattr(op, "pages", None)
        if not callable(pages):
            return None
        try:
            candidates = pages()
        except Exception:
            return None
        try:
            for page in candidates:
                cls_name = type(page).__name__.lower()
                if cls_name and cls_name != "gpage":
                    continue
                if self._object_long_name(page, default="") == graph_name:
                    return page
        except Exception:
            return None
        return None

    def _remember_graph_alias(
        self,
        requested_graph_name: str | None,
        actual_graph_name: str | None,
    ) -> None:
        if not requested_graph_name or not actual_graph_name:
            return
        self._graph_aliases[requested_graph_name] = actual_graph_name

    def _graph_page_names(self) -> set[str]:
        op = self._op
        if op is None:
            return set()
        pages = getattr(op, "pages", None)
        if not callable(pages):
            return set()
        try:
            candidates = pages()
        except Exception:
            return set()
        names = set()
        try:
            for page in candidates:
                if type(page).__name__.lower() != "gpage":
                    continue
                name = self._object_name(page, default="")
                if name:
                    names.add(name)
        except Exception:
            return set()
        return names

    def _created_graph_name(
        self,
        requested_graph_name: str,
        existing_graphs: set[str],
    ) -> str:
        graph = self._find_graph_optional(requested_graph_name)
        if graph is not None:
            return self._object_name(graph, default=requested_graph_name)

        created = self._graph_page_names() - existing_graphs
        if len(created) == 1:
            return next(iter(created))
        return requested_graph_name

    def _find_graph_optional(self, graph_name: str) -> Any | None:
        op = self._op
        if op is None:
            return None
        find_graph = getattr(op, "find_graph", None)
        if callable(find_graph):
            try:
                graph = find_graph(graph_name)
            except Exception:
                graph = None
            if graph is not None:
                return graph
        return self._find_graph_by_long_name(graph_name)

    def _graph_display_name(self, graph_name: str, default: str | None = None) -> str | None:
        graph = self._find_graph_optional(graph_name)
        if graph is None:
            return default
        return self._object_long_name(graph, default=default)

    def _add_plot(
        self,
        layer: Any,
        wks: Any,
        x_name: str,
        y_name: str,
        kind: str,
        z_name: str | None = None,
        y_error_name: str | None = None,
        x_error_name: str | None = None,
    ) -> None:
        add_plot = getattr(layer, "add_plot", None)
        if not callable(add_plot):
            raise OriginOperationError("Graph layer does not support add_plot().")

        plot_types = {
            "scatter": "s",
            "s": "s",
            "line": "l",
            "l": "l",
            "line_symbol": "y",
            "linesymbol": "y",
            "y": "y",
            "column": "c",
            "c": "c",
            "contour": "contour",
            "histogram": "histogram",
            "box": "box",
            "heatmap": "heatmap",
            "scatter3d": "3dscatter",
            "surface3d": "surface",
            "polar": "polar",
        }
        plot_type = plot_types.get(kind, "l")
        attempts = [
            {
                "coly": y_name,
                "colx": x_name,
                "colz": z_name or -1,
                "colyerr": y_error_name or -1,
                "colxerr": x_error_name or -1,
                "type": plot_type,
            },
            {"coly": y_name, "colx": x_name},
        ]
        for kwargs in attempts:
            try:
                add_plot(wks, **kwargs)
                return
            except TypeError:
                continue

        add_plot(wks, y_name, x_name)

    def _rescale(self, layer: Any) -> None:
        for name in ("rescale", "rescale_axis"):
            func = getattr(layer, name, None)
            if callable(func):
                func()
                return
        self.run_labtalk("layer -a;")

    def _set_legend(self, layer: Any, show: bool) -> None:
        if show:
            lt_exec = getattr(getattr(layer, "obj", None), "LT_execute", None)
            if callable(lt_exec):
                lt_exec("legend -r;")
            else:
                self.run_labtalk("legend -r;")
            return

        label = getattr(layer, "label", lambda _name: None)("Legend")
        if label is not None:
            remove = getattr(label, "remove", None)
            if callable(remove):
                remove()

    def _position_legend(
        self,
        graph_name: str,
        layer_index: int,
        legend: Any,
        left: int | None,
        top: int | None,
        position: str | None,
        margin_percent: float,
        coordinate_mode: str,
    ) -> dict[str, Any] | None:
        if left is None and top is None and position is None:
            return None

        mode = (coordinate_mode or "auto").strip().lower()
        if mode not in {"auto", "layer_percent", "page_pixel"}:
            raise OriginOperationError(
                "coordinate_mode must be one of: auto, layer_percent, page_pixel."
            )

        if left is not None or top is not None:
            if left is None or top is None:
                raise OriginOperationError("left and top must be provided together.")
            use_layer_percent = mode == "layer_percent" or (
                mode == "auto" and 0 <= left <= 100 and 0 <= top <= 100
            )
            if use_layer_percent:
                script = self._legend_layer_percent_script(
                    graph_name=graph_name,
                    layer_index=layer_index,
                    left_percent=float(left),
                    top_percent=float(top),
                )
                result = self.run_labtalk(script)
                return {
                    "mode": "layer_percent",
                    "left_percent": left,
                    "top_percent": top,
                    "script": script,
                    **result,
                }

            legend.set_int("left", int(left))
            legend.set_int("top", int(top))
            return {"mode": "page_pixel", "left": left, "top": top}

        normalized = position.strip().lower().replace("-", "_")
        aliases = {
            "upper_left": "inside_upper_left",
            "top_left": "inside_upper_left",
            "inside_top_left": "inside_upper_left",
            "upper_right": "inside_upper_right",
            "top_right": "inside_upper_right",
            "inside_top_right": "inside_upper_right",
            "lower_left": "inside_lower_left",
            "bottom_left": "inside_lower_left",
            "inside_bottom_left": "inside_lower_left",
            "lower_right": "inside_lower_right",
            "bottom_right": "inside_lower_right",
            "inside_bottom_right": "inside_lower_right",
        }
        normalized = aliases.get(normalized, normalized)
        supported = {
            "inside_upper_left",
            "inside_upper_right",
            "inside_lower_left",
            "inside_lower_right",
        }
        if normalized not in supported:
            raise OriginOperationError(
                f"Unsupported legend position: {position!r}. Supported: {sorted(supported)}."
            )

        script = self._legend_anchor_script(
            graph_name=graph_name,
            layer_index=layer_index,
            position=normalized,
            margin_percent=margin_percent or 0.0,
        )
        result = self.run_labtalk(script)
        return {
            "mode": "layer_anchor",
            "position": normalized,
            "margin_percent": margin_percent,
            "script": script,
            **result,
        }

    def _legend_anchor_script(
        self,
        graph_name: str,
        layer_index: int,
        position: str,
        margin_percent: float,
    ) -> str:
        margin = max(float(margin_percent), 0.0) / 100.0
        x_left = f"layer.x.from+(layer.x.to-layer.x.from)*{margin:.6g}+legend.dx/2"
        x_right = f"layer.x.to-(layer.x.to-layer.x.from)*{margin:.6g}-legend.dx/2"
        y_upper = f"layer.y.to-(layer.y.to-layer.y.from)*{margin:.6g}-legend.dy/2"
        y_lower = f"layer.y.from+(layer.y.to-layer.y.from)*{margin:.6g}+legend.dy/2"
        x_expr = x_right if position.endswith("_right") else x_left
        y_expr = y_lower if "_lower_" in position else y_upper
        return self._legend_position_script(graph_name, layer_index, x_expr, y_expr)

    def _legend_layer_percent_script(
        self,
        graph_name: str,
        layer_index: int,
        left_percent: float,
        top_percent: float,
    ) -> str:
        x_fraction = left_percent / 100.0
        y_fraction = top_percent / 100.0
        x_expr = f"layer.x.from+(layer.x.to-layer.x.from)*{x_fraction:.6g}+legend.dx/2"
        y_expr = f"layer.y.to-(layer.y.to-layer.y.from)*{y_fraction:.6g}-legend.dy/2"
        return self._legend_position_script(graph_name, layer_index, x_expr, y_expr)

    def _legend_position_script(
        self,
        graph_name: str,
        layer_index: int,
        x_expr: str,
        y_expr: str,
    ) -> str:
        parts = []
        if graph_name:
            parts.append(f'win -a "{self._escape_labtalk(graph_name)}";')
        parts.extend(
            [
                f"layer -s {layer_index + 1};",
                f"legend.x={x_expr};",
                f"legend.y={y_expr};",
            ]
        )
        return " ".join(parts)

    def _set_page_long_name(
        self,
        page: Any,
        long_name: str,
        force_labtalk: bool = False,
    ) -> None:
        page_name = self._object_name(page, default="")
        try:
            page.lname = long_name
        except Exception:
            pass
        if not page_name or (not force_labtalk and not self._supports_graph_page_commands(page)):
            return
        try:
            safe_page = self._escape_labtalk(page_name)
            safe_long_name = self._escape_labtalk(long_name)
            self.run_labtalk(f'win -a "{safe_page}"; page.longname$="{safe_long_name}";')
        except Exception:
            pass

    def _suppress_graph_title_text(
        self,
        graph_name: str | None = None,
        graph: Any | None = None,
        title: str | None = None,
    ) -> None:
        target = graph

        candidates = self._graph_title_text_candidates(target, graph_name, title)
        if target is not None:
            layer_count = len(target) if hasattr(target, "__len__") else 1
            for index in range(layer_count):
                try:
                    layer = target[index] if hasattr(target, "__getitem__") else target
                except Exception:
                    continue
                self._suppress_layer_title_text(layer, candidates)

        page_name = graph_name or ""
        if page_name:
            try:
                safe_page = self._escape_labtalk(page_name)
                self.run_labtalk(
                    f'win -a "{safe_page}"; '
                    'title.show=0; title.text$=""; '
                    'Title.show=0; Title.text$=""; '
                    'GraphTitle.show=0; GraphTitle.text$="";'
                )
            except Exception:
                pass

    def _suppress_layer_title_text(self, layer: Any, candidates: set[str]) -> None:
        labels = getattr(layer, "labels", None)
        if isinstance(labels, dict):
            for key, label in list(labels.items()):
                if self._is_graph_title_label(str(key), label, candidates):
                    self._remove_or_clear_label(label)
                    labels.pop(key, None)

        label_getter = getattr(layer, "label", None)
        if callable(label_getter):
            for name in ("title", "Title", "GraphTitle", "Graph Title"):
                try:
                    label = label_getter(name)
                except Exception:
                    continue
                if label is not None:
                    self._remove_or_clear_label(label)

    @staticmethod
    def _supports_graph_page_commands(graph: Any) -> bool:
        return bool(
            graph is not None
            and (
                hasattr(graph, "save_fig")
                or hasattr(graph, "obj")
                or graph.__class__.__module__.startswith("originpro")
            )
        )

    @staticmethod
    def _remove_or_clear_label(label: Any) -> None:
        remove = getattr(label, "remove", None)
        if callable(remove):
            try:
                remove()
                return
            except Exception:
                pass
        for attr, value in (("text", ""), ("show", False), ("visible", False)):
            try:
                setattr(label, attr, value)
            except Exception:
                pass

    def _graph_title_text_candidates(
        self,
        graph: Any | None,
        graph_name: str | None,
        title: str | None,
    ) -> set[str]:
        values = {
            graph_name,
            title,
            self._object_name(graph, default="") if graph is not None else None,
            str(getattr(graph, "lname", "")) if graph is not None else None,
        }
        return {self._plain_label_text(str(value)) for value in values if value}

    @classmethod
    def _is_graph_title_label(cls, name: str, label: Any, candidates: set[str]) -> bool:
        name_key = name.strip().lower().replace(" ", "").replace("_", "")
        object_name = cls._object_name(label, default="")
        object_key = object_name.strip().lower().replace(" ", "").replace("_", "")
        if name_key in {"title", "graphtitle"} or object_key in {"title", "graphtitle"}:
            return True
        text = cls._plain_label_text(str(getattr(label, "text", "") or ""))
        return bool(text and text in candidates)

    @staticmethod
    def _plain_label_text(value: str) -> str:
        return value.replace("\r", "\n").strip().casefold()

    def _activate_graph(self, graph: Any, graph_name: str) -> None:
        activate = getattr(graph, "activate", None)
        if callable(activate):
            activate()
            return
        if graph_name:
            self.run_labtalk(f"win -a {graph_name};")

    @staticmethod
    def _layer_plots(layer: Any) -> list[Any]:
        plot_list = getattr(layer, "plot_list", None)
        if not callable(plot_list):
            raise OriginOperationError("Graph layer does not support plot_list().")
        return list(plot_list())

    def _selected_layer_indexes(self, graph: Any, layer_index: int | None) -> list[int]:
        if layer_index is not None:
            self._graph_layer(graph, layer_index)
            return [layer_index]
        layer_count = len(graph) if hasattr(graph, "__len__") else 1
        return list(range(layer_count))

    def _layer_info(
        self,
        graph: Any,
        layer_index: int,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        layer = self._graph_layer(graph, layer_index)
        plots = self._layer_plots(layer)
        labels = self._layer_labels(layer)
        if graph_name:
            labels.extend(self._graph_annotations.get((graph_name, layer_index), []))
        axes: dict[str, dict[str, Any]] = {}
        for axis_name in ("x", "y", "z"):
            axis = getattr(layer, "axis", lambda _name: None)(axis_name)
            if axis is None:
                continue
            axes[axis_name] = self._axis_info(axis)
        return {
            "index": layer_index,
            "name": self._object_name(layer, default=f"Layer{layer_index + 1}"),
            "plots_count": len(plots),
            "plots": [self._plot_info(plot, index) for index, plot in enumerate(plots)],
            "axes": axes,
            "labels": labels,
            "legend_present": any(label["name"].lower() == "legend" for label in labels),
            "panel_label_present": self._panel_label_present(labels),
        }

    def _plot_info(self, plot: Any, index: int) -> dict[str, Any]:
        return {
            "index": index,
            "name": self._object_name(plot, default=f"Plot{index + 1}"),
            "color": self._safe_origin_attr(plot, "color"),
            "line_width": self._safe_origin_attr(plot, "line_width"),
            "line_style": self._safe_origin_attr(plot, "line_style"),
            "symbol_kind": self._safe_origin_attr(plot, "symbol_kind"),
            "symbol_size": self._safe_origin_attr(plot, "symbol_size"),
            "transparency": self._safe_origin_attr(plot, "transparency"),
        }

    @classmethod
    def _axis_info(cls, axis: Any) -> dict[str, Any]:
        scale = cls._safe_origin_attr(axis, "scale")
        return {
            "title": cls._safe_origin_attr(axis, "title"),
            "scale": scale,
            "scale_name": cls._axis_scale_name(scale),
            "limits": cls._safe_origin_attr(axis, "limits"),
        }

    @classmethod
    def _axis_settings_verified(
        cls,
        requested: dict[str, Any],
        axis_info: dict[str, Any],
    ) -> bool | None:
        checks: list[bool] = []
        if requested.get("scale") is not None:
            checks.append(
                cls._axis_scale_name(requested["scale"]) == axis_info.get("scale_name")
                or requested["scale"] == axis_info.get("scale")
            )
        if requested.get("title") is not None:
            checks.append(axis_info.get("title") == requested["title"])
        limits = axis_info.get("limits")
        if isinstance(limits, (list, tuple)):
            for index, key in enumerate(("start", "end", "step")):
                if requested.get(key) is not None and index < len(limits):
                    checks.append(limits[index] == requested[key])
        elif any(requested.get(key) is not None for key in ("start", "end", "step")):
            checks.append(False)
        return all(checks) if checks else None

    @staticmethod
    def _axis_scale_value(scale: str | int) -> str | int:
        if isinstance(scale, int):
            return scale
        aliases = {
            "linear": 1,
            "lin": 1,
            "log": 2,
            "log10": 2,
            "logarithmic": 2,
        }
        return aliases.get(scale.strip().lower(), scale)

    @staticmethod
    def _axis_scale_name(scale: Any) -> str | None:
        if scale is None:
            return None
        if isinstance(scale, str):
            value = scale.strip().lower()
            if value in {"lin", "linear"}:
                return "linear"
            if value in {"log", "log10", "logarithmic"}:
                return "log10"
            return value
        names = {
            1: "linear",
            2: "log10",
        }
        return names.get(scale, str(scale))

    @staticmethod
    def _layer_labels(layer: Any) -> list[dict[str, Any]]:
        labels: list[dict[str, Any]] = []
        layer_labels = getattr(layer, "labels", None)
        if isinstance(layer_labels, dict):
            iterable = layer_labels.items()
        else:
            iterable = []
        for name, label in iterable:
            label_name = _OriginClientBase._object_name(label, default=str(name))
            labels.append(
                {
                    "name": label_name,
                    "text": getattr(label, "text", None),
                }
            )
        label_getter = getattr(layer, "label", None)
        if callable(label_getter) and not any(label["name"] == "Legend" for label in labels):
            try:
                legend = label_getter("Legend")
            except Exception:
                legend = None
            if legend is not None:
                labels.append(
                    {
                        "name": "Legend",
                        "text": getattr(legend, "text", None),
                    }
                )
        return labels

    def _remember_graph_label(
        self,
        graph_name: str,
        layer_index: int,
        name: str,
        text: str,
    ) -> None:
        if not graph_name:
            return
        key = (graph_name, layer_index)
        labels = self._graph_annotations.setdefault(key, [])
        labels.append({"name": name, "text": text})

    @staticmethod
    def _panel_label_present(labels: list[dict[str, Any]]) -> bool:
        for label in labels:
            text = str(label.get("text") or "").strip()
            if len(text) == 1 and text.isalpha():
                return True
        return False

    @staticmethod
    def _safe_origin_attr(obj: Any, name: str) -> Any:
        try:
            return getattr(obj, name, None)
        except (RuntimeError, SystemError, ValueError, TypeError):
            return None

    @staticmethod
    def _set_plot_command(plot: Any, command: str) -> None:
        set_cmd = getattr(plot, "set_cmd", None)
        if not callable(set_cmd):
            raise OriginOperationError("Plot object does not support set_cmd().")
        set_cmd(command)

    @staticmethod
    def _set_origin_property(obj: Any, name: str, value: Any) -> None:
        setter = getattr(obj, "set_int", None)
        if callable(setter) and isinstance(value, int):
            setter(name, value)
            return
        setter = getattr(obj, "set_float", None)
        if callable(setter) and isinstance(value, float):
            setter(name, value)
            return
        try:
            setattr(obj, name, value)
        except Exception as exc:
            raise OriginOperationError(f"Could not set Origin property {name!r}.") from exc

    @staticmethod
    def _graph_layer(graph: Any, layer_index: int) -> Any:
        if layer_index < 0:
            raise OriginOperationError("layer_index must be non-negative.")
        if hasattr(graph, "__getitem__"):
            try:
                return graph[layer_index]
            except IndexError as exc:
                raise OriginOperationError(
                    f"Graph layer index out of range: {layer_index}"
                ) from exc
        if layer_index == 0:
            return graph
        raise OriginOperationError("Graph object does not expose multiple layers.")

