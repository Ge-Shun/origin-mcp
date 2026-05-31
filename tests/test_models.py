from pathlib import Path

import pytest
from pydantic import ValidationError

from origin_mcp.models import FigureSpec, PlotTableRequest, TableImportRequest


def test_table_import_request_accepts_supported_files(tmp_path: Path) -> None:
    path = tmp_path / "data.xlsx"
    path.write_text("placeholder", encoding="utf-8")

    req = TableImportRequest(path=path, excel_sheet="Run1")

    assert req.path == path
    assert req.excel_sheet == "Run1"


def test_table_import_request_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        TableImportRequest(path=tmp_path / "missing.csv")


def test_plot_table_request_defaults(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")

    req = PlotTableRequest(path=path)

    assert req.x_col is None
    assert req.y_cols is None
    assert req.show_legend is True


def test_figurespec_validates_references(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("time,response\n1,2\n", encoding="utf-8")

    spec = FigureSpec.model_validate(
        {
            "figure": {"id": "fig1"},
            "data": [{"id": "ds1", "source": str(path), "roles": {"x": "time", "y": "response"}}],
            "layers": [{"id": "panel_a", "data_ref": "ds1"}],
            "plots": [
                {
                    "id": "plot_a",
                    "layer": "panel_a",
                    "type": "line",
                    "map": {"x": "time", "y": "response"},
                }
            ],
        }
    )

    assert spec.figure.id == "fig1"
    assert spec.data[0].roles["x"] == "time"


def test_figurespec_rejects_unknown_plot_layer(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        FigureSpec.model_validate(
            {
                "figure": {"id": "fig1"},
                "data": [{"id": "ds1", "source": str(path)}],
                "layers": [{"id": "panel_a"}],
                "plots": [{"id": "plot_a", "layer": "missing", "type": "line"}],
            }
        )
