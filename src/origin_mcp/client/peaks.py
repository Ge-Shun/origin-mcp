from __future__ import annotations

from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase


class _PeakMixin(_OriginClientBase):
    """Peak Analyzer theme execution and batch spectroscopy workflows."""

    def peak_analyzer(
        self,
        *,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        theme: str | None = None,
        dialog_mode: str = "no_dialog",
    ) -> dict[str, Any]:
        range_expr = self._analysis_range(worksheet, x_col, y_col)
        if not range_expr:
            raise OriginOperationError(
                "Peak Analyzer requires an XY input range.", error_code="invalid_request"
            )
        mode_key = dialog_mode.strip().lower().replace("-", "_")
        mode_values = {
            "modeless": 0,
            "modeless_dialog": 0,
            "no_dialog": 1,
            "script": 1,
            "modal": 2,
            "modal_dialog": 2,
        }
        if mode_key not in mode_values:
            raise OriginOperationError(
                "dialog_mode must be no_dialog, modeless, or modal.",
                error_code="invalid_request",
            )
        if mode_values[mode_key] == 1 and not theme:
            raise OriginOperationError(
                "Script-mode Peak Analyzer requires a saved analysis theme.",
                error_code="invalid_request",
            )
        before = self._project_object_names()
        args = [f"iy:={self._peak_range_arg(range_expr)}", f"smode:={mode_values[mode_key]}"]
        if theme:
            args.append(self._peak_quoted_arg("theme", theme))
        script = "pa " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected Peak Analyzer.", error_code="peak_analyzer_failed"
            )
        after = self._project_object_names()
        return {
            "input_range": range_expr,
            "theme": theme,
            "dialog_mode": mode_key,
            "created_objects": sorted(after - before),
            "script": script,
            **result,
        }

    def peak_baseline(
        self,
        *,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        threshold: float = 0.05,
        anchor_count: int = 8,
        output_book: str = "PeakBaseline",
        output_sheet: str = "Anchors",
        include_output: bool = False,
        output_max_rows: int = 100,
    ) -> dict[str, Any]:
        if threshold <= 0:
            raise OriginOperationError("threshold must be positive.", error_code="invalid_request")
        if anchor_count < 2:
            raise OriginOperationError(
                "anchor_count must be at least 2.", error_code="invalid_request"
            )
        input_range = self._analysis_range(worksheet, x_col, y_col)
        if not input_range:
            raise OriginOperationError("Baseline creation requires an XY input range.")
        out = self._new_sheet(book_name=output_book, sheet_name=output_sheet)
        ref = self._worksheet_ref(out)
        output_range = f"[{ref.book_name}]{ref.sheet_name}!(1,2)"
        script = (
            f"blauto iy:={self._peak_range_arg(input_range)} thres:={float(threshold)} "
            f"number:={int(anchor_count)} oy:={output_range};"
        )
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected automatic baseline creation.",
                error_code="peak_baseline_failed",
            )
        response: dict[str, Any] = {
            "input_range": input_range,
            "output_range": output_range,
            "threshold": threshold,
            "anchor_count": anchor_count,
            "worksheet": ref.as_dict(),
            "script": script,
            **result,
        }
        if include_output:
            response["output"] = self.read_worksheet(
                book_name=ref.book_name,
                sheet_name=ref.sheet_name,
                max_rows=output_max_rows,
            )
        return response

    def peak_analyzer_batch(
        self,
        *,
        theme: str,
        input_range: str | None = None,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_cols: list[str | int] | None = None,
        result_sheet: str = "peak_properties",
        output_sheet: str | None = None,
        include_fit_statistics: bool = True,
        remove_intermediate: bool = True,
        dataset_identifier: str = "Range",
        clear_output: bool = True,
        append_mode: str = "rows",
        sequential_initialization: bool = False,
        before_script: str | None = None,
        loop_script: str | None = None,
        end_script: str | None = None,
        background_instances: int = 1,
    ) -> dict[str, Any]:
        if not theme.strip():
            raise OriginOperationError("theme is empty.", error_code="invalid_request")
        range_expr = (
            self._peak_range_arg(input_range)
            if input_range
            else self._peak_multi_range(worksheet, x_col, y_cols)
        )
        result_key = result_sheet.strip().lower().replace("-", "_")
        result_values = {
            "none": "none",
            "integrate": "integrate",
            "baseline": "baseline",
            "peak_centers": "peak_centers",
            "peak_properties": "peak_properties",
        }
        if result_key not in result_values:
            raise OriginOperationError(
                "result_sheet must be none, integrate, baseline, peak_centers, or peak_properties.",
                error_code="invalid_request",
            )
        append_key = append_mode.strip().lower()
        if append_key not in {"rows", "columns", "cols"}:
            raise OriginOperationError("append_mode must be rows or columns.")
        if not 1 <= background_instances <= 64:
            raise OriginOperationError(
                "background_instances must be between 1 and 64.",
                error_code="invalid_request",
            )
        args = [
            f"iy:={range_expr}",
            self._peak_quoted_arg("theme", theme),
            f"append:={result_values[result_key]}",
            f"fitresult:={int(include_fit_statistics)}",
            f"remove:={int(remove_intermediate)}",
            self._peak_quoted_arg("dataid", dataset_identifier),
            f"clear:={int(clear_output)}",
            f"mode:={0 if append_key == 'rows' else 1}",
            f"initvalues:={int(sequential_initialization)}",
            f"instance:={background_instances}",
        ]
        if output_sheet:
            args.append(self._peak_quoted_arg("ow", output_sheet))
        for key, value in (
            ("beforescript", before_script),
            ("loopscript", loop_script),
            ("endscript", end_script),
        ):
            if value:
                args.append(self._peak_quoted_arg(key, value))
        script = "paMultiY " + " ".join(args) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected batch Peak Analyzer.",
                error_code="peak_analyzer_batch_failed",
            )
        return {
            "input_range": range_expr,
            "theme": theme,
            "result_sheet": result_key,
            "script": script,
            **result,
        }

    def _peak_multi_range(
        self,
        worksheet: str | None,
        x_col: str | int | None,
        y_cols: list[str | int] | None,
    ) -> str:
        if not worksheet or x_col is None or not y_cols:
            raise OriginOperationError(
                "Provide input_range or worksheet, x_col, and y_cols.",
                error_code="invalid_request",
            )
        wks = self._find_sheet_from_ref(worksheet)
        columns = self._worksheet_column_names(wks)
        x_name = self._resolve_column(columns, x_col, 0)
        y_names = [self._resolve_column(columns, y, 1) for y in y_cols]
        x_index = columns.index(x_name) + 1
        y_indexes = [columns.index(name) + 1 for name in y_names]
        lt_range = str(wks.lt_range(False)).rstrip("!")
        if y_indexes == list(range(min(y_indexes), max(y_indexes) + 1)):
            return f"{lt_range}!({x_index},{min(y_indexes)}:{max(y_indexes)})"
        pairs = ",".join(f"({x_index},{index})" for index in y_indexes)
        return f"{lt_range}!({pairs})"

    def _project_object_names(self) -> set[str]:
        try:
            project = self.list_project()
        except Exception:
            return set()
        names: set[str] = set()
        for group in ("workbooks", "matrixbooks", "graphs", "images"):
            for item in project.get(group, []):
                name = str(item.get("name") or "")
                if name:
                    names.add(f"{group}:{name}")
        return names

    def _peak_quoted_arg(self, name: str, value: str) -> str:
        return f'{name}:="{self._escape_labtalk(value)}"'

    @staticmethod
    def _peak_range_arg(value: str) -> str:
        clean = value.strip()
        if not clean or any(char in clean for char in (";", '"', "\n", "\r", "{", "}")):
            raise OriginOperationError(
                "Peak input ranges cannot contain script delimiters.",
                error_code="invalid_request",
            )
        return clean
