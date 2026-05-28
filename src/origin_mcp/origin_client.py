from __future__ import annotations

from .client.analysis import _AnalysisMixin
from .client.base import GraphRef, WorksheetRef
from .client.export import _ExportMixin
from .client.graph_formatting import _GraphFormattingMixin
from .client.lifecycle import _LifecycleMixin
from .client.plot import _PlotMixin
from .client.worksheet import _WorksheetMixin

__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]


class OriginClient(
    _LifecycleMixin,
    _WorksheetMixin,
    _PlotMixin,
    _GraphFormattingMixin,
    _AnalysisMixin,
    _ExportMixin,
):
    """Small wrapper around the `originpro` package.

    The import is intentionally lazy so the MCP server can start and list tools even
    on machines where Origin is not installed yet.
    """













































































































































































