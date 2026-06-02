import pytest

from origin_mcp.analysis_adapters import resolve_analysis_adapter, xf_options
from origin_mcp.errors import OriginOperationError


def test_resolve_analysis_adapter_accepts_alias() -> None:
    adapter = resolve_analysis_adapter("peak-find", 10.3)

    assert adapter.name == "peak_find"
    assert adapter.x_function == "pkFind"


def test_resolve_analysis_adapter_rejects_unknown() -> None:
    with pytest.raises(OriginOperationError, match="Unsupported analysis type"):
        resolve_analysis_adapter("unknown", 10.3)


def test_xf_options_formats_values() -> None:
    text = xf_options({"enabled": True, "method": "Savitzky-Golay", "points": 5})

    assert "enabled:=1" in text
    assert 'method:="Savitzky-Golay"' in text
    assert "points:=5" in text


def test_xf_options_can_leave_origin_symbols_unquoted() -> None:
    text = xf_options({"method": "sg", "label": "Savitzky-Golay"}, ("method",))

    assert "method:=sg" in text
    assert 'label:="Savitzky-Golay"' in text


def test_smooth_adapter_uses_official_input_and_option_names() -> None:
    adapter = resolve_analysis_adapter("smooth", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet="SmoothOut",
        options={"points": 5, "polynomial_order": 2, "method": "sg"},
    )

    assert command.startswith("smooth iy:=[Book1]1!(time,signal)")
    assert "oy:=SmoothOut" in command
    assert "npts:=5" in command
    assert "polyorder:=2" in command


def test_polynomial_adapter_leaves_output_variables_unquoted() -> None:
    adapter = resolve_analysis_adapter("polynomial_fit", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet="[PolyOut]Result!(1,2)",
        options={"order": 2, "coef": "coefVec", "RSqCOD": "rsqVal"},
    )

    assert "oy:=[PolyOut]Result!(1,2)" in command
    assert "polyorder:=2" in command
    assert "coef:=coefVec" in command
    assert "RSqCOD:=rsqVal" in command


def test_peak_find_adapter_maps_common_names() -> None:
    adapter = resolve_analysis_adapter("peak-find", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet=None,
        options={"smooth_points": 7, "direction": "p", "threshold": 20},
    )

    assert "pkFind iy:=[Book1]1!(time,signal)" in command
    assert "smooth:=7" in command
    assert "dir:=p" in command
    assert "value:=20" in command


def test_peak_find_adapter_leaves_output_ranges_unquoted() -> None:
    adapter = resolve_analysis_adapter("peak_find", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet=None,
        options={"ocenter": "[PeakOut]Peaks!(1)", "ocenter_x": "[PeakOut]Peaks!(2)"},
    )

    assert "ocenter:=[PeakOut]Peaks!(1)" in command
    assert "ocenter_x:=[PeakOut]Peaks!(2)" in command


def test_descriptive_stats_adapter_uses_moments_input_without_worksheet_output() -> None:
    adapter = resolve_analysis_adapter("descriptive_stats", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(signal)",
        output_sheet="IgnoredOut",
        options={"mean": "meanVar", "sd": "sdVar", "se": "seVar"},
    )

    assert command.startswith("moments ix:=[Book1]1!(signal)")
    assert "oy:=" not in command
    assert "mean:=meanVar" in command
    assert "sd:=sdVar" in command
    assert "se:=seVar" in command


def test_xy_math_adapters_accept_output_ranges() -> None:
    diff = resolve_analysis_adapter("differentiate", 10.3).command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet="[DiffOut]Result!(1,2)",
        options={"points": 5, "derivative_order": 1},
    )
    integ = resolve_analysis_adapter("integrate", 10.3).command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet="[IntegOut]Result!(1,2)",
        options={},
    )

    assert "differentiate iy:=[Book1]1!(time,signal)" in diff
    assert "oy:=[DiffOut]Result!(1,2)" in diff
    assert "npts:=5" in diff
    assert "order:=1" in diff
    assert "integ1 iy:=[Book1]1!(time,signal)" in integ
    assert "oy:=[IntegOut]Result!(1,2)" in integ


def test_interpolate_adapter_maps_common_names() -> None:
    adapter = resolve_analysis_adapter("interpolation", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(time,signal)",
        output_sheet="[InterpOut]Result!(1,2)",
        options={"method": 1, "num_points": 200, "x_min": 0, "x_max": 10},
    )

    assert command.startswith("interp1xy iy:=[Book1]1!(time,signal)")
    assert "oy:=[InterpOut]Result!(1,2)" in command
    assert "method:=1" in command
    assert "npts:=200" in command
    assert "xmin:=0" in command
    assert "xmax:=10" in command


def test_normalize_adapter_maps_value_alias() -> None:
    adapter = resolve_analysis_adapter("normalize", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(signal)",
        output_sheet="[NormOut]Result!(1,2)",
        options={"method": 0, "value": 2.5},
    )

    assert command.startswith("normalize iy:=[Book1]1!(signal)")
    assert "oy:=[NormOut]Result!(1,2)" in command
    assert "method:=0" in command
    assert "val:=2.5" in command


def test_ttest_one_sample_adapter_uses_irng_and_scalar_outputs() -> None:
    adapter = resolve_analysis_adapter("one_sample_ttest", 10.3)
    assert adapter.scalar_outputs == ("stat", "prob", "df", "lcl", "ucl")
    command = adapter.command(
        range_expr="[Book1]1!(signal)",
        output_sheet=None,
        options={"hypothesized_mean": 10, "tail": "two", "prob": "osprob"},
    )

    assert command.startswith("ttest1 irng:=[Book1]1!(signal)")
    assert "oy:=" not in command
    assert "mean:=10" in command
    assert "tail:=two" in command
    assert "prob:=osprob" in command


def test_ttest_two_sample_adapter_maps_equal_variance_and_diff() -> None:
    adapter = resolve_analysis_adapter("ttest2", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(a,b)",
        output_sheet=None,
        options={"mean_difference": 0.5, "equal_variance": 0, "tail": "upper"},
    )

    assert command.startswith("ttest2 irng:=[Book1]1!(a,b)")
    assert "mdiff:=0.5" in command
    assert "equal:=0" in command
    assert "tail:=upper" in command


def test_ttest_paired_adapter_resolves_alias() -> None:
    adapter = resolve_analysis_adapter("paired-t-test", 10.3)

    assert adapter.name == "ttest_paired"
    assert adapter.x_function == "ttestpair"


def test_fft_adapter_uses_ix_and_binds_report_sheet() -> None:
    adapter = resolve_analysis_adapter("fourier", 10.3)
    assert adapter.report_output_option == "rd"
    command = adapter.command(
        range_expr="[Book1]1!(signal)",
        output_sheet=None,
        options={"window": "hanning", "sampling_interval": 0.01, "rd": "[FFTOut]Result!"},
    )

    assert command.startswith("fft1 ix:=[Book1]1!(signal)")
    assert "oy:=" not in command
    assert "win:=hanning" in command
    assert "interval:=0.01" in command
    # The report worksheet reference must stay unquoted.
    assert "rd:=[FFTOut]Result!" in command


def test_ifft_adapter_accepts_complex_input() -> None:
    adapter = resolve_analysis_adapter("ifft1", 10.3)
    command = adapter.command(
        range_expr="[Book1]1!(re,im)",
        output_sheet=None,
        options={"rd": "[IFFTOut]Result!"},
    )

    assert command.startswith("ifft1 ix:=[Book1]1!(re,im)")
    assert "rd:=[IFFTOut]Result!" in command


def test_correlation_adapter_uses_irng_and_coefficient_sheet() -> None:
    adapter = resolve_analysis_adapter("corrcoef", 10.3)
    assert adapter.report_output_option == "pwks"
    command = adapter.command(
        range_expr="[Book1]1!(a,b)",
        output_sheet=None,
        options={"pearson": 1, "confidence_level": 95, "pwks": "[CorrOut]Result!"},
    )

    assert command.startswith("corrcoef irng:=[Book1]1!(a,b)")
    assert "pearson:=1" in command
    assert "conflevel:=95" in command
    assert "pwks:=[CorrOut]Result!" in command
