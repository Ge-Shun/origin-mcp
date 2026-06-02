from __future__ import annotations

import uuid
from typing import Any

from ..analysis_adapters import resolve_analysis_adapter
from ..analysis_outputs import is_analysis_number, structure_analysis_output, structure_fit_result
from ..errors import OriginOperationError
from .base import ANALYSIS_XY_OUTPUTS, _OriginClientBase


class _AnalysisMixin(_OriginClientBase):
    """Curve fitting and Origin analysis methods."""

    def linear_fit_result(
        self,
        worksheet: str | None,
        x_col: str | int,
        y_col: str | int,
        y_error_col: str | int | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        op = self.op
        linear_fit_cls = getattr(op, "LinearFit", None)
        if not callable(linear_fit_cls):
            self.ensure_feature("linear_fit_api", "Structured linear fitting")
            raise OriginOperationError("originpro.LinearFit is not available.")
        wks = self._find_sheet_from_ref(worksheet)
        fit = linear_fit_cls()
        fit.set_data(wks, x_col, y_col, err=y_error_col or "")
        options = options or {}
        if "fix_intercept" in options:
            fit.fix_intercept(options["fix_intercept"])
        if "fix_slope" in options:
            fit.fix_slope(options["fix_slope"])
        if options.get("report"):
            report, curves = fit.report(int(options.get("band", 0)))
            result = {"mode": "report", "report_sheet": report, "curve_sheet": curves}
            if options.get("include_report_data") and report:
                result["report_data"] = self._analysis_output(
                    str(report),
                    options.get("max_rows", 100),
                )
            return result
        fit_result = fit.result()
        structured = structure_fit_result(fit_result)
        return {
            "mode": "result",
            "result": structured,
        }

    def list_fit_functions(self) -> dict[str, Any]:
        functions = [
            {
                "name": "Gauss",
                "category": "Peak",
                "parameters": ["y0", "xc", "w", "A"],
                "description": "Gaussian peak.",
            },
            {
                "name": "Lorentz",
                "category": "Peak",
                "parameters": ["y0", "xc", "w", "A"],
                "description": "Lorentzian peak.",
            },
            {
                "name": "ExpDec1",
                "category": "Exponential",
                "parameters": ["y0", "A1", "t1"],
                "description": "First-order exponential decay.",
            },
            {
                "name": "ExpDec2",
                "category": "Exponential",
                "parameters": ["y0", "A1", "t1", "A2", "t2"],
                "description": "Second-order exponential decay.",
            },
            {
                "name": "Boltzmann",
                "category": "Sigmoidal",
                "parameters": ["A1", "A2", "x0", "dx"],
                "description": "Boltzmann sigmoid.",
            },
            {
                "name": "Logistic",
                "category": "Sigmoidal",
                "parameters": ["A1", "A2", "x0", "p"],
                "description": "Logistic curve.",
            },
        ]
        return {"count": len(functions), "functions": functions}

    def nonlinear_fit_structured(
        self,
        worksheet: str | None,
        x_col: str | int,
        y_col: str | int,
        function: str,
        output_sheet: str | None = None,
        initial_params: dict[str, float] | None = None,
        fixed_params: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not function.strip():
            raise OriginOperationError("function is empty.")
        options = dict(options or {})
        options["function"] = function
        for name, value in (initial_params or {}).items():
            options[f"init_{name}"] = value
        if fixed_params:
            options["fixed"] = ",".join(fixed_params)
        return self.run_analysis(
            analysis="nonlinear_fit",
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_sheet,
            options=options,
            include_output=bool(output_sheet),
        )

    def run_analysis(
        self,
        analysis: str,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        output_sheet: str | None = None,
        options: dict[str, Any] | None = None,
        include_output: bool = False,
        output_max_rows: int = 100,
    ) -> dict[str, Any]:
        origin_version = self.capabilities(show=False).get("origin_version")
        adapter = resolve_analysis_adapter(analysis, origin_version)
        analysis_name = adapter.name
        options_for_script = dict(options or {})
        output_target = output_sheet
        polynomial_outputs: dict[str, str] = {}
        moments_outputs: dict[str, str] = {}
        peak_find_outputs: dict[str, str] = {}
        scalar_outputs: dict[str, str] = {}
        report_outputs: dict[str, str] = {}
        if output_sheet and analysis_name in ANALYSIS_XY_OUTPUTS | {"differentiate", "integrate"}:
            output_target = self._prepare_analysis_xy_output(output_sheet)
        if analysis_name == "polynomial_fit":
            polynomial_outputs = self._polynomial_output_variables()
            for key, value in polynomial_outputs.items():
                options_for_script.setdefault(key, value)
        if analysis_name == "descriptive_stats":
            output_target = None
            moments_outputs = self._moments_output_variables()
            for key, value in moments_outputs.items():
                options_for_script.setdefault(key, value)
        if analysis_name == "peak_find" and output_sheet:
            output_target = None
            peak_find_outputs = self._prepare_peak_find_outputs(output_sheet)
            for key, value in peak_find_outputs.items():
                if key != "worksheet":
                    options_for_script.setdefault(key, value)
        if adapter.scalar_outputs:
            # Statistical tests (t-tests) report their results as scalar LabTalk
            # variables rather than an output worksheet, mirroring the moments
            # path. Bind each output to a temp variable so we can read it back.
            output_target = None
            scalar_outputs = self._prepare_scalar_outputs(adapter.scalar_outputs)
            for key, value in scalar_outputs.items():
                options_for_script.setdefault(key, value)
        if adapter.report_output_option and output_sheet:
            # FFT/IFFT/correlation write a multi-column result into a report data
            # worksheet (rd, or the per-method coefficient sheet for corrcoef)
            # rather than an oy XY range. Bind it to a fresh sheet we can read
            # back. corrcoef exposes the requested method's table specifically.
            output_target = None
            report_option = adapter.report_output_option
            if analysis_name == "correlation":
                if options_for_script.get("spearman"):
                    report_option = "swks"
                elif options_for_script.get("kendall"):
                    report_option = "kwks"
            report_outputs = self._prepare_report_output(output_sheet)
            options_for_script.setdefault(report_option, report_outputs["ref"])
        script = self._analysis_script(
            analysis=analysis,
            worksheet=worksheet,
            x_col=x_col,
            y_col=y_col,
            output_sheet=output_target,
            options=options_for_script,
        )
        result = self.run_labtalk(script)
        executed = bool(result.get("result"))
        warning = "" if executed else "Origin returned false for this analysis command."
        warnings = [warning] if warning else []
        response = {
            "analysis": analysis_name,
            "script": script,
            "executed": executed,
            "parameters": [],
            "metrics": {},
            "sections": {},
            "warnings": warnings,
            "warning": warning,
            **result,
        }
        if output_target and output_target != output_sheet:
            response["output_target"] = output_target
        if moments_outputs:
            moments = self._structure_moments_outputs(moments_outputs)
            response["metrics"].update(moments["metrics"])
            response["sections"].update(moments["sections"])
        if peak_find_outputs:
            response["output_target"] = peak_find_outputs["worksheet"]
        if scalar_outputs:
            structured = self._structure_scalar_outputs(scalar_outputs)
            response["metrics"].update(structured["metrics"])
            response["sections"].update(structured["sections"])
        if report_outputs:
            response["output_target"] = report_outputs["worksheet"]
        if include_output:
            if report_outputs:
                output = self._analysis_output(report_outputs["worksheet"], output_max_rows)
                response["output"] = output
                if not output.get("found", True) and output.get("error"):
                    response["warnings"].append(str(output["error"]))
            elif not output_sheet:
                output_warning = "include_output requires output_sheet."
                response["output_warning"] = output_warning
                response["warnings"].append(output_warning)
            else:
                output = self._analysis_output(output_sheet, output_max_rows)
                response["output"] = output
                structured = structure_analysis_output(analysis_name, output)
                response["parameters"] = structured["parameters"]
                response["metrics"] = structured["metrics"]
                response["sections"] = structured["sections"]
                if polynomial_outputs:
                    polynomial = self._structure_polynomial_outputs(
                        polynomial_outputs,
                        options_for_script,
                    )
                    if polynomial["parameters"]:
                        response["parameters"] = polynomial["parameters"]
                    response["metrics"].update(polynomial["metrics"])
                if moments_outputs:
                    moments = self._structure_moments_outputs(moments_outputs)
                    response["metrics"].update(moments["metrics"])
                    response["sections"].update(moments["sections"])
                if not output.get("found", True) and output.get("error"):
                    response["warnings"].append(str(output["error"]))
        return response

    def _analysis_output(self, output_sheet: str, max_rows: int = 100) -> dict[str, Any]:
        if max_rows < 1:
            raise OriginOperationError("max_rows must be at least 1.")
        try:
            wks = self._find_sheet_from_ref(output_sheet)
            return self.read_worksheet(
                book_name=self._object_name(wks.get_book(), default=""),
                sheet_name=self._object_name(wks, default=""),
                max_rows=max_rows,
            )
        except Exception as exc:
            return {
                "found": False,
                "output_sheet": output_sheet,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    def _prepare_analysis_xy_output(self, output_sheet: str) -> str:
        output_sheet = output_sheet.strip()
        if "!" in output_sheet:
            return output_sheet
        if output_sheet.startswith("[") and "]" in output_sheet:
            return f"{output_sheet}!(1,2)"
        wks = self._new_sheet(book_name=output_sheet, sheet_name="Result")
        ref = self._worksheet_ref(wks)
        return f"[{ref.book_name}]{ref.sheet_name}!(1,2)"

    @staticmethod
    def _polynomial_output_variables() -> dict[str, str]:
        prefix = f"op{uuid.uuid4().hex[:6]}"
        return {
            "coef": f"{prefix}c",
            "err": f"{prefix}e",
            "N": f"{prefix}n",
            "AdjRSq": f"{prefix}a",
            "RSqCOD": f"{prefix}r",
        }

    @staticmethod
    def _moments_output_variables() -> dict[str, str]:
        prefix = f"om{uuid.uuid4().hex[:6]}"
        return {
            "mean": f"{prefix}mean",
            "sd": f"{prefix}sd",
            "se": f"{prefix}se",
            "n": f"{prefix}n",
            "sum": f"{prefix}sum",
            "skewness": f"{prefix}sk",
            "kurtosis": f"{prefix}ku",
            "cv": f"{prefix}cv",
        }

    def _prepare_report_output(
        self,
        output_sheet: str,
        default_sheet: str = "Result",
    ) -> dict[str, str]:
        wks = self._new_sheet(book_name=output_sheet, sheet_name=default_sheet)
        ref = self._worksheet_ref(wks)
        worksheet = f"[{ref.book_name}]{ref.sheet_name}"
        return {
            "worksheet": worksheet,
            "book": ref.book_name,
            "sheet": ref.sheet_name,
            "ref": f"{worksheet}!",
        }

    @staticmethod
    def _prepare_scalar_outputs(names: tuple[str, ...]) -> dict[str, str]:
        prefix = f"os{uuid.uuid4().hex[:6]}"
        return {name: f"{prefix}{name}" for name in names}

    def _structure_scalar_outputs(self, variables: dict[str, str]) -> dict[str, Any]:
        names = {
            "stat": "Statistic",
            "prob": "PValue",
            "df": "DF",
            "lcl": "LowerCL",
            "ucl": "UpperCL",
        }
        metrics: dict[str, Any] = {}
        for key, variable in variables.items():
            value = self._safe_eval(variable)
            if is_analysis_number(value):
                metrics[names.get(key, key)] = value
        return {"metrics": metrics, "sections": {"scalar_variables": variables}}

    def _prepare_peak_find_outputs(self, output_sheet: str) -> dict[str, str]:
        wks = self._new_sheet(book_name=output_sheet, sheet_name="Peaks")
        ref = self._worksheet_ref(wks)
        worksheet = f"[{ref.book_name}]{ref.sheet_name}"
        return {
            "worksheet": worksheet,
            "ocenter": f"{worksheet}!(1)",
            "ocenter_x": f"{worksheet}!(2)",
            "ocenter_y": f"{worksheet}!(3)",
        }

    def _structure_moments_outputs(self, variables: dict[str, str]) -> dict[str, Any]:
        names = {
            "mean": "Mean",
            "sd": "StandardDeviation",
            "se": "StandardError",
            "n": "N",
            "sum": "Sum",
            "skewness": "Skewness",
            "kurtosis": "Kurtosis",
            "cv": "CoefficientOfVariation",
        }
        metrics: dict[str, Any] = {}
        for key, name in names.items():
            value = self._safe_eval(variables[key])
            if is_analysis_number(value):
                metrics[name] = value
        return {"metrics": metrics, "sections": {"moments_variables": variables}}

    def _structure_polynomial_outputs(
        self,
        variables: dict[str, str],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_options = resolve_analysis_adapter(
            "polynomial_fit",
            self.capabilities(show=False).get("origin_version"),
        ).normalize_options(options)
        try:
            order = int(normalized_options.get("polyorder", 2))
        except (TypeError, ValueError):
            order = 2

        parameters = []
        for index in range(order + 1):
            value = self._safe_eval(f"{variables['coef']}[{index + 1}]")
            if is_analysis_number(value):
                parameter = {
                    "name": "Intercept" if index == 0 else f"B{index}",
                    "path": f"{variables['coef']}[{index + 1}]",
                    "value": value,
                }
                stderr = self._safe_eval(f"{variables['err']}[{index + 1}]")
                if is_analysis_number(stderr):
                    parameter["stderr"] = stderr
                parameters.append(parameter)

        metrics: dict[str, Any] = {}
        for key in ("N", "AdjRSq", "RSqCOD"):
            value = self._safe_eval(variables[key])
            if is_analysis_number(value):
                metrics[key] = value
        return {"parameters": parameters, "metrics": metrics}

    def _analysis_script(
        self,
        analysis: str,
        worksheet: str | None,
        x_col: str | int | None,
        y_col: str | int | None,
        output_sheet: str | None,
        options: dict[str, Any],
    ) -> str:
        origin_version = self.capabilities(show=False).get("origin_version")
        adapter = resolve_analysis_adapter(analysis, origin_version)
        range_expr = self._analysis_range(worksheet, x_col, y_col)
        if adapter.range_required and not range_expr:
            raise OriginOperationError(f"Analysis '{adapter.name}' requires an input range.")
        return " ".join(adapter.command(range_expr, output_sheet, options).split())

    def _analysis_range(
        self,
        worksheet: str | None,
        x_col: str | int | None,
        y_col: str | int | None,
    ) -> str:
        if worksheet is None and x_col is None and y_col is None:
            return ""
        if worksheet:
            try:
                wks = self._find_sheet_from_ref(worksheet)
                if x_col is not None and y_col is not None:
                    return wks.to_xy_range(x_col, y_col, "")
                if y_col is not None:
                    return wks.to_col_range(y_col)
                return wks.lt_range(False)
            except OriginOperationError:
                if x_col is not None or y_col is not None:
                    raise
        if worksheet and x_col is not None and y_col is not None:
            return f"{worksheet}!({x_col},{y_col})"
        if worksheet and y_col is not None:
            return f"{worksheet}!({y_col})"
        if worksheet:
            return worksheet
        return f"({x_col},{y_col})" if x_col is not None else f"({y_col})"
