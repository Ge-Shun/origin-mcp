from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

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

    def new_project(self, show: bool = True) -> dict[str, Any]:
        op = self.op
        if hasattr(op, "set_show"):
            op.set_show(show)
        self._call_first_available(op, ["new", "new_project"])
        return {"created": True}

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
    ) -> WorksheetRef:
        path = path.expanduser().resolve()
        self._validate_file(path)
        df = self._read_table(path, excel_sheet=excel_sheet)
        if df.empty:
            raise OriginOperationError(f"Data file contains no rows: {path}")

        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        if hasattr(wks, "from_df"):
            wks.from_df(df)
        else:
            raise OriginOperationError(
                "The worksheet object does not support from_df(); update the originpro package."
            )

        return WorksheetRef(
            book_name=self._object_name(getattr(wks, "book", None), default=book_name or ""),
            sheet_name=self._object_name(wks, default=sheet_name or ""),
            columns=[str(col) for col in df.columns],
            rows=len(df),
        )

    def plot_csv(
        self,
        path: Path,
        kind: str,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
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
        graph_name: str | None = None,
        template: str | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        show_legend: bool = True,
        export_path: Path | None = None,
    ) -> tuple[WorksheetRef, GraphRef]:
        path = path.expanduser().resolve()
        self._validate_file(path)
        df = self._read_table(path, excel_sheet=excel_sheet)
        if df.empty:
            raise OriginOperationError(f"Data file contains no rows: {path}")

        columns = [str(col) for col in df.columns]
        x_name = self._resolve_column(columns, x_col, default_index=0)
        y_names = self._resolve_y_columns(columns, x_name, y_cols)

        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.from_df(df)

        graph = self._new_graph(kind=kind, graph_name=graph_name, template=template)
        layer = graph[0] if hasattr(graph, "__getitem__") else graph

        for y_name in y_names:
            self._add_plot(layer, wks, x_name=x_name, y_name=y_name, kind=kind)

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

        worksheet = WorksheetRef(
            book_name=self._object_name(getattr(wks, "book", None), default=book_name or ""),
            sheet_name=self._object_name(wks, default=sheet_name or ""),
            columns=columns,
            rows=len(df),
        )
        return worksheet, GraphRef(graph_name=actual_graph_name, export_path=exported)

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

        graph_template = template or ("line" if kind == "line" else "scatter")
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

    def _add_plot(self, layer: Any, wks: Any, x_name: str, y_name: str, kind: str) -> None:
        add_plot = getattr(layer, "add_plot", None)
        if not callable(add_plot):
            raise OriginOperationError("Graph layer does not support add_plot().")

        plot_type = "s" if kind == "scatter" else "l"
        attempts = [
            {"coly": y_name, "colx": x_name, "type": plot_type},
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
    def _read_table(path: Path, excel_sheet: str | int | None = 0) -> pd.DataFrame:
        suffix = path.suffix.lower()
        if suffix in {".xls", ".xlsx", ".xlsm"}:
            return pd.read_excel(path, sheet_name=excel_sheet if excel_sheet is not None else 0)
        if suffix == ".tsv":
            return pd.read_csv(path, sep="\t")
        if suffix in {".txt", ".dat"}:
            return pd.read_csv(path, sep=None, engine="python")
        if suffix == ".csv":
            return pd.read_csv(path)
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
        if not path.exists():
            raise OriginOperationError(f"File does not exist: {path}")
        if not path.is_file():
            raise OriginOperationError(f"Path is not a file: {path}")

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

    @staticmethod
    def _call_first_available(obj: Any, names: list[str]) -> Any:
        for name in names:
            func = getattr(obj, name, None)
            if callable(func):
                return func()
        raise OriginOperationError(f"None of these functions is available: {names}")
