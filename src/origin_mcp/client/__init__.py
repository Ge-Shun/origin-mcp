from __future__ import annotations

from .analysis import _AnalysisMixin
from .base import GraphRef, WorksheetRef, _OriginClientBase
from .batch import _BatchMixin
from .expert import _ExpertMixin
from .export import _ExportMixin
from .graph_formatting import _GraphFormattingMixin
from .graph_style import _GraphStyleMixin
from .lifecycle import _LifecycleMixin
from .matrix_image import _MatrixImageMixin
from .peaks import _PeakMixin
from .plot_routing import _PlotRoutingMixin
from .project_organization import _ProjectOrganizationMixin
from .table_plot import _TablePlotMixin
from .worksheet import _WorksheetMixin


class OriginClient(
    _LifecycleMixin,
    _WorksheetMixin,
    _MatrixImageMixin,
    _ProjectOrganizationMixin,
    _BatchMixin,
    _PeakMixin,
    _ExpertMixin,
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
