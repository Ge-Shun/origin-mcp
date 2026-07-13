from __future__ import annotations

from typing import Any

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_list_xfunctions(category: str | None = None) -> dict[str, Any]:
    """List the controlled X-Function expert catalog and accepted arguments."""

    return _wrap(
        lambda: _ok(
            "Listed controlled Origin X-Functions.",
            **client.list_xfunctions(category=category),
        )
    )


@_mcp_tool()
def origin_run_xfunction(
    name: str,
    arguments: dict[str, Any] | None = None,
    theme: str | None = None,
) -> dict[str, Any]:
    """Run an allowlisted Origin X-Function with schema-validated arguments.

    Call origin_list_xfunctions first. Unknown functions and parameters are
    rejected; range arguments cannot contain script delimiters. This is the
    expert route for supported Origin features without exposing arbitrary
    LabTalk construction.
    """

    return _wrap(
        lambda: _ok(
            "Ran controlled Origin X-Function.",
            **client.run_xfunction(name=name, arguments=arguments, theme=theme),
        )
    )


@_mcp_tool()
def origin_fft_filter(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    filter_type: str = "low",
    cutoff: float | None = None,
    lower_cutoff: float | None = None,
    upper_cutoff: float | None = None,
    pass_frequency: float | None = None,
    stop_frequency: float | None = None,
    threshold: float | None = None,
    keep_dc_offset: bool = True,
    output_book: str | None = None,
    output_sheet: str = "Filtered",
) -> dict[str, Any]:
    """Apply an ideal/parabolic/band/threshold FFT filter to a signal."""

    return _wrap(
        lambda: _ok(
            "Filtered Origin signal with FFT.",
            **client.fft_filter(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                filter_type=filter_type,
                cutoff=cutoff,
                lower_cutoff=lower_cutoff,
                upper_cutoff=upper_cutoff,
                pass_frequency=pass_frequency,
                stop_frequency=stop_frequency,
                threshold=threshold,
                keep_dc_offset=keep_dc_offset,
                output_book=output_book,
                output_sheet=output_sheet,
            ),
        )
    )


@_mcp_tool()
def origin_principal_component_analysis(
    variables_range: str | None = None,
    worksheet: str | None = None,
    columns: list[str | int] | None = None,
    matrix_type: str = "corr",
    components: int = 2,
    standardize_scores: bool = False,
    missing: str = "listwise",
    scree_plot: bool = True,
    loading_plot: bool = True,
    score_plot: bool = False,
    biplot: bool = True,
    report_output: str | None = None,
    scores_output: str | None = None,
) -> dict[str, Any]:
    """Run OriginPro PCA with controlled output and plot options."""

    return _wrap(
        lambda: _ok(
            "Completed Origin principal component analysis.",
            **client.principal_component_analysis(
                variables_range=variables_range,
                worksheet=worksheet,
                columns=columns,
                matrix_type=matrix_type,
                components=components,
                standardize_scores=standardize_scores,
                missing=missing,
                scree_plot=scree_plot,
                loading_plot=loading_plot,
                score_plot=score_plot,
                biplot=biplot,
                report_output=report_output,
                scores_output=scores_output,
            ),
        )
    )


@_mcp_tool()
def origin_one_way_anova(
    worksheet: str,
    group_columns: list[str | int],
) -> dict[str, Any]:
    """Run raw-data one-way ANOVA on two or more worksheet group columns."""

    return _wrap(
        lambda: _ok(
            "Completed Origin one-way ANOVA.",
            **client.one_way_anova(
                worksheet=worksheet,
                group_columns=group_columns,
            ),
        )
    )
