from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_save_and_open_analysis_template(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_book("Analysis", pd.DataFrame({"x": [1], "y": [2]}))
    target = tmp_path / "analysis"

    saved = fake_client.save_analysis_template(target, book_name="Analysis")

    assert saved["saved"] is True
    assert Path(saved["path"]).suffix == ".ogwu"
    assert Path(saved["path"]).exists()

    opened = fake_client.open_analysis_template(Path(saved["path"]))
    assert opened["opened"] is True


def test_batch_process_files_builds_official_xfunction_call(
    fake_client: OriginClient, tmp_path: Path
) -> None:
    template = tmp_path / "analysis.ogwu"
    template.write_text("template", encoding="utf-8")
    first = tmp_path / "one.csv"
    second = tmp_path / "two.csv"
    first.write_text("x,y\n1,2\n", encoding="utf-8")
    second.write_text("x,y\n3,4\n", encoding="utf-8")

    result = fake_client.batch_process(
        source_type="files",
        files=[first, second],
        analysis_template=template,
        data_sheet="Data",
        result_sheet="Summary",
        output_sheet="[Batch]Results!",
        import_method="impCSV",
        append_mode="columns",
        before_script="_skip=0",
    )

    assert result["source_type"] == "files"
    assert result["files"] == [str(first.resolve()), str(second.resolve())]
    assert result["script"].startswith("batchprocess batch:=template data:=import")
    assert 'method:="impCSV"' in result["script"]
    assert "mode:=1" in result["script"]
    assert fake_client.op.lt_values["fname"] == ""
    set_calls = [args for name, args in fake_client.op.calls if name == "set_lt_str"]
    assert set_calls == [
        ("fname", f"{first.resolve()}\r\n{second.resolve()}"),
        ("fname", ""),
    ]


def test_batch_process_folder_and_existing_ranges(
    fake_client: OriginClient, tmp_path: Path
) -> None:
    template = tmp_path / "analysis.ogw"
    template.write_text("template", encoding="utf-8")

    folder_result = fake_client.batch_process(
        source_type="folder",
        folder=tmp_path,
        extensions="*.csv;*.dat",
        analysis_template=template,
    )
    assert "data:=folder" in folder_result["script"]

    range_result = fake_client.batch_process(
        source_type="existing_ranges",
        batch_range="[Book1]Sheet1!(1,2)",
        fixed_range="[Book1]Sheet1!3",
        mode="active",
    )
    assert "data:=existingRange" in range_result["script"]
    assert "irngb:=[Book1]Sheet1!(1,2)" in range_result["script"]


def test_clone_import_uses_source_worksheet(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.add_book("Analyzed", pd.DataFrame({"x": [1], "y": [2]}))
    source = tmp_path / "next.csv"
    source.write_text("x,y\n3,4\n", encoding="utf-8")

    result = fake_client.clone_import([source], book_name="Analyzed")

    assert result["source_range"] == "[Analyzed]Sheet1!"
    assert "cloneimport orng:=[Analyzed]Sheet1!;" in result["script"]


def test_batch_process_validates_controlled_arguments(
    fake_client: OriginClient, tmp_path: Path
) -> None:
    template = tmp_path / "analysis.ogwu"
    template.write_text("template", encoding="utf-8")

    with pytest.raises(OriginOperationError):
        fake_client.batch_process(
            source_type="existing_xy",
            input_range="[Book]Sheet!1; delete -all",
            analysis_template=template,
        )

    with pytest.raises(OriginOperationError):
        fake_client.batch_process(
            source_type="files",
            files=[template],
            analysis_template=template,
            import_method="impCSV; exit",
        )
