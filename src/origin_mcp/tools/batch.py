from __future__ import annotations

from pathlib import Path
from typing import Any

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_save_analysis_template(
    path: str,
    book_name: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Save an active workbook's recalculating operations as an OGW(U) template."""

    return _wrap(
        lambda: _ok(
            "Saved Origin analysis template.",
            **client.save_analysis_template(
                Path(path),
                book_name=book_name,
                overwrite=overwrite,
            ),
        )
    )


@_mcp_tool()
def origin_open_analysis_template(path: str) -> dict[str, Any]:
    """Open an OGW/OGWU analysis template while preserving its operations."""

    return _wrap(
        lambda: _ok(
            "Opened Origin analysis template.",
            **client.open_analysis_template(Path(path)),
        )
    )


@_mcp_tool()
def origin_batch_process(
    source_type: str = "files",
    files: list[str] | None = None,
    folder: str | None = None,
    extensions: str = "*.*",
    input_range: str | None = None,
    fixed_range: str | None = None,
    batch_range: str | None = None,
    worksheets: str | None = None,
    analysis_template: str | None = None,
    mode: str = "template",
    data_sheet: str | None = None,
    result_sheet: str | None = None,
    output_sheet: str | None = None,
    dataset_identifier: str = "File Name",
    import_method: str = "impASC",
    theme: str | None = None,
    import_filter: str | None = None,
    import_script: str | None = None,
    remove_intermediate: bool = True,
    clear_output: bool = True,
    append_mode: str = "rows",
    before_script: str | None = None,
    loop_script: str | None = None,
    end_script: str | None = None,
) -> dict[str, Any]:
    """Run Origin batchprocess with an analysis template or active workbook.

    source_type supports files, folder, existing_xy, existing_xyz,
    existing_worksheets, and existing_ranges. For existing ranges, pass Origin
    range syntax through input_range, worksheets, fixed_range, or batch_range.
    """

    return _wrap(
        lambda: _ok(
            "Completed Origin batch processing.",
            **client.batch_process(
                source_type=source_type,
                files=files,
                folder=folder,
                extensions=extensions,
                input_range=input_range,
                fixed_range=fixed_range,
                batch_range=batch_range,
                worksheets=worksheets,
                analysis_template=analysis_template,
                mode=mode,
                data_sheet=data_sheet,
                result_sheet=result_sheet,
                output_sheet=output_sheet,
                dataset_identifier=dataset_identifier,
                import_method=import_method,
                theme=theme,
                import_filter=import_filter,
                import_script=import_script,
                remove_intermediate=remove_intermediate,
                clear_output=clear_output,
                append_mode=append_mode,
                before_script=before_script,
                loop_script=loop_script,
                end_script=end_script,
            ),
        )
    )


@_mcp_tool()
def origin_clone_import(
    files: list[str],
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Clone an analyzed workbook and import each similarly structured file."""

    return _wrap(
        lambda: _ok(
            "Completed Origin clone import.",
            **client.clone_import(
                files=files,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )
