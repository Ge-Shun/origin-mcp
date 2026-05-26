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
