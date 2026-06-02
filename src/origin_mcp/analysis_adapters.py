from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .compat import is_origin_version_at_least
from .errors import OriginOperationError


@dataclass(frozen=True)
class AnalysisAdapter:
    name: str
    x_function: str
    aliases: tuple[str, ...] = ()
    minimum_origin_version: float | None = None
    range_required: bool = False
    input_option: str = "iy"
    output_option: str | None = "oy"
    option_aliases: dict[str, str] = field(default_factory=dict)
    symbol_options: tuple[str, ...] = ()
    scalar_outputs: tuple[str, ...] = ()
    report_output_option: str | None = None
    note: str = ""

    def supports(self, origin_version: float | int | None) -> bool:
        if self.minimum_origin_version is None:
            return True
        return is_origin_version_at_least(origin_version, self.minimum_origin_version)

    def normalize_options(self, options: dict[str, Any]) -> dict[str, Any]:
        normalized = {}
        for key, value in options.items():
            normalized[self.option_aliases.get(key, key)] = value
        return normalized

    def command(self, range_expr: str, output_sheet: str | None, options: dict[str, Any]) -> str:
        parts = [self.x_function]
        if range_expr:
            parts.append(f"{self.input_option}:={range_expr}")
        if output_sheet and self.output_option:
            parts.append(f"{self.output_option}:={output_sheet}")
        option_text = xf_options(self.normalize_options(options), self.symbol_options)
        if option_text:
            parts.append(option_text)
        return " ".join(parts) + ";"


ANALYSIS_ADAPTERS = {
    "linear_fit": AnalysisAdapter(
        name="linear_fit",
        x_function="fitlr",
        aliases=("fitlr", "linear-fit"),
        range_required=True,
        option_aliases={"intercept": "fixintercept", "slope": "fixslope"},
    ),
    "polynomial_fit": AnalysisAdapter(
        name="polynomial_fit",
        x_function="fitpoly",
        aliases=("fitpoly", "polynomial-fit"),
        minimum_origin_version=9.0,
        range_required=True,
        symbol_options=("coef", "err", "N", "AdjRSq", "RSqCOD"),
        option_aliases={
            "order": "polyorder",
            "degree": "polyorder",
            "fix_intercept": "fixint",
            "fixed_intercept": "intercept",
            "coefficients": "coef",
        },
    ),
    "nonlinear_fit": AnalysisAdapter(
        name="nonlinear_fit",
        x_function="nlfit",
        aliases=("nlfit", "nonlinear-fit"),
        range_required=True,
        note="For structured nonlinear fitting prefer originpro.NLFit in future adapters.",
    ),
    "smooth": AnalysisAdapter(
        name="smooth",
        x_function="smooth",
        aliases=("smoothing",),
        range_required=True,
        option_aliases={
            "points": "npts",
            "window_points": "npts",
            "polynomial_order": "polyorder",
            "percentile": "percent",
        },
        symbol_options=("method", "boundary", "prop"),
    ),
    "differentiate": AnalysisAdapter(
        name="differentiate",
        x_function="differentiate",
        aliases=("diff", "derivative"),
        range_required=True,
        option_aliases={
            "derivative_order": "order",
            "polynomial_order": "poly",
            "window_points": "npts",
            "points": "npts",
        },
    ),
    "integrate": AnalysisAdapter(
        name="integrate",
        x_function="integ1",
        aliases=("integration", "integ1"),
        range_required=True,
        option_aliases={
            "baseline": "baseline",
            "subtract_baseline": "sub",
        },
    ),
    "peak_find": AnalysisAdapter(
        name="peak_find",
        x_function="pkFind",
        aliases=("pkfind", "find_peaks", "peak-find"),
        range_required=True,
        option_aliases={
            "smooth_points": "smooth",
            "direction": "dir",
            "local_points": "npts",
            "size_option": "option",
            "threshold": "value",
            "max_peaks": "value",
            "filter_by": "filter",
            "max_half_width": "hwidth",
            "foot_height": "fheight",
            "center_indices": "ocenter",
            "center_x": "ocenter_x",
            "center_y": "ocenter_y",
            "left_indices": "oleft",
            "right_indices": "oright",
        },
        symbol_options=(
            "method",
            "dir",
            "option",
            "filter",
            "ocenter",
            "ocenter_x",
            "ocenter_y",
            "oleft",
            "oright",
        ),
    ),
    "descriptive_stats": AnalysisAdapter(
        name="descriptive_stats",
        x_function="moments",
        aliases=("moments", "statistics", "stats"),
        range_required=True,
        input_option="ix",
        output_option=None,
        symbol_options=("mean", "sd", "se", "n", "sum", "skewness", "kurtosis", "cv"),
    ),
    "interpolate": AnalysisAdapter(
        name="interpolate",
        x_function="interp1xy",
        aliases=("interp1xy", "interpolation", "interp"),
        range_required=True,
        option_aliases={
            "num_points": "npts",
            "points": "npts",
            "x_min": "xmin",
            "x_max": "xmax",
            "increment": "inc",
            "smoothing_factor": "sf",
        },
    ),
    "normalize": AnalysisAdapter(
        name="normalize",
        x_function="normalize",
        aliases=("normalization", "norm"),
        range_required=True,
        option_aliases={
            "value": "val",
            "divisor": "val",
            "reference_column": "refcol",
        },
    ),
    "ttest_one_sample": AnalysisAdapter(
        name="ttest_one_sample",
        x_function="ttest1",
        aliases=("ttest1", "one_sample_ttest", "one-sample-t-test", "t_test_one_sample"),
        range_required=True,
        input_option="irng",
        output_option=None,
        scalar_outputs=("stat", "prob", "df", "lcl", "ucl"),
        option_aliases={
            "hypothesized_mean": "mean",
            "significance": "alpha",
        },
        symbol_options=("tail", "stat", "prob", "df", "lcl", "ucl"),
    ),
    "ttest_two_sample": AnalysisAdapter(
        name="ttest_two_sample",
        x_function="ttest2",
        aliases=("ttest2", "two_sample_ttest", "two-sample-t-test", "independent_ttest"),
        range_required=True,
        input_option="irng",
        output_option=None,
        scalar_outputs=("stat", "prob", "df", "lcl", "ucl"),
        option_aliases={
            "mean_difference": "mdiff",
            "significance": "alpha",
            "equal_variance": "equal",
        },
        symbol_options=("tail", "stat", "prob", "df", "lcl", "ucl"),
    ),
    "ttest_paired": AnalysisAdapter(
        name="ttest_paired",
        x_function="ttestpair",
        aliases=("ttestpair", "paired_ttest", "paired-t-test"),
        range_required=True,
        input_option="irng",
        output_option=None,
        scalar_outputs=("stat", "prob", "df", "lcl", "ucl"),
        option_aliases={
            "mean_difference": "mdiff",
            "significance": "alpha",
        },
        symbol_options=("tail", "stat", "prob", "df", "lcl", "ucl"),
    ),
    "fft": AnalysisAdapter(
        name="fft",
        x_function="fft1",
        aliases=("fft1", "fourier", "fourier_transform"),
        range_required=True,
        input_option="ix",
        output_option=None,
        report_output_option="rd",
        option_aliases={
            "sampling_interval": "interval",
            "window": "win",
        },
        symbol_options=("win", "correct", "factor", "st", "norm", "pre", "rd"),
    ),
    "ifft": AnalysisAdapter(
        name="ifft",
        x_function="ifft1",
        aliases=("ifft1", "inverse_fft", "inverse_fourier"),
        range_required=True,
        input_option="ix",
        output_option=None,
        report_output_option="rd",
        option_aliases={
            "sampling_interval": "interval",
            "window": "win",
        },
        symbol_options=("win", "correct", "factor", "plot", "rd"),
    ),
    "correlation": AnalysisAdapter(
        name="correlation",
        x_function="corrcoef",
        aliases=("corrcoef", "correlation_coefficient", "corr"),
        range_required=True,
        input_option="irng",
        output_option=None,
        report_output_option="pwks",
        option_aliases={
            "confidence_level": "conflevel",
        },
        symbol_options=("pwks", "swks", "kwks"),
    ),
}


def resolve_analysis_adapter(name: str, origin_version: float | int | None) -> AnalysisAdapter:
    normalized = name.lower().replace("-", "_")
    adapter = ANALYSIS_ADAPTERS.get(normalized)
    if adapter is None:
        adapter = next(
            (
                item
                for item in ANALYSIS_ADAPTERS.values()
                if normalized in {alias.replace("-", "_") for alias in item.aliases}
            ),
            None,
        )
    if adapter is None:
        supported = ", ".join(sorted(ANALYSIS_ADAPTERS))
        raise OriginOperationError(
            f"Unsupported analysis type: {name}. Supported: {supported}",
            error_code="unsupported_analysis_type",
        )
    if not adapter.supports(origin_version):
        raise OriginOperationError(
            f"Analysis '{adapter.name}' requires Origin >= {adapter.minimum_origin_version}; "
            f"detected {origin_version}.",
            error_code="unsupported_origin_version",
        )
    return adapter


def xf_options(options: dict[str, Any], symbol_options: tuple[str, ...] = ()) -> str:
    parts = []
    for key, value in options.items():
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, str) and key in symbol_options:
            parts.append(f"{key}:={value}")
        elif isinstance(value, str):
            escaped = value.replace('"', r"\"")
            parts.append(f'{key}:="{escaped}"')
        else:
            parts.append(f"{key}:={value}")
    return " ".join(parts)
