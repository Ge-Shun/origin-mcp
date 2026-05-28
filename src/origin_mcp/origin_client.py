from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from .analysis_adapters import resolve_analysis_adapter
from .analysis_outputs import is_analysis_number, structure_analysis_output, structure_fit_result
from .client.base import ANALYSIS_XY_OUTPUTS, GraphRef, WorksheetRef
from .client.graph_formatting import _GraphFormattingMixin
from .client.lifecycle import _LifecycleMixin
from .client.plot import _PlotMixin
from .client.worksheet import _WorksheetMixin
from .errors import OriginOperationError
from .image_quality import (
    export_looks_nonempty,
    export_quality_issues,
    file_sha256,
    image_dimensions,
    image_quality,
)

__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]


class OriginClient(_LifecycleMixin, _WorksheetMixin, _PlotMixin, _GraphFormattingMixin):
    """Small wrapper around the `originpro` package.

    The import is intentionally lazy so the MCP server can start and list tools even
    on machines where Origin is not installed yet.
    """































































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

    def export_all_graphs(
        self,
        output_dir: Path,
        file_type: str = "png",
        overwrite: bool = True,
        width: int = 0,
    ) -> dict[str, Any]:
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.ensure_feature("graph_list", "Batch graph export")
        op = self.op
        graph_list = getattr(op, "graph_list", None)
        if not callable(graph_list):
            raise OriginOperationError("originpro.graph_list is not available.")
        exported = []
        for graph in graph_list("p", True):
            graph_name = self._object_name(graph, default="Graph")
            path = output_dir / f"{self._safe_filename(graph_name)}.{file_type.lstrip('.')}"
            if path.exists() and not overwrite:
                continue
            if hasattr(graph, "save_fig"):
                graph.save_fig(str(path), type=file_type, replace=overwrite, width=width)
            else:
                self.export_graph(path, graph=graph, overwrite=overwrite)
            exported.append(str(path))
        return {"count": len(exported), "paths": exported}







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
        if output_sheet and analysis_name in ANALYSIS_XY_OUTPUTS:
            output_target = self._prepare_analysis_xy_output(output_sheet)
        if analysis_name == "polynomial_fit":
            polynomial_outputs = self._polynomial_output_variables()
            for key, value in polynomial_outputs.items():
                options_for_script.setdefault(key, value)
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
        if include_output:
            if not output_sheet:
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
                if not output.get("found", True) and output.get("error"):
                    response["warnings"].append(str(output["error"]))
        return response


    def export_graph(
        self,
        path: Path,
        graph_name: str | None = None,
        graph: Any | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OriginOperationError(f"Export path already exists: {path}")

        if graph_name:
            self._suppress_graph_title_text(graph_name=graph_name, title=None)
            self.run_labtalk(self._export_graph_labtalk(path, graph_name))
        else:
            target = graph if graph is not None else self._find_or_active_graph(graph_name)
            self._suppress_graph_title_text(graph=target, graph_name=None, title=None)
            if not hasattr(target, "save_fig"):
                self.run_labtalk(self._export_graph_labtalk(path, None))
                return {"path": str(path)}
            target.save_fig(str(path))

        return {"path": str(path)}

    def _export_graph_labtalk(self, path: Path, graph_name: str | None) -> str:
        export_type = path.suffix.lower().lstrip(".") or "png"
        if export_type == "jpeg":
            export_type = "jpg"
        filename = path.stem
        safe_path = self._escape_labtalk(str(path.parent))
        safe_filename = self._escape_labtalk(filename)
        parts = []
        if graph_name:
            safe_graph_name = self._escape_labtalk(graph_name)
            parts.append(f'win -a "{safe_graph_name}";')
            parts.append(f'expGraph pages:="{safe_graph_name}"')
        else:
            parts.append("expGraph")
        parts.append(
            f'type:={export_type} path:="{safe_path}" '
            f'filename:="{safe_filename}" overwrite:=replace;'
        )
        return " ".join(parts)

    def export_preview(
        self,
        graph_name: str | None = None,
        output_dir: Path | None = None,
        file_type: str = "png",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        suffix = file_type.lower().lstrip(".") or "png"
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "origin-mcp-previews"
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(graph_name or "active_graph")
        path = output_dir / f"{safe_name}_{uuid.uuid4().hex[:8]}.{suffix}"
        exported = self.export_graph(path, graph_name=graph_name, overwrite=overwrite)
        return {
            **exported,
            "preview": self.inspect_export(Path(exported["path"])),
        }

    def _export_plot_command_graph(self, path: Path, graph_name: str) -> dict[str, Any]:
        try:
            return self.export_graph(path, graph_name=graph_name)
        except OriginOperationError as exc:
            if "Graph not found" not in str(exc):
                raise
            exported = self.export_graph(path)
            exported["warning"] = (
                f"Origin did not expose plot command output as {graph_name!r}; "
                "exported the active graph instead."
            )
            return exported

    def inspect_export(self, path: Path) -> dict[str, Any]:
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
        if not path.exists():
            raise OriginOperationError(f"Export file does not exist: {path}")
        if not path.is_file():
            raise OriginOperationError(f"Export path is not a file: {path}")
        info: dict[str, Any] = {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "suffix": path.suffix.lower(),
            "sha256": file_sha256(path),
        }
        dimensions = image_dimensions(path)
        if dimensions:
            info.update(dimensions)
        quality = image_quality(path)
        if quality:
            info["image_quality"] = quality
        quality_issues = export_quality_issues(info)
        info["quality_issues"] = quality_issues
        info["quality_passed"] = not quality_issues
        info["looks_nonempty"] = export_looks_nonempty(info)
        return info

















































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

