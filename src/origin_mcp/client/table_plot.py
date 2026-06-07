from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import template_library
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
    ) -> tuple[WorksheetRef, GraphRef]:
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

    def plot_dual_y(
        self,
        path: Path,
        x_col: str | int | None = None,
        y1_cols: list[str | int] | None = None,
        y2_cols: list[str | int] | None = None,
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
        y1_label: str | None = None,
        y2_label: str | None = None,
        plot_type: str = "line",
        style_mode: str = "origin_default",
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef]:
        if not y1_cols or not y2_cols:
            raise OriginOperationError(
                "Both y1_cols (left axis) and y2_cols (right axis) are required.",
                error_code="invalid_request",
            )
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
        y1_names = [self._resolve_column(columns, col, default_index=1) for col in y1_cols]
        y2_names = [self._resolve_column(columns, col, default_index=1) for col in y2_cols]
        style_mode_actual = self._normalize_style_mode(style_mode)

        actual_book_name = book_name or (
            self._safe_filename(f"{graph_name}_Data") if graph_name else None
        )
        wks = self._new_sheet(book_name=actual_book_name, sheet_name=sheet_name)
        wks.from_df(df)

        # The built-in "doubleY" template makes layer 2 share layer 1's X axis
        # and draw its own Y axis on the right, so we just add each side's plots
        # to the matching layer.
        graph = self._new_graph(kind="line", graph_name=graph_name, template="doubleY")
        layer_left = self._graph_layer(graph, 0)
        layer_right = self._graph_layer(graph, 1)
        for y_name in y1_names:
            self._add_plot(layer_left, wks, x_name=x_name, y_name=y_name, kind=plot_type)
        for y_name in y2_names:
            self._add_plot(layer_right, wks, x_name=x_name, y_name=y_name, kind=plot_type)

        actual_graph_name = self._object_name(graph, default=graph_name or "Graph")
        if len(y1_names) > 1:
            self._group_layer_plots(layer_left, graph_name=actual_graph_name, layer_index=0)
        if len(y2_names) > 1:
            self._group_layer_plots(layer_right, graph_name=actual_graph_name, layer_index=1)

        layer_left.axis("x").title = self._label_text(x_label or x_name)
        layer_left.axis("y").title = self._label_text(y1_label or ", ".join(y1_names))
        layer_right.axis("y").title = self._label_text(y2_label or ", ".join(y2_names))
        if title:
            self._set_page_long_name(graph, title, force_labtalk=graph_name is not None)
        self._rescale(layer_left)
        self._rescale(layer_right)
        self._remember_graph_alias(graph_name, actual_graph_name)
        if style_mode_actual == "nature":
            self.apply_nature_style(graph_name=actual_graph_name, chart_type=plot_type)

        exported: str | None = None
        if export_path is not None:
            exported = self._export_plot_command_graph(export_path, actual_graph_name)["path"]

        worksheet = self._worksheet_ref(wks, columns=columns, rows=len(df))
        return worksheet, GraphRef(
            graph_name=actual_graph_name,
            export_path=exported,
            template="doubleY",
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
    ) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
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
        if plot_type_id == 242:
            # Plot type 242 (3D Colormap Surface) consumes a matrix, not scattered
            # XYZ worksheet columns: plotxyz against XYZ produces an empty graph.
            # Grid the XYZ data into a matrix and plot it as a matrix surface (103).
            return self._plot_surface_from_xyz_table(
                df=df,
                wks=wks,
                columns=columns,
                selected=selected,
                graph_name=graph_name,
                title=title,
                x_label=x_label,
                y_label=y_label,
                style_mode=style_mode,
                palette_name=palette_name,
                export_path=export_path,
            )
        command, range_option = self._table_plot_command_options(plot_type_id)
        if command == "plotxyz" or plot_type_id in {183, 184}:
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
        self._assert_plot_created(
            plot_type_id=plot_type_id,
            template=template,
            selected=selected,
            existing_graphs=existing_graphs,
            reuse_existing=reuse_existing_graph,
            result=result,
            script=script,
        )
        graph_name_actual = self._created_graph_name(
            requested_graph_name=graph_name_actual,
            existing_graphs=existing_graphs,
            prefer_created=command == "worksheet",
        )
        output_warning = self._plot_command_output_warning(
            requested_graph_name=graph_name or graph_name_actual,
            actual_graph_name=graph_name_actual,
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
                "warning": output_warning,
            },
        )

    def _plot_surface_from_xyz_table(
        self,
        *,
        df: Any,
        wks: Any,
        columns: list[str],
        selected: list[str],
        graph_name: str | None,
        title: str | None,
        x_label: str | None,
        y_label: str | None,
        style_mode: str,
        palette_name: str | None,
        export_path: Path | None,
    ) -> tuple[WorksheetRef, GraphRef, dict[str, Any]]:
        """Grid scattered XYZ worksheet data into a matrix and plot a 3D
        colormap surface (matrix plot type 103), mirroring the return shape of
        :meth:`plot_table_by_id`."""

        data_range = self._build_surface_matrix_from_xyz(df, selected)
        existing_graphs = self._graph_page_names()
        graph_name_actual = graph_name or self._safe_filename("glmesh_242")
        self._activate_range_window(data_range)
        script = self._plot_command(
            command="plotm",
            range_option="im",
            data_range=data_range,
            plot_type_id=103,
            template="glmesh",
            graph_name=graph_name_actual,
        )
        result = self.run_labtalk(script)
        if not result.get("result"):
            raise OriginOperationError(f"Origin rejected surface plot command: {script}")
        graph_name_actual = self._created_graph_name(
            requested_graph_name=graph_name_actual,
            existing_graphs=existing_graphs,
        )
        output_warning = self._plot_command_output_warning(
            requested_graph_name=graph_name or graph_name_actual,
            actual_graph_name=graph_name_actual,
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
            style_kwargs: dict[str, Any] = {
                "graph_name": graph_name_actual,
                "chart_type": self._nature_chart_type_for_plot_id(242, "glmesh"),
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
                template="glmesh",
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
                "plot_type_id": 242,
                "template": "glmesh",
                "selected_columns": selected,
                "command": "plotm",
                "range_option": "im",
                "data_range": data_range,
                "warning": output_warning,
            },
        )

    def _build_surface_matrix_from_xyz(self, df: Any, selected: list[str]) -> str:
        """Build a regularly-gridded Origin matrix from XYZ worksheet columns and
        return its data range (e.g. ``[MBook1]MSheet1!1``). Expects data that
        lies on a rectangular X/Y grid; missing grid cells become gaps."""

        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - numpy ships with originpro
            raise OriginOperationError("numpy is required to build a 3D surface matrix.") from exc

        if len(selected) < 3:
            raise OriginOperationError(
                "A 3D surface needs three columns (X, Y, Z); "
                f"got {len(selected)} selected column(s)."
            )
        x_name, y_name, z_name = selected[0], selected[1], selected[2]
        x = np.round(df[x_name].to_numpy(dtype=float), 9)
        y = np.round(df[y_name].to_numpy(dtype=float), 9)
        z = df[z_name].to_numpy(dtype=float)

        xs = np.unique(x)
        ys = np.unique(y)
        if len(xs) < 2 or len(ys) < 2:
            raise OriginOperationError(
                "A 3D surface needs at least a 2x2 grid of distinct X and Y values."
            )
        x_index = {value: idx for idx, value in enumerate(xs)}
        y_index = {value: idx for idx, value in enumerate(ys)}
        grid = np.full((len(ys), len(xs)), np.nan, dtype=float)
        for xv, yv, zv in zip(x, y, z, strict=True):
            grid[y_index[yv], x_index[xv]] = zv

        op = self.op
        new_sheet = getattr(op, "new_sheet", None)
        if not callable(new_sheet):
            raise OriginOperationError("originpro.new_sheet is not available.")
        msheet = new_sheet("m")
        from_np = getattr(msheet, "from_np", None)
        if not callable(from_np):
            raise OriginOperationError("Matrix sheet does not support from_np().")
        from_np(grid)

        range_base = msheet.lt_range(False)
        book_name = range_base[1:].split("]", 1)[0] if range_base.startswith("[") else range_base
        self.run_labtalk(
            f'win -a "{self._escape_labtalk(book_name)}"; '
            f"mdim cols:={len(xs)} rows:={len(ys)} "
            f"x1:={xs[0]} x2:={xs[-1]} y1:={ys[0]} y2:={ys[-1]};"
        )
        return f"{range_base}!1"

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
    def _plot_command_output_warning(
        requested_graph_name: str | None,
        actual_graph_name: str | None,
    ) -> str | None:
        if not requested_graph_name or not actual_graph_name:
            return None
        if requested_graph_name == actual_graph_name:
            return None
        return (
            f"Origin did not create or expose the requested graph {requested_graph_name!r}; "
            f"using actual graph {actual_graph_name!r}."
        )

    def _assert_plot_created(
        self,
        plot_type_id: int,
        template: str,
        selected: list[str],
        existing_graphs: set[str],
        reuse_existing: bool,
        result: dict[str, Any],
        script: str,
    ) -> None:
        """Fail loudly when Origin rejected the plot command instead of silently
        returning a graph that was never created.

        Origin's ``worksheet -p`` route runs through the worksheet object's
        ``lt_exec``, whose boolean result does not survive the bridge (it comes
        back as ``None`` on both success and failure), so the only reliable
        success signal is that a new graph page actually appeared. The
        ``plotxy``/``plotxyz`` route does return a usable boolean, so an explicit
        ``False`` is treated as a rejection directly."""

        if reuse_existing:
            return
        status = result.get("result")
        if status is False:
            # plotxy/plotxyz return an authoritative boolean; False is a rejection.
            raise OriginOperationError(
                self._plot_rejected_message(plot_type_id, template, selected, script)
            )
        if status is True:
            return
        # status is None: the worksheet route's lt_exec boolean did not survive the
        # bridge, so the only reliable success signal is a newly created graph
        # page. Skip the check when page enumeration is unavailable so we never
        # raise on a false negative.
        if not callable(getattr(self._op, "pages", None)):
            return
        if self._graph_page_names() - existing_graphs:
            return
        raise OriginOperationError(
            self._plot_rejected_message(plot_type_id, template, selected, script)
        )

    @staticmethod
    def _plot_rejected_message(
        plot_type_id: int,
        template: str,
        selected: list[str],
        script: str,
    ) -> str:
        return (
            f"Origin created no graph for plot type {plot_type_id} ({template}); "
            "the plot command was rejected. Check that the selected columns match "
            f"the plot type's required input (got {selected}). Script: {script}"
        )

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
        if template:
            # A bare name may refer to a user-library template; resolve it to the
            # saved .otpu path so any plotting tool can reuse it by name. Built-in
            # names and explicit paths are not in the library and pass through for
            # Origin to resolve.
            saved = template_library.resolve_template_name(template)
            return str(saved) if saved is not None else template
        return self._default_graph_templates().get(kind, "line")

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
        return f"{command} {range_option}:={data_range} plot:={plot_type_id} {output_graph};"
