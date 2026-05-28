from __future__ import annotations

from .analysis import _AnalysisMixin
from .base import GraphRef, WorksheetRef, _OriginClientBase
from .export import _ExportMixin
from .graph_formatting import _GraphFormattingMixin
from .graph_style import _GraphStyleMixin
from .lifecycle import _LifecycleMixin
from .plot_routing import _PlotRoutingMixin
from .table_plot import _TablePlotMixin
from .worksheet import _WorksheetMixin


class OriginClient(
    _LifecycleMixin,
    _WorksheetMixin,
    _TablePlotMixin,
    _PlotRoutingMixin,
    _GraphFormattingMixin,
    _GraphStyleMixin,
    _AnalysisMixin,
    _ExportMixin,
    _OriginClientBase,
):
    """Public Origin/originpro client; behavior comes from the mixins."""


__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]
