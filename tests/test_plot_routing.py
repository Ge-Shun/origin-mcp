"""Behavioural tests for chart routing and range/template plotting."""

from __future__ import annotations

from pathlib import Path

import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def _xy_csv(tmp_path: Path) -> Path:
    path = tmp_path / "data.csv"
    path.write_text("x,y1,y2\n1,4,9\n2,5,8\n3,6,7\n", encoding="utf-8")
    return path


# -- recommend_chart / chart_atlas_route (pure routing) -------------------


def test_recommend_chart_returns_selection(fake_client: OriginClient, tmp_path: Path) -> None:
    result = fake_client.recommend_chart(path=_xy_csv(tmp_path))

    assert "selected" in result
    assert "candidates" in result
    assert result["candidates"]


def test_recommend_chart_rejects_empty(fake_client: OriginClient, tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("x,y\n", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.recommend_chart(path=empty)


def test_chart_atlas_route_resolves_intent(fake_client: OriginClient) -> None:
    route = fake_client.chart_atlas_route(intent="correlation", columns=["x", "y"])

    assert route["intent"]
    assert route["input_columns"] == ["x", "y"]


def test_chart_atlas_route_warns_on_matrix_misroute(fake_client: OriginClient) -> None:
    route = fake_client.chart_atlas_route(intent="correlation", columns=["x"], matrix=True)

    assert route.get("warnings")


# -- plot_range / batch ---------------------------------------------------


def test_plot_range_creates_plot(fake_client: OriginClient) -> None:
    graph = fake_client.plot_range(
        data_range="[Book1]Sheet1!(1,2)", template="line", graph_name="R1", title="T"
    )

    assert graph.graph_name
    page = fake_client.op.graphs[-1]
    assert len(page[0].plots) == 1


def test_plot_range_rejects_empty_range(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.plot_range(data_range="   ")


def test_batch_plot_from_template(fake_client: OriginClient, tmp_path: Path) -> None:
    result = fake_client.batch_plot_from_template(
        data_ranges=["[Book1]Sheet1!(1,2)", "[Book1]Sheet1!(1,3)"],
        template="line",
        output_dir=tmp_path,
    )

    assert result["count"] == 2
    assert all(Path(g["export_path"]).exists() for g in result["graphs"])


# -- list_graph_templates -------------------------------------------------


def test_list_graph_templates_builtin(fake_client: OriginClient) -> None:
    result = fake_client.list_graph_templates()

    assert "line" in result["builtin"]
    assert "ternary" in result["builtin"]
    assert result["discovered"] == []


def test_list_graph_templates_discovers_files(fake_client: OriginClient, tmp_path: Path) -> None:
    (tmp_path / "custom.otp").write_bytes(b"tmpl")
    (tmp_path / "ignored.txt").write_text("x", encoding="utf-8")

    result = fake_client.list_graph_templates(template_dir=tmp_path)

    names = {entry["name"] for entry in result["discovered"]}
    assert names == {"custom"}


def test_list_graph_templates_missing_dir(fake_client: OriginClient, tmp_path: Path) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.list_graph_templates(template_dir=tmp_path / "nope")


# -- plot_table_by_id (plotxy route) -------------------------------------


def test_plot_table_by_id_plotxy_route(fake_client: OriginClient, tmp_path: Path) -> None:
    worksheet, graph, command = fake_client.plot_table_by_id(
        path=_xy_csv(tmp_path),
        plot_type_id=200,
        template="line",
        selected_cols=["x", "y1"],
        graph_name="ById",
    )

    assert worksheet.columns == ["x", "y1", "y2"]
    assert command["command"] == "plotxy"
    assert command["plot_type_id"] == 200
    assert graph.template == "line"
