from __future__ import annotations

from pathlib import Path

import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_matrix_create_read_write_and_properties(fake_client: OriginClient) -> None:
    created = fake_client.create_matrix(
        data=[[1, 2, 3], [4, 5, 6]],
        book_name="MData",
        sheet_name="Values",
        xymap=(10, 20, -1, 1),
        labels=["Signal"],
    )

    assert created["shape"] == [2, 3]
    assert created["depth"] == 1
    assert created["xymap"] == [10.0, 20.0, -1.0, 1.0]
    assert created["data_ranges"] == ["[MData]Values!1"]

    window = fake_client.read_matrix(
        book_name="MData",
        sheet_name="Values",
        start_col=1,
        max_rows=2,
        max_cols=2,
    )
    assert window["data"] == [[2, 3], [5, 6]]

    written = fake_client.write_matrix(
        data=[[9, 8, 7], [6, 5, 4]],
        book_name="MData",
        sheet_name="Values",
        object_index=0,
    )
    assert written["shape"] == [2, 3]

    properties = fake_client.set_matrix_properties(
        book_name="MData",
        sheet_name="Values",
        show_image=True,
        show_thumbnails=True,
        show_slider=True,
    )
    assert properties["applied"]["show_image"] is True


def test_matrix_3d_depth_and_transform(fake_client: OriginClient) -> None:
    created = fake_client.create_matrix(
        data=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
        book_name="Stack",
    )
    assert created["depth"] == 2

    transformed = fake_client.transform_matrix("transpose", book_name="Stack")
    assert transformed["matrix"]["shape"] == [2, 2]
    second = fake_client.read_matrix(book_name="Stack", object_index=1)
    assert second["data"] == [[5, 7], [6, 8]]


def test_matrix_read_is_bounded(fake_client: OriginClient) -> None:
    fake_client.create_matrix(rows=2, cols=2, book_name="M")
    with pytest.raises(OriginOperationError):
        fake_client.read_matrix(book_name="M", max_rows=1000, max_cols=1000)


def test_image_import_read_process_and_convert(fake_client: OriginClient, tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    source.write_bytes(b"fake")

    imported = fake_client.import_image(str(source), image_name="Microscopy")
    assert imported["size"] == [2, 2]
    assert imported["channels"] == 3

    read = fake_client.read_image("Microscopy")
    assert read["shape"] == [2, 2, 3]

    processed = fake_client.process_image("grayscale", "Microscopy")
    assert processed["image"]["channels"] == 1

    matrix = fake_client.image_to_matrix("Microscopy", book_name="ImageMatrix", sheet_name="Pixels")
    assert matrix["shape"] == [2, 2]


def test_create_multiframe_image(fake_client: OriginClient) -> None:
    created = fake_client.create_image(
        data=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
        image_name="Stack",
        multiframe=True,
    )
    assert created["frames"] == 2

    frame = fake_client.read_image("Stack", frame=1)
    assert frame["data"] == [[5, 6], [7, 8]]
