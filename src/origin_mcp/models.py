from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PlotKind(str, Enum):
    line = "line"
    scatter = "scatter"


class CsvImportRequest(BaseModel):
    path: Path = Field(description="Absolute path to a CSV file.")
    book_name: str | None = Field(default=None, description="Optional Origin workbook name.")
    sheet_name: str | None = Field(default=None, description="Optional Origin worksheet name.")

    @field_validator("path")
    @classmethod
    def path_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"CSV file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"CSV path is not a file: {value}")
        return value


class PlotCsvRequest(CsvImportRequest):
    x_col: str | int | None = Field(
        default=None,
        description="Column name or zero-based index to use as X. Defaults to the first column.",
    )
    y_cols: list[str | int] | None = Field(
        default=None,
        description="Column names or zero-based indexes to plot as Y. Defaults to all non-X columns.",
    )
    graph_name: str | None = Field(default=None, description="Optional Origin graph page name.")
    export_path: Path | None = Field(default=None, description="Optional graph export path.")


class ToolResult(BaseModel):
    ok: bool = True
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
