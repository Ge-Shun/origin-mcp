from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PlotKind(str, Enum):
    line = "line"
    scatter = "scatter"


class TableImportRequest(BaseModel):
    path: Path = Field(description="Absolute path to a CSV, TSV, TXT, DAT, XLS, or XLSX file.")
    book_name: str | None = Field(default=None, description="Optional Origin workbook name.")
    sheet_name: str | None = Field(default=None, description="Optional Origin worksheet name.")
    excel_sheet: str | int | None = Field(
        default=0,
        description="Excel sheet name or zero-based index. Ignored for text files.",
    )

    @field_validator("path")
    @classmethod
    def path_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Data file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"Data path is not a file: {value}")
        supported = {".csv", ".tsv", ".txt", ".dat", ".xls", ".xlsx", ".xlsm"}
        if value.suffix.lower() not in supported:
            raise ValueError(f"Unsupported data file extension: {value.suffix}")
        return value


class CsvImportRequest(TableImportRequest):
    path: Path = Field(description="Absolute path to a CSV file.")


class PlotTableRequest(TableImportRequest):
    x_col: str | int | None = Field(
        default=None,
        description="Column name or zero-based index to use as X. Defaults to the first column.",
    )
    y_cols: list[str | int] | None = Field(
        default=None,
        description=(
            "Column names or zero-based indexes to plot as Y. Defaults to all non-X columns."
        ),
    )
    graph_name: str | None = Field(default=None, description="Optional Origin graph page name.")
    template: str | None = Field(
        default=None,
        description="Optional Origin graph template name or path.",
    )
    title: str | None = Field(default=None, description="Optional graph title label.")
    x_label: str | None = Field(default=None, description="Optional X axis title.")
    y_label: str | None = Field(default=None, description="Optional Y axis title.")
    show_legend: bool = Field(default=True, description="Whether to refresh/show the graph legend.")
    export_path: Path | None = Field(default=None, description="Optional graph export path.")


class PlotCsvRequest(PlotTableRequest):
    path: Path = Field(description="Absolute path to a CSV file.")


class GraphFormatRequest(BaseModel):
    graph_name: str | None = Field(default=None, description="Optional graph page name.")
    title: str | None = Field(default=None, description="Optional graph title label.")
    x_label: str | None = Field(default=None, description="Optional X axis title.")
    y_label: str | None = Field(default=None, description="Optional Y axis title.")
    show_legend: bool | None = Field(
        default=None,
        description="Set legend visibility when provided.",
    )
    rescale: bool = Field(
        default=True,
        description="Whether to rescale graph axes after formatting.",
    )


class ToolResult(BaseModel):
    ok: bool = True
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
