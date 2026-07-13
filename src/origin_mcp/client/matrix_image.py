from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..errors import OriginDependencyError, OriginOperationError
from .base import _OriginClientBase

MAX_MATRIX_READ_CELLS = 100_000
MAX_IMAGE_READ_VALUES = 1_000_000


class _MatrixImageMixin(_OriginClientBase):
    """Origin matrix-book and image-window object operations."""

    def create_matrix(
        self,
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
        np = self._numpy()
        if data is None:
            if rows < 1 or cols < 1:
                raise OriginOperationError(
                    "rows and cols must be positive.", error_code="invalid_request"
                )
            array = np.full((rows, cols), fill_value, dtype=float)
        else:
            array = np.asarray(data)
            if array.ndim not in {2, 3} or 0 in array.shape:
                raise OriginOperationError(
                    "Matrix data must be a non-empty 2D or 3D array.",
                    error_code="invalid_request",
                )
        msheet = self._new_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        self._matrix_from_array(
            msheet,
            array,
            dstack=dstack,
            missing_value=missing_value,
        )
        if xymap is not None:
            self._set_matrix_xymap(msheet, xymap)
        if labels is not None:
            self._set_matrix_labels(msheet, labels)
        if formula is not None:
            if not formula.strip():
                raise OriginOperationError("formula is empty.", error_code="invalid_request")
            self._execute_on_matrix(msheet, f"matrix -v {formula};")
        return self._matrix_info_for_sheet(msheet)

    def matrix_info(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        return self._matrix_info_for_sheet(
            self._find_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        )

    def read_matrix(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        object_index: int = 0,
        start_row: int = 0,
        start_col: int = 0,
        max_rows: int = 100,
        max_cols: int = 100,
    ) -> dict[str, Any]:
        if min(object_index, start_row, start_col) < 0 or max_rows < 1 or max_cols < 1:
            raise OriginOperationError(
                "Indexes must be non-negative and read sizes must be positive.",
                error_code="invalid_request",
            )
        if max_rows * max_cols > MAX_MATRIX_READ_CELLS:
            raise OriginOperationError(
                f"A matrix read cannot exceed {MAX_MATRIX_READ_CELLS} cells.",
                error_code="invalid_request",
            )
        msheet = self._find_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        array = self._matrix_object_array(msheet, object_index)
        row_end = min(array.shape[0], start_row + max_rows)
        col_end = min(array.shape[1], start_col + max_cols)
        window = array[start_row:row_end, start_col:col_end]
        return {
            "matrix": self._matrix_info_for_sheet(msheet),
            "object_index": object_index,
            "start_row": start_row,
            "start_col": start_col,
            "returned_shape": list(window.shape),
            "data": window.tolist(),
        }

    def write_matrix(
        self,
        data: list[Any],
        book_name: str | None = None,
        sheet_name: str | None = None,
        object_index: int | None = None,
        dstack: bool = False,
        missing_value: float | int | None = None,
    ) -> dict[str, Any]:
        np = self._numpy()
        array = np.asarray(data)
        if array.ndim not in {2, 3} or 0 in array.shape:
            raise OriginOperationError(
                "Matrix data must be a non-empty 2D or 3D array.",
                error_code="invalid_request",
            )
        msheet = self._find_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        if object_index is None:
            self._matrix_from_array(
                msheet,
                array,
                dstack=dstack,
                missing_value=missing_value,
            )
        else:
            if object_index < 0 or array.ndim != 2:
                raise OriginOperationError(
                    "object_index requires a non-negative index and 2D data.",
                    error_code="invalid_request",
                )
            existing_shape = tuple(
                self._call_or_value(msheet, "shape", default=array.shape) or array.shape
            )
            if tuple(array.shape) != existing_shape:
                raise OriginOperationError(
                    "A single MatrixObject update must match the matrix sheet shape "
                    f"{existing_shape}; received {tuple(array.shape)}.",
                    error_code="invalid_request",
                )
            writer = getattr(msheet, "from_np2d", None)
            if not callable(writer):
                raise OriginOperationError("Matrix sheet does not support from_np2d().")
            result = writer(array, object_index)
            if result is False:
                raise OriginOperationError("Origin rejected the MatrixObject update.")
        return self._matrix_info_for_sheet(msheet)

    def set_matrix_properties(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        xymap: tuple[float, float, float, float] | None = None,
        labels: list[str] | None = None,
        show_image: bool | None = None,
        show_thumbnails: bool | None = None,
        show_slider: bool | None = None,
    ) -> dict[str, Any]:
        msheet = self._find_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        applied: dict[str, Any] = {}
        if xymap is not None:
            self._set_matrix_xymap(msheet, xymap)
            applied["xymap"] = list(xymap)
        if labels is not None:
            self._set_matrix_labels(msheet, labels)
            applied["labels"] = labels
        for name, value in (
            ("show_image", show_image),
            ("show_thumbnails", show_thumbnails),
            ("show_slider", show_slider),
        ):
            if value is None:
                continue
            setter = getattr(msheet, name, None)
            if not callable(setter):
                raise OriginOperationError(f"Matrix sheet does not support {name}().")
            setter(bool(value))
            applied[name] = bool(value)
        return {"matrix": self._matrix_info_for_sheet(msheet), "applied": applied}

    def transform_matrix(
        self,
        operation: str,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        operation_key = operation.strip().lower().replace("-", "_")
        scripts = {
            "transpose": "matrix -t;",
            "rotate_90": "matrix -c r;",
            "rotate": "matrix -c r;",
            "flip_horizontal": "matrix -c h;",
            "flip_vertical": "matrix -c v;",
        }
        if operation_key not in scripts:
            raise OriginOperationError(
                "operation must be transpose, rotate_90, flip_horizontal, or flip_vertical.",
                error_code="invalid_request",
            )
        msheet = self._find_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        self._execute_on_matrix(msheet, scripts[operation_key])
        return {
            "matrix": self._matrix_info_for_sheet(msheet),
            "operation": operation_key,
        }

    def import_image(
        self,
        source: str,
        image_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_source = self._normalize_image_source(source)
        new_image = getattr(self.op, "new_image", None)
        if not callable(new_image):
            raise OriginOperationError(
                "originpro.new_image is not available.",
                error_code="unsupported_origin_feature",
            )
        try:
            image = new_image(image_name or "")
        except TypeError:
            image = new_image()
        if image_name:
            self._set_object_name(image, image_name)
        loader = getattr(image, "from_file", None)
        if not callable(loader):
            raise OriginOperationError("Image page does not support from_file().")
        result = loader(normalized_source)
        if result is False:
            raise OriginOperationError("Origin could not import the image source.")
        return self._image_info_for_page(image)

    def create_image(
        self,
        data: list[Any],
        image_name: str | None = None,
        channels: int = 1,
        multiframe: bool = False,
        channel_type: int = -1,
        dstack: bool = False,
    ) -> dict[str, Any]:
        if channels not in {1, 3, 4}:
            raise OriginOperationError("channels must be 1, 3, or 4.", error_code="invalid_request")
        array = self._numpy().asarray(data)
        if array.ndim not in {2, 3, 4} or 0 in array.shape:
            raise OriginOperationError(
                "Image data must be a non-empty 2D, 3D, or 4D array.",
                error_code="invalid_request",
            )
        new_image = getattr(self.op, "new_image", None)
        if not callable(new_image):
            raise OriginOperationError("originpro.new_image is not available.")
        image = new_image()
        if image_name:
            self._set_object_name(image, image_name)
        setup = getattr(image, "setup", None)
        writer = getattr(image, "from_np", None)
        if not callable(setup) or not callable(writer):
            raise OriginOperationError("Image page does not support setup()/from_np().")
        if setup(channels, multiframe, channel_type) is False:
            raise OriginOperationError("Origin rejected the image setup.")
        writer(array, dstack)
        return self._image_info_for_page(image)

    def image_info(self, image_name: str | None = None) -> dict[str, Any]:
        return self._image_info_for_page(self._find_image(image_name))

    def read_image(
        self,
        image_name: str | None = None,
        frame: int | None = None,
        max_values: int = MAX_IMAGE_READ_VALUES,
    ) -> dict[str, Any]:
        if max_values < 1 or max_values > MAX_IMAGE_READ_VALUES:
            raise OriginOperationError(
                f"max_values must be between 1 and {MAX_IMAGE_READ_VALUES}.",
                error_code="invalid_request",
            )
        image = self._find_image(image_name)
        if frame is None:
            reader = getattr(image, "to_np", None)
            args: tuple[Any, ...] = ()
        else:
            if frame < 0:
                raise OriginOperationError("frame must be non-negative.")
            reader = getattr(image, "to_np2d", None)
            args = (frame,)
        if not callable(reader):
            raise OriginOperationError("Image page does not support the requested read method.")
        array = reader(*args)
        if array is None:
            raise OriginOperationError("Origin returned no image data.")
        np_array = self._numpy().asarray(array)
        if int(np_array.size) > max_values:
            raise OriginOperationError(
                f"Image contains {np_array.size} values; max_values is {max_values}.",
                error_code="result_too_large",
            )
        return {
            "image": self._image_info_for_page(image),
            "frame": frame,
            "shape": list(np_array.shape),
            "data": np_array.tolist(),
        }

    def process_image(
        self,
        operation: str,
        image_name: str | None = None,
    ) -> dict[str, Any]:
        operation_key = operation.strip().lower().replace("-", "_")
        methods = {
            "grayscale": "rgb2gray",
            "rgb2gray": "rgb2gray",
            "split": "split",
            "merge": "merge",
        }
        if operation_key not in methods:
            raise OriginOperationError(
                "operation must be grayscale, split, or merge.", error_code="invalid_request"
            )
        image = self._find_image(image_name)
        method = getattr(image, methods[operation_key], None)
        if not callable(method):
            raise OriginOperationError(f"Image page does not support {methods[operation_key]}().")
        result = method()
        if result is False:
            raise OriginOperationError(f"Origin rejected image operation {operation_key!r}.")
        return {"image": self._image_info_for_page(image), "operation": operation_key}

    def image_to_matrix(
        self,
        image_name: str | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        image = self._find_image(image_name)
        msheet = self._new_matrix_sheet(book_name=book_name, sheet_name=sheet_name)
        converter = getattr(msheet, "from_img", None)
        if not callable(converter):
            raise OriginOperationError("Matrix sheet does not support from_img().")
        converter(image)
        return self._matrix_info_for_sheet(msheet)

    @staticmethod
    def _numpy() -> Any:
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - numpy ships with Origin
            raise OriginDependencyError("numpy is required for matrix/image operations.") from exc
        return np

    def _new_matrix_sheet(self, book_name: str | None, sheet_name: str | None) -> Any:
        new_sheet = getattr(self.op, "new_sheet", None)
        if not callable(new_sheet):
            raise OriginOperationError("originpro.new_sheet is not available.")
        try:
            msheet = new_sheet("m", book_name or "")
        except TypeError:
            msheet = new_sheet("m")
        if book_name:
            try:
                msheet.get_book().lname = book_name
            except Exception:
                pass
        if sheet_name:
            self._set_object_name(msheet, sheet_name)
        return msheet

    def _find_matrix_sheet(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> Any:
        finder = getattr(self.op, "find_sheet", None)
        if not callable(finder):
            raise OriginOperationError("originpro.find_sheet is not available.")
        ref = (
            f"[{book_name}]{sheet_name}"
            if book_name and sheet_name
            else book_name or sheet_name or ""
        )
        msheet = finder("m", ref)
        if msheet is None:
            raise OriginOperationError(
                f"Matrix sheet not found: {ref or '<active matrix>'}",
                error_code="matrix_not_found",
            )
        return msheet

    def _matrix_from_array(
        self,
        msheet: Any,
        array: Any,
        *,
        dstack: bool,
        missing_value: float | int | None,
    ) -> None:
        writer = getattr(msheet, "from_np", None)
        if not callable(writer):
            raise OriginOperationError("Matrix sheet does not support from_np().")
        try:
            writer(array, dstack, missing_value)
        except TypeError:
            writer(array, dstack=dstack, mv=missing_value)

    @staticmethod
    def _matrix_object_array(msheet: Any, object_index: int) -> Any:
        reader = getattr(msheet, "to_np2d", None)
        if not callable(reader):
            raise OriginOperationError("Matrix sheet does not support to_np2d().")
        try:
            return reader(object_index, "C")
        except TypeError:
            return reader(object_index)

    def _matrix_info_for_sheet(self, msheet: Any) -> dict[str, Any]:
        shape = self._call_or_value(msheet, "shape", default=(0, 0))
        depth = self._call_or_value(msheet, "depth", default=1)
        xymap = self._call_or_value(msheet, "xymap", default=None)
        get_labels = getattr(msheet, "get_labels", None)
        labels = list(get_labels("L") or []) if callable(get_labels) else []
        range_base = self._matrix_range(msheet)
        return {
            "book_name": self._object_name(msheet.get_book(), default=""),
            "sheet_name": self._object_name(msheet, default=""),
            "shape": list(shape or (0, 0)),
            "depth": int(depth or 0),
            "xymap": list(xymap) if xymap is not None else None,
            "labels": [str(value) for value in labels],
            "data_ranges": [f"{range_base}!{index + 1}" for index in range(int(depth or 0))],
        }

    @staticmethod
    def _matrix_range(msheet: Any) -> str:
        lt_range = getattr(msheet, "lt_range", None)
        if not callable(lt_range):
            raise OriginOperationError("Matrix sheet does not expose lt_range().")
        try:
            return str(lt_range(False)).rstrip("!")
        except TypeError:
            return str(lt_range()).rstrip("!")

    def _set_matrix_xymap(self, msheet: Any, xymap: tuple[float, float, float, float]) -> None:
        x1, x2, y1, y2 = (float(value) for value in xymap)
        if not x1 < x2 or not y1 < y2:
            raise OriginOperationError(
                "xymap must satisfy x1 < x2 and y1 < y2.", error_code="invalid_request"
            )
        try:
            msheet.xymap = (x1, x2, y1, y2)
            return
        except Exception:
            pass
        self._execute_on_matrix(msheet, f"mdim x1:={x1} x2:={x2} y1:={y1} y2:={y2};")

    @staticmethod
    def _set_matrix_labels(msheet: Any, labels: list[str]) -> None:
        setter = getattr(msheet, "set_labels", None)
        if not callable(setter):
            raise OriginOperationError("Matrix sheet does not support set_labels().")
        setter([str(label) for label in labels], "L", offset=0)

    def _execute_on_matrix(self, msheet: Any, script: str) -> None:
        activate = getattr(msheet, "activate", None)
        if callable(activate):
            activate()
        executor = getattr(msheet, "lt_exec", None)
        result = executor(script) if callable(executor) else self.run_labtalk(script).get("result")
        if result is False:
            raise OriginOperationError("Origin rejected the matrix operation.")

    def _normalize_image_source(self, source: str) -> str:
        clean_source = str(source).strip()
        if not clean_source:
            raise OriginOperationError("source is empty.", error_code="invalid_request")
        parsed = urlparse(clean_source)
        if parsed.scheme and parsed.scheme.lower() != "file":
            return clean_source
        local = Path(parsed.path if parsed.scheme.lower() == "file" else clean_source)
        normalized = self._normalize_user_path(local)
        self._validate_file(normalized)
        return str(normalized)

    def _find_image(self, image_name: str | None) -> Any:
        finder = getattr(self.op, "find_image", None)
        if not callable(finder):
            raise OriginOperationError("originpro.find_image is not available.")
        image = finder(image_name or "")
        if image is None:
            raise OriginOperationError(
                f"Image window not found: {image_name or '<active image>'}",
                error_code="image_not_found",
            )
        return image

    def _image_info_for_page(self, image: Any) -> dict[str, Any]:
        size = self._call_or_value(image, "size", default=(0, 0))
        return {
            "image_name": self._object_name(image, default=""),
            "size": list(size or (0, 0)),
            "channels": int(self._call_or_value(image, "channels", default=0) or 0),
            "frames": int(self._call_or_value(image, "frames", default=0) or 0),
            "media_type": int(self._call_or_value(image, "type", default=0) or 0),
        }

    @staticmethod
    def _call_or_value(obj: Any, name: str, default: Any = None) -> Any:
        value = getattr(obj, name, default)
        if callable(value):
            try:
                return value()
            except TypeError:
                return default
        return value

    @staticmethod
    def _set_object_name(obj: Any, name: str) -> None:
        try:
            obj.name = name
        except Exception:
            try:
                obj.lname = name
            except Exception as exc:
                raise OriginOperationError(f"Could not rename Origin object to {name!r}.") from exc
