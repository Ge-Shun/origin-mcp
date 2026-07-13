from __future__ import annotations

from typing import Any

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_create_matrix(
    data: list[Any] | None = None,
    rows: int = 10,
    cols: int = 10,
    fill_value: float = 0.0,
    formula: str | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
    dstack: bool = False,
    missing_value: float | int | None = None,
    xymap: tuple[float, float, float, float] | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create an Origin matrix from 2D/3D data or a filled shape.

    xymap is (x_min, x_max, y_min, y_max). A 3D array creates multiple
    MatrixObjects; set dstack when its layout is rows, columns, depth.
    formula can fill cells with an Origin matrix expression using X, Y, i, j.
    """

    return _wrap(
        lambda: _ok(
            "Created Origin matrix.",
            matrix=client.create_matrix(
                data=data,
                rows=rows,
                cols=cols,
                fill_value=fill_value,
                formula=formula,
                book_name=book_name,
                sheet_name=sheet_name,
                dstack=dstack,
                missing_value=missing_value,
                xymap=xymap,
                labels=labels,
            ),
        )
    )


@_mcp_tool()
def origin_get_matrix_info(
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Inspect matrix shape, object depth, XY mapping, labels, and data ranges."""

    return _wrap(
        lambda: _ok(
            "Inspected Origin matrix.",
            matrix=client.matrix_info(book_name=book_name, sheet_name=sheet_name),
        )
    )


@_mcp_tool()
def origin_read_matrix(
    book_name: str | None = None,
    sheet_name: str | None = None,
    object_index: int = 0,
    start_row: int = 0,
    start_col: int = 0,
    max_rows: int = 100,
    max_cols: int = 100,
) -> dict[str, Any]:
    """Read a bounded 2D window from one MatrixObject."""

    return _wrap(
        lambda: _ok(
            "Read Origin matrix data.",
            **client.read_matrix(
                book_name=book_name,
                sheet_name=sheet_name,
                object_index=object_index,
                start_row=start_row,
                start_col=start_col,
                max_rows=max_rows,
                max_cols=max_cols,
            ),
        )
    )


@_mcp_tool()
def origin_write_matrix(
    data: list[Any],
    book_name: str | None = None,
    sheet_name: str | None = None,
    object_index: int | None = None,
    dstack: bool = False,
    missing_value: float | int | None = None,
) -> dict[str, Any]:
    """Replace a matrix sheet or update one MatrixObject with numeric data."""

    return _wrap(
        lambda: _ok(
            "Wrote Origin matrix data.",
            matrix=client.write_matrix(
                data=data,
                book_name=book_name,
                sheet_name=sheet_name,
                object_index=object_index,
                dstack=dstack,
                missing_value=missing_value,
            ),
        )
    )


@_mcp_tool()
def origin_set_matrix_properties(
    book_name: str | None = None,
    sheet_name: str | None = None,
    xymap: tuple[float, float, float, float] | None = None,
    labels: list[str] | None = None,
    show_image: bool | None = None,
    show_thumbnails: bool | None = None,
    show_slider: bool | None = None,
) -> dict[str, Any]:
    """Set matrix coordinate mapping, object labels, and image-view controls."""

    return _wrap(
        lambda: _ok(
            "Updated Origin matrix properties.",
            **client.set_matrix_properties(
                book_name=book_name,
                sheet_name=sheet_name,
                xymap=xymap,
                labels=labels,
                show_image=show_image,
                show_thumbnails=show_thumbnails,
                show_slider=show_slider,
            ),
        )
    )


@_mcp_tool()
def origin_transform_matrix(
    operation: str,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Transpose, rotate 90 degrees, or flip an Origin matrix."""

    return _wrap(
        lambda: _ok(
            "Transformed Origin matrix.",
            **client.transform_matrix(
                operation=operation,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )


@_mcp_tool()
def origin_import_image(source: str, image_name: str | None = None) -> dict[str, Any]:
    """Import a local image, URL, wildcard stack, or multipage image into Origin."""

    return _wrap(
        lambda: _ok(
            "Imported Origin image.",
            image=client.import_image(source=source, image_name=image_name),
        )
    )


@_mcp_tool()
def origin_create_image(
    data: list[Any],
    image_name: str | None = None,
    channels: int = 1,
    multiframe: bool = False,
    channel_type: int = -1,
    dstack: bool = False,
) -> dict[str, Any]:
    """Create an Origin image or image stack from numeric array data."""

    return _wrap(
        lambda: _ok(
            "Created Origin image.",
            image=client.create_image(
                data=data,
                image_name=image_name,
                channels=channels,
                multiframe=multiframe,
                channel_type=channel_type,
                dstack=dstack,
            ),
        )
    )


@_mcp_tool()
def origin_get_image_info(image_name: str | None = None) -> dict[str, Any]:
    """Inspect an Origin image's size, channels, frames, and media type."""

    return _wrap(
        lambda: _ok("Inspected Origin image.", image=client.image_info(image_name=image_name))
    )


@_mcp_tool()
def origin_read_image(
    image_name: str | None = None,
    frame: int | None = None,
    max_values: int = 1_000_000,
) -> dict[str, Any]:
    """Read an Origin image or one image-stack frame into a bounded array result."""

    return _wrap(
        lambda: _ok(
            "Read Origin image data.",
            **client.read_image(
                image_name=image_name,
                frame=frame,
                max_values=max_values,
            ),
        )
    )


@_mcp_tool()
def origin_process_image(operation: str, image_name: str | None = None) -> dict[str, Any]:
    """Convert to grayscale, split RGB channels, or merge image frames."""

    return _wrap(
        lambda: _ok(
            "Processed Origin image.",
            **client.process_image(operation=operation, image_name=image_name),
        )
    )


@_mcp_tool()
def origin_image_to_matrix(
    image_name: str | None = None,
    book_name: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Convert an Origin image window into a new matrix sheet."""

    return _wrap(
        lambda: _ok(
            "Converted Origin image to matrix.",
            matrix=client.image_to_matrix(
                image_name=image_name,
                book_name=book_name,
                sheet_name=sheet_name,
            ),
        )
    )
