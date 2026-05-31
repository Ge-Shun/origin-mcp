"""File-system helpers used by ``OriginClient``.

These are pure utilities — no Origin/originpro dependency — covering tabular
file reading, allowed-roots enforcement, and filename sanitisation.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from .errors import OriginOperationError


def read_table(
    path: Path,
    excel_sheet: str | int | None = 0,
    delimiter: str | None = None,
    encoding: str | None = None,
    header: int | None = 0,
    skiprows: int | list[int] | None = None,
    nrows: int | None = None,
    na_values: str | list[str] | None = None,
) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xls", ".xlsx", ".xlsm"}:
        return pd.read_excel(
            path,
            sheet_name=excel_sheet if excel_sheet is not None else 0,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
    read_kwargs = {
        "encoding": encoding,
        "header": header,
        "skiprows": skiprows,
        "nrows": nrows,
        "na_values": na_values,
    }
    read_kwargs = {key: value for key, value in read_kwargs.items() if value is not None}
    if suffix == ".tsv":
        return pd.read_csv(path, sep=delimiter or "\t", **read_kwargs)
    if suffix in {".txt", ".dat"}:
        return pd.read_csv(path, sep=delimiter, engine="python", **read_kwargs)
    if suffix == ".csv":
        return pd.read_csv(path, sep=delimiter or ",", **read_kwargs)
    raise OriginOperationError(
        f"Unsupported data file extension: {path.suffix}",
        error_code="unsupported_file_type",
    )


def check_path_allowed(path: Path) -> None:
    raw_roots = os.environ.get("ORIGIN_MCP_ALLOWED_ROOTS", "").strip()
    if not raw_roots:
        return
    resolved = path.expanduser().resolve()
    roots = [
        Path(root).expanduser().resolve() for root in raw_roots.split(os.pathsep) if root.strip()
    ]
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise OriginOperationError(
            f"Path is outside ORIGIN_MCP_ALLOWED_ROOTS: {resolved}",
            error_code="path_not_allowed",
        )


def validate_file(path: Path) -> None:
    check_path_allowed(path)
    if not path.exists():
        raise OriginOperationError(
            f"File does not exist: {path}",
            error_code="file_not_found",
        )
    if not path.is_file():
        raise OriginOperationError(
            f"Path is not a file: {path}",
            error_code="invalid_file_path",
        )


def safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name).strip()
    return cleaned or "graph"
