"""Behavioural tests for graph creation, formatting, and export.

These drive the graph-object orchestration (plot_table, format_graph, set_axis,
list_project, export_*) against the in-memory fake graph surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def _write_csv(tmp_path: Path, name: str = "data.csv") -> Path:
    path = tmp_path / name
    path.write_text("x,y1,y2\n1,10,100\n2,20,200\n3,30,300\n", encoding="utf-8")
    return path


# -- plot_table orchestration --------------------------------------------


def test_plot_table_creates_graph_and_plots(fake_client: OriginClient, tmp_path: Path) -> None:
    csv = _write_csv(tmp_path)

    worksheet, graph = fake_client.plot_table(
        path=csv,
        kind="line",
        x_col="x",
        y_cols=["y1", "y2"],
        graph_name="MyPlot",
        title="Title",
        x_label="X axis",
        y_label="Y axis",
    )

    assert worksheet.columns == ["x", "y1", "y2"]
    assert worksheet.rows == 3
    assert graph.template == "line"
    # Two Y columns -> two plots in the first layer.
    page = fake_client.op.graphs[-1]
    assert len(page[0].plots) == 2
    # Axis titles were applied via format_graph.
    assert page[0].axis("x").title == "X axis"
    assert page[0].axis("y").title == "Y axis"


def test_plot_table_exports_when_requested(fake_client: OriginClient, tmp_path: Path) -> None:
    csv = _write_csv(tmp_path)
    out = tmp_path / "fig.png"

    _, graph = fake_client.plot_table(
        path=csv,
        kind="scatter",
        x_col="x",
        y_cols=["y1"],
        graph_name="Exp",
        export_path=out,
    )

    assert graph.export_path is not None
    assert Path(graph.export_path).exists()


def test_plot_table_rejects_empty_file(fake_client: OriginClient, tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("x,y\n", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.plot_table(path=empty, kind="line")


# -- list_project ---------------------------------------------------------


def test_list_project_classifies_books_and_graphs(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1]}))
    fake_client.op.add_graph("G1", lname="My Graph")

    project = fake_client.list_project()

    assert len(project["workbooks"]) == 1
    assert project["workbooks"][0]["name"] == "Data"
    assert len(project["graphs"]) == 1
    assert project["graphs"][0]["long_name"] == "My Graph"


# -- set_axis -------------------------------------------------------------


def test_set_axis_applies_scale_and_limits(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")

    result = fake_client.set_axis(graph_name="G1", axis="y", scale="log", start=1.0, end=100.0)

    assert result["axis"] == "y"
    assert result["axis_info"]["scale_name"] == "log10"
    assert result["axis_info"]["limits"] == (1.0, 100.0, None)
    assert result["verified"] is True


def test_set_axis_unknown_graph_raises(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError) as excinfo:
        fake_client.set_axis(graph_name="Missing", axis="x", scale="linear")
    assert excinfo.value.error_code == "graph_not_found"


# -- format_graph ---------------------------------------------------------


def test_format_graph_sets_titles_and_rescales(fake_client: OriginClient) -> None:
    page = fake_client.op.add_graph("G1")

    result = fake_client.format_graph(
        graph_name="G1", x_label="time", y_label="signal", rescale=True
    )

    assert result["formatted"] is True
    assert page[0].axis("x").title == "time"
    assert page[0].rescaled == 1


# -- rename / delete ------------------------------------------------------


def test_rename_object(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")

    result = fake_client.rename_object(name="G1", new_name="Renamed", object_type="graph")

    assert result["new_name"] == "Renamed"


def test_delete_object(fake_client: OriginClient) -> None:
    page = fake_client.op.add_graph("G1")

    result = fake_client.delete_object(name="G1", object_type="graph")

    assert result["deleted"] is True
    assert page.destroyed is True


# -- export ---------------------------------------------------------------


def test_export_graph_by_name_uses_save_fig(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_graph("G1")
    out = tmp_path / "g.png"

    result = fake_client.export_graph(path=out, graph_name="G1")

    assert result["path"] == str(out)
    assert result["method"] == "originpro.save_fig"
    assert out.exists()


def test_export_graph_by_name_can_set_pixel_width(
    fake_client: OriginClient,
    tmp_path: Path,
) -> None:
    fake_client.op.add_graph("G1")
    out = tmp_path / "g.png"

    result = fake_client.export_graph(path=out, graph_name="G1", width=1600)

    assert result["method"] == "originpro.save_fig"


def test_export_graph_falls_back_to_labtalk_when_save_fig_fails(
    fake_client: OriginClient,
    tmp_path: Path,
) -> None:
    page = fake_client.op.add_graph("G1")

    def fail_save_fig(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("save_fig failed")

    page.save_fig = fail_save_fig  # type: ignore[method-assign]
    out = tmp_path / "g.png"

    result = fake_client.export_graph(path=out, graph_name="G1", width=1600)

    assert result["method"] == "labtalk.expGraph"
    assert result["fallback_error"].startswith("RuntimeError: save_fig failed")
    scripts = [call[1][0] for call in _lt_exec_calls(fake_client)]
    assert 'tr1.width:=1600 tr1.unit:=pixel type:=png path:="' in scripts[-1]


def test_export_graph_refuses_existing(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_graph("G1")
    out = tmp_path / "g.png"
    out.write_text("x", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.export_graph(path=out, graph_name="G1", overwrite=False)


def test_export_all_graphs_writes_files(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_graph("Alpha")
    fake_client.op.add_graph("Beta")

    result = fake_client.export_all_graphs(output_dir=tmp_path, file_type="png")

    assert result["count"] == 2
    assert all(Path(p).exists() for p in result["paths"])


def test_export_preview_returns_inspection(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_graph("G1")

    result = fake_client.export_preview(graph_name="G1", output_dir=tmp_path)

    assert Path(result["path"]).exists()
    assert result["preview"]["exists"] is True
    assert result["preview"]["width"] == 1


def _lt_exec_calls(client: OriginClient) -> list[tuple[str, tuple]]:
    return [call for call in client.op.calls if call[0] == "lt_exec"]


# -- plot editing & introspection ----------------------------------------


def test_add_plot_to_graph(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
    page = fake_client.op.add_graph("G1")

    result = fake_client.add_plot_to_graph(worksheet="Data", x_col="x", y_col="y", graph_name="G1")

    assert result["x_col"] == "x"
    assert result["y_col"] == "y"
    assert len(page[0].plots) == 1


def test_add_uncertainty_band_adds_bounds_and_fill(fake_client: OriginClient) -> None:
    fake_client.op.add_book(
        "Data",
        pd.DataFrame({"x": [1, 2], "lower": [2, 3], "upper": [4, 5]}),
    )
    page = fake_client.op.add_graph("G1")

    result = fake_client.add_uncertainty_band(
        worksheet="Data",
        x_col="x",
        lower_col="lower",
        upper_col="upper",
        graph_name="G1",
        fill_color="lightblue",
        transparency=70,
    )

    assert result["lower_col"] == "lower"
    assert result["upper_col"] == "upper"
    assert result["plot_indices"] == [0]
    assert "plotxy iy:=[Data]Sheet1!(1,2,3) plot:=249 ogl:=[G1]1;" == result["plot_script"]
    assert "layer -s 1;" in result["fill_script"]
    assert "set __origin_mcp_band_plot -pf 1;" in result["fill_script"]
    assert "set __origin_mcp_band_plot -pfv 9;" in result["fill_script"]
    assert "set __origin_mcp_band_plot -paap 70;" in result["fill_script"]
    assert len(page[0].plots) == 0
    scripts = [call[1][0] for call in _lt_exec_calls(fake_client)]
    assert scripts[0] == "plotxy iy:=[Data]Sheet1!(1,2,3) plot:=249 ogl:=[G1]1;"
    assert "set __origin_mcp_band_plot -paap 70;" in scripts[1]


def test_arrange_layers_applies_custom_geometry(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1", layers=2)

    result = fake_client.arrange_layers(
        graph_name="G1",
        rows=1,
        columns=2,
        gap_x=4,
        gap_y=6,
        layer_geometries=[
            {"layer_index": 0, "left": 10, "top": 12, "width": 40, "height": 80},
            {"layer_index": 1, "left": 55, "top": 12, "width": 35, "height": 80},
        ],
    )

    assert result["rows"] == 1
    assert result["columns"] == 2
    assert result["layer_geometries"][1]["left"] == 55
    scripts = [call[1][0] for call in _lt_exec_calls(fake_client)]
    assert scripts[0] == "layarrange row:=1 col:=2 xgap:=4 ygap:=6;"
    assert "layer -s 1; layer.left=10.0; layer.top=12.0;" in scripts[1]
    assert "layer -s 2; layer.left=55.0; layer.top=12.0;" in scripts[1]


def test_merge_graphs_builds_publication_panel_command(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")
    fake_client.op.add_graph("G2")
    fake_client.op.add_graph("G3")

    result = fake_client.merge_graphs(
        ["G1", "G2", "G3"],
        output_name="Figure1",
        rows=1,
        columns=3,
        label_style="capitalA",
        common_x_scale=True,
    )

    assert result["output_graph"] == "Figure1"
    assert 'graphs:="G1"+char(10)$+"G2"+char(10)$+"G3"' in result["script"]
    assert "row:=1 col:=3" in result["script"]
    assert "labeltext:=capitalA" in result["script"]
    assert "resizewidthbyscale:=1" in result["script"]
    assert "resizeheightbyscale" not in result["script"]
    assert "ogp:=" not in result["script"]


def test_merge_graphs_requires_2026b_for_common_y_scale(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")
    fake_client.op.add_graph("G2")

    with pytest.raises(OriginOperationError) as excinfo:
        fake_client.merge_graphs(["G1", "G2"], common_y_scale=True)

    assert excinfo.value.error_code == "unsupported_origin_feature"


def test_graph_layout_and_layer_relationship_commands(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1", layers=3)
    fake_client.op.add_graph("G2")

    layout = fake_client.create_graph_layout(["G1", "G2"], rows=1, columns=2)
    linked = fake_client.link_graph_layers(
        "G1", source_layer=0, destination_layers=[1, 2], link_x=True, link_y=False
    )
    copied = fake_client.copy_layer_scale("G1", 0, [1, 2], axis=1)
    extracted = fake_client.extract_graph_layers("G1", [0, 2])

    assert "g2layout option:=specified" in layout["script"]
    assert 'destlayers:="2:3"' in linked["script"]
    assert "XAxis:=1 YAxis:=0" in linked["script"]
    assert "igl:=1 dest:=2:3 axis:=1" in copied["script"]
    assert 'layer:="1,3"' in extracted["script"]


def test_graph_layer_relationships_validate_indexes(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1", layers=2)

    with pytest.raises(OriginOperationError):
        fake_client.link_graph_layers("G1", source_layer=0, destination_layers=[2])


def test_get_graph_info_reports_layers_and_plots(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
    fake_client.op.add_graph("G1", lname="Long")
    fake_client.add_plot_to_graph(worksheet="Data", x_col="x", y_col="y", graph_name="G1")

    info = fake_client.get_graph_info(graph_name="G1")

    assert info["long_name"] == "Long"
    assert info["layers_count"] == 1
    assert info["layers"][0]["plots_count"] == 1


def test_get_layer_info(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")

    info = fake_client.get_layer_info(graph_name="G1", layer_index=0)

    assert info["layer"]["index"] == 0
    assert "axes" in info["layer"]


def test_change_plot_type_issues_command(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
    page = fake_client.op.add_graph("G1")
    fake_client.add_plot_to_graph(worksheet="Data", x_col="x", y_col="y", graph_name="G1")

    result = fake_client.change_plot_type(plot_index=0, plot_type="s", graph_name="G1")

    assert result["plot_type"] == "s"
    assert "-c s" in page[0].plots[0].commands


def test_change_plot_type_out_of_range(fake_client: OriginClient) -> None:
    fake_client.op.add_graph("G1")
    with pytest.raises(OriginOperationError):
        fake_client.change_plot_type(plot_index=5, plot_type="s", graph_name="G1")


def test_remove_plot_from_graph(fake_client: OriginClient) -> None:
    fake_client.op.add_book("Data", pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
    fake_client.op.add_graph("G1")
    fake_client.add_plot_to_graph(worksheet="Data", x_col="x", y_col="y", graph_name="G1")

    result = fake_client.remove_plot_from_graph(plot_index=0, graph_name="G1")

    assert result["removed_plot_index"] == 0
