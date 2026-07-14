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
import copy
import re
from typing import Any

import numpy as np
import pandas as pd

_NCOLS_RE = re.compile(r"wks\.ncols\s*=\s*(\d+)\s*;?", re.IGNORECASE)
_EXP_PATH_RE = re.compile(r'path:="([^"]*)"')
_EXP_FILENAME_RE = re.compile(r'filename:="([^"]*)"')
_EXP_TYPE_RE = re.compile(r"type:=(\w+)")
_TEMPLATE_NAME_RE = re.compile(r'template:="([^"]*)"')
_TEMPLATE_FILEPATH_RE = re.compile(r'filepath:="([^"]*)"')
_DC_STRING_RE = re.compile(r'wks\.dc\.(sel|script|optn)\$="([^"]*)"', re.IGNORECASE)
_DC_INT_RE = re.compile(r"wks\.dc\.(flags|auto)\s*=\s*(-?\d+)", re.IGNORECASE)
_DC_NEW_SHEET_RE = re.compile(r'wbook\.dc\.newsheet\("([^"]*)"\s*,\s*1\s*\)', re.IGNORECASE)
_DC_REMOVE_RE = re.compile(r"wbook\.dc\.remove\((\d+)\)", re.IGNORECASE)
_SAVE_ANALYSIS_TEMPLATE_RE = re.compile(r'save\s+-ik\s+"([^"]+)"', re.IGNORECASE)
_TREE_COMMAND_RE = re.compile(r"\b(getresults|op_change)\b.*?\btr:=(\w+)", re.IGNORECASE)


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

    def activate(self) -> None:
        if self.sheets:
            self.op.active_sheet = self.sheets[0]


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
        self.from_df_calls = 0
        self.to_df_calls = 0
        self.dc: dict[str, Any] | None = None

    # -- Properties originpro exposes -------------------------------------
    @property
    def cols(self) -> int:
        return int(self._df.shape[1])

    @property
    def rows(self) -> int:
        return int(self._df.shape[0])

    # -- DataFrame round trip ---------------------------------------------
    def to_df(self, **_: Any) -> pd.DataFrame:
        self.to_df_calls += 1
        return self._df.copy()

    def from_df(self, df: pd.DataFrame, c1: int | str = 0) -> None:
        self.from_df_calls += 1
        if str(c1) in ("0", ""):
            self._df = df.reset_index(drop=True).copy()
            return
        # Non-zero start column: keep the leading columns, append the new frame.
        offset = int(c1)
        kept = self._df.iloc[:, :offset]
        appended = df.reset_index(drop=True).copy()
        self._df = pd.concat([kept.reset_index(drop=True), appended], axis=1)

    def to_list2(self, r1: int = 0, r2: int = -1, c1: int = 0, c2: int = -1) -> list[list[Any]]:
        r2 = self.rows - 1 if r2 < 0 else r2
        c2 = self.cols - 1 if c2 < 0 else c2
        return [self._df.iloc[r1 : r2 + 1, col].tolist() for col in range(c1, c2 + 1)]

    def from_list2(self, data: list[list[Any]], row: int = 0, col: int | str = 0) -> None:
        start = int(col) if not isinstance(col, str) else list(self._df.columns).index(col)
        for col_offset, values in enumerate(data):
            for row_offset, value in enumerate(values):
                self._df.iat[row + row_offset, start + col_offset] = value

    def cell(self, row: int, col: int) -> Any:
        return self._df.iat[row, col]

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

    # -- Data Connector ---------------------------------------------------
    def from_file(
        self,
        path: str,
        keep_dc: bool = True,
        dctype: str = "",
        sel: str = "",
        sparks: bool = False,
    ) -> None:
        self.dc = {
            "source": path,
            "keep_dc": keep_dc,
            "dctype": dctype,
            "sel": sel,
            "script": "",
            "optn": "",
            "flags": 0,
            "auto": 0,
            "imports": 1,
            "sparks": sparks,
        }

    def has_DC(self) -> bool:
        return self.dc is not None

    def remove_DC(self) -> None:
        self.dc = None

    def get_str(self, prop: str) -> str:
        if self.dc is None:
            raise RuntimeError("no connector")
        return str(self.dc[prop.split(".", 1)[-1].lower()])

    def get_int(self, prop: str) -> int:
        if self.dc is None:
            raise RuntimeError("no connector")
        return int(self.dc[prop.split(".", 1)[-1].lower()])

    # -- LabTalk execution -------------------------------------------------
    def activate(self) -> None:
        self.activated += 1
        self.book.op.active_sheet = self

    def lt_exec(self, script: str) -> int:
        self.scripts.append(script)
        match = _NCOLS_RE.fullmatch(script.strip())
        if match:
            self._df = self._df.iloc[:, : int(match.group(1))]
        if self.dc is not None:
            for name, value in _DC_STRING_RE.findall(script):
                self.dc[name.lower()] = value
            for name, value in _DC_INT_RE.findall(script):
                self.dc[name.lower()] = int(value)
        new_sheet = _DC_NEW_SHEET_RE.search(script)
        if new_sheet and self.dc is not None:
            FakeConnector(self, "", True).new_sheet(new_sheet.group(1))
        remove = _DC_REMOVE_RE.search(script)
        if remove:
            mode = int(remove.group(1))
            if mode == 0:
                for sheet in self.book.sheets:
                    sheet.dc = None
            elif mode == 1:
                self.dc = None
        return 0


class FakeMatrixSheet:
    def __init__(self, book: WBook, name: str = "MSheet1") -> None:
        self.book = book
        self.name = name
        self.lname = name
        self._data = np.zeros((1, 1, 1), dtype=float)
        self.xymap = (0.0, 1.0, 0.0, 1.0)
        self.labels: list[str] = ["1"]
        self.scripts: list[str] = []
        self.image_view = False
        self.thumbnails = False
        self.slider = False

    @property
    def shape(self) -> tuple[int, int]:
        return int(self._data.shape[1]), int(self._data.shape[2])

    @property
    def depth(self) -> int:
        return int(self._data.shape[0])

    def get_book(self) -> WBook:
        return self.book

    def from_np(self, arr: Any, dstack: bool = False, mv: Any = None) -> None:
        data = np.asarray(arr).copy()
        if data.ndim == 2:
            data = data[np.newaxis, :, :]
        elif dstack:
            data = np.moveaxis(data, -1, 0)
        self._data = data
        self.labels = [str(index + 1) for index in range(self.depth)]

    def from_np2d(self, arr: Any, index: int = 0) -> None:
        self._data[index] = np.asarray(arr)

    def to_np2d(self, index: int = 0, order: str = "C") -> Any:
        return np.array(self._data[index], order=order, copy=True)

    def to_np3d(self, dstack: bool = False, order: str = "C") -> Any:
        data = np.array(self._data, order=order, copy=True)
        return np.moveaxis(data, 0, -1) if dstack else data

    def from_img(self, image: FakeImage) -> None:
        data = np.asarray(image.to_np())
        if data.ndim == 2:
            self.from_np(data)
        elif data.ndim == 3 and data.shape[-1] in {3, 4}:
            self.from_np(np.moveaxis(data, -1, 0))
        else:
            self.from_np(data)

    def get_labels(self, type_: str = "L") -> list[str]:
        return list(self.labels) if type_ == "L" else []

    def set_labels(self, labels: list[str], type_: str = "L", offset: int = 0) -> None:
        if type_ != "L":
            return
        while len(self.labels) < offset:
            self.labels.append("")
        for index, label in enumerate(labels, start=offset):
            if index < len(self.labels):
                self.labels[index] = label
            else:
                self.labels.append(label)

    def show_image(self, show: bool = True) -> None:
        self.image_view = show

    def show_thumbnails(self, show: bool = True) -> None:
        self.thumbnails = show

    def show_slider(self, show: bool = True) -> None:
        self.slider = show

    def lt_range(self, _flag: bool = False) -> str:
        return f"[{self.book.name}]{self.name}"

    def activate(self) -> None:
        self.book.op.active_matrix = self

    def lt_exec(self, script: str) -> int:
        self.scripts.append(script)
        clean = script.strip().lower()
        if clean.startswith("matrix -t"):
            self._data = np.transpose(self._data, (0, 2, 1))
        elif clean.startswith("matrix -c r"):
            self._data = np.rot90(self._data, axes=(1, 2))
        elif clean.startswith("matrix -c h"):
            self._data = np.flip(self._data, axis=2)
        elif clean.startswith("matrix -c v"):
            self._data = np.flip(self._data, axis=1)
        return 0


class FakeImage:
    def __init__(self, op: FakeOp, name: str) -> None:
        self.op = op
        self.name = name
        self.lname = name
        self._data = np.zeros((1, 1), dtype=np.uint8)
        self._channels = 1
        self._multiframe = False
        self._channel_type = -1

    def setup(self, channels: int, multiframe: bool, channelType: int = -1) -> bool:
        self._channels = channels
        self._multiframe = multiframe
        self._channel_type = channelType
        return True

    def from_file(self, fname: str) -> bool:
        self._data = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
        self._channels = 3
        return True

    def from_np(self, arr: Any, dstack: bool = False) -> None:
        data = np.asarray(arr).copy()
        if dstack and self._multiframe and data.ndim >= 3:
            data = np.moveaxis(data, -1, 0)
        self._data = data

    def from_np2d(self, arr: Any, frame: int) -> bool:
        self._data[frame] = np.asarray(arr)
        return True

    def to_np(self) -> Any:
        return self._data.copy()

    def to_np2d(self, frame: int) -> Any:
        return self._data[frame].copy()

    @property
    def size(self) -> tuple[int, int]:
        if self._multiframe and self._data.ndim >= 3:
            height, width = self._data.shape[-2:]
        else:
            height, width = self._data.shape[:2]
        return int(width), int(height)

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def frames(self) -> int:
        return int(self._data.shape[0]) if self._multiframe else 1

    @property
    def type(self) -> int:
        return 2 if self._multiframe else 1

    def rgb2gray(self) -> None:
        if self._data.ndim == 3 and self._data.shape[-1] in {3, 4}:
            self._data = self._data[..., :3].mean(axis=-1)
            self._channels = 1

    def split(self) -> None:
        if self._data.ndim == 3 and self._data.shape[-1] in {3, 4}:
            self._data = np.moveaxis(self._data, -1, 0)
            self._channels = 1
            self._multiframe = True

    def merge(self) -> None:
        if self._multiframe and self._data.ndim == 3 and self._data.shape[0] in {3, 4}:
            self._channels = int(self._data.shape[0])
            self._data = np.moveaxis(self._data, 0, -1)
            self._multiframe = False


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
        self.fill_area_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def set_cmd(self, command: str) -> None:
        self.commands.append(command)

    def set_int(self, name: str, value: int) -> None:
        self.props[name] = value

    def set_float(self, name: str, value: float) -> None:
        self.props[name] = value

    def set_fill_area(self, *args: Any, **kwargs: Any) -> None:
        self.fill_area_calls.append((args, kwargs))


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


class FakeConnector:
    """Small in-memory stand-in for ``originpro.Connector``."""

    def __init__(self, wks: FakeWorksheet, dctype: str = "", keep_dc: bool = True) -> None:
        self.wks = wks
        if wks.dc is None:
            wks.dc = {
                "source": "",
                "keep_dc": keep_dc,
                "dctype": dctype,
                "sel": "",
                "script": "",
                "optn": "",
                "flags": 0,
                "auto": 0,
                "imports": 0,
                "sparks": False,
            }

    @property
    def source(self) -> str:
        assert self.wks.dc is not None
        return str(self.wks.dc["source"])

    @source.setter
    def source(self, value: str) -> None:
        assert self.wks.dc is not None
        self.wks.dc["source"] = value

    def settings(self) -> dict[str, Any]:
        assert self.wks.dc is not None
        return {
            "dctype": self.wks.dc["dctype"],
            "keep_dc": self.wks.dc["keep_dc"],
        }

    def imp(self, fname: str = "", sel: str = "", sparks: bool = False) -> None:
        assert self.wks.dc is not None
        if fname:
            self.wks.dc["source"] = fname
        if sel:
            self.wks.dc["sel"] = sel
        self.wks.dc["sparks"] = sparks
        self.wks.dc["imports"] = int(self.wks.dc["imports"]) + 1

    def new_sheet(self, name: str) -> FakeWorksheet:
        assert self.wks.dc is not None
        sheet = FakeWorksheet(self.wks.book, name)
        sheet.dc = dict(self.wks.dc)
        sheet.dc["sel"] = name
        sheet.dc["imports"] = 1
        self.wks.book.sheets.append(sheet)
        self.wks.book.op.active_sheet = sheet
        return sheet


class FakeOp:
    """Fake ``originpro`` module exposing only what OriginClient calls."""

    def __init__(self) -> None:
        self.books: list[WBook] = []
        self.matrix_books: list[WBook] = []
        self.graphs: list[GPage] = []
        self.images: list[FakeImage] = []
        self._counter = 0
        self._graph_counter = 0
        self.active_sheet: FakeWorksheet | None = None
        self.active_matrix: FakeMatrixSheet | None = None
        self.active_image: FakeImage | None = None
        self.lt_values: dict[str, Any] = {}
        self.lt_trees: dict[str, dict[str, Any]] = {}
        self.default_result_tree: dict[str, Any] = {}
        self.default_operation_tree: dict[str, Any] = {}
        self.last_operation_tree: dict[str, Any] | None = None
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
        self.active_sheet = wks
        return wks

    def add_graph(self, name: str, lname: str | None = None, layers: int = 1) -> GPage:
        page = GPage(name, lname=lname, layers=layers)
        self.graphs.append(page)
        return page

    def add_matrix(self, name: str, sheet: str = "MSheet1") -> FakeMatrixSheet:
        book = WBook(self, name)
        msheet = FakeMatrixSheet(book, sheet)
        book.sheets.append(msheet)  # type: ignore[arg-type]
        self.matrix_books.append(book)
        self.active_matrix = msheet
        return msheet

    # -- originpro surface -------------------------------------------------
    def new_sheet(self, _type: str = "w", book_name: str = "") -> Any:
        self._counter += 1
        if _type == "m":
            return self.add_matrix(book_name or f"MBook{self._counter}")
        name = book_name or f"Book{self._counter}"
        return self.add_book(name)

    def find_sheet(self, _type: str = "w", ref: str = "") -> Any:
        ref = (ref or "").strip()
        if _type == "m":
            return self._find_data_sheet(self.matrix_books, self.active_matrix, ref)
        if ref == "":
            return self.active_sheet
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
        if _type == "m":
            return list(self.matrix_books)
        if _type == "g":
            return list(self.graphs)
        return [*self.books, *self.matrix_books, *self.graphs, *self.images]

    def new_image(self, name: str = "") -> FakeImage:
        image = FakeImage(self, name or f"Image{len(self.images) + 1}")
        self.images.append(image)
        self.active_image = image
        return image

    def find_image(self, name: str = "") -> FakeImage | None:
        clean = name.strip()
        if not clean:
            return self.active_image
        for image in self.images:
            if clean in (image.name, image.lname):
                return image
        return None

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

    def Connector(
        self,
        wks: FakeWorksheet,
        dctype: str = "",
        keep_DC: bool = True,
    ) -> FakeConnector:
        return FakeConnector(wks, dctype=dctype, keep_dc=keep_DC)

    def set_lt_str(self, name: str, value: str) -> bool:
        self.lt_values[name.rstrip("$")] = value
        self.calls.append(("set_lt_str", (name, value)))
        return True

    def get_lt_str(self, name: str) -> str:
        return str(self.lt_values.get(name.rstrip("$"), ""))

    def lt_float(self, expression: str) -> Any:
        return self.lt_values.get(expression)

    def lt_tree_to_dict(self, name: str, add_attributes: bool = False) -> dict[str, Any]:
        del add_attributes
        return copy.deepcopy(self.lt_trees.get(name, {}))

    def lt_dict_to_tree(
        self,
        value: dict[str, Any],
        name: str,
        add_tree: bool = False,
        check_attributes: bool = False,
    ) -> None:
        del add_tree, check_attributes
        self.lt_trees[name] = copy.deepcopy(value)

    def lt_delete_tree(self, name: str) -> None:
        self.lt_trees.pop(name, None)

    # -- Lifecycle / LabTalk surface (opt-in per test) --------------------
    def set_show(self, show: bool) -> None:
        self.show = show
        self.calls.append(("set_show", (show,)))

    def lt_exec(self, script: str) -> Any:
        self.calls.append(("lt_exec", (script,)))
        tree_command = _TREE_COMMAND_RE.search(script)
        if tree_command:
            command, tree_name = tree_command.groups()
            if command.lower() == "getresults":
                self.lt_trees[tree_name] = copy.deepcopy(self.default_result_tree)
            elif "op:=get" in script.lower():
                self.lt_trees[tree_name] = copy.deepcopy(self.default_operation_tree)
            elif "op:=run" in script.lower():
                self.last_operation_tree = copy.deepcopy(self.lt_trees.get(tree_name, {}))
        if "expGraph" in script:
            self._emulate_export(script)
        if "template_saveas" in script:
            self._emulate_template_saveas(script)
        analysis_template = _SAVE_ANALYSIS_TEMPLATE_RE.search(script)
        if analysis_template:
            from pathlib import Path

            target = Path(analysis_template.group(1).replace("\\\\", "\\"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fake-analysis-template", encoding="utf-8")
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

    @staticmethod
    def _find_data_sheet(books: list[WBook], active: Any, ref: str) -> Any:
        if not ref:
            return active
        if ref.startswith("[") and "]" in ref:
            book_name, rest = ref[1:].split("]", 1)
            sheet_name = rest.split("!", 1)[0].strip() or None
        else:
            book_name, sheet_name = ref, None
        for book in books:
            if book_name in (book.name, book.lname):
                if sheet_name:
                    return next(
                        (sheet for sheet in book.sheets if sheet_name in (sheet.name, sheet.lname)),
                        None,
                    )
                return book.sheets[0] if book.sheets else None
        for book in books:
            for sheet in book.sheets:
                if ref in (sheet.name, sheet.lname):
                    return sheet
        return None
