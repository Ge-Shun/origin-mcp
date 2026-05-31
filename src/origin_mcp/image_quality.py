"""Image inspection helpers for export verification.

These functions are pure (no Origin dependency) and used by
``OriginClient.inspect_export`` to give a quick blank/near-blank/low-complexity
verdict on PNG/JPEG exports without pulling in Pillow.
"""

from __future__ import annotations

import hashlib
import math
import struct
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ImageQualityStats:
    pixels: int = 0
    transparent_pixels: int = 0
    non_white_pixels: int = 0
    background_diff_pixels: int = 0
    luma_sum: float = 0.0
    luma_sum_squares: float = 0.0
    min_x: int | None = None
    min_y: int | None = None
    max_x: int | None = None
    max_y: int | None = None

    def __post_init__(self) -> None:
        self.colors: Counter[tuple[int, int, int, int]] = Counter()
        self.background: tuple[int, int, int, int] | None = None

    def add(self, x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        if self.background is None:
            self.background = rgba
        self.pixels += 1
        self.colors[rgba] += 1
        red, green, blue, alpha = rgba
        if alpha == 0:
            self.transparent_pixels += 1
        luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        self.luma_sum += luma
        self.luma_sum_squares += luma * luma
        differs_from_white = alpha > 0 and min(red, green, blue) < 245
        differs_from_background = self._differs_from_background(rgba)
        if differs_from_white:
            self.non_white_pixels += 1
        if differs_from_background:
            self.background_diff_pixels += 1
        if differs_from_white or differs_from_background:
            self._extend_bbox(x, y)

    def as_dict(self, width: int, height: int, total_pixels: int) -> dict[str, Any]:
        non_transparent_pixels = self.pixels - self.transparent_pixels
        non_white_ratio = self._ratio(self.non_white_pixels)
        non_background_ratio = self._ratio(self.background_diff_pixels)
        non_transparent_ratio = self._ratio(non_transparent_pixels)
        mean_luma = self.luma_sum / self.pixels if self.pixels else 0.0
        variance = max(self.luma_sum_squares / self.pixels - mean_luma * mean_luma, 0.0)
        luma_stddev = variance**0.5
        has_visual_content = (
            non_transparent_pixels > 0
            and (self.background_diff_pixels >= max(8, int(self.pixels * 0.001)))
            and (luma_stddev >= 0.5 or len(self.colors) > 2)
        )
        issues = []
        if non_transparent_pixels == 0:
            issues.append("all_pixels_transparent")
        if len(self.colors) <= 1:
            issues.append("single_color_image")
        if not has_visual_content:
            issues.append("blank_or_near_blank")
        elif len(self.colors) <= 4 and non_background_ratio < 0.005:
            issues.append("low_color_complexity")
        return {
            "format": "png",
            "decoded": True,
            "width": width,
            "height": height,
            "pixel_count": total_pixels,
            "pixels_sampled": self.pixels,
            "unique_colors": len(self.colors),
            "top_colors": [
                {"rgba": list(color), "count": count} for color, count in self.colors.most_common(5)
            ],
            "non_white_ratio": round(non_white_ratio, 6),
            "non_background_ratio": round(non_background_ratio, 6),
            "non_transparent_ratio": round(non_transparent_ratio, 6),
            "mean_luma": round(mean_luma, 3),
            "luma_stddev": round(luma_stddev, 3),
            "content_bbox": self._bbox(),
            "has_visual_content": has_visual_content,
            "issues": issues,
        }

    def _differs_from_background(self, rgba: tuple[int, int, int, int]) -> bool:
        if self.background is None:
            return False
        if rgba[3] == 0 and self.background[3] == 0:
            return False
        delta = sum(abs(value - base) for value, base in zip(rgba, self.background, strict=True))
        return delta > 24

    def _extend_bbox(self, x: int, y: int) -> None:
        self.min_x = x if self.min_x is None else min(self.min_x, x)
        self.min_y = y if self.min_y is None else min(self.min_y, y)
        self.max_x = x if self.max_x is None else max(self.max_x, x)
        self.max_y = y if self.max_y is None else max(self.max_y, y)

    def _bbox(self) -> dict[str, int] | None:
        if self.min_x is None or self.min_y is None or self.max_x is None or self.max_y is None:
            return None
        return {
            "x_min": self.min_x,
            "y_min": self.min_y,
            "x_max": self.max_x,
            "y_max": self.max_y,
        }

    def _ratio(self, value: int) -> float:
        return value / self.pixels if self.pixels else 0.0


def image_dimensions(path: Path) -> dict[str, int] | None:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
            if suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n"):
                width, height = struct.unpack(">II", header[16:24])
                return {"width": width, "height": height}
            if suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8"):
                return jpeg_dimensions(path)
    except OSError:
        return None
    return None


def jpeg_dimensions(path: Path) -> dict[str, int] | None:
    try:
        with path.open("rb") as handle:
            handle.read(2)
            while True:
                marker_prefix = handle.read(1)
                if marker_prefix != b"\xff":
                    return None
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3"}:
                    handle.read(3)
                    height, width = struct.unpack(">HH", handle.read(4))
                    return {"width": width, "height": height}
                segment_length = struct.unpack(">H", handle.read(2))[0]
                handle.seek(segment_length - 2, 1)
    except (OSError, struct.error):
        return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_quality(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() != ".png":
        return None
    try:
        return png_quality(path)
    except (OSError, struct.error, zlib.error, ValueError):
        return None


def png_quality(path: Path) -> dict[str, Any] | None:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        width = height = bit_depth = color_type = interlace = None
        palette: list[tuple[int, int, int]] = []
        idat = bytearray()
        while True:
            length_bytes = handle.read(4)
            if not length_bytes:
                break
            length = struct.unpack(">I", length_bytes)[0]
            chunk_type = handle.read(4)
            data = handle.read(length)
            handle.read(4)
            if chunk_type == b"IHDR":
                width, height, bit_depth, color_type, _compression, _filter, interlace = (
                    struct.unpack(">IIBBBBB", data)
                )
            elif chunk_type == b"PLTE":
                palette = [
                    (data[index], data[index + 1], data[index + 2])
                    for index in range(0, len(data) - 2, 3)
                ]
            elif chunk_type == b"IDAT":
                idat.extend(data)
            elif chunk_type == b"IEND":
                break

    if width is None or height is None or color_type is None or bit_depth != 8 or interlace != 0:
        return None
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        return None
    raw = zlib.decompress(bytes(idat))
    stride = int(width) * channels
    expected = (stride + 1) * int(height)
    if len(raw) < expected:
        return None

    previous = bytearray(stride)
    offset = 0
    stats = ImageQualityStats()
    total_pixels = int(width) * int(height)
    sample_step = max(1, math.ceil((total_pixels / 500_000) ** 0.5))
    for row_index in range(int(height)):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + stride])
        offset += stride
        png_unfilter(row, previous, channels, filter_type)
        if row_index % sample_step == 0:
            for column in range(0, int(width), sample_step):
                rgba = png_pixel_rgba(
                    row,
                    column * channels,
                    color_type,
                    palette,
                )
                stats.add(column, row_index, rgba)
        previous = row
    return stats.as_dict(int(width), int(height), total_pixels)


def png_unfilter(row: bytearray, previous: bytearray, bpp: int, filter_type: int) -> None:
    if filter_type == 0:
        return
    for index, value in enumerate(row):
        left = row[index - bpp] if index >= bpp else 0
        up = previous[index] if previous else 0
        up_left = previous[index - bpp] if previous and index >= bpp else 0
        if filter_type == 1:
            row[index] = (value + left) & 0xFF
        elif filter_type == 2:
            row[index] = (value + up) & 0xFF
        elif filter_type == 3:
            row[index] = (value + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            row[index] = (value + png_paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")


def png_paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    up_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def png_pixel_rgba(
    row: bytearray,
    offset: int,
    color_type: int | None,
    palette: list[tuple[int, int, int]],
) -> tuple[int, int, int, int]:
    if color_type == 0:
        gray = row[offset]
        return gray, gray, gray, 255
    if color_type == 2:
        return row[offset], row[offset + 1], row[offset + 2], 255
    if color_type == 3:
        red, green, blue = palette[row[offset]]
        return red, green, blue, 255
    if color_type == 4:
        gray = row[offset]
        return gray, gray, gray, row[offset + 1]
    if color_type == 6:
        return row[offset], row[offset + 1], row[offset + 2], row[offset + 3]
    raise ValueError(f"Unsupported PNG color type: {color_type}")


def export_quality_issues(info: dict[str, Any]) -> list[str]:
    issues = []
    if info["size_bytes"] <= 0:
        issues.append("empty_file")
    width = info.get("width")
    height = info.get("height")
    if isinstance(width, int) and isinstance(height, int) and (width < 64 or height < 64):
        issues.append("dimensions_too_small")
    quality = info.get("image_quality")
    if isinstance(quality, dict):
        issues.extend(quality.get("issues", []))
    return issues


def export_looks_nonempty(info: dict[str, Any]) -> bool:
    if info["size_bytes"] <= 0:
        return False
    quality = info.get("image_quality")
    if isinstance(quality, dict):
        return bool(quality.get("has_visual_content"))
    return True
