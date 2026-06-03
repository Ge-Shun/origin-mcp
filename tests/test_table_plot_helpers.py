"""Unit tests for the pure command-building helpers on ``_TablePlotMixin``.

The full plot path drives Origin's graphing engine, but the LabTalk command
construction and route-selection logic are pure functions worth pinning down on
their own.
"""

from __future__ import annotations

import pytest

from origin_mcp.client.base import TABLE_PLOTXYZ_IDS, TABLE_WORKSHEET_PLOT_IDS
from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_table_plot_command_options_routes_by_id() -> None:
    worksheet_id = next(iter(TABLE_WORKSHEET_PLOT_IDS))
    plotxyz_id = next(iter(TABLE_PLOTXYZ_IDS))

    assert OriginClient._table_plot_command_options(worksheet_id) == ("worksheet", "selection")
    assert OriginClient._table_plot_command_options(plotxyz_id) == ("plotxyz", "iz")
    # 200 is a plain XY line plot id, not in either special set.
    assert OriginClient._table_plot_command_options(200) == ("plotxy", "iy")


def test_plot_command_output_warning_only_on_mismatch() -> None:
    assert OriginClient._plot_command_output_warning(None, "G") is None
    assert OriginClient._plot_command_output_warning("G", "G") is None
    warning = OriginClient._plot_command_output_warning("Requested", "Actual")
    assert warning is not None and "Requested" in warning and "Actual" in warning


def test_plot_rejected_message_includes_context() -> None:
    message = OriginClient._plot_rejected_message(200, "line", ["A", "B"], "plotxy ...;")

    assert "200" in message
    assert "line" in message
    assert "['A', 'B']" in message


def test_worksheet_plot_command_requires_contiguous_selection() -> None:
    columns = ["x", "y1", "y2"]

    script = OriginClient._worksheet_plot_command(columns, ["x", "y1"], 100, "tmpl")
    assert "worksheet -s 1 0 2 0;" in script
    assert "worksheet -p 100 tmpl;" in script

    with pytest.raises(OriginOperationError):
        OriginClient._worksheet_plot_command(columns, ["x", "y2"], 100, "tmpl")


@pytest.mark.parametrize(
    ("plot_type_id", "count", "expected"),
    [
        (183, 6, (4, 1, 6, 4, 1, 6)),
        (184, 4, (4, 1, 6, 6)),
        (200, 3, (4, 1, 6)),
        (183, 3, (4, 1, 6)),  # too few selected -> default pattern
    ],
)
def test_plotxyz_type_pattern(plot_type_id: int, count: int, expected: tuple[int, ...]) -> None:
    assert OriginClient._plotxyz_type_pattern(plot_type_id, count) == expected


def test_plotxyz_axis_spec_maps_types() -> None:
    assert OriginClient._plotxyz_axis_spec((4, 1, 6)) == "XYZ"
    assert OriginClient._plotxyz_axis_spec((4, 1, 6, 6)) == "XYZZ"


def test_resolve_graph_template_prefers_explicit() -> None:
    client = OriginClient()
    assert client._resolve_graph_template("scatter") == "scatter"
    assert client._resolve_graph_template("scatter", template="custom") == "custom"
    # Unknown kind falls back to "line".
    assert client._resolve_graph_template("nonexistent-kind") == "line"


def test_plot_command_new_vs_reuse() -> None:
    new_script = OriginClient._plot_command(
        "plotxy", "iy", "[Book1]Sheet1!(1,2)", 200, "line", "MyGraph"
    )
    assert "plotxy iy:=[Book1]Sheet1!(1,2)" in new_script
    assert "plot:=200" in new_script
    assert "name:=MyGraph" in new_script

    reuse_script = OriginClient._plot_command(
        "plotxy", "iy", "[Book1]Sheet1!(1,2)", 200, "line", "MyGraph", reuse_existing=True
    )
    assert "ogl:=[MyGraph]1" in reuse_script


def test_assert_plot_type_command_detects_route_mismatch() -> None:
    client = OriginClient()
    # 200 should route through plotxy/iy; claiming worksheet is a mismatch.
    with pytest.raises(OriginOperationError):
        client._assert_plot_type_command(200, "line", "worksheet", "selection", "worksheet -p ...")
