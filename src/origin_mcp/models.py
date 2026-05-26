from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PlotKind(str, Enum):
    line = "line"
    scatter = "scatter"
    line_symbol = "line_symbol"
    column = "column"
    contour = "contour"
    histogram = "histogram"
    box = "box"
    heatmap = "heatmap"
    scatter3d = "scatter3d"
    surface3d = "surface3d"
    polar = "polar"


class TableImportRequest(BaseModel):
    path: Path = Field(description="Absolute path to a CSV, TSV, TXT, DAT, XLS, or XLSX file.")
    book_name: str | None = Field(default=None, description="Optional Origin workbook name.")
    sheet_name: str | None = Field(default=None, description="Optional Origin worksheet name.")
    excel_sheet: str | int | None = Field(
        default=0,
        description="Excel sheet name or zero-based index. Ignored for text files.",
    )
    delimiter: str | None = Field(
        default=None,
        description=(
            "Delimiter for text files. If omitted, CSV/TSV defaults or auto-detection are used."
        ),
    )
    encoding: str | None = Field(default=None, description="Optional text file encoding.")
    header: int | None = Field(
        default=0,
        description="Zero-based row number to use as column names.",
    )
    skiprows: int | list[int] | None = Field(
        default=None,
        description="Rows to skip while reading.",
    )
    nrows: int | None = Field(default=None, description="Maximum number of data rows to read.")
    na_values: str | list[str] | None = Field(
        default=None,
        description="Additional missing value markers.",
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
    z_col: str | int | None = Field(
        default=None,
        description="Optional Z column for contour/XYZ plots.",
    )
    y_error_col: str | int | None = Field(default=None, description="Optional Y error column.")
    x_error_col: str | int | None = Field(default=None, description="Optional X error column.")
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


class AxisSettingsRequest(BaseModel):
    graph_name: str | None = Field(default=None, description="Optional graph page name.")
    axis: str = Field(default="x", description="Axis name: x, y, x2, y2, z, or z2.")
    scale: str | int | None = Field(
        default=None,
        description="Axis scale, such as linear or log10.",
    )
    start: float | None = Field(default=None, description="Axis start value.")
    end: float | None = Field(default=None, description="Axis end value.")
    step: float | None = Field(default=None, description="Axis major tick step.")
    title: str | None = Field(default=None, description="Axis title.")


class PlotStyleRequest(BaseModel):
    graph_name: str | None = Field(default=None, description="Optional graph page name.")
    plot_index: int | None = Field(
        default=None,
        description="Zero-based plot index. Applies to all plots if omitted.",
    )
    color: str | tuple[int, int, int] | None = Field(default=None, description="Plot color.")
    line_width: float | None = Field(default=None, description="Line width.")
    line_style: int | None = Field(default=None, description="Origin line style integer.")
    symbol_kind: int | None = Field(default=None, description="Origin symbol kind integer.")
    symbol_size: float | None = Field(default=None, description="Symbol size.")
    transparency: float | None = Field(default=None, description="Transparency percent, 0 to 100.")


class ProjectObjectRequest(BaseModel):
    name: str = Field(description="Origin page or object name.")
    object_type: str = Field(
        default="graph",
        description="graph, workbook, matrixbook, or worksheet.",
    )


class AnalysisRequest(BaseModel):
    analysis: str = Field(description="Analysis type.")
    worksheet: str | None = Field(
        default=None,
        description="Worksheet range or book/sheet reference.",
    )
    x_col: str | int | None = Field(default=None, description="Optional X column.")
    y_col: str | int | None = Field(default=None, description="Optional Y column.")
    output_sheet: str | None = Field(default=None, description="Optional output sheet/name hint.")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra LabTalk/X-Function options.",
    )
    include_output: bool = Field(
        default=False,
        description="Read output worksheet rows back into the response when possible.",
    )
    output_max_rows: int = Field(
        default=100,
        description="Maximum rows to read from an output worksheet.",
    )


class ToolResult(BaseModel):
    ok: bool = True
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
