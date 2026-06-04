"""In-memory fake of the slice of ``originpro`` that ``OriginClient`` uses.

The client mixins talk to originpro through a small, stable surface:
``op.new_sheet``/``op.find_sheet``/``op.pages``/``op.lt_float`` and a worksheet
object exposing ``to_df``/``from_df``/``get_book``/``get_labels``/``cols``/
``rows``/``activate``/``lt_exec``/``add_col``. These fakes implement exactly that
surface backed by pandas DataFrames, so the pure data-shaping logic in the
worksheet, transform, and analysis mixins can be exercised without a real Origin
install.

Inject one onto a client with ``client._op = FakeOp(...)``; the lazy ``op``
property then returns it instead of importing ``originpro`` (see
``_OriginClientBase.op``).
"""

from __future__ import annotations

import base64
import re
from typing import Any

import pandas as pd

_NCOLS_RE = re.compile(r"wks\.ncols\s*=\s*(\d+)\s*;?", re.IGNORECASE)
_EXP_PATH_RE = re.compile(r'path:="([^"]*)"')
_EXP_FILENAME_RE = re.compile(r'filename:="([^"]*)"')
_EXP_TYPE_RE = re.compile(r"type:=(\w+)")
_TEMPLATE_NAME_RE = re.compile(r'template:="([^"]*)"')
_TEMPLATE_FILEPATH_RE = re.compile(r'filepath:="([^"]*)"')


class WBook:
    def __init__(self, op: FakeOp, name: str) -> None:
        self.op = op
        self.name = name
        self.lname = name
        self.sheets: list[FakeWorksheet] = []

    def __iter__(self) -> Any:
        return iter(self.sheets)

    def __getitem__(self, index: int) -> FakeWorksheet:
        return self.sheets[index]


class FakeWorksheet:
    def __init__(self, book: WBook, name: str, df: pd.DataFrame | None = None) -> None:
        self.book = book
        self.name = name
        self.lname = name
        self._df = (df if df is not None else pd.DataFrame()).reset_index(drop=True)
        self.scripts: list[str] = []
        self.activated = 0
        self.label_calls: list[tuple[list[str], str, int]] = []
        self.designation_calls: list[tuple[str, int, int, bool]] = []

    # -- Properties originpro exposes -------------------------------------
    @property
    def cols(self) -> int:
        return int(self._df.shape[1])

    @property
    def rows(self) -> int:
        return int(self._df.shape[0])

    # -- DataFrame round trip ---------------------------------------------
    def to_df(self, **_: Any) -> pd.DataFrame:
        return self._df.copy()

    def from_df(self, df: pd.DataFrame, c1: int | str = 0) -> None:
        if str(c1) in ("0", ""):
            self._df = df.reset_index(drop=True).copy()
            return
        # Non-zero start column: keep the leading columns, append the new frame.
        offset = int(c1)
        kept = self._df.iloc[:, :offset]
        appended = df.reset_index(drop=True).copy()
        self._df = pd.concat([kept.reset_index(drop=True), appended], axis=1)

    # -- Metadata ----------------------------------------------------------
    def get_book(self) -> WBook:
        return self.book

    # -- Range expressions (used by analysis commands) --------------------
    def to_xy_range(self, x: Any, y: Any, _extra: str = "") -> str:
        return f"[{self.book.name}]{self.name}!({x},{y})"

    def to_col_range(self, y: Any) -> str:
        return f"[{self.book.name}]{self.name}!({y})"

    def lt_range(self, _flag: bool = False) -> str:
        return f"[{self.book.name}]{self.name}!"

    def get_labels(self, kind: str = "L") -> list[str]:
        if kind == "L":
            return [str(col) for col in self._df.columns]
        return []

    def add_col(self, name: str | None = None) -> None:
        column = name or f"Col{self.cols + 1}"
        self._df[column] = pd.NA

    def set_labels(self, labels: list[str], label_type: str = "L", offset: int = 0) -> None:
        self.label_calls.append((list(labels), label_type, offset))

    def cols_axis(self, spec: str, c1: int = 0, c2: int = -1, repeat: bool = True) -> None:
        self.designation_calls.append((spec, c1, c2, repeat))

    # -- LabTalk execution -------------------------------------------------
    def activate(self) -> None:
        self.activated += 1

    def lt_exec(self, script: str) -> int:
        self.scripts.append(script)
        match = _NCOLS_RE.fullmatch(script.strip())
        if match:
            self._df = self._df.iloc[:, : int(match.group(1))]
        return 0


# A minimal valid 1x1 PNG, used by GPage.save_fig so export/inspect paths that
# read the written file (dimensions, sha256, quality) operate on a real image.
_ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class GAxis:
    """A graph layer axis (``layer.axis("x")``)."""

    def __init__(self, title: str = "") -> None:
        self.title = title
        self.scale: Any = 1
        self.limits: Any = None


class GPlot:
    """A single data plot inside a layer."""

    def __init__(self, index: int) -> None:
        self.name = f"Plot{index + 1}"
        self.commands: list[str] = []
        self.props: dict[str, Any] = {}

    def set_cmd(self, command: str) -> None:
        self.commands.append(command)

    def set_int(self, name: str, value: int) -> None:
        self.props[name] = value

    def set_float(self, name: str, value: float) -> None:
        self.props[name] = value


class GLayer:
    """A graph layer (``graph[i]``)."""

    def __init__(self, index: int) -> None:
        self.name = f"Layer{index + 1}"
        self.lname = self.name
        self._axes = {"x": GAxis("X"), "y": GAxis("Y"), "z": GAxis("Z")}
        self.plots: list[GPlot] = []
        self.labels: dict[str, Any] = {}
        self.rescaled = 0
        self.grouped = False

    def axis(self, name: str) -> GAxis | None:
        return self._axes.get(name.lower())

    def add_plot(self, _wks: Any, *args: Any, **kwargs: Any) -> GPlot:
        plot = GPlot(len(self.plots))
        self.plots.append(plot)
        return plot

    def plot_list(self) -> list[GPlot]:
        return list(self.plots)

    def rescale(self) -> None:
        self.rescaled += 1

    def group(self, *_: Any) -> None:
        self.grouped = True

    def label(self, name: str) -> Any:
        return self.labels.get(name)


class GPage:
    """A graph page (``op.new_graph`` / ``op.find_graph`` result)."""

    def __init__(self, name: str, lname: str | None = None, layers: int = 1) -> None:
        self.name = name
        self.lname = lname or name
        self.layers = [GLayer(i) for i in range(layers)]
        self.activated = 0
        self.destroyed = False

    def __len__(self) -> int:
        return len(self.layers)

    def __getitem__(self, index: int) -> GLayer:
        return self.layers[index]

    def activate(self) -> None:
        self.activated += 1

    def destroy(self) -> None:
        self.destroyed = True

    def is_open(self) -> bool:
        return True

    def save_fig(
        self,
        path: str,
        type: str = "png",  # noqa: A002 - matches originpro signature
        replace: bool = True,
        width: int = 0,
    ) -> None:
        from pathlib import Path

        Path(path).write_bytes(_ONE_BY_ONE_PNG)


class FakeLinearFit:
    """Stand-in for ``originpro.LinearFit``.

    Not attached to ``FakeOp`` by default (so ``linear_fit_api`` stays absent in
    capability probes); a test opts in with ``op.LinearFit = FakeLinearFit``.
    """

    def __init__(self) -> None:
        self.data: tuple[Any, ...] | None = None
        self.fixed_intercept: Any = None
        self.fixed_slope: Any = None

    def set_data(self, wks: Any, x: Any, y: Any, err: str = "") -> None:
        self.data = (wks, x, y, err)

    def fix_intercept(self, value: Any) -> None:
        self.fixed_intercept = value

    def fix_slope(self, value: Any) -> None:
        self.fixed_slope = value

    def result(self) -> dict[str, Any]:
        return {"slope": 2.0, "intercept": 1.0, "r": 0.99, "adj_rsquare": 0.98}

    def report(self, band: int = 0) -> tuple[str, str]:
        return ("FitReport", "FitCurves")


class FakeOp:
    """Fake ``originpro`` module exposing only what OriginClient calls."""

    def __init__(self) -> None:
        self.books: list[WBook] = []
        self.graphs: list[GPage] = []
        self._counter = 0
        self._graph_counter = 0
        self.lt_values: dict[str, Any] = {}
        # Records of lifecycle / LabTalk calls so tests can assert on side effects.
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.lt_exec_result: Any = True
        self.show: bool | None = None
        self.save_raises = False

    # -- Test helpers ------------------------------------------------------
    def add_book(
        self,
        name: str,
        df: pd.DataFrame | None = None,
        sheet: str = "Sheet1",
    ) -> FakeWorksheet:
        book = WBook(self, name)
        wks = FakeWorksheet(book, sheet, df)
        book.sheets.append(wks)
        self.books.append(book)
        return wks

    def add_graph(self, name: str, lname: str | None = None, layers: int = 1) -> GPage:
        page = GPage(name, lname=lname, layers=layers)
        self.graphs.append(page)
        return page

    # -- originpro surface -------------------------------------------------
    def new_sheet(self, _type: str = "w", book_name: str = "") -> FakeWorksheet:
        self._counter += 1
        name = book_name or f"Book{self._counter}"
        return self.add_book(name)

    def find_sheet(self, _type: str = "w", ref: str = "") -> FakeWorksheet | None:
        ref = (ref or "").strip()
        if ref == "":
            return self.books[-1].sheets[0] if self.books else None
        if ref.startswith("[") and "]" in ref:
            book_name, rest = ref[1:].split("]", 1)
            sheet_name = rest.split("!", 1)[0].strip() or None
            return self._lookup(book_name, sheet_name)
        found = self._lookup(ref, None)
        if found is not None:
            return found
        for book in self.books:
            for sheet in book.sheets:
                if ref in (sheet.name, sheet.lname):
                    return sheet
        return None

    def pages(self, _type: str = "") -> list[Any]:
        if _type == "w":
            return list(self.books)
        if _type == "g":
            return list(self.graphs)
        return [*self.books, *self.graphs]

    def new_graph(self, template: str = "", lname: str | None = None) -> GPage:
        self._graph_counter += 1
        name = f"Graph{self._graph_counter}"
        return self.add_graph(name, lname=lname)

    def find_graph(self, name: str = "") -> GPage | None:
        name = (name or "").strip()
        if name == "":
            return self.graphs[-1] if self.graphs else None
        for graph in self.graphs:
            if name in (graph.name, graph.lname):
                return graph
        return None

    def graph_list(self, _type: str = "p", _active_first: bool = True) -> list[GPage]:
        return list(self.graphs)

    def lt_float(self, expression: str) -> Any:
        return self.lt_values.get(expression)

    # -- Lifecycle / LabTalk surface (opt-in per test) --------------------
    def set_show(self, show: bool) -> None:
        self.show = show
        self.calls.append(("set_show", (show,)))

    def lt_exec(self, script: str) -> Any:
        self.calls.append(("lt_exec", (script,)))
        if "expGraph" in script:
            self._emulate_export(script)
        if "template_saveas" in script:
            self._emulate_template_saveas(script)
        return self.lt_exec_result

    @staticmethod
    def _emulate_template_saveas(script: str) -> None:
        """Emulate LabTalk ``template_saveas`` writing ``<filepath>/<template>.otpu``."""

        from pathlib import Path

        name = _TEMPLATE_NAME_RE.search(script)
        folder = _TEMPLATE_FILEPATH_RE.search(script)
        if not name or not folder:
            return
        target = Path(folder.group(1)) / f"{name.group(1)}.otpu"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fake-origin-template", encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _emulate_export(script: str) -> None:
        """Emulate LabTalk ``expGraph`` writing an image file to disk."""

        from pathlib import Path

        path_match = _EXP_PATH_RE.search(script)
        name_match = _EXP_FILENAME_RE.search(script)
        if not path_match or not name_match:
            return
        type_match = _EXP_TYPE_RE.search(script)
        suffix = (type_match.group(1) if type_match else "png").lstrip(".")
        target = Path(path_match.group(1)) / f"{name_match.group(1)}.{suffix}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_ONE_BY_ONE_PNG)
        except OSError:
            pass

    def new(self) -> None:
        self.calls.append(("new", ()))

    def save(self, path: str) -> None:
        self.calls.append(("save", (path,)))
        if self.save_raises:
            raise RuntimeError("originpro.save failed")

    def open(self, path: str, readonly: bool = False, asksave: bool = False) -> bool:
        self.calls.append(("open", (path, readonly, asksave)))
        return True

    def exit(self) -> None:
        self.calls.append(("exit", ()))

    def detach(self) -> None:
        self.calls.append(("detach", ()))

    def _lookup(self, book_name: str, sheet_name: str | None) -> FakeWorksheet | None:
        for book in self.books:
            if book_name not in (book.name, book.lname):
                continue
            if sheet_name:
                for sheet in book.sheets:
                    if sheet_name in (sheet.name, sheet.lname):
                        return sheet
                return None
            return book.sheets[0] if book.sheets else None
        return None
