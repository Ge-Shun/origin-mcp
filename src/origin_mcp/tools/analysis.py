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
