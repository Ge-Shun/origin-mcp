from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class PlotStyleMode(str, Enum):
    origin_default = "origin_default"
    template = "template"
    theme = "theme"
    none = "none"
    nature = "nature"


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
    title: str | None = Field(default=None, description="Optional graph page long name.")
    x_label: str | None = Field(default=None, description="Optional X axis title.")
    y_label: str | None = Field(default=None, description="Optional Y axis title.")
    show_legend: bool = Field(default=True, description="Whether to refresh/show the graph legend.")
    style_mode: PlotStyleMode = Field(
        default=PlotStyleMode.origin_default,
        description=(
            "Graph styling policy. origin_default/template/theme/none preserve Origin template "
            "defaults; nature applies origin-mcp styling after plotting."
        ),
    )
    export_path: Path | None = Field(default=None, description="Optional graph export path.")


class PlotCsvRequest(PlotTableRequest):
    path: Path = Field(description="Absolute path to a CSV file.")


class GraphFormatRequest(BaseModel):
    graph_name: str | None = Field(default=None, description="Optional graph page name.")
    title: str | None = Field(default=None, description="Optional graph page long name.")
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
    layer_index: int = Field(default=0, description="Zero-based graph layer index.")
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
    layer_index: int = Field(default=0, description="Zero-based graph layer index.")
    plot_index: int | None = Field(
        default=None,
        description="Zero-based plot index. Applies to all plots if omitted.",
    )
    color: str | tuple[int, int, int] | None = Field(default=None, description="Plot color.")
    line_width: float | None = Field(default=None, description="Line width in points.")
    bar_gap: float | None = Field(
        default=None,
        description="Bar/column gap percent (-vg). Larger values make bars narrower.",
    )
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


class FigureMeta(BaseModel):
    id: str = Field(description="Stable figure identifier.")
    title: str | None = Field(default=None, description="Optional figure title/long name.")


class FigureRuntimeSpec(BaseModel):
    show_origin: bool = Field(default=True, description="Whether Origin should be visible.")
    new_project: bool = Field(default=False, description="Start a fresh Origin project first.")
    save_project: bool = Field(default=False, description="Save the Origin project after export.")
    project_path: Path | None = Field(default=None, description="Optional OPJU/OPJ save path.")


class FigureDataSpec(BaseModel):
    id: str = Field(description="Dataset id referenced by layers and plots.")
    source: Path = Field(description="Source data file path.")
    format: str | None = Field(default=None, description="csv/tsv/txt/dat/xlsx/xls/xlsm.")
    object: Literal["worksheet", "matrix", "xyz"] = Field(default="worksheet")
    roles: dict[str, str | int | list[str | int]] = Field(
        default_factory=dict,
        description="Semantic column roles such as x, y, z, group, error, err_low, err_high.",
    )
    excel_sheet: str | int | None = 0
    delimiter: str | None = None
    encoding: str | None = None
    header: int | None = 0
    skiprows: int | list[int] | None = None
    nrows: int | None = None
    na_values: str | list[str] | None = None

    @field_validator("source")
    @classmethod
    def source_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Data file does not exist: {value}")
        if not value.is_file():
            raise ValueError(f"Data path is not a file: {value}")
        supported = {".csv", ".tsv", ".txt", ".dat", ".xls", ".xlsx", ".xlsm"}
        if value.suffix.lower() not in supported:
            raise ValueError(f"Unsupported data file extension: {value.suffix}")
        return value


class FigureAxisSpec(BaseModel):
    title: str | None = None
    scale: str | int | None = None
    limits: Literal["auto"] | list[float | None] | None = "auto"
    step: float | None = None


class FigurePageSpec(BaseModel):
    id: str = Field(default="page_main")
    layout: Literal["single", "grid", "custom"] = Field(default="single")
    size_mm: list[float] | None = None
    margins_mm: list[float] | None = None
    panel_spacing_mm: list[float] | None = None


class FigureLayerSpec(BaseModel):
    id: str = Field(description="Layer/panel id.")
    page: str | None = None
    position_mode: Literal["grid", "absolute"] = Field(default="grid")
    grid_cell: list[int] | None = None
    grid_span: list[int] | None = None
    title: str | None = None
    panel_tag: str | None = None
    data_ref: str | None = None
    x: FigureAxisSpec = Field(default_factory=FigureAxisSpec)
    y: FigureAxisSpec = Field(default_factory=FigureAxisSpec)
    frame: dict[str, bool] = Field(default_factory=dict)


class FigurePlotSpec(BaseModel):
    id: str = Field(description="Plot primitive id.")
    layer: str
    type: str = Field(description="line/scatter/line_symbol/column/histogram/box/contour/heatmap.")
    data_ref: str | None = None
    map: dict[str, str | int | list[str | int]] = Field(
        default_factory=dict,
        description="Visual channel mapping such as x, y, z, group, error.",
    )
    style: dict[str, Any] = Field(default_factory=dict)
    group_style: dict[str, Any] = Field(default_factory=dict)
    uncertainty: dict[str, Any] = Field(default_factory=dict)


class FigureAnnotationSpec(BaseModel):
    id: str | None = None
    type: str
    layer: str | None = None
    text: str | None = None
    location: str | None = None
    frame: bool | None = None
    value: float | None = None
    orientation: str | None = None
    style: dict[str, Any] = Field(default_factory=dict)


class FigureStyleSpec(BaseModel):
    theme: Literal["origin_default", "template", "theme", "none", "nature"] = "origin_default"
    template: str | None = None
    font_family: str | None = None
    annotation_font_size: int | None = None
    palette_role: str | None = None
    palette_name: str | None = None


class FigureExportFormatSpec(BaseModel):
    enabled: bool = False
    path: Path | None = None
    width_px: int | None = None


class FigureExportSpec(BaseModel):
    dir_figures: Path | None = None
    dir_opju: Path | None = None
    png: FigureExportFormatSpec | bool | None = None
    pdf: FigureExportFormatSpec | bool | None = None
    svg: FigureExportFormatSpec | bool | None = None
    tiff: FigureExportFormatSpec | bool | None = None
    save_clean_data: bool = False
    qa: dict[str, Any] = Field(default_factory=dict)


class FigureSpec(BaseModel):
    figure: FigureMeta
    runtime: FigureRuntimeSpec = Field(default_factory=FigureRuntimeSpec)
    data: list[FigureDataSpec] = Field(default_factory=list)
    page: FigurePageSpec = Field(default_factory=FigurePageSpec)
    layers: list[FigureLayerSpec] = Field(default_factory=list)
    plots: list[FigurePlotSpec] = Field(default_factory=list)
    annotations: list[FigureAnnotationSpec] = Field(default_factory=list)
    style: FigureStyleSpec = Field(default_factory=FigureStyleSpec)
    export: FigureExportSpec = Field(default_factory=FigureExportSpec)

    @model_validator(mode="after")
    def validate_refs(self) -> FigureSpec:
        if not self.data:
            raise ValueError("FigureSpec requires at least one data item.")
        if not self.layers:
            raise ValueError("FigureSpec requires at least one layer.")
        if not self.plots:
            raise ValueError("FigureSpec requires at least one plot.")

        data_ids = _require_unique("data", [item.id for item in self.data])
        layer_ids = _require_unique("layers", [item.id for item in self.layers])
        _require_unique("plots", [item.id for item in self.plots])

        for layer in self.layers:
            if layer.data_ref is not None and layer.data_ref not in data_ids:
                raise ValueError(
                    f"Layer {layer.id!r} references unknown data_ref {layer.data_ref!r}."
                )
        for plot in self.plots:
            if plot.layer not in layer_ids:
                raise ValueError(f"Plot {plot.id!r} references unknown layer {plot.layer!r}.")
            if plot.data_ref is not None and plot.data_ref not in data_ids:
                raise ValueError(f"Plot {plot.id!r} references unknown data_ref {plot.data_ref!r}.")
        for annotation in self.annotations:
            if annotation.layer is not None and annotation.layer not in layer_ids:
                raise ValueError(
                    f"Annotation {annotation.id or annotation.type!r} references unknown layer "
                    f"{annotation.layer!r}."
                )
        return self


def _require_unique(label: str, values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"Duplicate {label} ids: {sorted(duplicates)}")
    return seen


# The searchable template metadata record (TemplateRecord) is a plain dataclass
# in origin_mcp.template_library, not a pydantic model here: that module is
# imported by the Origin-embedded bridge, whose Python does not ship pydantic.


class SaveGraphTemplateRequest(BaseModel):
    name: str = Field(description="Template name. Reused later as the plotting template name.")
    description: str | None = Field(default=None, description="Optional description.")
    tags: list[str] = Field(default_factory=list, description="Optional searchable tags.")
    plot_types: list[str] = Field(
        default_factory=list,
        description="Plot kinds this template is for, e.g. ['scatter']. Improves search matching.",
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Data roles the source plot used, e.g. ['x', 'y', 'error'].",
    )
    n_columns: int | None = Field(
        default=None,
        description="Number of data columns the source plot used. Improves search matching.",
    )
    graph_name: str | None = Field(
        default=None,
        description="Graph page to save. Defaults to the active graph.",
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite an existing template with the same name.",
    )


class SearchTemplatesRequest(BaseModel):
    query: str | None = Field(
        default=None, description="Free-text keywords to match name/tags/desc."
    )
    plot_type: str | None = Field(default=None, description="Desired plot kind, e.g. scatter.")
    n_columns: int | None = Field(default=None, description="Number of data columns to plot.")
    tags: list[str] = Field(default_factory=list, description="Tags the template should carry.")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of ranked results.")


class ToolResult(BaseModel):
    ok: bool = True
    message: str
    error_code: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
