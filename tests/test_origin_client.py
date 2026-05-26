from pathlib import Path

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_read_table_csv(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("time,value\n0,1\n1,2\n", encoding="utf-8")

    df = OriginClient._read_table(path)

    assert list(df.columns) == ["time", "value"]
    assert df["value"].tolist() == [1, 2]


def test_read_table_tsv(tmp_path: Path) -> None:
    path = tmp_path / "data.tsv"
    path.write_text("time\tvalue\n0\t1\n1\t2\n", encoding="utf-8")

    df = OriginClient._read_table(path)

    assert list(df.columns) == ["time", "value"]
    assert df["time"].tolist() == [0, 1]


def test_read_table_excel(tmp_path: Path) -> None:
    path = tmp_path / "data.xlsx"
    expected = pd.DataFrame({"time": [0, 1], "value": [1.5, 2.5]})
    expected.to_excel(path, index=False, sheet_name="Run1")

    df = OriginClient._read_table(path, excel_sheet="Run1")

    assert list(df.columns) == ["time", "value"]
    assert df["value"].tolist() == [1.5, 2.5]


def test_read_table_rejects_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(OriginOperationError):
        OriginClient._read_table(path)
