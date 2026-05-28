from __future__ import annotations

from pathlib import Path
from typing import Any

from ..chart_router import profile_table
from ..chart_router import recommend_chart as recommend_chart_route
from ..errors import OriginOperationError
from .base import (
    MATRIX_PLOTM_IDS,
    TABLE_PLOTXYZ_IDS,
    TABLE_WORKSHEET_PLOT_IDS,
    GraphRef,
    WorksheetRef,
    _OriginClientBase,
)


class _PlotMixin(_OriginClientBase):
    """Plot construction, chart routing, and template discovery methods."""

    def plot_csv(
        self,
        path: Path,
        kind: str,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        graph_name: str | None = None,
        style_mode: str = "origin_default",
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
        return self.plot_table(
            path=path,
            kind=kind,
            x_col=x_col,
            y_cols=y_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            graph_name=graph_name,
            style_mode=style_mode,
            export_path=export_path,
        )

    def plot_table(
        self,
        path: Path,
        kind: str,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
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
        template: str | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        z_col: str | int | None = None,
        y_error_col: str | int | None = None,
        x_error_col: str | int | None = None,
        show_legend: bool = True,
        style_mode: str = "origin_default",
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef]:
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

        columns = [str(col) for col in df.columns]
        x_name = self._resolve_column(columns, x_col, default_index=0)
        y_names = self._resolve_y_columns(columns, x_name, y_cols)
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

        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.from_df(df)

        style_mode_actual = self._normalize_style_mode(style_mode)
        graph_template = self._resolve_graph_template(kind=kind, template=template)
        graph = self._new_graph(kind=kind, graph_name=graph_name, template=graph_template)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph

        for y_name in y_names:
            self._add_plot(
                layer,
                wks,
                x_name=x_name,
                y_name=y_name,
                kind=kind,
                z_name=z_name,
                y_error_name=yerr_name,
                x_error_name=xerr_name,
            )

        self.format_graph(
            graph=graph,
            title=title,
            x_label=x_label or x_name,
            y_label=y_label or ", ".join(y_names),
            show_legend=show_legend,
            rescale=True,
        )
        actual_graph_name = self._object_name(graph, default=graph_name or "Graph")
        self._remember_graph_alias(graph_name, actual_graph_name)
        if style_mode_actual == "publication":
            self.apply_publication_style(graph_name=actual_graph_name)
        elif style_mode_actual == "nature":
            self.apply_nature_style(graph_name=actual_graph_name, chart_type=kind)
        exported: str | None = None
        if export_path is not None:
            exported = self._export_plot_command_graph(export_path, actual_graph_name)["path"]

        worksheet = self._worksheet_ref(wks, columns=columns, rows=len(df))
        return worksheet, GraphRef(
            graph_name=actual_graph_name,
            export_path=exported,
            template=graph_template,
            style_mode=style_mode_actual,
            requested_graph_name=graph_name,
            display_name=self._object_long_name(graph, default=graph_name),
        )

    def plot_table_by_id(
        self,
        path: Path,
        plot_type_id: int,
        template: str,
        selected_cols: list[str | int] | None = None,
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
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef]:
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

        columns = [str(col) for col in df.columns]
        selected = self._resolve_selected_columns(columns, selected_cols)
        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.from_df(df)
        command, range_option = self._table_plot_command_options(plot_type_id)
        if command in {"plotxyz", "worksheet"}:
            self._set_plotxyz_designations(wks, columns, selected, plot_type_id)
        data_range = self._worksheet_range_expr(wks, columns, selected)
        graph_name_actual = graph_name or self._safe_filename(f"{template}_{plot_type_id}")
        existing_graphs = self._graph_page_names()
        if command == "worksheet":
            script = self._worksheet_plot_command(columns, selected, plot_type_id, template)
            result = self._execute_on_worksheet(wks, script)
        else:
            script = self._plot_command(
                command=command,
                range_option=range_option,
                data_range=data_range,
                plot_type_id=plot_type_id,
                template=template,
                graph_name=graph_name_actual,
            )
            result = self.run_labtalk(script)
        graph_name_actual = self._created_graph_name(
            requested_graph_name=graph_name_actual,
            existing_graphs=existing_graphs,
        )
        self._remember_graph_alias(graph_name, graph_name_actual)
        if title or x_label or y_label:
            try:
                self.format_graph(
                    graph_name=graph_name_actual,
                    title=title,
                    x_label=x_label,
                    y_label=y_label,
                    rescale=True,
                )
            except OriginOperationError:
                pass
        self._suppress_graph_title_text(graph_name=graph_name_actual, title=title)
        style_mode_actual = self._normalize_style_mode(style_mode)
        if style_mode_actual == "publication":
            self.apply_publication_style(graph_name=graph_name_actual)
        elif style_mode_actual == "nature":
            self.apply_nature_style(
                graph_name=graph_name_actual,
                chart_type=self._nature_chart_type_for_plot_id(plot_type_id, template),
            )
        exported = None
        if export_path is not None:
            exported = self._export_plot_command_graph(export_path, graph_name_actual)["path"]
        worksheet = self._worksheet_ref(wks, columns=columns, rows=len(df))
        return (
            worksheet,
            GraphRef(
                graph_name=graph_name_actual,
                export_path=exported,
                template=template,
                style_mode=style_mode_actual,
                requested_graph_name=graph_name,
                display_name=self._graph_display_name(
                    graph_name_actual,
                    default=title or graph_name,
                ),
            ),
            {
                "script": script,
                "result": result.get("result"),
                "plot_type_id": plot_type_id,
                "template": template,
                "selected_columns": selected,
                "command": command,
                "range_option": range_option,
            },
        )

    def plot_matrix_by_id(
        self,
        data_range: str,
        plot_type_id: int,
        template: str,
        graph_name: str | None = None,
        title: str | None = None,
        export_path: Path | None = None,
    ) -> GraphRef:
        if not data_range.strip():
            raise OriginOperationError("data_range is empty.")
        graph_name_actual = graph_name or self._safe_filename(f"{template}_{plot_type_id}")
        command = "plotm" if plot_type_id in MATRIX_PLOTM_IDS else "plotxyz"
        range_option = "im" if command == "plotm" else "iz"
        if command == "plotm":
            self._activate_range_window(data_range)
        script = self._plot_command(
            command=command,
            range_option=range_option,
            data_range=data_range,
            plot_type_id=plot_type_id,
            template=template,
            graph_name=graph_name_actual,
        )
        result = self.run_labtalk(script)
        if not result.get("result"):
            raise OriginOperationError(f"Origin rejected plot command: {script}")
        if title:
            try:
                self.format_graph(graph_name=graph_name_actual, title=title, rescale=True)
            except OriginOperationError:
                pass
        else:
            self._suppress_graph_title_text(graph_name=graph_name_actual, title=None)
        exported = None
        if export_path is not None:
            exported = self._export_plot_command_graph(export_path, graph_name_actual)["path"]
        return GraphRef(graph_name=graph_name_actual, export_path=exported)

    @staticmethod
    def _table_plot_command_options(plot_type_id: int) -> tuple[str, str]:
        if plot_type_id in TABLE_WORKSHEET_PLOT_IDS:
            return "worksheet", "selection"
        if plot_type_id in TABLE_PLOTXYZ_IDS:
            return "plotxyz", "iz"
        return "plotxy", "iy"

    @staticmethod
    def _worksheet_plot_command(
        columns: list[str],
        selected: list[str],
        plot_type_id: int,
        template: str,
    ) -> str:
        indexes = [columns.index(column) + 1 for column in selected]
        if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
            raise OriginOperationError(
                f"Plot type {plot_type_id} requires a contiguous worksheet selection."
            )
        safe_template = _OriginClientBase._escape_labtalk(template)
        return (
            f"worksheet -s {indexes[0]} 0 {indexes[-1]} 0; "
            f"worksheet -p {plot_type_id} {safe_template};"
        )

    def _activate_range_window(self, data_range: str) -> None:
        if not data_range.startswith("[") or "]" not in data_range:
            return
        window_name = data_range[1:].split("]", 1)[0].strip()
        if not window_name:
            return
        try:
            self.run_labtalk(f'win -a "{self._escape_labtalk(window_name)}";')
        except OriginOperationError:
            pass

    def _set_plotxyz_designations(
        self,
        wks: Any,
        columns: list[str],
        selected: list[str],
        plot_type_id: int,
    ) -> None:
        if len(selected) < 3:
            return
        type_pattern = self._plotxyz_type_pattern(plot_type_id, len(selected))
        indexes = [columns.index(column) for column in selected[: len(type_pattern)]]
        cols_axis = getattr(wks, "cols_axis", None)
        if callable(cols_axis) and indexes == list(range(indexes[0], indexes[0] + len(indexes))):
            try:
                cols_axis(
                    self._plotxyz_axis_spec(type_pattern),
                    c1=indexes[0],
                    c2=indexes[-1],
                    repeat=False,
                )
                return
            except Exception:
                pass
        script = " ".join(
            f"wks.col{index + 1}.type={column_type};"
            for index, column_type in zip(indexes, type_pattern, strict=True)
        )
        self._execute_on_worksheet(wks, script)

    @staticmethod
    def _plotxyz_type_pattern(plot_type_id: int, selected_count: int) -> tuple[int, ...]:
        if plot_type_id == 183 and selected_count >= 6:
            return (4, 1, 6, 4, 1, 6)
        if plot_type_id == 184 and selected_count >= 4:
            return (4, 1, 6, 6)
        return (4, 1, 6)

    @staticmethod
    def _plotxyz_axis_spec(type_pattern: tuple[int, ...]) -> str:
        symbols = {1: "Y", 4: "X", 6: "Z"}
        return "".join(symbols.get(column_type, "Y") for column_type in type_pattern)

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
                export_path=export_path,
            )
            command = None
        diagnostics = self.diagnose_graph(
            graph_name=graph.graph_name,
            style=style_mode_actual if style_mode_actual == "nature" else None,
            palette_role=selected.get("palette_role"),
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
                export_path=export_path,
            )

        style_result = None
        if style_mode_actual == "nature":
            style_result = self.apply_nature_style(
                graph_name=graph.graph_name,
                chart_type=str(route["chart_type"]),
                palette_role=route_palette,
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
        add_plot(data_range, type=plot_type)
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
                "publication": (
                    "Apply origin-mcp publication styling after Origin creates the graph."
                ),
                "nature": ("Apply a compact Nature-style scientific figure preset after plotting."),
            },
            "mcp_overrides": {
                "origin_default": ["title", "axis titles", "legend refresh", "axis rescale"],
                "publication": [
                    "title",
                    "axis titles",
                    "legend refresh",
                    "axis rescale",
                    "axis/title font sizes",
                    "tick lengths",
                    "line width",
                    "symbol size",
                    "legend font size",
                ],
                "nature": [
                    "Arial-compatible font settings",
                    "small axis/title/tick/legend font sizes",
                    "short ticks",
                    "thin lines",
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

    def _new_graph(self, kind: str, graph_name: str | None, template: str | None = None) -> Any:
        op = self.op
        new_graph = getattr(op, "new_graph", None)
        if not callable(new_graph):
            raise OriginOperationError("originpro.new_graph is not available.")

        graph_template = self._resolve_graph_template(kind=kind, template=template)
        kwargs: dict[str, Any] = {"template": graph_template}
        if graph_name:
            kwargs["lname"] = graph_name

        try:
            return new_graph(**kwargs)
        except TypeError:
            graph = new_graph(graph_template)
            if graph_name:
                self._set_page_long_name(graph, graph_name)
            return graph

    @staticmethod
    def _default_graph_templates() -> dict[str, str]:
        return {
            "line": "line",
            "scatter": "scatter",
            "line_symbol": "line",
            "column": "column",
            "contour": "contour",
            "histogram": "histogram",
            "box": "box",
            "heatmap": "heatmap",
            "scatter3d": "3dscatter",
            "surface3d": "surface",
            "polar": "polar",
        }

    def _resolve_graph_template(self, kind: str, template: str | None = None) -> str:
        return template or self._default_graph_templates().get(kind, "line")

    @classmethod
    def _nature_chart_style(
        cls,
        chart_type: str | None,
        line_width: float,
        symbol_size: float,
    ) -> dict[str, Any]:
        normalized = cls._normalize_chart_type(chart_type)
        line_default = line_width == 1.2
        symbol_default = symbol_size == 4.5
        rules: dict[str, dict[str, float | None]] = {
            "line": {"line_width": 1.2, "symbol_size": 4.5},
            "scatter": {"line_width": 0.8, "symbol_size": 5.0},
            "bar": {"line_width": 0.8, "symbol_size": None},
            "box": {"line_width": 0.9, "symbol_size": None},
            "heatmap": {"line_width": None, "symbol_size": None},
            "surface": {"line_width": 0.8, "symbol_size": None},
            "polar": {"line_width": 1.0, "symbol_size": 4.5},
            "generic": {"line_width": line_width, "symbol_size": symbol_size},
        }
        selected = rules.get(normalized, rules["generic"])
        return {
            "chart_type": normalized,
            "line_width": selected["line_width"] if line_default else line_width,
            "symbol_size": selected["symbol_size"] if symbol_default else symbol_size,
        }

    @staticmethod
    def _normalize_chart_type(chart_type: str | None) -> str:
        value = (chart_type or "generic").strip().lower().replace("-", "_").replace(" ", "_")
        if value in {"l", "line", "line_symbol", "linesymbol", "line_scatter"}:
            return "line"
        if value in {
            "s",
            "scatter",
            "scatter3d",
            "3dscatter",
            "3d_scatter",
            "bubble",
            "bubble_color_mapped",
            "color_mapped",
        }:
            return "scatter"
        if value in {
            "bar",
            "column",
            "histogram",
            "stack_bar",
            "floating_bar",
            "column_stack",
            "3d_bars",
        }:
            return "bar"
        if value in {"box", "boxplot"}:
            return "box"
        if value in {
            "heatmap",
            "contour",
            "image",
            "matrix_heatmap",
            "matrix_contour",
            "ternary_contour",
        }:
            return "heatmap"
        if value in {
            "surface",
            "surface3d",
            "3d_surface",
            "matrix_3d_surface",
            "waterfall",
            "3d_ribbon",
        }:
            return "surface"
        if value in {"polar", "polar_xr_ytheta", "ternary", "smith"}:
            return "polar"
        return "generic"

    @classmethod
    def _nature_chart_type_for_plot_id(cls, plot_type_id: int, template: str) -> str:
        from_template = cls._normalize_chart_type(template)
        if from_template != "generic":
            return from_template
        if plot_type_id in {200, 202, 205, 207}:
            return "line"
        if plot_type_id in {193, 201, 240, 242, 243, 245, 247}:
            return "scatter"
        if plot_type_id in {203, 215, 216, 217, 219}:
            return "bar"
        if plot_type_id in {101, 103, 105, 220, 226}:
            return "heatmap"
        if plot_type_id in {241, 242, 243}:
            return "surface"
        return "generic"

    @classmethod
    def _chart_atlas_routes(cls) -> dict[str, dict[str, Any]]:
        return {
            "correlation": {
                "kind": "scatter",
                "chart_type": "scatter",
                "template": "scatter",
                "palette_role": "hero",
                "regression": True,
                "matrix_required": False,
                "rationale": "Correlation is clearest as scatter with a linear-fit summary.",
            },
            "effect_size": {
                "plot_type_id": 231,
                "template": "Errbar",
                "chart_type": "line",
                "palette_role": "hero,neutral",
                "matrix_required": False,
                "rationale": "Effect sizes are best shown as interval/error-bar estimates.",
            },
            "composition": {
                "plot_type_id": 216,
                "template": "bar",
                "chart_type": "bar",
                "palette_role": "hero,secondary,accent,neutral",
                "matrix_required": False,
                "rationale": "Compositional comparisons are routed to stacked/grouped bars.",
            },
            "matrix": {
                "plot_type_id": 105,
                "template": "heatmap",
                "chart_type": "heatmap",
                "palette_role": "neutral",
                "matrix_required": True,
                "rationale": "Matrix-like values are best represented as a heatmap.",
            },
            "image_plate": {
                "plot_type_id": 220,
                "template": "image",
                "chart_type": "heatmap",
                "palette_role": "neutral",
                "matrix_required": True,
                "rationale": "Image plates should use image/heatmap plots plus panel metadata.",
            },
            "time_series": {
                "kind": "line",
                "chart_type": "line",
                "template": "line",
                "palette_role": "hero,baseline",
                "matrix_required": False,
                "rationale": "Ordered continuous values are routed to line plots.",
            },
            "distribution": {
                "kind": "box",
                "chart_type": "box",
                "template": "box",
                "palette_role": "hero,neutral",
                "matrix_required": False,
                "rationale": "Distribution summaries are routed to compact box plots.",
            },
        }

    @classmethod
    def _normalize_chart_intent(cls, intent: str) -> str:
        value = intent.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "corr": "correlation",
            "correlation_plot": "correlation",
            "regression": "correlation",
            "effect": "effect_size",
            "effectsize": "effect_size",
            "forest": "effect_size",
            "interval": "effect_size",
            "composition_plot": "composition",
            "stacked_bar": "composition",
            "grouped_bar": "composition",
            "heatmap": "matrix",
            "matrix_heatmap": "matrix",
            "image": "image_plate",
            "microscopy": "image_plate",
            "image_panel": "image_plate",
            "timeseries": "time_series",
            "time": "time_series",
            "histogram": "distribution",
            "box": "distribution",
        }
        normalized = aliases.get(value, value)
        if normalized not in cls._chart_atlas_routes():
            supported = ", ".join(sorted(cls._chart_atlas_routes()))
            raise OriginOperationError(
                f"Unsupported chart atlas intent: {intent!r}. Supported: {supported}."
            )
        return normalized

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

    @staticmethod
    def _nature_palette() -> list[tuple[int, int, int]]:
        return [
            (0, 114, 178),
            (213, 94, 0),
            (0, 158, 115),
            (204, 121, 167),
            (230, 159, 0),
            (86, 180, 233),
            (240, 228, 66),
            (0, 0, 0),
        ]

    @staticmethod
    def _nature_semantic_palette() -> dict[str, tuple[int, int, int]]:
        return {
            "hero": (0, 114, 178),
            "baseline": (0, 0, 0),
            "positive": (0, 158, 115),
            "negative": (213, 94, 0),
            "neutral": (117, 117, 117),
            "accent": (204, 121, 167),
            "secondary": (86, 180, 233),
            "warning": (230, 159, 0),
        }

    @classmethod
    def _nature_acceptable_palette(cls) -> set[tuple[int, int, int]]:
        return set(cls._nature_palette()) | set(cls._nature_semantic_palette().values())

    @classmethod
    def _palette_roles(
        cls,
        palette_role: str | list[str] | None,
        plot_count: int,
    ) -> list[str]:
        if plot_count <= 0:
            return []
        if palette_role is None:
            return [""] * plot_count
        if isinstance(palette_role, str):
            raw_roles = [role.strip().lower() for role in palette_role.split(",")]
        else:
            raw_roles = [str(role).strip().lower() for role in palette_role]
        available = cls._nature_semantic_palette()
        roles = [role for role in raw_roles if role in available]
        if not roles:
            return [""] * plot_count
        if len(roles) == 1 and plot_count > 1:
            return roles + ["neutral"] * (plot_count - 1)
        return [roles[index % len(roles)] for index in range(plot_count)]

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

    @staticmethod
    def _plot_command(
        command: str,
        range_option: str,
        data_range: str,
        plot_type_id: int,
        template: str,
        graph_name: str,
    ) -> str:
        safe_template = _OriginClientBase._escape_labtalk(template)
        safe_graph = _OriginClientBase._escape_labtalk(graph_name)
        return (
            f"{command} {range_option}:={data_range} plot:={plot_type_id} "
            f"ogl:=<new template:={safe_template} name:={safe_graph}>;"
        )

