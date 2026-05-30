from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
