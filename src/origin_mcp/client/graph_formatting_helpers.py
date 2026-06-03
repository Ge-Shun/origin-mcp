from __future__ import annotations

from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase


class _GraphFormattingHelperMixin(_OriginClientBase):
    """Private graph lookup, inspection, and Origin property helpers."""

    def _find_or_active_graph(self, graph_name: str | None) -> Any:
        op = self.op
        alias = self._graph_aliases.get(graph_name or "")
        if hasattr(op, "find_graph"):
            graph = op.find_graph(graph_name or "")
            if graph is not None:
                return graph
            if alias:
                graph = op.find_graph(alias)
                if graph is not None:
                    return graph
        if graph_name:
            graph = self._find_graph_by_long_name(graph_name)
            if graph is not None:
                return graph
            if alias:
                graph = self._find_graph_by_long_name(alias)
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
        prefer_created: bool = False,
    ) -> str:
        created = self._graph_page_names() - existing_graphs
        if len(created) == 1:
            return next(iter(created))

        graph = self._find_graph_optional(requested_graph_name)
        if graph is not None:
            return self._object_name(graph, default=requested_graph_name)
        active_graph = self._active_graph_optional()
        if active_graph is not None:
            active_name = self._object_name(active_graph, default="")
            if active_name and (prefer_created or active_name not in existing_graphs):
                return active_name
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

    def _active_graph_optional(self) -> Any | None:
        op = self._op
        if op is None:
            return None
        find_graph = getattr(op, "find_graph", None)
        if callable(find_graph):
            try:
                graph = find_graph("")
            except Exception:
                graph = None
            if graph is not None:
                return graph
        for attr_name in ("graph_active", "active_graph"):
            getter = getattr(op, attr_name, None)
            if callable(getter):
                try:
                    graph = getter()
                except Exception:
                    graph = None
                if graph is not None:
                    return graph
        return None

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

        # originpro.GLayer.add_plot only accepts these plot-type codes; multi-char
        # names outside {line,scatter,linesymbol,column,contour} raise KeyError
        # inside originpro. Kinds with no basic add_plot code (polar and the 3D
        # families) use "?" so the layer's own template drives the rendering —
        # e.g. a polar template produces a polar plot from an auto-type plot.
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
            "polar": "?",
        }
        plot_type = plot_types.get(kind, "?")
        attempts: list[dict[str, Any]] = [
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
            except (TypeError, KeyError):
                # TypeError: originpro signature mismatch across versions.
                # KeyError: unsupported plot-type code — retry without a type
                # so the layer template decides.
                continue

        add_plot(wks, y_name, x_name)

    def _group_layer_plots(
        self,
        layer: Any,
        graph_name: str | None = None,
        layer_index: int = 0,
    ) -> dict[str, Any]:
        """Group plots in a layer so multi-Y column plots render side-by-side."""

        for target in (layer, getattr(layer, "obj", None)):
            group = getattr(target, "group", None)
            if callable(group):
                try:
                    group()
                    return {"grouped": True, "method": "originpro.group"}
                except TypeError:
                    try:
                        group(True)
                        return {"grouped": True, "method": "originpro.group"}
                    except Exception:
                        pass
                except Exception:
                    pass

        parts = []
        if graph_name:
            parts.append(f'win -a "{self._escape_labtalk(graph_name)}";')
        parts.append(f"layer -s {layer_index + 1};")
        parts.append("layer -g;")
        result = self.run_labtalk(" ".join(parts))
        return {"grouped": bool(result.get("result")), "method": "labtalk.layer_g", **result}

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

    def _set_legend_font(self, graph_name: str, font_family: str) -> dict[str, Any]:
        """Set the active layer's legend font via LabTalk.

        Applied after legend creation/refresh so the font survives ``legend -r``,
        which otherwise resets the legend object to the template default font.
        """
        safe_font = self._escape_labtalk(font_family)
        parts = []
        if graph_name:
            parts.append(f'win -a "{self._escape_labtalk(graph_name)}";')
        parts.append(f"legend.font=font({safe_font});")
        return self.run_labtalk(" ".join(parts))

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

        # Reached only when left and top are both None, so the top-of-function
        # guard guarantees position is set.
        assert position is not None
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

    @staticmethod
    def _graph_layers(graph: Any) -> list[Any]:
        if hasattr(graph, "__len__") and hasattr(graph, "__getitem__"):
            try:
                length = len(graph)
            except Exception:
                length = 0
            layers = []
            for index in range(length):
                try:
                    layers.append(graph[index])
                except Exception:
                    continue
            if layers:
                return layers
        return [graph]

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
            "bar_gap": self._plot_bar_gap(plot),
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
        iterable: list[Any] = list(layer_labels.items()) if isinstance(layer_labels, dict) else []
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
            name = str(label.get("name") or "").strip().lower()
            text = str(label.get("text") or "").strip()
            plain = text.strip("()[]{}").strip()
            if name in {"panellabel", "panel_label"} or name.endswith("_panel_tag"):
                return True
            if len(plain) == 1 and plain.isalpha():
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

    def _set_plot_line_width(self, plot: Any, line_width: float) -> None:
        native_width = self._origin_line_width_units(line_width)
        self._set_plot_command(plot, f"-w {native_width}")
        self._set_plot_command(plot, f"-wp {line_width}")
        for property_name in ("line_width", "width"):
            try:
                self._set_origin_property(plot, property_name, line_width)
            except OriginOperationError:
                pass

    def _set_plot_bar_gap(self, plot: Any, bar_gap: float) -> None:
        """Set bar/column gap percent. Larger values render narrower bars."""

        self._set_plot_command(plot, f"-vg {bar_gap:g}")
        try:
            self._set_origin_property(plot, "bar_gap", float(bar_gap))
        except OriginOperationError:
            pass

    @classmethod
    def _plot_bar_gap(cls, plot: Any) -> Any:
        value = cls._safe_origin_attr(plot, "bar_gap")
        if value is not None:
            return value
        for getter_name in ("get_int", "get_float"):
            getter = getattr(plot, getter_name, None)
            if not callable(getter):
                continue
            for property_name in ("-vg", "vg", "bar_gap", "barGap", "gap"):
                try:
                    return getter(property_name)
                except Exception:
                    continue
        return None

    @staticmethod
    def _origin_line_width_units(line_width: float) -> int:
        return int(round(line_width * 500))

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
                    f"Graph layer index out of range: {layer_index}. "
                    "Use a zero-based layer_index; the first layer is 0."
                ) from exc
        if layer_index == 0:
            return graph
        raise OriginOperationError("Graph object does not expose multiple layers.")
