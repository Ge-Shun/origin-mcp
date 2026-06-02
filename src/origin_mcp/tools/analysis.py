from __future__ import annotations

from typing import Any

from origin_mcp.models import (
    AnalysisRequest,
)

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_run_analysis(
    analysis: str,
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run a named Origin analysis X-Function through LabTalk."""

    def run() -> dict[str, Any]:
        if analysis.strip().lower().replace("-", "_") in {"linear_fit", "fitlr"}:
            if x_col is not None and y_col is not None:
                return _ok(
                    "Ran Origin linear fitting.",
                    **client.linear_fit_result(
                        worksheet=worksheet,
                        x_col=x_col,
                        y_col=y_col,
                        y_error_col=(options or {}).get("y_error_col"),
                        options=options,
                    ),
                )
        req = AnalysisRequest(
            analysis=analysis,
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_sheet,
            options=options or {},
            include_output=include_output,
            output_max_rows=output_max_rows,
        )
        return _ok("Ran Origin analysis.", **client.run_analysis(**req.model_dump()))

    return _wrap(run)


def _run_named_analysis(
    analysis: str,
    *,
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    return origin_run_analysis(
        analysis=analysis,
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_linear_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin linear fitting."""

    if x_col is not None and y_col is not None:
        return _wrap(
            lambda: _ok(
                "Ran Origin linear fitting.",
                **client.linear_fit_result(
                    worksheet=worksheet,
                    x_col=x_col,
                    y_col=y_col,
                    y_error_col=(options or {}).get("y_error_col"),
                    options=options,
                ),
            )
        )
    return _run_named_analysis(
        "linear_fit",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_polynomial_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin polynomial fitting."""

    return _run_named_analysis(
        "polynomial_fit",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_smooth(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin smoothing."""

    return _run_named_analysis(
        "smooth",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_peak_find(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin peak finding."""

    return _run_named_analysis(
        "peak_find",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_differentiate(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin differentiation."""

    return _run_named_analysis(
        "differentiate",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_integrate(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin integration."""

    return _run_named_analysis(
        "integrate",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_descriptive_stats(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin descriptive statistics."""

    return _run_named_analysis(
        "descriptive_stats",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_interpolate(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    method: int = 0,
    num_points: int | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Interpolate an XY curve onto a denser grid (Origin interp1xy).

    method selects the technique: 0=Linear, 1=Cubic Spline, 2=B-Spline,
    3=Akima. Set output_sheet (and include_output) to read the resampled XY
    data back.
    """

    merged: dict[str, Any] = {"method": method, **(options or {})}
    if num_points is not None:
        merged["num_points"] = num_points
    if x_min is not None:
        merged["x_min"] = x_min
    if x_max is not None:
        merged["x_max"] = x_max
    return _run_named_analysis(
        "interpolate",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=merged,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_normalize(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    method: int = 1,
    value: float | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Normalize a data column or XY curve (Origin normalize).

    method selects the approach: 0=Specify (divide by value), 1=Range [0,1],
    2=Z score, 3=Max, 5=Mean, 7=Standard deviation, 10=Sum, 13=Range [0,100].
    Pass value when method=0. Set output_sheet (and include_output) to read the
    normalized data back.
    """

    merged: dict[str, Any] = {"method": method, **(options or {})}
    if value is not None:
        merged["value"] = value
    return _run_named_analysis(
        "normalize",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=merged,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_ttest_one_sample(
    worksheet: str | None = None,
    data_col: str | int | None = None,
    hypothesized_mean: float = 0.0,
    tail: str = "two",
    alpha: float = 0.05,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-sample t-test against a hypothesized mean (Origin ttest1).

    tail is "two", "upper", or "lower". Results (Statistic, PValue, DF,
    LowerCL, UpperCL) are returned in the response metrics.
    """

    merged: dict[str, Any] = {
        "mean": hypothesized_mean,
        "tail": tail,
        "alpha": alpha,
        **(options or {}),
    }
    return _run_named_analysis(
        "ttest_one_sample",
        worksheet=worksheet,
        y_col=data_col,
        options=merged,
    )


@_mcp_tool()
def origin_ttest_two_sample(
    worksheet: str | None = None,
    col_a: str | int | None = None,
    col_b: str | int | None = None,
    mean_difference: float = 0.0,
    tail: str = "two",
    alpha: float = 0.05,
    equal_variance: bool = True,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Independent two-sample t-test on two columns (Origin ttest2).

    Set equal_variance=False for the Welch (unequal-variance) test. tail is
    "two", "upper", or "lower". Results (Statistic, PValue, DF, LowerCL,
    UpperCL) are returned in the response metrics.
    """

    merged: dict[str, Any] = {
        "mdiff": mean_difference,
        "tail": tail,
        "alpha": alpha,
        "equal": 1 if equal_variance else 0,
        **(options or {}),
    }
    return _run_named_analysis(
        "ttest_two_sample",
        worksheet=worksheet,
        x_col=col_a,
        y_col=col_b,
        options=merged,
    )


@_mcp_tool()
def origin_ttest_paired(
    worksheet: str | None = None,
    col_a: str | int | None = None,
    col_b: str | int | None = None,
    mean_difference: float = 0.0,
    tail: str = "two",
    alpha: float = 0.05,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Paired-sample t-test on two same-sized columns (Origin ttestpair).

    tail is "two", "upper", or "lower". Results (Statistic, PValue, DF,
    LowerCL, UpperCL) are returned in the response metrics.
    """

    merged: dict[str, Any] = {
        "mdiff": mean_difference,
        "tail": tail,
        "alpha": alpha,
        **(options or {}),
    }
    return _run_named_analysis(
        "ttest_paired",
        worksheet=worksheet,
        x_col=col_a,
        y_col=col_b,
        options=merged,
    )


@_mcp_tool()
def origin_fft(
    worksheet: str | None = None,
    signal_col: str | int | None = None,
    imaginary_col: str | int | None = None,
    output_sheet: str | None = None,
    window: str = "rect",
    sampling_interval: float = 1.0,
    options: dict[str, Any] | None = None,
    include_output: bool = True,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Forward FFT of a signal into its frequency spectrum (Origin fft1).

    Pass signal_col for a real signal, or signal_col plus imaginary_col for a
    complex signal. window selects the apodization (rect, welch, hanning,
    hamming, blackman, gauss, kaiser, ...). Set output_sheet to capture the
    spectrum worksheet (frequency, amplitude, phase, power, real, imaginary);
    include_output then returns its rows.
    """

    merged: dict[str, Any] = {
        "win": window,
        "interval": sampling_interval,
        **(options or {}),
    }
    if imaginary_col is not None:
        return _run_named_analysis(
            "fft",
            worksheet=worksheet,
            x_col=signal_col,
            y_col=imaginary_col,
            output_sheet=output_sheet,
            options=merged,
            include_output=include_output,
            output_max_rows=output_max_rows,
        )
    return _run_named_analysis(
        "fft",
        worksheet=worksheet,
        y_col=signal_col,
        output_sheet=output_sheet,
        options=merged,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_ifft(
    worksheet: str | None = None,
    real_col: str | int | None = None,
    imaginary_col: str | int | None = None,
    output_sheet: str | None = None,
    window: str = "rect",
    sampling_interval: float = 1.0,
    options: dict[str, Any] | None = None,
    include_output: bool = True,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Inverse FFT from a frequency-domain signal back to time domain (Origin ifft1).

    Pass real_col (and imaginary_col for a complex spectrum). Set output_sheet
    to capture the reconstructed time-domain worksheet; include_output then
    returns its rows.
    """

    merged: dict[str, Any] = {
        "win": window,
        "interval": sampling_interval,
        **(options or {}),
    }
    if imaginary_col is not None:
        return _run_named_analysis(
            "ifft",
            worksheet=worksheet,
            x_col=real_col,
            y_col=imaginary_col,
            output_sheet=output_sheet,
            options=merged,
            include_output=include_output,
            output_max_rows=output_max_rows,
        )
    return _run_named_analysis(
        "ifft",
        worksheet=worksheet,
        y_col=real_col,
        output_sheet=output_sheet,
        options=merged,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_correlation(
    worksheet: str | None = None,
    col_a: str | int | None = None,
    col_b: str | int | None = None,
    method: str = "pearson",
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = True,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Correlation coefficient between two columns (Origin corrcoef, OriginPro only).

    method is "pearson" (linear), "spearman" (rank), or "kendall". Set
    output_sheet to capture the coefficient-matrix worksheet for the chosen
    method; include_output then returns its rows. Requires OriginPro; on a
    non-Pro install the command returns executed=false with a warning.
    """

    flags = {"pearson": 0, "spearman": 0, "kendall": 0}
    chosen = method.strip().lower()
    flags[chosen if chosen in flags else "pearson"] = 1
    merged: dict[str, Any] = {**flags, **(options or {})}
    return _run_named_analysis(
        "correlation",
        worksheet=worksheet,
        x_col=col_a,
        y_col=col_b,
        output_sheet=output_sheet,
        options=merged,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_nonlinear_fit(
    worksheet: str | None = None,
    x_col: str | int | None = None,
    y_col: str | int | None = None,
    output_sheet: str | None = None,
    options: dict[str, Any] | None = None,
    include_output: bool = False,
    output_max_rows: int = 100,
) -> dict[str, Any]:
    """Run Origin nonlinear fitting."""

    return _run_named_analysis(
        "nonlinear_fit",
        worksheet=worksheet,
        x_col=x_col,
        y_col=y_col,
        output_sheet=output_sheet,
        options=options,
        include_output=include_output,
        output_max_rows=output_max_rows,
    )


@_mcp_tool()
def origin_list_fit_functions() -> dict[str, Any]:
    """List common Origin nonlinear fit function names and parameters."""

    return _wrap(lambda: _ok("Listed Origin fit functions.", **client.list_fit_functions()))


@_mcp_tool()
def origin_nonlinear_fit_structured(
    worksheet: str | None,
    x_col: str | int,
    y_col: str | int,
    function: str,
    output_sheet: str | None = None,
    initial_params: dict[str, float] | None = None,
    fixed_params: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run nonlinear fitting with explicit function and parameter hints."""

    return _wrap(
        lambda: _ok(
            "Ran structured Origin nonlinear fitting.",
            **client.nonlinear_fit_structured(
                worksheet=worksheet,
                x_col=x_col,
                y_col=y_col,
                function=function,
                output_sheet=output_sheet,
                initial_params=initial_params,
                fixed_params=fixed_params,
                options=options,
            ),
        )
    )
