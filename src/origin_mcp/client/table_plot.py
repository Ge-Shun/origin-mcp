from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import OriginOperationError
from .base import (
    MATRIX_PLOTM_IDS,
    TABLE_PLOTXYZ_IDS,
    TABLE_WORKSHEET_PLOT_IDS,
    GraphRef,
    WorksheetRef,
    _OriginClientBase,
)


class _TablePlotMixin(_OriginClientBase):
    """Table-driven plotting: import CSV/Excel data and plot directly.

    Owns plot_csv / plot_table / plot_table_by_id / plot_matrix_by_id and
    the worksheet/plotxyz/matrix LabTalk command builders. Also home to
    the cross-cutting graph-construction helpers (_new_graph, template
    resolution, _plot_command) that other plotting flows reach via MRO.
    """

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
        palette_name: str | None = None,
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
            palette_name=palette_name,
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
        palette_name: str | None = None,
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

        actual_book_name = book_name or (
            self._safe_filename(f"{graph_name}_Data") if graph_name else None
        )
        wks = self._new_sheet(book_name=actual_book_name, sheet_name=sheet_name)
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

        actual_graph_name = self._object_name(graph, default=graph_name or "Graph")
        if kind in {"column", "c"} and len(y_names) > 1:
            self._group_layer_plots(layer, graph_name=actual_graph_name, layer_index=0)

        self.format_graph(
            graph=graph,
            title=title,
            x_label=x_label or x_name,
            y_label=y_label or ", ".join(y_names),
            show_legend=show_legend,
            rescale=True,
        )
        self._remember_graph_alias(graph_name, actual_graph_name)
        if style_mode_actual == "nature":
            style_kwargs: dict[str, Any] = {
                "graph_name": actual_graph_name,
                "chart_type": kind,
            }
            if palette_name is not None:
                style_kwargs["palette_name"] = palette_name
            self.apply_nature_style(**style_kwargs)
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
        palette_name: str | None = None,
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
        actual_book_name = book_name or (
            self._safe_filename(f"{graph_name}_Data") if graph_name else None
        )
        wks = self._new_sheet(book_name=actual_book_name, sheet_name=sheet_name)
        wks.from_df(df)
        command, range_option = self._table_plot_command_options(plot_type_id)
        if command in {"plotxyz", "worksheet"}:
            self._set_plotxyz_designations(wks, columns, selected, plot_type_id)
        data_range = self._worksheet_range_expr(wks, columns, selected)
        graph_name_actual = graph_name or self._safe_filename(f"{template}_{plot_type_id}")
        existing_graphs = self._graph_page_names()
        existing_graph = self._find_graph_optional(graph_name_actual)
        reuse_existing_graph = existing_graph is not None and command != "worksheet"
        if reuse_existing_graph:
            self._clear_graph_plots(existing_graph, graph_name_actual)
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
                reuse_existing=reuse_existing_graph,
            )
            result = self.run_labtalk(script)
        self._assert_plot_type_command(
            plot_type_id=plot_type_id,
            template=template,
            command=command,
            range_option=range_option,
            script=script,
        )
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
        if style_mode_actual == "nature":
            style_kwargs = {
                "graph_name": graph_name_actual,
                "chart_type": self._nature_chart_type_for_plot_id(plot_type_id, template),
            }
            if palette_name is not None:
                style_kwargs["palette_name"] = palette_name
            self.apply_nature_style(**style_kwargs)
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

    def _assert_plot_type_command(
        self,
        plot_type_id: int,
        template: str,
        command: str,
        range_option: str,
        script: str,
    ) -> None:
        expected_command, expected_range_option = self._table_plot_command_options(plot_type_id)
        expected_fragments = {
            "plotxy": f"plotxy {expected_range_option}:=",
            "plotxyz": f"plotxyz {expected_range_option}:=",
            "worksheet": f"worksheet -p {plot_type_id} {template}",
        }
        expected_fragment = expected_fragments[expected_command]
        if (
            command != expected_command
            or range_option != expected_range_option
            or expected_fragment not in script
        ):
            raise OriginOperationError(
                "Plot type route mismatch: "
                f"id={plot_type_id}, expected {expected_command}/{expected_range_option}, "
                f"got {command}/{range_option}."
            )

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


    def _new_graph(self, kind: str, graph_name: str | None, template: str | None = None) -> Any:
        if graph_name:
            graph = self._find_graph_optional(graph_name)
            if graph is not None:
                self._clear_graph_plots(graph, graph_name)
                self._set_page_long_name(graph, graph_name)
                return graph

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

    @staticmethod
    def _plot_command(
        command: str,
        range_option: str,
        data_range: str,
        plot_type_id: int,
        template: str,
        graph_name: str,
        reuse_existing: bool = False,
    ) -> str:
        safe_template = _OriginClientBase._escape_labtalk(template)
        safe_graph = _OriginClientBase._escape_labtalk(graph_name)
        output_graph = (
            f"ogl:=[{safe_graph}]1"
            if reuse_existing
            else f"ogl:=<new template:={safe_template} name:={safe_graph}>"
        )
        return (
            f"{command} {range_option}:={data_range} plot:={plot_type_id} "
            f"{output_graph};"
        )

