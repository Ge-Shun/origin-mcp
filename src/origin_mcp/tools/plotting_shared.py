from __future__ import annotations

from pathlib import Path
from typing import Any

from origin_mcp.models import (
    PlotKind,
    PlotStyleMode,
    PlotTableRequest,
)

from ._shared import (
    _export_inspection,
    _ok,
    _wrap,
    client,
)

PLOT_TYPE_ID_ROUTES: dict[str, tuple[int, str]] = {
    "area": (204, "area"),
    "stack_area": (214, "stackarea"),
    "fill_area": (249, "fillarea"),
    "bar": (215, "bar"),
    "stack_bar": (216, "bar"),
    "floating_bar": (207, "floatbar"),
    "column_stack": (213, "column"),
    "pie": (225, "pie"),
    "ternary": (245, "ternary"),
    "ternary_contour": (185, "TernaryContour"),
    "bubble": (193, "scatter"),
    "bubble_color_mapped": (248, "scatter"),
    "color_mapped": (247, "scatter"),
    "vector_xyam": (208, "vector"),
    "vector_xyxy": (218, "vectxyxy"),
    "vector_3d": (183, "gl3DVector"),
    "high_low_close": (205, "hclose"),
    "candlestick": (221, "Candlestick"),
    "waterfall": (210, "walls"),
    "ribbon_3d": (211, "ribbon"),
    "bars_3d": (212, "bar3d"),
    "errorbar_3d": (184, "gl3DError"),
    "polar_xr_ytheta": (186, "PolarXrYTheta"),
    "smith": (191, "SmithCht"),
    "dendrogram": (108, "Cluster"),
}

MATRIX_PLOT_TYPE_ID_ROUTES: dict[str, tuple[int, str]] = {
    "scatter_3d": (101, "gl3DScatterMat"),
    "surface_3d": (103, "glmesh"),
    "heatmap": (105, "heatmap"),
    "contour": (226, "contour"),
    "image": (220, "image"),
}


def _plot_csv(
    kind: PlotKind,
    path: str,
    x_col: str | int | None,
    y_cols: list[str | int] | None,
    book_name: str | None,
    sheet_name: str | None,
    excel_sheet: str | int | None,
    delimiter: str | None,
    encoding: str | None,
    header: int | None,
    skiprows: int | list[int] | None,
    nrows: int | None,
    na_values: str | list[str] | None,
    graph_name: str | None,
    template: str | None,
    title: str | None,
    x_label: str | None,
    y_label: str | None,
    show_legend: bool,
    style_mode: str,
    export_path: str | None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    bar_gap: float | None = None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        req = PlotTableRequest(
            path=Path(path),
            x_col=x_col,
            y_cols=y_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
            graph_name=graph_name,
            template=template,
            title=title,
            x_label=x_label,
            y_label=y_label,
            z_col=z_col,
            y_error_col=y_error_col,
            x_error_col=x_error_col,
            show_legend=show_legend,
            style_mode=PlotStyleMode(style_mode),
            export_path=Path(export_path) if export_path else None,
        )
        worksheet, graph = client.plot_table(
            path=req.path,
            kind=kind.value,
            x_col=req.x_col,
            y_cols=req.y_cols,
            book_name=req.book_name,
            sheet_name=req.sheet_name,
            excel_sheet=req.excel_sheet,
            delimiter=req.delimiter,
            encoding=req.encoding,
            header=req.header,
            skiprows=req.skiprows,
            nrows=req.nrows,
            na_values=req.na_values,
            graph_name=req.graph_name,
            template=req.template,
            title=req.title,
            x_label=req.x_label,
            y_label=req.y_label,
            z_col=req.z_col,
            y_error_col=req.y_error_col,
            x_error_col=req.x_error_col,
            show_legend=req.show_legend,
            style_mode=req.style_mode.value,
            export_path=req.export_path,
        )
        if bar_gap is not None:
            client.set_plot_style(graph_name=graph.graph_name, bar_gap=bar_gap)
        return _ok(
            f"Created {kind.value} plot from table data.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            export_inspection=_export_inspection(graph.as_dict()),
        )

    return _wrap(run)


def _plot_table_id(
    path: str,
    plot_type_id: int,
    template: str,
    selected_cols: list[str | int] | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
    graph_name: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    style_mode: str = "origin_default",
    palette_name: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        style_mode_actual = PlotStyleMode(style_mode).value
        worksheet, graph, command = client.plot_table_by_id(
            path=Path(path),
            plot_type_id=plot_type_id,
            template=template,
            selected_cols=selected_cols,
            book_name=book_name,
            sheet_name=sheet_name,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
            graph_name=graph_name,
            title=title,
            x_label=x_label,
            y_label=y_label,
            style_mode=style_mode_actual,
            palette_name=palette_name,
            export_path=Path(export_path) if export_path else None,
        )
        return _ok(
            "Created Origin graph from table data and Plot Type ID.",
            worksheet=worksheet.as_dict(),
            graph=graph.as_dict(),
            command=command,
            export_inspection=_export_inspection(graph.as_dict()),
        )

    return _wrap(run)
