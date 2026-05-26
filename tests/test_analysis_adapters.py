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
