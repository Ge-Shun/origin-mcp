from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis_adapters import resolve_analysis_adapter, xf_options
from .compat import collect_capabilities, feature_available
from .errors import OriginDependencyError, OriginOperationError


@dataclass(frozen=True)
class WorksheetRef:
    book_name: str
    sheet_name: str
    columns: list[str]
    rows: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "book_name": self.book_name,
            "sheet_name": self.sheet_name,
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass(frozen=True)
class GraphRef:
    graph_name: str
    export_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"graph_name": self.graph_name, "export_path": self.export_path}


class OriginClient:
    """Small wrapper around the `originpro` package.

    The import is intentionally lazy so the MCP server can start and list tools even
    on machines where Origin is not installed yet.
    """

    def __init__(self) -> None:
        self._op: Any | None = None
        self._capabilities: dict[str, Any] | None = None

    @property
    def op(self) -> Any:
        if self._op is None:
            try:
                self._op = importlib.import_module("originpro")
            except ImportError as exc:
                raise OriginDependencyError(
                    "The 'originpro' package is not available. Install Origin/OriginPro and "
                    "run `python -m pip install -e .[origin]`, or make Origin's Python package "
                    "visible to this interpreter."
                ) from exc
        return self._op

    def connect(self, show: bool = True) -> dict[str, Any]:
        op = self.op
        if hasattr(op, "set_show"):
            op.set_show(show)

        version = self._safe_eval("@V")
        return {
            "connected": True,
            "visible": show,
            "origin_version": version,
        }

    def capabilities(self, show: bool = False, refresh: bool = False) -> dict[str, Any]:
        if self._capabilities is not None and not refresh:
            return self._capabilities
        connection = self.connect(show=show)
        self._capabilities = {
            **connection,
            **collect_capabilities(self.op, connection.get("origin_version")),
        }
        return self._capabilities

    def ensure_feature(self, feature: str, operation: str) -> None:
        caps = self.capabilities(show=False)
        if feature_available(caps, feature):
            return
        info = caps.get("features", {}).get(feature, {})
        minimum = info.get("minimum_origin_version")
        note = info.get("note") or "No compatible API was detected."
        version = caps.get("origin_version")
        requirement = f" Requires Origin >= {minimum}." if minimum else ""
        raise OriginOperationError(
            f"{operation} is not supported by this Origin/originpro environment. "
            f"Detected Origin version: {version}.{requirement} {note}"
        )

    def new_project(self, show: bool = True) -> dict[str, Any]:
        op = self.op
        if hasattr(op, "set_show"):
            op.set_show(show)
        self._call_first_available(op, ["new", "new_project"])
        return {"created": True}

    def open_project(
        self,
        path: Path,
        readonly: bool = False,
        asksave: bool = False,
    ) -> dict[str, Any]:
        path = path.expanduser().resolve()
        self._validate_file(path)
        if path.suffix.lower() not in {".opju", ".opj"}:
            raise OriginOperationError(f"Not an Origin project file: {path}")

        op = self.op
        open_project = getattr(op, "open", None)
        if not callable(open_project):
            raise OriginOperationError("originpro.open is not available.")
        ok = open_project(str(path), readonly=readonly, asksave=asksave)
        return {"path": str(path), "opened": bool(ok)}

    def save_project(self, path: Path) -> dict[str, Any]:
        path = path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        op = self.op

        if hasattr(op, "save"):
            op.save(str(path))
        else:
            self.run_labtalk(f'save -i "{path}";')
        return {"path": str(path)}

    def quit(self) -> dict[str, Any]:
        op = self.op
        for name in ("exit", "quit"):
            func = getattr(op, name, None)
            if callable(func):
                func()
                return {"closed": True}
        self.run_labtalk("exit;")
        return {"closed": True}

    def run_labtalk(self, script: str) -> dict[str, Any]:
        if not script.strip():
            raise OriginOperationError("LabTalk script is empty.")

        op = self.op
        func = getattr(op, "lt_exec", None)
        if not callable(func):
            raise OriginOperationError("originpro.lt_exec is not available in this environment.")

        result = func(script)
        return {"result": result}

    def import_csv(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> WorksheetRef:
        return self.import_table(path=path, book_name=book_name, sheet_name=sheet_name)

    def import_table(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
    ) -> WorksheetRef:
        path = path.expanduser().resolve()
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

        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        if hasattr(wks, "from_df"):
            wks.from_df(df)
        else:
            raise OriginOperationError(
                "The worksheet object does not support from_df(); update the originpro package."
            )

        return self._worksheet_ref(wks, columns=[str(col) for col in df.columns], rows=len(df))

    def import_file_connector(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        keep_dc: bool = True,
        dctype: str = "",
        sel: str = "",
        sparks: bool = False,
    ) -> WorksheetRef:
        path = path.expanduser().resolve()
        self._validate_file(path)
        self.ensure_feature("worksheet_from_file", "Origin Data Connector import")
        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        from_file = getattr(wks, "from_file", None)
        if not callable(from_file):
            raise OriginOperationError("The worksheet object does not support from_file().")
        from_file(str(path), keep_dc, dctype, sel, sparks)
        if book_name:
            try:
                wks.get_book().lname = book_name
            except Exception:
                pass
        return self._worksheet_ref(wks)

    def append_table(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        start_col: str | int = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
    ) -> WorksheetRef:
        path = path.expanduser().resolve()
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

        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.from_df(df, c1=start_col)
        return self._worksheet_ref(wks, columns=[str(col) for col in df.columns], rows=len(df))

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
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef]:
        path = path.expanduser().resolve()
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
            self._resolve_column(columns, z_col, default_index=2)
            if z_col is not None
            else None
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

        graph = self._new_graph(kind=kind, graph_name=graph_name, template=template)
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
        exported: str | None = None
        if export_path is not None:
            exported = self.export_graph(export_path, graph=graph)["path"]

        worksheet = self._worksheet_ref(wks, columns=columns, rows=len(df))
        return worksheet, GraphRef(graph_name=actual_graph_name, export_path=exported)

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
            ax.title = self._labtalk_text(title)
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

    def set_column_labels(
        self,
        labels: list[str],
        label_type: str = "L",
        book_name: str | None = None,
        sheet_name: str | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.set_labels(labels, label_type, offset=offset)
        return self._worksheet_ref(wks).as_dict()

    def set_column_designations(
        self,
        spec: str,
        book_name: str | None = None,
        sheet_name: str | None = None,
        c1: int = 0,
        c2: int = -1,
        repeat: bool = True,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.cols_axis(spec, c1=c1, c2=c2, repeat=repeat)
        return self._worksheet_ref(wks).as_dict()

    def format_legend(
        self,
        graph_name: str | None = None,
        text: str | None = None,
        font_size: int | None = None,
        show_frame: bool | None = None,
        left: int | None = None,
        top: int | None = None,
    ) -> dict[str, Any]:
        graph = self._find_or_active_graph(graph_name)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph
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
        if left is not None:
            legend.set_int("left", left)
        if top is not None:
            legend.set_int("top", top)
        return {"graph_name": self._object_name(graph, default=graph_name or ""), "legend": True}

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
            return {"mode": "report", "report_sheet": report, "curve_sheet": curves}
        return {"mode": "result", "result": fit.result()}

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

    def run_analysis(
        self,
        analysis: str,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        output_sheet: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        script = self._analysis_script(
            analysis=analysis,
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_sheet,
            options=options or {},
        )
        result = self.run_labtalk(script)
        executed = bool(result.get("result"))
        return {
            "script": script,
            "executed": executed,
            "warning": "" if executed else "Origin returned false for this analysis command.",
            **result,
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
            layer.axis("x").title = self._labtalk_text(x_label)
        if y_label:
            layer.axis("y").title = self._labtalk_text(y_label)
        if title:
            self._set_graph_title(layer, title)

        if show_legend is not None:
            self._set_legend(layer, show=show_legend)
        if rescale:
            self._rescale(layer)

        return {
            "graph_name": self._object_name(target, default=graph_name or "Graph"),
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

        target = graph if graph is not None else self._find_or_active_graph(graph_name)
        if hasattr(target, "save_fig"):
            target.save_fig(str(path))
        elif graph_name:
            self.run_labtalk(f'win -a {graph_name}; expGraph type:=auto path:="{path}";')
        else:
            self.run_labtalk(f'expGraph type:=auto path:="{path}";')

        return {"path": str(path)}

    def _new_sheet(self, book_name: str | None, sheet_name: str | None) -> Any:
        op = self.op
        new_sheet = getattr(op, "new_sheet", None)
        if not callable(new_sheet):
            raise OriginOperationError("originpro.new_sheet is not available.")

        try:
            wks = new_sheet("w", book_name or "")
        except TypeError:
            wks = new_sheet()

        if book_name:
            try:
                wks.get_book().lname = book_name
            except Exception:
                pass

        if sheet_name:
            try:
                wks.name = sheet_name
            except Exception:
                try:
                    wks.lname = sheet_name
                except Exception as exc:
                    raise OriginOperationError(
                        f"Could not rename worksheet to {sheet_name!r}."
                    ) from exc
        return wks

    def _new_graph(self, kind: str, graph_name: str | None, template: str | None = None) -> Any:
        op = self.op
        new_graph = getattr(op, "new_graph", None)
        if not callable(new_graph):
            raise OriginOperationError("originpro.new_graph is not available.")

        default_templates = {
            "line": "line",
            "scatter": "scatter",
            "line_symbol": "linesymbol",
            "column": "column",
            "contour": "contour",
        }
        graph_template = template or default_templates.get(kind, "line")
        kwargs: dict[str, Any] = {"template": graph_template}
        if graph_name:
            kwargs["lname"] = graph_name

        try:
            return new_graph(**kwargs)
        except TypeError:
            return new_graph(graph_template)

    def _find_or_active_graph(self, graph_name: str | None) -> Any:
        op = self.op
        if hasattr(op, "find_graph"):
            graph = op.find_graph(graph_name or "")
            if graph is not None:
                return graph

        if graph_name:
            raise OriginOperationError(f"Graph not found: {graph_name}")

        raise OriginOperationError("No active graph found. Create or name a graph first.")

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
            "line": "l",
            "line_symbol": "y",
            "column": "c",
            "contour": "contour",
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

    def _set_graph_title(self, layer: Any, title: str) -> None:
        label = getattr(layer, "label", lambda _name: None)("title")
        if label is None:
            add_label = getattr(layer, "add_label", None)
            if callable(add_label):
                label = add_label(title)
        if label is not None:
            try:
                label.name = "title"
            except Exception:
                pass
            label.text = title

    @staticmethod
    def _read_table(
        path: Path,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
    ) -> pd.DataFrame:
        suffix = path.suffix.lower()
        if suffix in {".xls", ".xlsx", ".xlsm"}:
            return pd.read_excel(
                path,
                sheet_name=excel_sheet if excel_sheet is not None else 0,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
            )
        read_kwargs = {
            "encoding": encoding,
            "header": header,
            "skiprows": skiprows,
            "nrows": nrows,
            "na_values": na_values,
        }
        read_kwargs = {key: value for key, value in read_kwargs.items() if value is not None}
        if suffix == ".tsv":
            return pd.read_csv(path, sep=delimiter or "\t", **read_kwargs)
        if suffix in {".txt", ".dat"}:
            return pd.read_csv(path, sep=delimiter, engine="python", **read_kwargs)
        if suffix == ".csv":
            return pd.read_csv(path, sep=delimiter or ",", **read_kwargs)
        raise OriginOperationError(f"Unsupported data file extension: {path.suffix}")

    @staticmethod
    def _labtalk_text(text: str) -> str:
        return text.replace("\r", " ").replace("\n", " ")

    def _safe_eval(self, expression: str) -> Any:
        op = self.op
        func = getattr(op, "lt_float", None)
        if not callable(func):
            return None
        try:
            return func(expression)
        except Exception:
            return None

    @staticmethod
    def _validate_file(path: Path) -> None:
        OriginClient._check_path_allowed(path)
        if not path.exists():
            raise OriginOperationError(f"File does not exist: {path}")
        if not path.is_file():
            raise OriginOperationError(f"Path is not a file: {path}")

    @staticmethod
    def _check_path_allowed(path: Path) -> None:
        raw_roots = os.environ.get("ORIGIN_MCP_ALLOWED_ROOTS", "").strip()
        if not raw_roots:
            return
        resolved = path.expanduser().resolve()
        roots = [
            Path(root).expanduser().resolve()
            for root in raw_roots.split(os.pathsep)
            if root.strip()
        ]
        if not any(resolved == root or root in resolved.parents for root in roots):
            raise OriginOperationError(
                f"Path is outside ORIGIN_MCP_ALLOWED_ROOTS: {resolved}"
            )

    @staticmethod
    def _resolve_column(columns: list[str], value: str | int | None, default_index: int) -> str:
        if value is None:
            return columns[default_index]
        if isinstance(value, int):
            try:
                return columns[value]
            except IndexError as exc:
                raise OriginOperationError(f"Column index out of range: {value}") from exc
        if value not in columns:
            raise OriginOperationError(f"Column not found: {value}. Available columns: {columns}")
        return value

    def _resolve_y_columns(
        self,
        columns: list[str],
        x_name: str,
        y_cols: list[str | int] | None,
    ) -> list[str]:
        if y_cols is None:
            resolved = [col for col in columns if col != x_name]
        else:
            resolved = [self._resolve_column(columns, col, default_index=1) for col in y_cols]

        if not resolved:
            raise OriginOperationError("No Y columns selected.")
        return resolved

    @staticmethod
    def _object_name(obj: Any, default: str) -> str:
        if obj is None:
            return default
        for attr in ("name", "lname"):
            value = getattr(obj, attr, None)
            if callable(value):
                try:
                    return str(value())
                except Exception:
                    continue
            if value:
                return str(value)
        return default

    def _find_sheet(self, book_name: str | None = None, sheet_name: str | None = None) -> Any:
        op = self.op
        find_sheet = getattr(op, "find_sheet", None)
        if not callable(find_sheet):
            raise OriginOperationError("originpro.find_sheet is not available.")
        if book_name and sheet_name:
            ref = f"[{book_name}]{sheet_name}"
        else:
            ref = book_name or sheet_name or ""
        wks = find_sheet("w", ref)
        if wks is not None:
            return wks
        if book_name:
            wks = self._find_sheet_by_book_label(book_name, sheet_name)
            if wks is not None:
                return wks
        raise OriginOperationError(f"Worksheet not found: {ref or '<active worksheet>'}")

    def _find_sheet_from_ref(self, worksheet: str | None = None) -> Any:
        op = self.op
        find_sheet = getattr(op, "find_sheet", None)
        if not callable(find_sheet):
            raise OriginOperationError("originpro.find_sheet is not available.")
        wks = find_sheet("w", worksheet or "")
        if wks is None and worksheet:
            clean = worksheet.strip()
            if clean.startswith("[") and "]" in clean:
                book_name, sheet_name = clean[1:].split("]", 1)
                sheet_name = sheet_name.strip("! ") or None
                wks = self._find_sheet_by_book_label(book_name, sheet_name)
        if wks is None:
            raise OriginOperationError(f"Worksheet not found: {worksheet or '<active worksheet>'}")
        return wks

    def _find_sheet_by_book_label(self, book_name: str, sheet_name: str | None) -> Any | None:
        pages = getattr(self.op, "pages", None)
        if not callable(pages):
            return None
        for page in pages("w"):
            labels = {
                self._object_name(page, default=""),
                str(getattr(page, "lname", "")),
            }
            if not self._origin_name_matches(book_name, labels):
                continue
            if sheet_name:
                for sheet in page:
                    sheet_labels = {
                        self._object_name(sheet, default=""),
                        str(getattr(sheet, "lname", "")),
                    }
                    if sheet_name in sheet_labels:
                        return sheet
                return None
            return page[0]
        return None

    @staticmethod
    def _origin_name_matches(requested: str, labels: set[str]) -> bool:
        requested_lower = requested.lower()
        for label in labels:
            label_lower = label.lower()
            if not label_lower:
                continue
            if requested_lower == label_lower:
                return True
            if requested_lower.startswith(label_lower) or label_lower.startswith(requested_lower):
                return True
        return False

    def _worksheet_ref(
        self,
        wks: Any,
        columns: list[str] | None = None,
        rows: int | None = None,
    ) -> WorksheetRef:
        if columns is None:
            get_labels = getattr(wks, "get_labels", None)
            if callable(get_labels):
                labels = [label for label in get_labels("L") if label]
                columns = labels or [f"Col{i + 1}" for i in range(getattr(wks, "cols", 0))]
            else:
                columns = []
        return WorksheetRef(
            book_name=self._object_name(wks.get_book(), default=""),
            sheet_name=self._object_name(wks, default=""),
            columns=columns,
            rows=rows if rows is not None else int(getattr(wks, "rows", 0)),
        )

    def _find_object(self, name: str, object_type: str) -> Any:
        object_type = object_type.lower()
        op = self.op
        if object_type in {"graph", "g"}:
            obj = op.find_graph(name)
        elif object_type in {"workbook", "book", "w"}:
            obj = op.find_book("w", name)
        elif object_type in {"matrixbook", "matrix", "m"}:
            obj = op.find_book("m", name)
        elif object_type in {"worksheet", "sheet"}:
            obj = op.find_sheet("w", name)
        else:
            raise OriginOperationError(f"Unsupported object type: {object_type}")
        if obj is None:
            raise OriginOperationError(f"{object_type} not found: {name}")
        return obj

    @staticmethod
    def _safe_filename(name: str) -> str:
        invalid = '<>:"/\\|?*'
        cleaned = "".join("_" if ch in invalid else ch for ch in name).strip()
        return cleaned or "graph"

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
        normalized_options = adapter.normalize_options(options)
        option_text = xf_options(normalized_options)
        output_text = f' {adapter.output_option}:="{output_sheet}"' if output_sheet else ""
        command = f"{adapter.x_function} {range_expr}{output_text} {option_text};"
        return " ".join(command.split())

    @staticmethod
    def _analysis_range(
        worksheet: str | None,
        x_col: str | int | None,
        y_col: str | int | None,
    ) -> str:
        if worksheet is None and x_col is None and y_col is None:
            return ""
        if worksheet and x_col is not None and y_col is not None:
            return f"{worksheet}!({x_col},{y_col})"
        if worksheet and y_col is not None:
            return f"{worksheet}!({y_col})"
        if worksheet:
            return worksheet
        return f"({x_col},{y_col})" if x_col is not None else f"({y_col})"

    @staticmethod
    def _call_first_available(obj: Any, names: list[str]) -> Any:
        for name in names:
            func = getattr(obj, name, None)
            if callable(func):
                return func()
        raise OriginOperationError(f"None of these functions is available: {names}")
