from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..errors import OriginDependencyError, OriginOperationError
from .base import WorksheetRef, _OriginClientBase


class _WorksheetMixin(_OriginClientBase):
    """Worksheet import, mutation, and serialization methods."""

    def import_csv(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> WorksheetRef:
        return self.import_table(path=path, book_name=book_name, sheet_name=sheet_name)

    def import_table(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
    ) -> WorksheetRef:
        path = self._normalize_user_path(path)
        self._validate_file(path)
        df = self._read_table(
            path,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        if df.empty:
            raise OriginOperationError(f"Data file contains no rows: {path}")

        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        if hasattr(wks, "from_df"):
            wks.from_df(df)
        else:
            raise OriginOperationError(
                "The worksheet object does not support from_df(); update the originpro package."
            )

        return self._worksheet_ref(wks, columns=[str(col) for col in df.columns], rows=len(df))

    def import_file_connector(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        keep_dc: bool = True,
        dctype: str = "",
        sel: str = "",
        sparks: bool = False,
    ) -> WorksheetRef:
        path = self._normalize_user_path(path)
        self._validate_file(path)
        self.ensure_feature("worksheet_from_file", "Origin Data Connector import")
        wks = self._new_sheet(book_name=book_name, sheet_name=sheet_name)
        from_file = getattr(wks, "from_file", None)
        if not callable(from_file):
            raise OriginOperationError("The worksheet object does not support from_file().")
        from_file(str(path), keep_dc, dctype, sel, sparks)
        if book_name:
            try:
                wks.get_book().lname = book_name
            except Exception:
                pass
        return self._worksheet_ref(wks)

    def append_table(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        excel_sheet: str | int | None = 0,
        start_col: str | int = 0,
        delimiter: str | None = None,
        encoding: str | None = None,
        header: int | None = 0,
        skiprows: int | list[int] | None = None,
        nrows: int | None = None,
        na_values: str | list[str] | None = None,
    ) -> WorksheetRef:
        path = self._normalize_user_path(path)
        self._validate_file(path)
        df = self._read_table(
            path,
            excel_sheet=excel_sheet,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
            skiprows=skiprows,
            nrows=nrows,
            na_values=na_values,
        )
        if df.empty:
            raise OriginOperationError(f"Data file contains no rows: {path}")

        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.from_df(df, c1=start_col)
        return self._worksheet_ref(wks, columns=[str(col) for col in df.columns], rows=len(df))

    def worksheet_info(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        label_types: list[str] | None = None,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        labels: dict[str, list[str]] = {}
        get_labels = getattr(wks, "get_labels", None)
        if callable(get_labels):
            for label_type in label_types or ["L", "U", "C"]:
                labels[label_type] = [str(value) for value in get_labels(label_type)]
        ref = self._worksheet_ref(wks).as_dict()
        return {
            **ref,
            "columns_count": int(getattr(wks, "cols", len(ref["columns"]) or 0)),
            "labels": labels,
        }

    def read_worksheet(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        start_row: int = 0,
        max_rows: int = 100,
        columns: list[str | int] | None = None,
    ) -> dict[str, Any]:
        if start_row < 0:
            raise OriginOperationError("start_row must be non-negative.")
        if max_rows < 1:
            raise OriginOperationError("max_rows must be at least 1.")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        if columns:
            available = [str(col) for col in df.columns]
            selected = [self._resolve_column(available, col, default_index=0) for col in columns]
            df = df[selected]
        total_rows = len(df)
        window = df.iloc[start_row : start_row + max_rows]
        rows = self._dataframe_records(window)
        worksheet = self._worksheet_ref(
            wks,
            columns=[str(col) for col in df.columns],
        ).as_dict()
        return {
            "worksheet": worksheet,
            "columns": [str(col) for col in df.columns],
            "start_row": start_row,
            "returned_rows": len(rows),
            "total_rows": total_rows,
            "rows": rows,
        }

    def write_worksheet(
        self,
        rows: list[dict[str, Any]] | list[list[Any]],
        columns: list[str] | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        start_col: str | int = 0,
        create: bool = False,
    ) -> dict[str, Any]:
        df = self._rows_to_dataframe(rows, columns)
        if df.empty:
            raise OriginOperationError("No worksheet rows were provided.")
        wks = (
            self._new_sheet(book_name=book_name, sheet_name=sheet_name)
            if create
            else self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        )
        from_df = getattr(wks, "from_df", None)
        if not callable(from_df):
            raise OriginOperationError("The worksheet object does not support from_df().")
        try:
            from_df(df, c1=start_col)
        except TypeError:
            from_df(df)
        # When writing from the first column, drop any leftover columns (such as
        # a freshly created sheet's default empty "B") so the book holds exactly
        # what was written. A non-zero start_col is an append, so leave it.
        if start_col in (0, "0"):
            self._trim_worksheet_columns(wks, len(df.columns))
        worksheet = self._worksheet_ref(wks, columns=[str(col) for col in df.columns]).as_dict()
        return {"worksheet": worksheet}

    def add_calculated_column(
        self,
        column_name: str,
        formula: str,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        if not column_name.strip():
            raise OriginOperationError("column_name is empty.")
        if not formula.strip():
            raise OriginOperationError("formula is empty.")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        add_col = getattr(wks, "add_col", None)
        if callable(add_col):
            add_col(column_name)
        else:
            self._execute_on_worksheet(wks, f'wks.addcol("{self._escape_labtalk(column_name)}");')
        self._execute_on_worksheet(
            wks,
            f'col("{self._escape_labtalk(column_name)}")={formula};',
        )
        return {
            "worksheet": self._worksheet_ref(wks).as_dict(),
            "column_name": column_name,
            "formula": formula,
        }

    def add_calculated_columns(
        self,
        columns: list[dict[str, str]],
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        if not columns:
            raise OriginOperationError("No columns were provided.", error_code="invalid_request")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        add_col = getattr(wks, "add_col", None)
        applied: list[dict[str, str]] = []
        for spec in columns:
            name = str(spec.get("name") or spec.get("column_name") or "").strip()
            formula = str(spec.get("formula") or "").strip()
            if not name:
                raise OriginOperationError("A column spec is missing 'name'.")
            if not formula:
                raise OriginOperationError(f"Column {name!r} is missing 'formula'.")
            if callable(add_col):
                add_col(name)
            else:
                self._execute_on_worksheet(wks, f'wks.addcol("{self._escape_labtalk(name)}");')
            self._execute_on_worksheet(wks, f'col("{self._escape_labtalk(name)}")={formula};')
            applied.append({"column_name": name, "formula": formula})
        return {"worksheet": self._worksheet_ref(wks).as_dict(), "columns": applied}

    def sort_worksheet(
        self,
        by: str | int,
        ascending: bool = True,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        column = self._resolve_column([str(col) for col in df.columns], by, default_index=0)
        sorted_df = df.sort_values(by=column, ascending=ascending, kind="mergesort")
        from_df = getattr(wks, "from_df", None)
        if not callable(from_df):
            raise OriginOperationError("The worksheet object does not support from_df().")
        from_df(sorted_df.reset_index(drop=True))
        worksheet = self._worksheet_ref(
            wks,
            columns=[str(col) for col in sorted_df.columns],
        ).as_dict()
        return {
            "worksheet": worksheet,
            "sorted_by": column,
            "ascending": ascending,
        }

    def get_cell_value(
        self,
        row: int,
        column: str | int,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        if row < 0:
            raise OriginOperationError("row must be non-negative.")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        column_name = self._resolve_column([str(col) for col in df.columns], column, 0)
        if row >= len(df):
            raise OriginOperationError(f"row is out of range: {row}")
        value = df.iloc[row][column_name]
        return {
            "row": row,
            "column": column_name,
            "value": None if pd.isna(value) else value,
        }

    def set_cell_value(
        self,
        row: int,
        column: str | int,
        value: Any,
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        if row < 0:
            raise OriginOperationError("row must be non-negative.")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        column_name = self._resolve_column([str(col) for col in df.columns], column, 0)
        if row >= len(df):
            raise OriginOperationError(f"row is out of range: {row}")
        df.at[df.index[row], column_name] = value
        self._write_dataframe_to_worksheet(wks, df)
        return {"row": row, "column": column_name, "value": value}

    def delete_columns(
        self,
        columns: list[str | int],
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        if not columns:
            raise OriginOperationError("No columns were provided.")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        available = [str(col) for col in df.columns]
        selected = [self._resolve_column(available, column, 0) for column in columns]
        remaining = df.drop(columns=selected)
        self._write_dataframe_to_worksheet(wks, remaining)
        return {
            "worksheet": self._worksheet_ref(
                wks,
                columns=[str(col) for col in remaining.columns],
            ).as_dict(),
            "deleted_columns": selected,
        }

    def clear_worksheet(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        keep_columns: bool = True,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        if keep_columns:
            cleared = pd.DataFrame(columns=df.columns)
        else:
            cleared = pd.DataFrame()
        self._write_dataframe_to_worksheet(wks, cleared, allow_empty=True)
        return {
            "worksheet": self._worksheet_ref(
                wks,
                columns=[str(col) for col in cleared.columns],
                rows=0,
            ).as_dict(),
            "kept_columns": keep_columns,
        }

    def diagnose_worksheet(
        self,
        book_name: str | None = None,
        sheet_name: str | None = None,
        columns: list[str | int] | None = None,
        high_missing_threshold: float = 0.5,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        available = [str(col) for col in df.columns]
        if columns:
            selected = [self._resolve_column(available, col, 0) for col in columns]
            df = df.loc[:, selected]

        issues: list[dict[str, Any]] = []
        total_rows = len(df)
        if total_rows == 0:
            issues.append(
                self._worksheet_issue("empty_worksheet", "error", "Worksheet has no rows.")
            )

        names = [str(col) for col in df.columns]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            issues.append(
                self._worksheet_issue(
                    "duplicate_columns",
                    "warning",
                    f"Duplicate column names: {duplicates}.",
                )
            )

        column_reports: list[dict[str, Any]] = []
        for index in range(df.shape[1]):
            series = df.iloc[:, index]
            name = names[index]
            missing = int(series.isna().sum())
            missing_pct = (missing / total_rows) if total_rows else 0.0
            numeric = bool(pd.api.types.is_numeric_dtype(series))
            non_null = series.dropna()
            n_unique = int(non_null.nunique())
            column_reports.append(
                {
                    "name": name,
                    "index": index,
                    "dtype": str(series.dtype),
                    "numeric": numeric,
                    "missing": missing,
                    "missing_pct": round(missing_pct, 4),
                    "n_unique": n_unique,
                }
            )
            if total_rows and missing == total_rows:
                issues.append(
                    self._worksheet_issue(
                        "all_null_column",
                        "error",
                        f"Column {name!r} is entirely empty.",
                        column=name,
                    )
                )
            elif missing_pct >= high_missing_threshold and total_rows:
                issues.append(
                    self._worksheet_issue(
                        "high_missing",
                        "warning",
                        f"Column {name!r} is {missing_pct:.0%} missing.",
                        column=name,
                    )
                )
            if not numeric and len(non_null) > 0:
                issues.append(
                    self._worksheet_issue(
                        "non_numeric_column",
                        "info",
                        f"Column {name!r} is non-numeric ({series.dtype}); "
                        "plotting and analysis expect numeric data.",
                        column=name,
                    )
                )
            if numeric and n_unique == 1 and len(non_null) > 1:
                issues.append(
                    self._worksheet_issue(
                        "constant_column",
                        "info",
                        f"Column {name!r} is constant; fits and correlations may be undefined.",
                        column=name,
                    )
                )

        return {
            "worksheet": self._worksheet_ref(wks, columns=names, rows=total_rows).as_dict(),
            "rows": total_rows,
            "columns_count": df.shape[1],
            "column_reports": column_reports,
            "issues": issues,
            "passed": not any(issue["severity"] == "error" for issue in issues),
        }

    @staticmethod
    def _worksheet_issue(
        code: str, severity: str, message: str, column: str | None = None
    ) -> dict[str, Any]:
        issue: dict[str, Any] = {"code": code, "severity": severity, "message": message}
        if column is not None:
            issue["column"] = column
        return issue

    def export_worksheet_csv(
        self,
        path: Path,
        book_name: str | None = None,
        sheet_name: str | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OriginOperationError(f"Export path already exists: {path}")
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        df = self._worksheet_to_df(wks)
        df.to_csv(path, index=False)
        return {"path": str(path), "rows": len(df), "columns": [str(col) for col in df.columns]}

    # -- Data transforms (pandas round trip) -------------------------------

    def filter_rows(
        self,
        conditions: list[dict[str, Any]],
        combine: str = "and",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        if not conditions:
            raise OriginOperationError(
                "No filter conditions provided.", error_code="invalid_request"
            )
        wks, df = self._transform_source(book_name, sheet_name)
        masks = [self._row_mask(df, condition) for condition in conditions]
        mask = self._combine_masks(masks, combine)
        result = df[mask].reset_index(drop=True)
        return self._write_transform_result(
            wks,
            result,
            output_book,
            output_sheet,
            extra={"matched_rows": len(result), "total_rows": len(df)},
        )

    def drop_duplicates(
        self,
        subset: list[str | int] | None = None,
        keep: str = "first",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        wks, df = self._transform_source(book_name, sheet_name)
        available = [str(col) for col in df.columns]
        cols = [self._resolve_column(available, column, 0) for column in subset] if subset else None
        keep_arg: Any = keep
        if str(keep).lower() in {"none", "false", "drop_all"}:
            keep_arg = False
        result = df.drop_duplicates(subset=cols, keep=keep_arg).reset_index(drop=True)
        return self._write_transform_result(
            wks,
            result,
            output_book,
            output_sheet,
            extra={"removed_rows": len(df) - len(result), "total_rows": len(df)},
        )

    def fill_missing(
        self,
        strategy: str = "value",
        value: Any = None,
        columns: list[str | int] | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        wks, df = self._transform_source(book_name, sheet_name)
        available = [str(col) for col in df.columns]
        cols = (
            [self._resolve_column(available, column, 0) for column in columns]
            if columns
            else available
        )
        mode = strategy.strip().lower()
        result = df.copy()
        if mode in {"drop_rows", "dropna_rows", "drop"}:
            result = df.dropna(subset=cols).reset_index(drop=True)
        elif mode in {"drop_columns", "dropna_cols"}:
            result = df.dropna(axis=1)
        elif mode == "value":
            if value is None:
                raise OriginOperationError(
                    "strategy='value' requires a value.", error_code="invalid_request"
                )
            result[cols] = result[cols].fillna(value)
        elif mode in {"ffill", "forward"}:
            result[cols] = result[cols].ffill()
        elif mode in {"bfill", "backward"}:
            result[cols] = result[cols].bfill()
        elif mode in {"mean", "median"}:
            for column in cols:
                if pd.api.types.is_numeric_dtype(result[column]):
                    fill_value = (
                        result[column].mean() if mode == "mean" else result[column].median()
                    )
                    result[column] = result[column].fillna(fill_value)
        else:
            raise OriginOperationError(
                f"Unsupported missing-value strategy: {strategy}.", error_code="invalid_request"
            )
        return self._write_transform_result(
            wks,
            result,
            output_book,
            output_sheet,
            extra={"strategy": mode, "total_rows": len(result)},
        )

    def transpose_worksheet(
        self,
        label_column: str | int | None = None,
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        wks, df = self._transform_source(book_name, sheet_name)
        available = [str(col) for col in df.columns]
        if label_column is not None:
            key = self._resolve_column(available, label_column, 0)
            headers = [str(value) for value in df[key].tolist()]
            body = df.drop(columns=[key])
        else:
            headers = [f"R{index + 1}" for index in range(len(df))]
            body = df
        transposed = body.T
        transposed.columns = self._dedupe_headers(headers)
        transposed.insert(0, "Field", [str(col) for col in body.columns])
        result = transposed.reset_index(drop=True)
        return self._write_transform_result(wks, result, output_book, output_sheet)

    def merge_worksheets(
        self,
        right_book: str | None = None,
        right_sheet: str | None = None,
        on: str | list[str] | None = None,
        left_on: str | list[str] | None = None,
        right_on: str | list[str] | None = None,
        how: str = "inner",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        if how not in {"inner", "left", "right", "outer", "cross"}:
            raise OriginOperationError(
                f"Unsupported join type: {how}.", error_code="invalid_request"
            )
        left_wks, left_df = self._transform_source(book_name, sheet_name)
        right_wks = self._find_sheet(book_name=right_book, sheet_name=right_sheet)
        right_df = self._worksheet_to_df(right_wks)
        kwargs: dict[str, Any] = {"how": how, "suffixes": ("", "_right")}
        if how != "cross":
            if on is not None:
                kwargs["on"] = [on] if isinstance(on, str) else list(on)
            elif left_on is not None and right_on is not None:
                kwargs["left_on"] = [left_on] if isinstance(left_on, str) else list(left_on)
                kwargs["right_on"] = [right_on] if isinstance(right_on, str) else list(right_on)
            else:
                common = [col for col in left_df.columns if col in set(right_df.columns)]
                if not common:
                    raise OriginOperationError(
                        "No shared key columns; provide on, or left_on and right_on.",
                        error_code="invalid_request",
                    )
                kwargs["on"] = common
        merged = left_df.merge(right_df, **kwargs)
        return self._write_transform_result(
            left_wks,
            merged.reset_index(drop=True),
            output_book,
            output_sheet,
            extra={"how": how, "result_rows": len(merged)},
        )

    def concat_worksheets(
        self,
        others: list[dict[str, str]],
        axis: str = "rows",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        if axis not in {"rows", "columns"}:
            raise OriginOperationError(
                f"Unsupported concat axis: {axis}.", error_code="invalid_request"
            )
        if not others:
            raise OriginOperationError(
                "No other worksheets were provided to concatenate.", error_code="invalid_request"
            )
        primary_wks, primary_df = self._transform_source(book_name, sheet_name)
        frames = [primary_df]
        for source in others:
            other_wks = self._find_sheet(
                book_name=source.get("book") or source.get("book_name"),
                sheet_name=source.get("sheet") or source.get("sheet_name"),
            )
            frames.append(self._worksheet_to_df(other_wks))
        if axis == "rows":
            result = pd.concat(frames, axis=0, ignore_index=True)
        else:
            result = pd.concat(frames, axis=1)
            result.columns = self._dedupe_headers([str(col) for col in result.columns])
        return self._write_transform_result(
            primary_wks,
            result,
            output_book,
            output_sheet,
            extra={"axis": axis, "result_rows": len(result), "combined_sheets": len(frames)},
        )

    def pivot_worksheet(
        self,
        index: str | list[str],
        columns: str | list[str],
        values: str | list[str] | None = None,
        aggfunc: str = "mean",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        wks, df = self._transform_source(book_name, sheet_name)
        available = [str(col) for col in df.columns]
        idx = self._resolve_column_list(available, index)
        cols = self._resolve_column_list(available, columns)
        if values is None:
            vals: Any = None
        elif isinstance(values, list):
            vals = self._resolve_column_list(available, values)
        else:
            vals = self._resolve_column(available, values, 0)
        table = pd.pivot_table(df, index=idx, columns=cols, values=vals, aggfunc=aggfunc)
        table = table.reset_index()
        table.columns = self._flatten_columns(table.columns)
        return self._write_transform_result(
            wks,
            table,
            output_book,
            output_sheet,
            extra={"aggfunc": aggfunc},
        )

    def melt_worksheet(
        self,
        id_vars: list[str | int] | None = None,
        value_vars: list[str | int] | None = None,
        var_name: str = "variable",
        value_name: str = "value",
        book_name: str | None = None,
        sheet_name: str | None = None,
        output_book: str | None = None,
        output_sheet: str | None = None,
    ) -> dict[str, Any]:
        wks, df = self._transform_source(book_name, sheet_name)
        available = [str(col) for col in df.columns]
        ids = [self._resolve_column(available, col, 0) for col in id_vars] if id_vars else None
        vals = (
            [self._resolve_column(available, col, 0) for col in value_vars] if value_vars else None
        )
        melted = df.melt(id_vars=ids, value_vars=vals, var_name=var_name, value_name=value_name)
        return self._write_transform_result(wks, melted, output_book, output_sheet)

    def _transform_source(
        self, book_name: str | None, sheet_name: str | None
    ) -> tuple[Any, pd.DataFrame]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        return wks, self._worksheet_to_df(wks)

    def _write_transform_result(
        self,
        source_wks: Any,
        df: pd.DataFrame,
        output_book: str | None,
        output_sheet: str | None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        dest = (
            self._new_sheet(book_name=output_book, sheet_name=output_sheet)
            if (output_book or output_sheet)
            else source_wks
        )
        self._write_dataframe_to_worksheet(dest, df, allow_empty=True)
        result: dict[str, Any] = {
            "worksheet": self._worksheet_ref(
                dest,
                columns=[str(col) for col in df.columns],
                rows=len(df),
            ).as_dict()
        }
        if extra:
            result.update(extra)
        return result

    def _row_mask(self, df: pd.DataFrame, condition: dict[str, Any]) -> pd.Series[bool]:
        available = [str(col) for col in df.columns]
        column = self._resolve_column(available, condition.get("column"), 0)
        op = str(condition.get("op", "eq")).strip().lower()
        value = condition.get("value")
        series = df[column]
        if op in {"eq", "=="}:
            return series == value
        if op in {"ne", "!="}:
            return series != value
        if op in {"gt", ">"}:
            return series > value
        if op in {"ge", ">="}:
            return series >= value
        if op in {"lt", "<"}:
            return series < value
        if op in {"le", "<="}:
            return series <= value
        if op == "in":
            return series.isin(value if isinstance(value, list) else [value])
        if op == "not_in":
            return ~series.isin(value if isinstance(value, list) else [value])
        if op == "contains":
            return series.astype(str).str.contains(str(value), na=False)
        if op == "startswith":
            return series.astype(str).str.startswith(str(value))
        if op == "isna":
            return series.isna()
        if op == "notna":
            return series.notna()
        raise OriginOperationError(f"Unsupported filter op: {op}.", error_code="invalid_request")

    @staticmethod
    def _combine_masks(masks: list[pd.Series[bool]], combine: str) -> pd.Series[bool]:
        mode = combine.strip().lower()
        mask = masks[0]
        for other in masks[1:]:
            mask = (mask & other) if mode == "and" else (mask | other)
        return mask

    def _resolve_column_list(
        self, available: list[str], value: str | list[str] | int | list[int]
    ) -> list[str]:
        items = value if isinstance(value, list) else [value]
        return [self._resolve_column(available, item, 0) for item in items]

    @staticmethod
    def _dedupe_headers(headers: list[str]) -> list[str]:
        seen: dict[str, int] = {}
        result: list[str] = []
        for header in headers:
            if header in seen:
                seen[header] += 1
                result.append(f"{header}_{seen[header]}")
            else:
                seen[header] = 0
                result.append(header)
        return result

    @staticmethod
    def _flatten_columns(columns: Any) -> list[str]:
        flattened: list[str] = []
        for column in columns:
            if isinstance(column, tuple):
                parts = [str(part) for part in column if str(part) != ""]
                flattened.append("_".join(parts) if parts else "value")
            else:
                flattened.append(str(column))
        return flattened

    def create_sample_matrix_range(
        self,
        book_name: str = "OriginMcpMatrix",
        sheet_name: str = "MatrixData",
        rows: int = 12,
        cols: int = 12,
    ) -> dict[str, Any]:
        if rows < 2 or cols < 2:
            raise OriginOperationError("Matrix sample rows and cols must be at least 2.")
        try:
            import numpy as np
        except ImportError as exc:
            raise OriginDependencyError("numpy is required to create sample matrix data.") from exc

        op = self.op
        new_sheet = getattr(op, "new_sheet", None)
        if not callable(new_sheet):
            raise OriginOperationError("originpro.new_sheet is not available.")
        msheet = new_sheet("m")
        data = np.fromfunction(
            lambda row, col: np.sin(row / 2.0) + np.cos(col / 3.0) + row * col / 80.0,
            (rows, cols),
            dtype=float,
        )
        from_np = getattr(msheet, "from_np", None)
        if not callable(from_np):
            raise OriginOperationError("Matrix sheet does not support from_np().")
        from_np(data)
        if book_name:
            try:
                msheet.get_book().lname = book_name
            except Exception:
                pass
        if sheet_name:
            try:
                msheet.name = sheet_name
            except Exception:
                try:
                    msheet.lname = sheet_name
                except Exception:
                    pass
        range_base = msheet.lt_range(False)
        data_range = f"{range_base}!1"
        return {
            "book_name": self._object_name(msheet.get_book(), default=book_name),
            "sheet_name": self._object_name(msheet, default=sheet_name),
            "rows": rows,
            "cols": cols,
            "data_range": data_range,
        }

    def set_column_labels(
        self,
        labels: list[str],
        label_type: str = "L",
        book_name: str | None = None,
        sheet_name: str | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.set_labels([self._label_text(label) for label in labels], label_type, offset=offset)
        return self._worksheet_ref(wks).as_dict()

    def set_column_designations(
        self,
        spec: str,
        book_name: str | None = None,
        sheet_name: str | None = None,
        c1: int = 0,
        c2: int = -1,
        repeat: bool = True,
    ) -> dict[str, Any]:
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        wks.cols_axis(spec, c1=c1, c2=c2, repeat=repeat)
        return self._worksheet_ref(wks).as_dict()

    def _new_sheet(self, book_name: str | None, sheet_name: str | None) -> Any:
        if book_name or sheet_name:
            try:
                return self._find_sheet(book_name=book_name, sheet_name=sheet_name)
            except OriginOperationError:
                pass

        op = self.op
        new_sheet = getattr(op, "new_sheet", None)
        if not callable(new_sheet):
            raise OriginOperationError("originpro.new_sheet is not available.")

        try:
            wks = new_sheet("w", book_name or "")
        except TypeError:
            wks = new_sheet()

        if book_name:
            try:
                wks.get_book().lname = book_name
            except Exception:
                pass

        if sheet_name:
            try:
                wks.name = sheet_name
            except Exception:
                try:
                    wks.lname = sheet_name
                except Exception as exc:
                    raise OriginOperationError(
                        f"Could not rename worksheet to {sheet_name!r}."
                    ) from exc
        return wks

    def _worksheet_to_df(self, wks: Any) -> pd.DataFrame:
        to_df = getattr(wks, "to_df", None)
        if callable(to_df):
            for kwargs in ({}, {"c1": 0}, {"head": "L"}):
                try:
                    df = to_df(**kwargs)
                    if isinstance(df, pd.DataFrame):
                        df.columns = [str(col) for col in df.columns]
                        return df
                except TypeError:
                    continue
        raise OriginOperationError("The worksheet object does not support to_df().")

    def _write_dataframe_to_worksheet(
        self,
        wks: Any,
        df: pd.DataFrame,
        allow_empty: bool = False,
    ) -> None:
        if df.empty and not allow_empty:
            raise OriginOperationError("No worksheet data was provided.")
        from_df = getattr(wks, "from_df", None)
        if not callable(from_df):
            raise OriginOperationError("The worksheet object does not support from_df().")
        try:
            from_df(df)
        except ValueError:
            if not allow_empty:
                raise
            from_df(pd.DataFrame(columns=df.columns))
        # from_df overwrites cell data but leaves any columns the sheet had
        # beyond the new frame's width (e.g. the default empty "B" column, or
        # stale columns when a transform narrows the sheet). Trim them so the
        # worksheet holds exactly the result columns.
        self._trim_worksheet_columns(wks, len(df.columns))

    def _trim_worksheet_columns(self, wks: Any, target_cols: int) -> None:
        """Best-effort removal of worksheet columns beyond ``target_cols``.

        Never raises: trimming is a cleanup step, so any originpro/LabTalk
        incompatibility leaves the (functionally correct) data in place.
        """

        if target_cols < 1:
            return
        try:
            current = int(getattr(wks, "cols", 0) or 0)
        except (TypeError, ValueError):
            return
        if current <= target_cols:
            return
        try:
            self._execute_on_worksheet(wks, f"wks.ncols={target_cols};")
        except Exception:
            pass

    @staticmethod
    def _rows_to_dataframe(
        rows: list[dict[str, Any]] | list[list[Any]],
        columns: list[str] | None,
    ) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=columns or [])
        first = rows[0]
        if isinstance(first, dict):
            df = pd.DataFrame(rows)
            if columns:
                missing = [column for column in columns if column not in df.columns]
                if missing:
                    raise OriginOperationError(f"Rows are missing columns: {missing}")
                df = df[columns]
            return df
        if columns is None:
            width = max(len(row) for row in rows)  # type: ignore[arg-type]
            columns = [f"Col{i + 1}" for i in range(width)]
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
        return [{str(key): value for key, value in row.items()} for row in records]

    def _execute_on_worksheet(self, wks: Any, script: str) -> dict[str, Any]:
        activate = getattr(wks, "activate", None)
        if callable(activate):
            activate()
        lt_exec = getattr(wks, "lt_exec", None)
        if callable(lt_exec):
            return {"result": lt_exec(script)}
        obj = getattr(wks, "obj", None)
        obj_exec = getattr(obj, "LT_execute", None)
        if callable(obj_exec):
            return {"result": obj_exec(script)}
        return self.run_labtalk(script)

    @staticmethod
    def _resolve_column(columns: list[str], value: str | int | None, default_index: int) -> str:
        if value is None:
            return columns[default_index]
        if isinstance(value, int):
            try:
                return columns[value]
            except IndexError as exc:
                raise OriginOperationError(f"Column index out of range: {value}") from exc
        if value not in columns:
            raise OriginOperationError(f"Column not found: {value}. Available columns: {columns}")
        return value

    def _resolve_y_columns(
        self,
        columns: list[str],
        x_name: str,
        y_cols: list[str | int] | None,
    ) -> list[str]:
        if y_cols is None:
            resolved = [col for col in columns if col != x_name]
        else:
            resolved = [self._resolve_column(columns, col, default_index=1) for col in y_cols]

        if not resolved:
            raise OriginOperationError("No Y columns selected.")
        return resolved

    def _resolve_selected_columns(
        self,
        columns: list[str],
        selected_cols: list[str | int] | None,
    ) -> list[str]:
        if selected_cols is None:
            return columns
        resolved = [
            self._resolve_column(columns, column, default_index=0) for column in selected_cols
        ]
        if not resolved:
            raise OriginOperationError("No columns selected.")
        return resolved

    def _worksheet_range_expr(
        self,
        wks: Any,
        columns: list[str],
        selected: list[str],
    ) -> str:
        ref = self._worksheet_ref(wks, columns=columns)
        indexes = [columns.index(column) + 1 for column in selected]
        return f"[{ref.book_name}]{ref.sheet_name}!({','.join(str(index) for index in indexes)})"

    def _find_sheet(self, book_name: str | None = None, sheet_name: str | None = None) -> Any:
        op = self.op
        find_sheet = getattr(op, "find_sheet", None)
        if not callable(find_sheet):
            raise OriginOperationError("originpro.find_sheet is not available.")
        if book_name and sheet_name:
            ref = f"[{book_name}]{sheet_name}"
        else:
            ref = book_name or sheet_name or ""
        wks = find_sheet("w", ref)
        if wks is not None:
            return wks
        if book_name:
            wks = self._find_sheet_by_book_label(book_name, sheet_name)
            if wks is not None:
                return wks
        elif ref:
            wks = self._find_sheet_by_book_label(ref, None)
            if wks is not None:
                return wks
        raise OriginOperationError(
            f"Worksheet not found: {ref or '<active worksheet>'}",
            error_code="worksheet_not_found",
        )

    def _find_sheet_from_ref(self, worksheet: str | None = None) -> Any:
        op = self.op
        find_sheet = getattr(op, "find_sheet", None)
        if not callable(find_sheet):
            raise OriginOperationError("originpro.find_sheet is not available.")
        wks = find_sheet("w", worksheet or "")
        if wks is None and worksheet:
            clean = worksheet.strip()
            if clean.startswith("[") and "]" in clean:
                book_name, sheet_name = clean[1:].split("]", 1)
                sheet_name = sheet_name.split("!", 1)[0].strip() or None
                wks = self._find_sheet_by_book_label(book_name, sheet_name)
            else:
                wks = self._find_sheet_by_book_label(clean, None)
        if wks is None:
            raise OriginOperationError(
                f"Worksheet not found: {worksheet or '<active worksheet>'}",
                error_code="worksheet_not_found",
            )
        return wks

    def _find_sheet_by_book_label(self, book_name: str, sheet_name: str | None) -> Any | None:
        pages = getattr(self.op, "pages", None)
        if not callable(pages):
            return None
        for page in pages("w"):
            labels = {
                self._object_name(page, default=""),
                str(getattr(page, "lname", "")),
            }
            if not self._origin_name_matches(book_name, labels):
                continue
            if sheet_name:
                for sheet in page:
                    sheet_labels = {
                        self._object_name(sheet, default=""),
                        str(getattr(sheet, "lname", "")),
                    }
                    if sheet_name in sheet_labels:
                        return sheet
                return None
            return page[0]
        return None

    def _worksheet_ref(
        self,
        wks: Any,
        columns: list[str] | None = None,
        rows: int | None = None,
    ) -> WorksheetRef:
        if columns is None:
            get_labels = getattr(wks, "get_labels", None)
            if callable(get_labels):
                labels = [label for label in get_labels("L") if label]
                columns = labels or [f"Col{i + 1}" for i in range(getattr(wks, "cols", 0))]
            else:
                columns = []
        return WorksheetRef(
            book_name=self._object_name(wks.get_book(), default=""),
            sheet_name=self._object_name(wks, default=""),
            columns=columns,
            rows=rows if rows is not None else int(getattr(wks, "rows", 0)),
        )
