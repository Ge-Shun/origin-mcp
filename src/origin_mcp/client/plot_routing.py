from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import template_library
from ..chart_router import profile_table
from ..chart_router import recommend_chart as recommend_chart_route
from ..errors import OriginOperationError
from ..template_library import TemplateRecord
from .base import GraphRef, WorksheetRef, _OriginClientBase


class _PlotRoutingMixin(_OriginClientBase):
    """Plot routing, chart-atlas presets, range plotting, and template discovery.

    Owns recommend_chart / plot_auto / chart_atlas_route / plot_chart_atlas,
    plot_range / batch_plot_from_template, and list_graph_templates /
    default_plot_config. These rely on _TablePlotMixin for the actual plot
    construction primitives (plot_table, plot_table_by_id, _new_graph,
    _plot_command) via MRO.
    """

    def recommend_chart(
        self,
        path: Path,
        intent: str | None = None,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        z_col: str | int | None = None,
        y_error_col: str | int | None = None,
        x_error_col: str | int | None = None,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
        max_recommendations: int = 5,
    ) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        self._validate_file(path)
        df = self._read_table(
            path,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        if df.empty:
            raise OriginOperationError(f"Data file contains no rows: {path}")
        profile = profile_table(df)
        return recommend_chart_route(
            profile,
            intent=intent,
            x_col=x_col,
            y_cols=y_cols,
            z_col=z_col,
            y_error_col=y_error_col,
            x_error_col=x_error_col,
            max_recommendations=max_recommendations,
        )

    def plot_auto(
        self,
        path: Path,
        intent: str | None = None,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        z_col: str | int | None = None,
        y_error_col: str | int | None = None,
        x_error_col: str | int | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
        graph_name: str | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        style_mode: str = "origin_default",
        palette_name: str | None = None,
        export_path: Path | None = None,
    ) -> dict[str, Any]:
        recommendation = self.recommend_chart(
            path=path,
            intent=intent,
            x_col=x_col,
            y_cols=y_cols,
            z_col=z_col,
            y_error_col=y_error_col,
            x_error_col=x_error_col,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        selected = recommendation["selected"]
        style_mode_actual = self._normalize_style_mode(style_mode)
        if selected.get("plot_type_id"):
            worksheet, graph, command = self.plot_table_by_id(
                path=path,
                plot_type_id=int(selected["plot_type_id"]),
                template=str(selected.get("template") or "line"),
                selected_cols=selected.get("selected_cols"),
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                style_mode=style_mode_actual,
                palette_name=palette_name,
                export_path=export_path,
            )
        else:
            worksheet, graph = self.plot_table(
                path=path,
                kind=str(selected.get("kind") or "line"),
                x_col=x_col if x_col is not None else selected.get("x_col"),
                y_cols=y_cols if y_cols is not None else selected.get("y_cols"),
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                template=selected.get("template"),
                title=title,
                x_label=x_label,
                y_label=y_label,
                z_col=z_col if z_col is not None else selected.get("z_col"),
                y_error_col=y_error_col if y_error_col is not None else selected.get("y_error_col"),
                x_error_col=x_error_col if x_error_col is not None else selected.get("x_error_col"),
                style_mode=style_mode_actual,
                palette_name=palette_name,
                export_path=export_path,
            )
            command = None
        diagnostics = self.diagnose_graph(
            graph_name=graph.graph_name,
            style=style_mode_actual if style_mode_actual == "nature" else None,
            palette_role=selected.get("palette_role"),
            palette_name=palette_name,
            export_path=export_path,
        )
        return {
            "recommendation": recommendation,
            "worksheet": worksheet.as_dict(),
            "graph": graph.as_dict(),
            "command": command,
            "diagnostics": diagnostics,
        }

    def chart_atlas_route(
        self,
        intent: str,
        columns: list[str] | None = None,
        matrix: bool = False,
    ) -> dict[str, Any]:
        normalized = self._normalize_chart_intent(intent)
        routes = self._chart_atlas_routes()
        route = dict(routes[normalized])
        route["intent"] = normalized
        route["input_columns"] = columns or []
        route["matrix_input"] = matrix
        if matrix and normalized not in {"matrix", "image_plate"}:
            route["warnings"] = ["Matrix input is best routed to matrix or image_plate."]
        return route

    def plot_chart_atlas(
        self,
        path: Path,
        intent: str,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        z_col: str | int | None = None,
        y_error_col: str | int | None = None,
        x_error_col: str | int | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
        graph_name: str | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        style_mode: str = "origin_default",
        palette_role: str | list[str] | None = None,
        palette_name: str | None = None,
        export_path: Path | None = None,
    ) -> dict[str, Any]:
        route = self.chart_atlas_route(intent)
        if route.get("matrix_required"):
            raise OriginOperationError(
                f"Chart atlas intent {route['intent']!r} requires an Origin matrix range."
            )
        route_palette = palette_role if palette_role is not None else route.get("palette_role")
        style_mode_actual = self._normalize_style_mode(style_mode)
        initial_style = "origin_default" if style_mode_actual == "nature" else style_mode_actual
        worksheet: WorksheetRef
        graph: GraphRef
        command: dict[str, Any] | None = None
        if route.get("plot_type_id"):
            selected_cols = self._atlas_selected_columns(
                route["intent"],
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
            )
            worksheet, graph, command = self.plot_table_by_id(
                path=path,
                plot_type_id=int(route["plot_type_id"]),
                template=str(route["template"]),
                selected_cols=selected_cols,
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                style_mode=initial_style,
                palette_name=palette_name,
                export_path=export_path,
            )
        else:
            worksheet, graph = self.plot_table(
                path=path,
                kind=str(route["kind"]),
                x_col=x_col,
                y_cols=y_cols,
                book_name=book_name,
                sheet_name=sheet_name,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
                style_mode=initial_style,
                palette_name=palette_name,
                export_path=export_path,
            )

        style_result = None
        if style_mode_actual == "nature":
            style_result = self.apply_nature_style(
                graph_name=graph.graph_name,
                chart_type=str(route["chart_type"]),
                palette_role=route_palette,
                palette_name=palette_name,
            )
            if export_path is not None:
                self._export_plot_command_graph(export_path, graph.graph_name)
            graph = GraphRef(
                graph_name=graph.graph_name,
                export_path=graph.export_path,
                template=graph.template,
                style_mode=style_mode_actual,
            )

        regression = None
        if route.get("regression") and y_cols:
            regression = self._atlas_linear_fit(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_cols[0],
                y_error_col=y_error_col,
            )

        diagnostics = self.diagnose_graph(
            graph_name=graph.graph_name,
            style=style_mode_actual if style_mode_actual == "nature" else None,
            palette_role=route_palette,
            palette_name=palette_name,
            export_path=export_path,
        )
        return {
            "route": route,
            "worksheet": worksheet.as_dict(),
            "graph": graph.as_dict(),
            "command": command,
            "style": style_result,
            "regression": regression,
            "diagnostics": diagnostics,
        }

    def plot_range(
        self,
        data_range: str,
        template: str = "line",
        plot_type: str = "?",
        graph_name: str | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        export_path: Path | None = None,
    ) -> GraphRef:
        if not data_range.strip():
            raise OriginOperationError("Data range is empty.")
        graph = self._new_graph(kind="line", graph_name=graph_name, template=template)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph
        add_plot = getattr(layer, "add_plot", None)
        if not callable(add_plot):
            raise OriginOperationError("Graph layer does not support add_plot().")
        before_count = len(self._layer_plots(layer))
        add_plot(data_range, type=plot_type)
        after_count = len(self._layer_plots(layer))
        if after_count <= before_count:
            raise OriginOperationError(
                "Origin created a graph page but no plot was added. "
                "Check data_range, plot_type, and template.",
                error_code="empty_graph_created",
            )
        self.format_graph(
            graph=graph,
            title=title,
            x_label=x_label,
            y_label=y_label,
            show_legend=True,
            rescale=True,
        )
        exported: str | None = None
        if export_path is not None:
            exported = self.export_graph(export_path, graph=graph)["path"]
        return GraphRef(
            graph_name=self._object_name(graph, default=graph_name or "Graph"),
            export_path=exported,
        )

    def batch_plot_from_template(
        self,
        data_ranges: list[str],
        template: str,
        output_dir: Path | None = None,
        file_type: str = "png",
        plot_type: str = "?",
    ) -> dict[str, Any]:
        if output_dir is not None:
            output_dir = self._normalize_user_path(output_dir)
        graphs = []
        for index, data_range in enumerate(data_ranges, start=1):
            export_path = None
            if output_dir is not None:
                export_path = output_dir / f"template_plot_{index}.{file_type.lstrip('.')}"
            graph = self.plot_range(
                data_range=data_range,
                template=template,
                plot_type=plot_type,
                graph_name=f"template_plot_{index}",
                export_path=export_path,
            )
            graphs.append(graph.as_dict())
        return {"count": len(graphs), "graphs": graphs}

    def list_graph_templates(self, template_dir: Path | None = None) -> dict[str, Any]:
        builtin = sorted(set(self._default_graph_templates().values()) | {"bar", "ternary"})
        discovered: list[dict[str, str]] = []
        if template_dir is not None:
            template_dir = self._normalize_user_path(template_dir)
            if not template_dir.exists() or not template_dir.is_dir():
                raise OriginOperationError(f"Template directory does not exist: {template_dir}")
            for suffix in ("*.otp", "*.otpu", "*.otm", "*.otmu"):
                for path in template_dir.glob(suffix):
                    discovered.append({"name": path.stem, "path": str(path)})
        return {
            "builtin": builtin,
            "discovered": discovered,
            "count": len(builtin) + len(discovered),
        }

    def default_plot_config(
        self,
        template_dir: Path | None = None,
        max_templates: int = 200,
    ) -> dict[str, Any]:
        if max_templates < 1:
            raise OriginOperationError("max_templates must be at least 1.")
        capabilities = self.capabilities(show=False)
        origin_paths = self._origin_template_paths()
        search_dirs = [Path(path) for path in origin_paths.values() if path]
        if template_dir is not None:
            template_dir = self._normalize_user_path(template_dir)
            search_dirs.insert(0, template_dir)
        discovered = self._discover_template_files(search_dirs, max_templates=max_templates)
        return {
            "style_mode_default": "origin_default",
            "preserves_origin_defaults": True,
            "origin_version": capabilities.get("origin_version"),
            "originpro_version": capabilities.get("originpro_version"),
            "originext_version": capabilities.get("originext_version"),
            "python_version": capabilities.get("python_version"),
            "default_templates": self._default_graph_templates(),
            "template_search_paths": {key: str(path) for key, path in origin_paths.items()},
            "templates": {
                "builtin": self.list_graph_templates().get("builtin", []),
                "discovered": discovered,
                "discovered_count": len(discovered),
                "truncated": len(discovered) >= max_templates,
            },
            "style_modes": {
                "origin_default": (
                    "Use the resolved Origin graph template and preserve the user's Origin "
                    "template/theme defaults. This is the default."
                ),
                "template": "Alias for origin_default; pass template to force a template.",
                "theme": "Alias for origin_default; Origin applies its configured theme/template.",
                "none": (
                    "Alias for origin_default; origin-mcp does not apply extra style overrides."
                ),
                "nature": ("Apply a compact Nature-style scientific figure preset after plotting."),
            },
            "mcp_overrides": {
                "origin_default": ["title", "axis titles", "legend refresh", "axis rescale"],
                "nature": [
                    "Arial-compatible font settings",
                    "Nature axis/title/tick/legend font sizes",
                    "short ticks",
                    "Nature line weights",
                    "compact symbols",
                    "colorblind-safe palette",
                    "legend frame off",
                ],
            },
            "notes": [
                "origin-mcp does not parse every Origin theme preference file directly.",
                "Origin itself resolves template names against user and system template folders.",
                "Pass template explicitly when a user has a preferred custom template.",
            ],
        }

    @staticmethod
    def _atlas_selected_columns(
        intent: str,
        x_col: str | int | None,
        y_cols: list[str | int] | None,
        z_col: str | int | None,
        y_error_col: str | int | None,
        x_error_col: str | int | None,
    ) -> list[str | int] | None:
        selected: list[str | int] = []
        if x_col is not None:
            selected.append(x_col)
        if y_cols:
            selected.extend(y_cols)
        if intent == "effect_size" and y_error_col is not None:
            selected.append(y_error_col)
        if intent == "effect_size" and x_error_col is not None:
            selected.append(x_error_col)
        if z_col is not None:
            selected.append(z_col)
        return selected or None

    def _atlas_linear_fit(
        self,
        worksheet: WorksheetRef,
        x_col: str | int | None,
        y_col: str | int,
        y_error_col: str | int | None,
    ) -> dict[str, Any]:
        worksheet_ref = f"[{worksheet.book_name}]{worksheet.sheet_name}"
        x_value = x_col if x_col is not None else worksheet.columns[0]
        try:
            return self.linear_fit_result(
                worksheet=worksheet_ref,
                x_col=x_value,
                y_col=y_col,
                y_error_col=y_error_col,
            )
        except OriginOperationError as exc:
            return {"warning": str(exc)}

    def _origin_template_paths(self) -> dict[str, str]:
        paths: dict[str, str] = {}
        op = self.op
        path_func = getattr(op, "path", None)
        if not callable(path_func):
            return paths
        for key, label in (("u", "user_files"), ("e", "program")):
            try:
                value = path_func(key)
            except Exception:
                continue
            if value:
                paths[label] = str(Path(value).expanduser())
        return paths

    def _discover_template_files(
        self,
        directories: list[Path],
        max_templates: int,
    ) -> list[dict[str, str]]:
        suffixes = {".otp", ".otpu", ".otm", ".otmu"}
        discovered: list[dict[str, str]] = []
        seen: set[Path] = set()
        for directory in directories:
            directory = directory.expanduser()
            if not directory.exists() or not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if len(discovered) >= max_templates:
                    return discovered
                if not path.is_file() or path.suffix.lower() not in suffixes:
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                discovered.append(
                    {
                        "name": path.stem,
                        "path": str(resolved),
                        "source_dir": str(directory.resolve()),
                    }
                )
        return discovered

    def save_graph_template(
        self,
        name: str,
        description: str | None = None,
        tags: list[str] | None = None,
        plot_types: list[str] | None = None,
        roles: list[str] | None = None,
        n_columns: int | None = None,
        graph_name: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Save a finished graph into the user's template library.

        Writes ``<slug>.otpu`` via Origin's ``template_saveas``, renders a
        ``<slug>.png`` thumbnail, enriches the metadata with the live graph's
        layer/plot counts, and persists a searchable
        :class:`~origin_mcp.models.TemplateRecord` sidecar plus index entry.
        """

        if not name.strip():
            raise OriginOperationError("Template name must not be empty.")

        root = self._normalize_user_path(template_library.template_root())
        root.mkdir(parents=True, exist_ok=True)
        slug = template_library.slugify(name)
        otpu_path = root / f"{slug}.otpu"
        if otpu_path.exists() and not overwrite:
            raise OriginOperationError(
                f"Template {name!r} already exists at {otpu_path}. "
                "Pass overwrite=True to replace it."
            )

        graph = self._find_or_active_graph(graph_name)
        actual_name = self._object_name(graph, default=graph_name or "")
        if not actual_name:
            raise OriginOperationError("Could not resolve a graph page to save as a template.")

        self._write_graph_template(actual_name, otpu_path)
        if not otpu_path.is_file():
            raise OriginOperationError(
                f"Origin did not write a template file for graph {actual_name!r}. "
                "template_saveas may have failed."
            )

        thumbnail_path: str | None = None
        thumb_file = root / f"{slug}.png"
        try:
            self.export_graph(thumb_file, graph_name=actual_name, overwrite=True)
            thumbnail_path = str(thumb_file)
        except Exception:
            # A missing thumbnail must never block saving the template itself.
            thumbnail_path = None

        layer_count: int | None = None
        plots_count: int | None = None
        try:
            info = self.get_graph_info(graph_name=actual_name)
            layer_count = info.get("layers_count")
            plots_count = sum(
                int(layer.get("plots_count") or 0) for layer in info.get("layers", [])
            )
        except Exception:
            layer_count = plots_count = None

        record = TemplateRecord(
            name=name,
            slug=slug,
            description=description,
            tags=[tag for tag in (tags or []) if tag.strip()],
            plot_types=[value.strip().lower() for value in (plot_types or []) if value.strip()],
            roles=[role.strip().lower() for role in (roles or []) if role.strip()],
            n_columns=n_columns,
            layer_count=layer_count,
            plots_count=plots_count,
            source_graph=actual_name,
            otpu_path=str(otpu_path),
            thumbnail_path=thumbnail_path,
            created_at=template_library.now_iso(),
        )
        payload = template_library.write_template_record(record, root=root)
        return {"saved": True, "template_dir": str(root), "template": payload}

    def _write_graph_template(self, graph_name: str, otpu_path: Path) -> None:
        """Issue the LabTalk that saves a graph window as an Origin template file.

        Isolated so the exact ``template_saveas`` form is easy to confirm/adjust
        against a live Origin during validation.
        """

        safe_graph = self._escape_labtalk(graph_name)
        safe_template = self._escape_labtalk(otpu_path.stem)
        safe_folder = self._escape_labtalk(str(otpu_path.parent))
        # template_saveas writes <filepath>/<template>.otpu (ftype:=0). emf/bmp are
        # turned off because we render our own PNG thumbnail separately.
        self.run_labtalk(
            f'template_saveas pg:=[{safe_graph}] template:="{safe_template}" '
            f'filepath:="{safe_folder}" ftype:=0 emf:=0 bmp:=0;'
        )
