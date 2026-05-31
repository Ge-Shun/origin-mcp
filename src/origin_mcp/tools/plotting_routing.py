from __future__ import annotations

from pathlib import Path
from typing import Any

from ._shared import (
    _export_inspection,
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_plot_from_range(
    data_range: str,
    template: str = "line",
    plot_type: str = "?",
    graph_name: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a graph from an existing Origin range and template."""

    def run() -> dict[str, Any]:
        graph = client.plot_range(
            data_range=data_range,
            template=template,
            plot_type=plot_type,
            graph_name=graph_name,
            title=title,
            x_label=x_label,
            y_label=y_label,
            export_path=Path(export_path) if export_path else None,
        )
        graph_data = graph.as_dict()
        return _ok(
            "Created graph from Origin range.",
            graph=graph_data,
            export_inspection=_export_inspection(graph_data),
        )

    return _wrap(run)


@_mcp_tool()
def origin_batch_plot_from_template(
    data_ranges: list[str],
    template: str,
    output_dir: str | None = None,
    file_type: str = "png",
    plot_type: str = "?",
) -> dict[str, Any]:
    """Create multiple graphs from existing Origin ranges using one template."""

    return _wrap(
        lambda: _ok(
            "Created batch template plots.",
            **client.batch_plot_from_template(
                data_ranges=data_ranges,
                template=template,
                output_dir=Path(output_dir) if output_dir else None,
                file_type=file_type,
                plot_type=plot_type,
            ),
        )
    )


@_mcp_tool()
def origin_recommend_chart(
    path: str,
    intent: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
    max_recommendations: int = 5,
) -> dict[str, Any]:
    """Recommend chart types from table shape, column semantics, and optional intent."""

    return _wrap(
        lambda: _ok(
            "Recommended chart route.",
            **client.recommend_chart(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
                excel_sheet=excel_sheet,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                skiprows=skiprows,
                nrows=nrows,
                na_values=na_values,
                max_recommendations=max_recommendations,
            ),
        )
    )


@_mcp_tool()
def origin_plot_auto(
    path: str,
    intent: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
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
    """Choose a chart route from table data and create the plot."""

    return _wrap(
        lambda: _ok(
            "Created automatically routed plot.",
            **client.plot_auto(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
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
                style_mode=style_mode,
                palette_name=palette_name,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )


@_mcp_tool()
def origin_chart_atlas_route(
    intent: str,
    columns: list[str] | None = None,
    matrix: bool = False,
) -> dict[str, Any]:
    """Choose the recommended plot route for a semantic chart intent."""

    return _wrap(
        lambda: _ok(
            "Selected chart atlas route.",
            **client.chart_atlas_route(intent=intent, columns=columns, matrix=matrix),
        )
    )


@_mcp_tool()
def origin_plot_chart_atlas(
    path: str,
    intent: str,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    z_col: str | int | None = None,
    y_error_col: str | int | None = None,
    x_error_col: str | int | None = None,
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
    palette_role: str | None = None,
    palette_name: str | None = None,
    export_path: str | None = None,
) -> dict[str, Any]:
    """Create a plot using chart-atlas intent routing."""

    return _wrap(
        lambda: _ok(
            "Created chart atlas plot.",
            **client.plot_chart_atlas(
                path=Path(path),
                intent=intent,
                x_col=x_col,
                y_cols=y_cols,
                z_col=z_col,
                y_error_col=y_error_col,
                x_error_col=x_error_col,
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
                style_mode=style_mode,
                palette_role=palette_role,
                palette_name=palette_name,
                export_path=Path(export_path) if export_path else None,
            ),
        )
    )
