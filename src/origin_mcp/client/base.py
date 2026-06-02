from __future__ import annotations

import importlib
import threading
from pathlib import Path
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
from ..chart_palette import (
    auto_palette_notice,
    chart_atlas_routes,
    named_acceptable_palette,
    named_palette,
    named_semantic_palette,
    nature_acceptable_palette,
    nature_chart_style,
    nature_chart_type_for_plot_id,
    nature_palette,
    nature_semantic_palette,
    normalize_chart_intent,
    normalize_chart_type,
    normalize_palette_name,
    palette_roles,
    select_palette_for_count,
)
from ..errors import OriginDependencyError, OriginOperationError
from ..file_io import check_path_allowed, read_table, safe_filename, validate_file
from ..refs import GraphRef as GraphRef
from ..refs import WorksheetRef as WorksheetRef
from ..runtime import python_runtime_profile
from ..text_format import normalize_label_text, origin_rich_text

TABLE_PLOTXYZ_IDS = {103, 185, 240, 242, 243, 245}
TABLE_WORKSHEET_PLOT_IDS = {
    183,
    184,
    206,
    210,
    211,
    212,
    214,
    215,
    216,
    225,
    249,
}
MATRIX_PLOTM_IDS = {101, 103, 105, 220, 226, 242}
ANALYSIS_XY_OUTPUTS = {"polynomial_fit", "smooth", "interpolate", "normalize"}
# Minimum prefix length for treating a stored short name as an Origin-truncated
# form of a longer requested name. Origin only truncates names that exceed its
# short-name cap (well above this), so genuine truncations are long; requiring a
# substantial prefix stops unrelated short names (e.g. "T") from matching longer
# requests (e.g. "Trans").
_MIN_TRUNCATION_PREFIX_LEN = 12


class _OriginClientBase:
    """Shared state and helpers for OriginClient mixins."""

    def __init__(self) -> None:
        self._op: Any | None = None
        self._capabilities: dict[str, Any] | None = None
        self._graph_annotations: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self._graph_aliases: dict[str, str] = {}
        # originpro drives Origin's single UI thread and is not thread-safe.
        # The bridge serves synchronous requests and async tasks on different
        # threads, so the bridge dispatch layer serializes every Origin call
        # through this reentrant lock (reentrant because high-level methods such
        # as plot_table fan out into further client calls under the same lock).
        self._origin_call_lock = threading.RLock()

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

    # Backwards-compatible shims for palette / chart-atlas helpers extracted
    # to ``chart_palette``. Both _PlotMixin and _GraphStyleMixin reach them
    # via ``self._nature_palette()`` etc., so the shims preserve that API.
    _nature_palette = staticmethod(nature_palette)
    _nature_semantic_palette = staticmethod(nature_semantic_palette)
    _nature_acceptable_palette = staticmethod(nature_acceptable_palette)
    _normalize_palette_name = staticmethod(normalize_palette_name)
    _named_palette = staticmethod(named_palette)
    _named_semantic_palette = staticmethod(named_semantic_palette)
    _named_acceptable_palette = staticmethod(named_acceptable_palette)
    _palette_roles = staticmethod(palette_roles)
    _select_palette_for_count = staticmethod(select_palette_for_count)
    _auto_palette_notice = staticmethod(auto_palette_notice)
    _normalize_chart_type = staticmethod(normalize_chart_type)
    _nature_chart_style = staticmethod(nature_chart_style)
    _nature_chart_type_for_plot_id = staticmethod(nature_chart_type_for_plot_id)
    _chart_atlas_routes = staticmethod(chart_atlas_routes)
    _normalize_chart_intent = staticmethod(normalize_chart_intent)

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
    def _normalize_user_path(path: Path | str) -> Path:
        """Resolve a user-supplied path and enforce ORIGIN_MCP_ALLOWED_ROOTS.

        Every public method that accepts a filesystem path (data files,
        export targets, project files, template directories) must route the
        argument through this helper before using it. The check is a no-op
        when ORIGIN_MCP_ALLOWED_ROOTS is unset.
        """

        resolved = Path(path).expanduser().resolve()
        check_path_allowed(resolved)
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
        # Exact (case-insensitive) match always wins, and is checked across all
        # labels first so an exact candidate is never shadowed by a prefix one.
        for label in labels:
            if label and requested_lower == label.lower():
                return True
        # Otherwise only accept a stored label that is a long, strict prefix of
        # the requested name -- Origin truncates over-long short names, leaving
        # the stored short name as a prefix of the original. The length floor
        # keeps unrelated short names ("T") from matching longer requests
        # ("Trans"), which previously caused the wrong workbook to be reused.
        for label in labels:
            label_lower = label.lower()
            if (
                len(label_lower) >= _MIN_TRUNCATION_PREFIX_LEN
                and len(label_lower) < len(requested_lower)
                and requested_lower.startswith(label_lower)
            ):
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
