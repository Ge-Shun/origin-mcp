from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from ..analysis_outputs import (
    analysis_output_rows,
    analysis_row_metrics,
    analysis_row_parameter,
    is_analysis_number,
    serialize_analysis_value,
    structure_analysis_output,
    structure_fit_result,
)
from ..errors import OriginDependencyError, OriginOperationError
from ..file_io import check_path_allowed, read_table, safe_filename, validate_file
from ..runtime import python_runtime_profile
from ..text_format import normalize_label_text, origin_rich_text

TABLE_PLOTXYZ_IDS = {103, 183, 184, 185, 240, 242, 243, 245}
TABLE_WORKSHEET_PLOT_IDS = {183, 184}
MATRIX_PLOTM_IDS = {101, 103, 105, 220, 226, 242}
ANALYSIS_XY_OUTPUTS = {"polynomial_fit", "smooth"}


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
    template: str | None = None
    style_mode: str = "origin_default"
    requested_graph_name: str | None = None
    display_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = {
            "graph_name": self.graph_name,
            "export_path": self.export_path,
            "template": self.template,
            "style_mode": self.style_mode,
        }
        if self.requested_graph_name is not None:
            data["requested_graph_name"] = self.requested_graph_name
        if self.display_name is not None:
            data["display_name"] = self.display_name
        return data



class _OriginClientBase:
    """Shared state and helpers for OriginClient mixins."""

    def __init__(self) -> None:
        self._op: Any | None = None
        self._capabilities: dict[str, Any] | None = None
        self._graph_annotations: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self._graph_aliases: dict[str, str] = {}

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

    @staticmethod
    def _normalize_style_mode(style_mode: str | None) -> str:
        value = (style_mode or "origin_default").strip().lower()
        aliases = {
            "default": "origin_default",
            "origin": "origin_default",
            "origin_default": "origin_default",
            "template": "origin_default",
            "theme": "origin_default",
            "none": "origin_default",
            "publication": "publication",
            "nature": "nature",
            "nature_style": "nature",
            "nature-style": "nature",
        }
        try:
            return aliases[value]
        except KeyError as exc:
            supported = ", ".join(sorted(aliases))
            raise OriginOperationError(
                f"Unsupported style_mode: {style_mode!r}. Supported: {supported}."
            ) from exc

    # Backwards-compatible shims for analysis output helpers extracted to
    # ``analysis_outputs``. Tests still call ``client._structure_fit_result``
    # directly, and the static delegates make it cheap to keep the old API.
    _structure_fit_result = staticmethod(structure_fit_result)

    _structure_analysis_output = staticmethod(structure_analysis_output)

    _analysis_output_rows = staticmethod(analysis_output_rows)

    _analysis_row_metrics = staticmethod(analysis_row_metrics)

    _analysis_row_parameter = staticmethod(analysis_row_parameter)

    _is_analysis_number = staticmethod(is_analysis_number)

    _serialize_analysis_value = staticmethod(serialize_analysis_value)

    @staticmethod
    def _escape_labtalk(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    _read_table = staticmethod(read_table)

    @staticmethod
    def _labtalk_text(text: str) -> str:
        return normalize_label_text(text)

    @staticmethod
    def _label_text(text: str) -> str:
        return origin_rich_text(text)

    def _safe_eval(self, expression: str) -> Any:
        op = self.op
        func = getattr(op, "lt_float", None)
        if not callable(func):
            return None
        try:
            return func(expression)
        except Exception:
            return None

    def _try_set_show(self, show: bool) -> dict[str, Any]:
        op = self.op
        set_show = getattr(op, "set_show", None)
        if not callable(set_show):
            return {"show_set": False, "show_warning": "originpro.set_show is unavailable."}
        try:
            set_show(show)
        except (RuntimeError, SystemError) as exc:
            return {
                "show_set": False,
                "show_warning": self._automation_failure_message("set Origin visibility", exc),
            }
        return {"show_set": True}

    @staticmethod
    def _automation_failure_message(operation: str, exc: BaseException) -> str:
        runtime = python_runtime_profile()
        return (
            f"Origin automation failed while trying to {operation}: {exc}. "
            f"Python {runtime.version} is running at {runtime.executable}. "
            f"Runtime tier: {runtime.origin_ext_tier}; recommended backend: "
            f"{runtime.recommended_backend}. {runtime.note} Make sure no other process is "
            "holding the Origin automation session."
        )

    _validate_file = staticmethod(validate_file)

    _check_path_allowed = staticmethod(check_path_allowed)

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
    def _object_long_name(obj: Any, default: str | None = None) -> str | None:
        if obj is None:
            return default
        value = getattr(obj, "lname", None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        return str(value) if value else default

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

    _safe_filename = staticmethod(safe_filename)

    @staticmethod
    def _call_first_available(
        obj: Any,
        names: list[str],
        operation: str | None = None,
    ) -> Any:
        for name in names:
            func = getattr(obj, name, None)
            if callable(func):
                try:
                    return func()
                except (RuntimeError, SystemError) as exc:
                    if operation:
                        raise OriginOperationError(
                            _OriginClientBase._automation_failure_message(operation, exc)
                        ) from exc
                    raise
        raise OriginOperationError(f"None of these functions is available: {names}")

