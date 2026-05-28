from __future__ import annotations

from .analysis import _AnalysisMixin
from .base import GraphRef, WorksheetRef, _OriginClientBase
from .export import _ExportMixin
from .graph_formatting import _GraphFormattingMixin
from .lifecycle import _LifecycleMixin
from .plot import _PlotMixin
from .worksheet import _WorksheetMixin


class OriginClient(
    _LifecycleMixin,
    _WorksheetMixin,
    _PlotMixin,
    _GraphFormattingMixin,
    _AnalysisMixin,
    _ExportMixin,
    _OriginClientBase,
):
    """Public Origin/originpro client; behavior comes from the mixins."""


__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]
