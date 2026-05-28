from __future__ import annotations

from .base import GraphRef, WorksheetRef

__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]


def __getattr__(name: str):
    if name == "OriginClient":
        from ..origin_client import OriginClient

        return OriginClient
    raise AttributeError(name)
