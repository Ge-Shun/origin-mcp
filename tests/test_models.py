from pathlib import Path

import pytest
from pydantic import ValidationError

from origin_mcp.models import PlotTableRequest, TableImportRequest


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
