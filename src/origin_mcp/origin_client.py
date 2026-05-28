from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from .analysis_adapters import resolve_analysis_adapter
from .analysis_outputs import is_analysis_number, structure_analysis_output, structure_fit_result
from .client.base import ANALYSIS_XY_OUTPUTS, GraphRef, WorksheetRef
from .client.lifecycle import _LifecycleMixin
from .client.plot import _PlotMixin
from .client.worksheet import _WorksheetMixin
from .errors import OriginOperationError
from .image_quality import (
    export_looks_nonempty,
    export_quality_issues,
    file_sha256,
    image_dimensions,
    image_quality,
)

__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]


class OriginClient(_LifecycleMixin, _WorksheetMixin, _PlotMixin):
    """Small wrapper around the `originpro` package.

    The import is intentionally lazy so the MCP server can start and list tools even
    on machines where Origin is not installed yet.
    """







































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
            ax.scale = scale
        if start is not None or end is not None or step is not None:
            ax.limits = (start, end, step)
        if title:
            ax.title = self._label_text(title)
        self._rescale(layer) if start is None and end is None else None
        return {"graph_name": self._object_name(graph, default=graph_name or ""), "axis": axis}

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

    def apply_publication_style(
        self,
        graph_name: str | None = None,
        layer_index: int | None = None,
        page_width: float | None = 6.0,
        page_height: float | None = 4.0,
        axis_title_size: int = 18,
        tick_label_size: int = 14,
        legend_font_size: int = 12,
        line_width: float = 2.0,
        symbol_size: float = 8.0,
        tick_length: int = 6,
        show_legend: bool = True,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        if page_width is not None or page_height is not None:
            if page_width is not None:
                self._set_origin_property(graph, "width", page_width)
            if page_height is not None:
                self._set_origin_property(graph, "height", page_height)
        indexes = self._selected_layer_indexes(graph, layer_index)
        styled_plots = 0
        for index in indexes:
            layer = self._graph_layer(graph, index)
            plots = self._layer_plots(layer)
            for plot in plots:
                if line_width is not None:
                    self._set_plot_command(plot, f"-w {line_width}")
                if symbol_size is not None:
                    self._set_origin_property(plot, "symbol_size", symbol_size)
            styled_plots += len(plots)
        script_parts = [f"win -a {graph_name_actual};"] if graph_name_actual else []
        for index in indexes:
            script_parts.extend(
                [
                    f"layer -s {index + 1};",
                    f"layer.x.label.pt={axis_title_size};",
                    f"layer.y.label.pt={axis_title_size};",
                    f"layer.x.ticklabel.pt={tick_label_size};",
                    f"layer.y.ticklabel.pt={tick_label_size};",
                    f"layer.x.ticks.len={tick_length};",
                    f"layer.y.ticks.len={tick_length};",
                ]
            )
            if show_legend:
                script_parts.append(f"legend.fsize={legend_font_size};")
        script = " ".join(script_parts)
        result = self.run_labtalk(script) if script_parts else {"result": None}
        if show_legend:
            try:
                self.format_legend(graph_name_actual, font_size=legend_font_size)
            except OriginOperationError:
                pass
        return {
            "graph_name": graph_name_actual,
            "styled_layers": indexes,
            "styled_plots": styled_plots,
            "script": script,
            **result,
        }

    def apply_nature_style(
        self,
        graph_name: str | None = None,
        layer_index: int | None = None,
        chart_type: str | None = None,
        page_width: float | None = None,
        page_height: float | None = None,
        font_family: str = "Arial",
        axis_title_size: int = 8,
        tick_label_size: int = 7,
        legend_font_size: int = 6,
        line_width: float = 1.2,
        symbol_size: float = 4.5,
        tick_length: int = 3,
        show_legend: bool = True,
        palette_role: str | list[str] | None = None,
        run_diagnostics: bool = True,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        if page_width is not None:
            self._set_origin_property(graph, "width", page_width)
        if page_height is not None:
            self._set_origin_property(graph, "height", page_height)

        indexes = self._selected_layer_indexes(graph, layer_index)
        palette = self._nature_palette()
        semantic_palette = self._nature_semantic_palette()
        chart_style = self._nature_chart_style(chart_type, line_width, symbol_size)
        actual_line_width = chart_style["line_width"]
        actual_symbol_size = chart_style["symbol_size"]
        styled_plots = 0
        applied_roles: list[str] = []
        for index in indexes:
            layer = self._graph_layer(graph, index)
            plots = self._layer_plots(layer)
            roles = self._palette_roles(palette_role, len(plots))
            for plot_index, plot in enumerate(plots):
                if actual_line_width is not None:
                    self._set_plot_command(plot, f"-w {actual_line_width}")
                if actual_symbol_size is not None:
                    self._set_origin_property(plot, "symbol_size", actual_symbol_size)
                role = roles[plot_index]
                color = semantic_palette[role] if role else palette[plot_index % len(palette)]
                self._set_origin_property(plot, "color", color)
                try:
                    self._set_origin_property(plot, "transparency", 0)
                except OriginOperationError:
                    pass
                applied_roles.append(role or f"category_{plot_index + 1}")
            styled_plots += len(plots)

        safe_font = self._escape_labtalk(font_family)
        script_parts = (
            [f'win -a "{self._escape_labtalk(graph_name_actual)}";'] if graph_name_actual else []
        )
        for index in indexes:
            script_parts.extend(
                [
                    f"layer -s {index + 1};",
                    f'layer.x.label.font$="{safe_font}";',
                    f'layer.y.label.font$="{safe_font}";',
                    f'layer.x.ticklabel.font$="{safe_font}";',
                    f'layer.y.ticklabel.font$="{safe_font}";',
                    f"layer.x.label.pt={axis_title_size};",
                    f"layer.y.label.pt={axis_title_size};",
                    f"layer.x.ticklabel.pt={tick_label_size};",
                    f"layer.y.ticklabel.pt={tick_label_size};",
                    f"layer.x.ticks.len={tick_length};",
                    f"layer.y.ticks.len={tick_length};",
                ]
            )
            if show_legend:
                script_parts.extend(
                    [
                        f"legend.fsize={legend_font_size};",
                        "legend.showframe=0;",
                    ]
                )
        script = " ".join(script_parts)
        result = self.run_labtalk(script) if script_parts else {"result": None}
        if show_legend:
            try:
                self.format_legend(
                    graph_name_actual,
                    font_size=legend_font_size,
                    show_frame=False,
                )
            except OriginOperationError:
                pass
        response = {
            "graph_name": graph_name_actual,
            "style": "nature",
            "chart_type": chart_style["chart_type"],
            "font_family": font_family,
            "palette": palette,
            "semantic_palette": semantic_palette,
            "palette_role": palette_role,
            "applied_palette_roles": applied_roles,
            "styled_layers": indexes,
            "styled_plots": styled_plots,
            "script": script,
            **result,
        }
        if run_diagnostics:
            response["diagnostics"] = self.diagnose_graph(
                graph_name=graph_name_actual,
                style="nature",
                palette_role=palette_role,
            )
        return response

    def diagnose_graph(
        self,
        graph_name: str | None = None,
        style: str | None = None,
        palette_role: str | list[str] | None = None,
        require_axis_titles: bool = True,
        require_plots: bool = True,
        require_legend: bool = False,
        require_panel_label: bool = False,
        require_scale_bar: bool = False,
        require_channel_label: bool = False,
        require_dynamic_range: bool = False,
        export_path: Path | str | None = None,
        min_export_width: int = 600,
        min_export_height: int = 400,
    ) -> dict[str, Any]:
        info = self.get_graph_info(graph_name)
        issues: list[dict[str, Any]] = []
        style_actual = self._normalize_style_mode(style) if style else None
        layers = info.get("layers", [])
        if not layers:
            issues.append(
                self._diagnostic_issue(
                    "no_layers",
                    "error",
                    "Graph has no layers.",
                )
            )

        palette = self._nature_acceptable_palette()
        for layer in layers:
            layer_index = layer.get("index")
            if require_plots and layer.get("plots_count", 0) == 0:
                issues.append(
                    self._diagnostic_issue(
                        "no_plots",
                        "error",
                        "Layer has no plots.",
                        layer_index=layer_index,
                    )
                )
            if require_axis_titles:
                for axis_name in ("x", "y"):
                    axis = layer.get("axes", {}).get(axis_name)
                    if axis is None:
                        continue
                    if not self._has_meaningful_label(axis.get("title")):
                        issues.append(
                            self._diagnostic_issue(
                                "missing_axis_title",
                                "warning",
                                f"Layer {layer_index} has no {axis_name.upper()} axis title.",
                                layer_index=layer_index,
                                axis=axis_name,
                            )
                        )
            if require_legend and not layer.get("legend_present"):
                issues.append(
                    self._diagnostic_issue(
                        "missing_legend",
                        "warning",
                        "Layer has no detected legend label.",
                        layer_index=layer_index,
                    )
                )
            if require_panel_label and not layer.get("panel_label_present"):
                issues.append(
                    self._diagnostic_issue(
                        "missing_panel_label",
                        "warning",
                        "Layer has no detected panel label.",
                        layer_index=layer_index,
                    )
                )
            labels = layer.get("labels", [])
            if require_scale_bar and not self._label_present(
                labels,
                names={"ScaleBar", "ScaleBarLabel"},
                text_markers={"scale", "um", "µm", "mm", "nm"},
            ):
                issues.append(
                    self._diagnostic_issue(
                        "missing_scale_bar",
                        "warning",
                        "Layer has no detected scale bar label.",
                        layer_index=layer_index,
                    )
                )
            if require_channel_label and not self._label_present(
                labels,
                names={"ChannelLabel"},
                text_markers={"channel", "ch "},
            ):
                issues.append(
                    self._diagnostic_issue(
                        "missing_channel_label",
                        "warning",
                        "Layer has no detected channel label.",
                        layer_index=layer_index,
                    )
                )
            if require_dynamic_range and not self._label_present(
                labels,
                names={"DynamicRangeLabel"},
                text_markers={"range", "min", "max"},
            ):
                issues.append(
                    self._diagnostic_issue(
                        "missing_dynamic_range_label",
                        "warning",
                        "Layer has no detected dynamic range label.",
                        layer_index=layer_index,
                    )
                )
            expected_roles = self._palette_roles(palette_role, len(layer.get("plots", [])))
            for plot in layer.get("plots", []):
                if style_actual == "nature":
                    color = self._rgb_tuple(plot.get("color"))
                    if color is not None and color not in palette:
                        issues.append(
                            self._diagnostic_issue(
                                "non_nature_palette_color",
                                "info",
                                "Plot color is outside the Nature-style palette.",
                                layer_index=layer_index,
                                plot_index=plot.get("index"),
                            )
                        )
                    plot_index = plot.get("index", 0)
                    expected_role = (
                        expected_roles[plot_index] if plot_index < len(expected_roles) else ""
                    )
                    expected_color = self._nature_semantic_palette().get(expected_role)
                    if color is not None and expected_color is not None and color != expected_color:
                        issues.append(
                            self._diagnostic_issue(
                                "semantic_palette_mismatch",
                                "warning",
                                f"Plot color does not match palette role {expected_role!r}.",
                                layer_index=layer_index,
                                plot_index=plot_index,
                                palette_role=expected_role,
                            )
                        )
                    transparency = plot.get("transparency")
                    if transparency not in (None, 0):
                        issues.append(
                            self._diagnostic_issue(
                                "plot_transparency",
                                "warning",
                                "Plot transparency is not zero.",
                                layer_index=layer_index,
                                plot_index=plot.get("index"),
                            )
                        )
                symbol_size_value = self._numeric_or_none(plot.get("symbol_size"))
                if symbol_size_value is not None and symbol_size_value < 0:
                    issues.append(
                        self._diagnostic_issue(
                            "invalid_symbol_size",
                            "warning",
                            "Plot symbol size is negative.",
                            layer_index=layer_index,
                            plot_index=plot.get("index"),
                        )
                    )

        export_inspection = None
        if export_path is not None:
            export_inspection = self.inspect_export(Path(export_path))
            for issue_code in export_inspection.get("quality_issues", []):
                issues.append(
                    self._diagnostic_issue(
                        f"export_{issue_code}",
                        "error",
                        f"Export quality issue: {issue_code}.",
                        export_path=str(export_path),
                    )
                )
            width = self._numeric_or_none(export_inspection.get("width"))
            height = self._numeric_or_none(export_inspection.get("height"))
            if width is not None and width < min_export_width:
                issues.append(
                    self._diagnostic_issue(
                        "export_width_too_small",
                        "warning",
                        f"Export width is below {min_export_width}px.",
                        export_path=str(export_path),
                    )
                )
            if height is not None and height < min_export_height:
                issues.append(
                    self._diagnostic_issue(
                        "export_height_too_small",
                        "warning",
                        f"Export height is below {min_export_height}px.",
                        export_path=str(export_path),
                    )
                )

        score = max(0, 100 - sum(self._diagnostic_penalty(issue) for issue in issues))
        passed = not any(issue["severity"] == "error" for issue in issues)
        response = {
            "graph_name": info.get("graph_name", graph_name or ""),
            "style": style_actual,
            "passed": passed,
            "score": score,
            "issues": issues,
            "checklist": self._qa_checklist(
                issues=issues,
                export_checked=export_path is not None,
                require_legend=require_legend,
                require_panel_label=require_panel_label,
                require_scale_bar=require_scale_bar,
                require_channel_label=require_channel_label,
                require_dynamic_range=require_dynamic_range,
            ),
            "summary": {
                "layers": info.get("layers_count", 0),
                "plots": sum(layer.get("plots_count", 0) for layer in layers),
                "errors": sum(1 for issue in issues if issue["severity"] == "error"),
                "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
                "info": sum(1 for issue in issues if issue["severity"] == "info"),
            },
        }
        if export_inspection is not None:
            response["export"] = export_inspection
        return response





    def apply_image_panel_style(
        self,
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
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        indexes = self._selected_layer_indexes(graph, layer_index)
        labels: list[dict[str, Any]] = []
        for index in indexes:
            if panel_label:
                labels.append(
                    self.add_graph_label(
                        panel_label,
                        graph_name=graph_name_actual,
                        layer_index=index,
                        name="PanelLabel",
                        left=5,
                        top=5,
                        font_size=font_size + 2,
                    )
                )
            if channel_label:
                labels.append(
                    self.add_graph_label(
                        channel_label,
                        graph_name=graph_name_actual,
                        layer_index=index,
                        name="ChannelLabel",
                        left=5,
                        top=28,
                        font_size=font_size,
                    )
                )
            if scale_bar_label:
                labels.append(
                    self.add_graph_label(
                        scale_bar_label,
                        graph_name=graph_name_actual,
                        layer_index=index,
                        name="ScaleBarLabel",
                        left=72,
                        top=88,
                        font_size=font_size,
                    )
                )
            if dynamic_range_label:
                labels.append(
                    self.add_graph_label(
                        dynamic_range_label,
                        graph_name=graph_name_actual,
                        layer_index=index,
                        name="DynamicRangeLabel",
                        left=72,
                        top=5,
                        font_size=font_size,
                    )
                )
        script_parts = [f'win -a "{self._escape_labtalk(graph_name_actual)}";']
        for index in indexes:
            script_parts.append(f"layer -s {index + 1};")
            if dark_panel:
                script_parts.extend(["page.color=1;", "layer.color=1;"])
        script = " ".join(script_parts)
        result = self.run_labtalk(script) if script_parts else {"result": None}
        response = {
            "graph_name": graph_name_actual,
            "styled_layers": indexes,
            "dark_panel": dark_panel,
            "labels": labels,
            "script": script,
            **result,
        }
        if run_diagnostics:
            response["diagnostics"] = self.diagnose_graph(
                graph_name=graph_name_actual,
                require_panel_label=panel_label is not None,
                require_scale_bar=scale_bar_label is not None,
                require_channel_label=channel_label is not None,
                require_dynamic_range=dynamic_range_label is not None,
            )
        return response

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

    def linear_fit_result(
        self,
        worksheet: str | None,
        x_col: str | int,
        y_col: str | int,
        y_error_col: str | int | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        op = self.op
        linear_fit_cls = getattr(op, "LinearFit", None)
        if not callable(linear_fit_cls):
            self.ensure_feature("linear_fit_api", "Structured linear fitting")
            raise OriginOperationError("originpro.LinearFit is not available.")
        wks = self._find_sheet_from_ref(worksheet)
        fit = linear_fit_cls()
        fit.set_data(wks, x_col, y_col, err=y_error_col or "")
        options = options or {}
        if "fix_intercept" in options:
            fit.fix_intercept(options["fix_intercept"])
        if "fix_slope" in options:
            fit.fix_slope(options["fix_slope"])
        if options.get("report"):
            report, curves = fit.report(int(options.get("band", 0)))
            result = {"mode": "report", "report_sheet": report, "curve_sheet": curves}
            if options.get("include_report_data") and report:
                result["report_data"] = self._analysis_output(
                    str(report),
                    options.get("max_rows", 100),
                )
            return result
        fit_result = fit.result()
        structured = structure_fit_result(fit_result)
        return {
            "mode": "result",
            "result": structured,
        }

    def export_all_graphs(
        self,
        output_dir: Path,
        file_type: str = "png",
        overwrite: bool = True,
        width: int = 0,
    ) -> dict[str, Any]:
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.ensure_feature("graph_list", "Batch graph export")
        op = self.op
        graph_list = getattr(op, "graph_list", None)
        if not callable(graph_list):
            raise OriginOperationError("originpro.graph_list is not available.")
        exported = []
        for graph in graph_list("p", True):
            graph_name = self._object_name(graph, default="Graph")
            path = output_dir / f"{self._safe_filename(graph_name)}.{file_type.lstrip('.')}"
            if path.exists() and not overwrite:
                continue
            if hasattr(graph, "save_fig"):
                graph.save_fig(str(path), type=file_type, replace=overwrite, width=width)
            else:
                self.export_graph(path, graph=graph, overwrite=overwrite)
            exported.append(str(path))
        return {"count": len(exported), "paths": exported}





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

    def list_fit_functions(self) -> dict[str, Any]:
        functions = [
            {
                "name": "Gauss",
                "category": "Peak",
                "parameters": ["y0", "xc", "w", "A"],
                "description": "Gaussian peak.",
            },
            {
                "name": "Lorentz",
                "category": "Peak",
                "parameters": ["y0", "xc", "w", "A"],
                "description": "Lorentzian peak.",
            },
            {
                "name": "ExpDec1",
                "category": "Exponential",
                "parameters": ["y0", "A1", "t1"],
                "description": "First-order exponential decay.",
            },
            {
                "name": "ExpDec2",
                "category": "Exponential",
                "parameters": ["y0", "A1", "t1", "A2", "t2"],
                "description": "Second-order exponential decay.",
            },
            {
                "name": "Boltzmann",
                "category": "Sigmoidal",
                "parameters": ["A1", "A2", "x0", "dx"],
                "description": "Boltzmann sigmoid.",
            },
            {
                "name": "Logistic",
                "category": "Sigmoidal",
                "parameters": ["A1", "A2", "x0", "p"],
                "description": "Logistic curve.",
            },
        ]
        return {"count": len(functions), "functions": functions}

    def nonlinear_fit_structured(
        self,
        worksheet: str | None,
        x_col: str | int,
        y_col: str | int,
        function: str,
        output_sheet: str | None = None,
        initial_params: dict[str, float] | None = None,
        fixed_params: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not function.strip():
            raise OriginOperationError("function is empty.")
        options = dict(options or {})
        options["function"] = function
        for name, value in (initial_params or {}).items():
            options[f"init_{name}"] = value
        if fixed_params:
            options["fixed"] = ",".join(fixed_params)
        return self.run_analysis(
            analysis="nonlinear_fit",
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_sheet,
            options=options,
            include_output=bool(output_sheet),
        )

    def run_analysis(
        self,
        analysis: str,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        output_sheet: str | None = None,
        options: dict[str, Any] | None = None,
        include_output: bool = False,
        output_max_rows: int = 100,
    ) -> dict[str, Any]:
        origin_version = self.capabilities(show=False).get("origin_version")
        adapter = resolve_analysis_adapter(analysis, origin_version)
        analysis_name = adapter.name
        options_for_script = dict(options or {})
        output_target = output_sheet
        polynomial_outputs: dict[str, str] = {}
        if output_sheet and analysis_name in ANALYSIS_XY_OUTPUTS:
            output_target = self._prepare_analysis_xy_output(output_sheet)
        if analysis_name == "polynomial_fit":
            polynomial_outputs = self._polynomial_output_variables()
            for key, value in polynomial_outputs.items():
                options_for_script.setdefault(key, value)
        script = self._analysis_script(
            analysis=analysis,
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_target,
            options=options_for_script,
        )
        result = self.run_labtalk(script)
        executed = bool(result.get("result"))
        warning = "" if executed else "Origin returned false for this analysis command."
        warnings = [warning] if warning else []
        response = {
            "analysis": analysis_name,
            "script": script,
            "executed": executed,
            "parameters": [],
            "metrics": {},
            "sections": {},
            "warnings": warnings,
            "warning": warning,
            **result,
        }
        if output_target and output_target != output_sheet:
            response["output_target"] = output_target
        if include_output:
            if not output_sheet:
                output_warning = "include_output requires output_sheet."
                response["output_warning"] = output_warning
                response["warnings"].append(output_warning)
            else:
                output = self._analysis_output(output_sheet, output_max_rows)
                response["output"] = output
                structured = structure_analysis_output(analysis_name, output)
                response["parameters"] = structured["parameters"]
                response["metrics"] = structured["metrics"]
                response["sections"] = structured["sections"]
                if polynomial_outputs:
                    polynomial = self._structure_polynomial_outputs(
                        polynomial_outputs,
                        options_for_script,
                    )
                    if polynomial["parameters"]:
                        response["parameters"] = polynomial["parameters"]
                    response["metrics"].update(polynomial["metrics"])
                if not output.get("found", True) and output.get("error"):
                    response["warnings"].append(str(output["error"]))
        return response

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

    def export_graph(
        self,
        path: Path,
        graph_name: str | None = None,
        graph: Any | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OriginOperationError(f"Export path already exists: {path}")

        if graph_name:
            self._suppress_graph_title_text(graph_name=graph_name, title=None)
            self.run_labtalk(self._export_graph_labtalk(path, graph_name))
        else:
            target = graph if graph is not None else self._find_or_active_graph(graph_name)
            self._suppress_graph_title_text(graph=target, graph_name=None, title=None)
            if not hasattr(target, "save_fig"):
                self.run_labtalk(self._export_graph_labtalk(path, None))
                return {"path": str(path)}
            target.save_fig(str(path))

        return {"path": str(path)}

    def _export_graph_labtalk(self, path: Path, graph_name: str | None) -> str:
        export_type = path.suffix.lower().lstrip(".") or "png"
        if export_type == "jpeg":
            export_type = "jpg"
        filename = path.stem
        safe_path = self._escape_labtalk(str(path.parent))
        safe_filename = self._escape_labtalk(filename)
        parts = []
        if graph_name:
            safe_graph_name = self._escape_labtalk(graph_name)
            parts.append(f'win -a "{safe_graph_name}";')
            parts.append(f'expGraph pages:="{safe_graph_name}"')
        else:
            parts.append("expGraph")
        parts.append(
            f'type:={export_type} path:="{safe_path}" '
            f'filename:="{safe_filename}" overwrite:=replace;'
        )
        return " ".join(parts)

    def export_preview(
        self,
        graph_name: str | None = None,
        output_dir: Path | None = None,
        file_type: str = "png",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        suffix = file_type.lower().lstrip(".") or "png"
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "origin-mcp-previews"
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(graph_name or "active_graph")
        path = output_dir / f"{safe_name}_{uuid.uuid4().hex[:8]}.{suffix}"
        exported = self.export_graph(path, graph_name=graph_name, overwrite=overwrite)
        return {
            **exported,
            "preview": self.inspect_export(Path(exported["path"])),
        }

    def _export_plot_command_graph(self, path: Path, graph_name: str) -> dict[str, Any]:
        try:
            return self.export_graph(path, graph_name=graph_name)
        except OriginOperationError as exc:
            if "Graph not found" not in str(exc):
                raise
            exported = self.export_graph(path)
            exported["warning"] = (
                f"Origin did not expose plot command output as {graph_name!r}; "
                "exported the active graph instead."
            )
            return exported

    def inspect_export(self, path: Path) -> dict[str, Any]:
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
        if not path.exists():
            raise OriginOperationError(f"Export file does not exist: {path}")
        if not path.is_file():
            raise OriginOperationError(f"Export path is not a file: {path}")
        info: dict[str, Any] = {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "suffix": path.suffix.lower(),
            "sha256": file_sha256(path),
        }
        dimensions = image_dimensions(path)
        if dimensions:
            info.update(dimensions)
        quality = image_quality(path)
        if quality:
            info["image_quality"] = quality
        quality_issues = export_quality_issues(info)
        info["quality_issues"] = quality_issues
        info["quality_passed"] = not quality_issues
        info["looks_nonempty"] = export_looks_nonempty(info)
        return info

















    @staticmethod
    def _qa_checklist(
        issues: list[dict[str, Any]],
        export_checked: bool,
        require_legend: bool,
        require_panel_label: bool,
        require_scale_bar: bool,
        require_channel_label: bool,
        require_dynamic_range: bool,
    ) -> list[dict[str, Any]]:
        issue_codes = {issue["code"] for issue in issues}

        def check(name: str, codes: set[str], active: bool = True) -> dict[str, Any]:
            failed = sorted(issue_codes & codes)
            return {
                "name": name,
                "active": active,
                "passed": (not active) or not failed,
                "issues": failed,
            }

        return [
            check("layers", {"no_layers"}),
            check("plots", {"no_plots"}),
            check("axis_titles", {"missing_axis_title"}),
            check(
                "palette",
                {"non_nature_palette_color", "semantic_palette_mismatch"},
            ),
            check("transparency", {"plot_transparency"}),
            check("legend", {"missing_legend"}, active=require_legend),
            check("panel_label", {"missing_panel_label"}, active=require_panel_label),
            check("scale_bar", {"missing_scale_bar"}, active=require_scale_bar),
            check("channel_label", {"missing_channel_label"}, active=require_channel_label),
            check(
                "dynamic_range",
                {"missing_dynamic_range_label"},
                active=require_dynamic_range,
            ),
            check(
                "export_quality",
                {
                    "export_all_pixels_transparent",
                    "export_single_color_image",
                    "export_blank_or_near_blank",
                    "export_low_color_complexity",
                },
                active=export_checked,
            ),
            check(
                "export_dimensions",
                {"export_width_too_small", "export_height_too_small"},
                active=export_checked,
            ),
        ]

    @staticmethod
    def _diagnostic_issue(
        code: str,
        severity: str,
        message: str,
        **context: Any,
    ) -> dict[str, Any]:
        issue = {"code": code, "severity": severity, "message": message}
        issue.update({key: value for key, value in context.items() if value is not None})
        return issue

    @staticmethod
    def _diagnostic_penalty(issue: dict[str, Any]) -> int:
        return {"error": 35, "warning": 15, "info": 5}.get(issue.get("severity"), 0)

    @staticmethod
    def _has_meaningful_label(value: Any) -> bool:
        if value is None:
            return False
        text = str(value).strip()
        return bool(text and text.lower() not in {"none", "axis"})

    @staticmethod
    def _rgb_tuple(value: Any) -> tuple[int, int, int] | None:
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            return None
        try:
            return (int(value[0]), int(value[1]), int(value[2]))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _numeric_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _label_present(
        labels: list[dict[str, Any]],
        names: set[str],
        text_markers: set[str],
    ) -> bool:
        lower_names = {name.lower() for name in names}
        lower_markers = {marker.lower() for marker in text_markers}
        for label in labels:
            name = str(label.get("name") or "").lower()
            text = str(label.get("text") or "").lower()
            if name in lower_names:
                return True
            if any(marker in text for marker in lower_markers):
                return True
        return False



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


    def _analysis_output(self, output_sheet: str, max_rows: int = 100) -> dict[str, Any]:
        if max_rows < 1:
            raise OriginOperationError("max_rows must be at least 1.")
        try:
            wks = self._find_sheet_from_ref(output_sheet)
            return self.read_worksheet(
                book_name=self._object_name(wks.get_book(), default=""),
                sheet_name=self._object_name(wks, default=""),
                max_rows=max_rows,
            )
        except Exception as exc:
            return {
                "found": False,
                "output_sheet": output_sheet,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    def _prepare_analysis_xy_output(self, output_sheet: str) -> str:
        output_sheet = output_sheet.strip()
        if "!" in output_sheet:
            return output_sheet
        if output_sheet.startswith("[") and "]" in output_sheet:
            return f"{output_sheet}!(1,2)"
        wks = self._new_sheet(book_name=output_sheet, sheet_name="Result")
        ref = self._worksheet_ref(wks)
        return f"[{ref.book_name}]{ref.sheet_name}!(1,2)"

    @staticmethod
    def _polynomial_output_variables() -> dict[str, str]:
        prefix = f"op{uuid.uuid4().hex[:6]}"
        return {
            "coef": f"{prefix}c",
            "err": f"{prefix}e",
            "N": f"{prefix}n",
            "AdjRSq": f"{prefix}a",
            "RSqCOD": f"{prefix}r",
        }

    def _structure_polynomial_outputs(
        self,
        variables: dict[str, str],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_options = resolve_analysis_adapter(
            "polynomial_fit",
            self.capabilities(show=False).get("origin_version"),
        ).normalize_options(options)
        try:
            order = int(normalized_options.get("polyorder", 2))
        except (TypeError, ValueError):
            order = 2

        parameters = []
        for index in range(order + 1):
            value = self._safe_eval(f"{variables['coef']}[{index + 1}]")
            if is_analysis_number(value):
                parameter = {
                    "name": "Intercept" if index == 0 else f"B{index}",
                    "path": f"{variables['coef']}[{index + 1}]",
                    "value": value,
                }
                stderr = self._safe_eval(f"{variables['err']}[{index + 1}]")
                if is_analysis_number(stderr):
                    parameter["stderr"] = stderr
                parameters.append(parameter)

        metrics: dict[str, Any] = {}
        for key in ("N", "AdjRSq", "RSqCOD"):
            value = self._safe_eval(variables[key])
            if is_analysis_number(value):
                metrics[key] = value
        return {"parameters": parameters, "metrics": metrics}






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
            axes[axis_name] = {
                "title": self._safe_origin_attr(axis, "title"),
                "scale": self._safe_origin_attr(axis, "scale"),
                "limits": self._safe_origin_attr(axis, "limits"),
            }
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

    @staticmethod
    def _layer_labels(layer: Any) -> list[dict[str, Any]]:
        labels: list[dict[str, Any]] = []
        layer_labels = getattr(layer, "labels", None)
        if isinstance(layer_labels, dict):
            iterable = layer_labels.items()
        else:
            iterable = []
        for name, label in iterable:
            label_name = OriginClient._object_name(label, default=str(name))
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























    def _analysis_script(
        self,
        analysis: str,
        worksheet: str | None,
        x_col: str | int | None,
        y_col: str | int | None,
        output_sheet: str | None,
        options: dict[str, Any],
    ) -> str:
        origin_version = self.capabilities(show=False).get("origin_version")
        adapter = resolve_analysis_adapter(analysis, origin_version)
        range_expr = self._analysis_range(worksheet, x_col, y_col)
        if adapter.range_required and not range_expr:
            raise OriginOperationError(f"Analysis '{adapter.name}' requires an input range.")
        return " ".join(adapter.command(range_expr, output_sheet, options).split())

    def _analysis_range(
        self,
        worksheet: str | None,
        x_col: str | int | None,
        y_col: str | int | None,
    ) -> str:
        if worksheet is None and x_col is None and y_col is None:
            return ""
        if worksheet:
            try:
                wks = self._find_sheet_from_ref(worksheet)
                if x_col is not None and y_col is not None:
                    return wks.to_xy_range(x_col, y_col, "")
                if y_col is not None:
                    return wks.to_col_range(y_col)
                return wks.lt_range(False)
            except OriginOperationError:
                if x_col is not None or y_col is not None:
                    raise
        if worksheet and x_col is not None and y_col is not None:
            return f"{worksheet}!({x_col},{y_col})"
        if worksheet and y_col is not None:
            return f"{worksheet}!({y_col})"
        if worksheet:
            return worksheet
        return f"({x_col},{y_col})" if x_col is not None else f"({y_col})"

