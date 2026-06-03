from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase

NATURE_LEGEND_FONT_SIZE = 20
NATURE_AXIS_TITLE_SIZE = 20
NATURE_TICK_LABEL_SIZE = 18
NATURE_ANNOTATION_FONT_SIZE = 18


class _GraphStyleMixin(_OriginClientBase):
    """Style presets and graph quality diagnostics.

    Methods here apply opinionated styling (Nature-style, image panel) or
    evaluate the current graph against a QA checklist. They lean
    on graph editing helpers (``_find_or_active_graph``, ``_layer_plots``,
    ``_set_origin_property`` etc.) from :class:`_GraphFormattingMixin` via
    ``self.<helper>`` MRO dispatch.
    """

    def apply_nature_style(
        self,
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
        palette_role: str | list[str] | None = None,
        palette_name: str | None = None,
        run_diagnostics: bool = True,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        graph_name_actual = self._object_name(graph, default=graph_name or "")
        palette_name_actual = self._normalize_palette_name(palette_name)
        if page_width is not None:
            self._set_origin_property(graph, "width", page_width)
        if page_height is not None:
            self._set_origin_property(graph, "height", page_height)

        indexes = self._selected_layer_indexes(graph, layer_index)
        total_plots = sum(
            len(self._layer_plots(self._graph_layer(graph, index))) for index in indexes
        )
        auto_palette = None
        if palette_name_actual == "lcpmgh_auto":
            palette_name_actual, _palette_meta = self._select_palette_for_count(total_plots)
            auto_palette = self._auto_palette_notice(total_plots, palette_name_actual)
        palette = self._named_palette(palette_name_actual)
        semantic_palette = self._named_semantic_palette(palette_name_actual)
        chart_style = self._nature_chart_style(chart_type, line_width, symbol_size)
        actual_line_width = chart_style["line_width"]
        actual_symbol_size = chart_style["symbol_size"]
        styled_plots = 0
        applied_roles: list[str] = []
        for index in indexes:
            layer = self._graph_layer(graph, index)
            plots = self._layer_plots(layer)
            roles = self._palette_roles(palette_role, len(plots), palette_name_actual)
            for plot_index, plot in enumerate(plots):
                if actual_line_width is not None:
                    self._set_nature_plot_line_width(plot, actual_line_width)
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
            layer = self._graph_layer(graph, index)
            x_title = self._nature_axis_title_text(layer, "x", safe_font)
            y_title = self._nature_axis_title_text(layer, "y", safe_font)
            plot_count = len(self._layer_plots(layer))
            script_parts.extend(
                [
                    f"layer -s {index + 1};",
                    f"layer.x.label.font=font({safe_font});",
                    f"layer.y.label.font=font({safe_font});",
                    f"layer.x.ticklabel.font=font({safe_font});",
                    f"layer.y.ticklabel.font=font({safe_font});",
                    f"layer.x.label.pt={axis_title_size};",
                    f"layer.y.label.pt={axis_title_size};",
                    f"layer.x.ticklabel.pt={tick_label_size};",
                    f"layer.y.ticklabel.pt={tick_label_size};",
                    f"xb.font=font({safe_font});",
                    f"yl.font=font({safe_font});",
                    f'xb.text$="{x_title}";',
                    f'yl.text$="{y_title}";',
                    f"xb.fsize={axis_title_size};",
                    f"yl.fsize={axis_title_size};",
                    f"layer.x.ticks.len={tick_length};",
                    f"layer.y.ticks.len={tick_length};",
                ]
            )
            if actual_line_width is not None:
                script_parts.extend(
                    self._nature_plot_line_width_script(plot_count, actual_line_width)
                )
            if show_legend:
                script_parts.extend(
                    [
                        f"legend.font=font({safe_font});",
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
                    font_family=font_family,
                    show_frame=False,
                )
            except OriginOperationError:
                pass
        response = {
            "graph_name": graph_name_actual,
            "style": "nature",
            "palette_name": palette_name_actual,
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
        if auto_palette is not None:
            response["auto_palette"] = auto_palette
        if run_diagnostics:
            response["diagnostics"] = self.diagnose_graph(
                graph_name=graph_name_actual,
                style="nature",
                palette_role=palette_role,
                palette_name=palette_name_actual,
            )
            if auto_palette is not None:
                response["diagnostics"]["auto_palette"] = auto_palette
        return response

    def _nature_axis_title_text(self, layer: Any, axis_name: str, safe_font: str) -> str:
        axis = layer.axis(axis_name)
        title = self._safe_origin_attr(axis, "title")
        text = self._labtalk_text(str(title or "")).replace('"', '\\"').replace(")", r"\)")
        return f"\\f:{safe_font}({text})"

    def _set_nature_plot_line_width(self, plot: Any, line_width: float) -> None:
        self._set_plot_line_width(plot, line_width)

    def _nature_plot_line_width_script(self, plot_count: int, line_width: float) -> list[str]:
        native_width = self._origin_line_width_units(line_width)
        return [
            command
            for plot_index in range(1, plot_count + 1)
            for command in (
                f"range __omcpNaturePlot{plot_index} = !{plot_index};",
                f"set __omcpNaturePlot{plot_index} -w {native_width};",
                f"set __omcpNaturePlot{plot_index} -wp {line_width};",
            )
        ]

    def diagnose_graph(
        self,
        graph_name: str | None = None,
        style: str | None = None,
        palette_role: str | list[str] | None = None,
        palette_name: str | None = None,
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
        palette_name_actual, palette_warning = self._diagnostic_palette_name(
            palette_name,
            strict=style_actual == "nature",
        )
        palette_validation_name = "nature" if palette_warning else palette_name_actual
        if palette_warning:
            issues.append(palette_warning)
        layers = info.get("layers", [])
        if not layers:
            issues.append(
                self._diagnostic_issue(
                    "no_layers",
                    "error",
                    "Graph has no layers.",
                )
            )

        palette = self._named_acceptable_palette(palette_validation_name)
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
            for axis_name in ("x", "y", "z"):
                axis = layer.get("axes", {}).get(axis_name)
                if axis:
                    issues.extend(self._axis_range_issues(layer_index, axis_name, axis))
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
            expected_roles = self._palette_roles(
                palette_role,
                len(layer.get("plots", [])),
                palette_validation_name,
            )
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
                    expected_color = self._named_semantic_palette(palette_validation_name).get(
                        expected_role
                    )
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
            "palette_name": palette_name_actual,
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
        font_size: int = NATURE_ANNOTATION_FONT_SIZE,
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

    def _axis_range_issues(
        self,
        layer_index: int | None,
        axis_name: str,
        axis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Flag axis limits that silently hide data (log <=0, degenerate, reversed)."""

        limits = axis.get("limits")
        if not isinstance(limits, (list, tuple)) or len(limits) < 2:
            return []
        start, end = limits[0], limits[1]
        if isinstance(start, bool) or isinstance(end, bool):
            return []
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return []

        label = axis_name.upper()
        if not (math.isfinite(start) and math.isfinite(end)):
            return [
                self._diagnostic_issue(
                    "degenerate_axis_limits",
                    "warning",
                    f"Layer {layer_index} {label} axis has non-finite limits.",
                    layer_index=layer_index,
                    axis=axis_name,
                )
            ]

        out: list[dict[str, Any]] = []
        scale_name = str(axis.get("scale_name") or "").lower()
        is_log = "log" in scale_name or scale_name == "ln"
        if is_log and (start <= 0 or end <= 0):
            out.append(
                self._diagnostic_issue(
                    "nonpositive_log_axis",
                    "error",
                    f"Layer {layer_index} {label} axis uses {scale_name} scale but its range "
                    f"{start}..{end} includes non-positive values; data will not render.",
                    layer_index=layer_index,
                    axis=axis_name,
                )
            )
        if start == end:
            out.append(
                self._diagnostic_issue(
                    "degenerate_axis_limits",
                    "warning",
                    f"Layer {layer_index} {label} axis has a zero-width range at {start}.",
                    layer_index=layer_index,
                    axis=axis_name,
                )
            )
        elif start > end:
            out.append(
                self._diagnostic_issue(
                    "reversed_axis_limits",
                    "info",
                    f"Layer {layer_index} {label} axis range is reversed ({start} > {end}).",
                    layer_index=layer_index,
                    axis=axis_name,
                )
            )
        return out

    @staticmethod
    def _diagnostic_penalty(issue: dict[str, Any]) -> int:
        severity = str(issue.get("severity") or "")
        return {"error": 35, "warning": 15, "info": 5}.get(severity, 0)

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

    @classmethod
    def _diagnostic_palette_name(
        cls,
        palette_name: str | None,
        strict: bool,
    ) -> tuple[str, dict[str, Any] | None]:
        try:
            return cls._normalize_palette_name(palette_name), None
        except OriginOperationError:
            if strict:
                raise
            return (
                palette_name or "nature",
                cls._diagnostic_issue(
                    "external_palette_name",
                    "info",
                    "Palette name is not in the built-in origin-mcp palette catalog; "
                    "diagnostics skipped palette-specific validation.",
                    palette_name=palette_name,
                ),
            )
