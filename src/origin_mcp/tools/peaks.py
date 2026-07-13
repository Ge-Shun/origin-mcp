from __future__ import annotations

from typing import Any

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_peak_analyzer(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    theme: str | None = None,
    dialog_mode: str = "no_dialog",
) -> dict[str, Any]:
    """Run Origin Peak Analyzer with a saved theme or open its wizard.

    no_dialog is reproducible script mode and requires theme. modeless/modal
    opens the wizard and may omit the theme. A theme can represent baseline
    creation/subtraction, peak finding, integration, or OriginPro peak fitting.
    """

    return _wrap(
        lambda: _ok(
            "Ran Origin Peak Analyzer.",
            **client.peak_analyzer(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                theme=theme,
                dialog_mode=dialog_mode,
            ),
        )
    )


@_mcp_tool()
def origin_peak_baseline(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    threshold: float = 0.05,
    anchor_count: int = 8,
    output_book: str = "PeakBaseline",
    output_sheet: str = "Anchors",
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Automatically create spectrum baseline anchor points with blauto."""

    return _wrap(
        lambda: _ok(
            "Created Origin peak baseline anchors.",
            **client.peak_baseline(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                threshold=threshold,
                anchor_count=anchor_count,
                output_book=output_book,
                output_sheet=output_sheet,
                include_output=include_output,
                output_max_rows=output_max_rows,
            ),
        )
    )


@_mcp_tool()
def origin_peak_analyzer_batch(
    theme: str,
    input_range: str | None = None,
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_cols: list[str | int] | None = None,
    result_sheet: str = "peak_properties",
    output_sheet: str | None = None,
    include_fit_statistics: bool = True,
    remove_intermediate: bool = True,
    dataset_identifier: str = "Range",
    clear_output: bool = True,
    append_mode: str = "rows",
    sequential_initialization: bool = False,
    before_script: str | None = None,
    loop_script: str | None = None,
    end_script: str | None = None,
    background_instances: int = 1,
) -> dict[str, Any]:
    """Batch-analyze multiple spectra using an Origin Peak Analyzer theme.

    Pass a full Origin XYRange or worksheet/x_col/y_cols. result_sheet must
    match the theme goal: integrate, baseline, peak_centers, peak_properties,
    or none. Sequential initialization is useful for related peak-fit spectra.
    """

    return _wrap(
        lambda: _ok(
            "Completed batch Origin Peak Analyzer.",
            **client.peak_analyzer_batch(
                theme=theme,
                input_range=input_range,
                worksheet=worksheet,
                x_col=x_col,
                y_cols=y_cols,
                result_sheet=result_sheet,
                output_sheet=output_sheet,
                include_fit_statistics=include_fit_statistics,
                remove_intermediate=remove_intermediate,
                dataset_identifier=dataset_identifier,
                clear_output=clear_output,
                append_mode=append_mode,
                sequential_initialization=sequential_initialization,
                before_script=before_script,
                loop_script=loop_script,
                end_script=end_script,
                background_instances=background_instances,
            ),
        )
    )
