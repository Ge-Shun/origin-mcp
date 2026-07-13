from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..errors import OriginOperationError
from .base import _OriginClientBase

ArgumentKind = Literal["range", "string", "enum", "bool", "int", "number"]


@dataclass(frozen=True)
class XFunctionArgument:
    kind: ArgumentKind
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class XFunctionSpec:
    name: str
    category: str
    description: str
    arguments: dict[str, XFunctionArgument]
    originpro_only: bool = False


def _a(kind: ArgumentKind, *choices: str) -> XFunctionArgument:
    return XFunctionArgument(kind=kind, choices=tuple(choices))


XFUNCTION_CATALOG: dict[str, XFunctionSpec] = {
    "smooth": XFunctionSpec(
        "smooth",
        "signal",
        "Smooth noisy XY data.",
        {
            "iy": _a("range"),
            "method": _a("enum", "aav", "sg", "pf", "fft", "lw", "le", "bm"),
            "weight": _a("bool"),
            "prop": _a("enum", "pts", "prop", "x"),
            "xval": _a("number"),
            "span": _a("number"),
            "npts": _a("int"),
            "boundary": _a("enum", "none", "reflect", "repeat", "periodic", "extrap"),
            "polyorder": _a("int"),
            "percent": _a("number"),
            "pad": _a("bool"),
            "filter": _a("enum", "new", "old"),
            "baseline": _a("enum", "two_ends", "two_ends_1", "none"),
            "oy": _a("range"),
        },
    ),
    "fft_filters": XFunctionSpec(
        "fft_filters",
        "signal",
        "Low/high/band/threshold FFT filtering.",
        {
            "iy": _a("range"),
            "filter": _a("enum", "low", "high", "bandpass", "bandblock", "threshold", "lowpp"),
            "freq1": _a("number"),
            "freq2": _a("number"),
            "cutoff": _a("number"),
            "pass": _a("number"),
            "stop": _a("number"),
            "threshold": _a("number"),
            "offset": _a("bool"),
            "oy": _a("range"),
        },
    ),
    "stft": XFunctionSpec(
        "stft",
        "signal",
        "Short-time Fourier transform.",
        {
            "ix": _a("range"),
            "mode": _a("enum", "interval", "freq"),
            "interval": _a("number"),
            "freq": _a("number"),
            "fftlen": _a("int"),
            "winlen": _a("int"),
            "overlap": _a("int"),
            "win": _a(
                "enum",
                "rect",
                "welch",
                "tri",
                "bartlett",
                "hanning",
                "hamming",
                "blackman",
                "gauss",
                "kaiser",
            ),
            "alpha": _a("number"),
            "beta": _a("number"),
            "correct": _a("enum", "none", "amp", "power"),
            "option": _a("enum", "complex", "amp", "ampdb"),
            "swapxy": _a("bool"),
            "om": _a("range"),
            "plot": _a("bool"),
            "rd": _a("range"),
        },
        originpro_only=True,
    ),
    "hilbert": XFunctionSpec(
        "hilbert",
        "signal",
        "Hilbert transform and analytic signal.",
        {"ix": _a("range"), "hil": _a("bool"), "ansig": _a("bool"), "rd": _a("range")},
        originpro_only=True,
    ),
    "envelope": XFunctionSpec(
        "envelope",
        "signal",
        "Upper/lower signal envelopes.",
        {
            "iy": _a("range"),
            "type": _a("enum", "upper", "lower", "both"),
            "npts": _a("int"),
            "rd": _a("range"),
        },
        originpro_only=True,
    ),
    "pca": XFunctionSpec(
        "pca",
        "statistics",
        "Principal component analysis.",
        {
            "irng": _a("range"),
            "label": _a("range"),
            "mtype": _a("enum", "corr", "cov"),
            "npc": _a("int"),
            "std": _a("bool"),
            "missing": _a("enum", "listwise", "pairwise"),
            "stat": _a("bool"),
            "corr": _a("bool"),
            "eigenval": _a("bool"),
            "eigenvec": _a("bool"),
            "scores": _a("bool"),
            "screeplot": _a("bool"),
            "xcomp": _a("int"),
            "ycomp": _a("int"),
            "lplot": _a("bool"),
            "splot": _a("bool"),
            "biplot": _a("bool"),
            "rt": _a("range"),
            "rd": _a("range"),
            "rdplot": _a("range"),
        },
        originpro_only=True,
    ),
    "freqcounts": XFunctionSpec(
        "freqcounts",
        "statistics",
        "Frequency counts and binned frequencies.",
        {
            "irng": _a("range"),
            "bin": _a("enum", "center", "end", "custom"),
            "min": _a("number"),
            "max": _a("number"),
            "stepby": _a("enum", "increment", "interval"),
            "inc": _a("number"),
            "intervals": _a("number"),
            "outleft": _a("bool"),
            "outright": _a("bool"),
            "cmin": _a("bool"),
            "cmax": _a("bool"),
            "center": _a("bool"),
            "end": _a("bool"),
            "count": _a("bool"),
            "cumulcount": _a("bool"),
            "freq": _a("bool"),
            "cumulfreq": _a("bool"),
            "show": _a("enum", "fraction", "percent"),
            "rd": _a("range"),
        },
    ),
}


class _ExpertMixin(_OriginClientBase):
    """Curated X-Function dispatcher and higher-level statistics/signal tools."""

    def list_xfunctions(self, category: str | None = None) -> dict[str, Any]:
        category_key = category.strip().lower() if category else None
        specs = [
            spec
            for spec in XFUNCTION_CATALOG.values()
            if category_key is None or spec.category == category_key
        ]
        if category_key and not specs:
            raise OriginOperationError(
                f"Unknown X-Function category: {category}.", error_code="invalid_request"
            )
        return {
            "categories": sorted({spec.category for spec in XFUNCTION_CATALOG.values()}),
            "xfunctions": [self._xfunction_spec_dict(spec) for spec in specs],
        }

    def run_xfunction(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        theme: str | None = None,
    ) -> dict[str, Any]:
        key = name.strip().lower()
        spec = XFUNCTION_CATALOG.get(key)
        if spec is None:
            raise OriginOperationError(
                f"X-Function {name!r} is not in the controlled catalog.",
                error_code="xfunction_not_allowed",
            )
        supplied = arguments or {}
        unknown = sorted(set(supplied) - set(spec.arguments))
        if unknown:
            raise OriginOperationError(
                f"Unsupported arguments for {spec.name}: {unknown}.",
                error_code="invalid_request",
            )
        before = self._project_object_names()
        parts = [spec.name]
        if theme:
            parts.extend(["-t", f'"{self._escape_labtalk(theme)}"'])
        for arg_name, value in supplied.items():
            if value is None:
                continue
            parts.append(
                f"{arg_name}:={self._format_xfunction_value(spec.arguments[arg_name], value)}"
            )
        script = " ".join(parts) + ";"
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                f"Origin rejected X-Function {spec.name}.",
                error_code="xfunction_failed",
            )
        after = self._project_object_names()
        return {
            "name": spec.name,
            "category": spec.category,
            "originpro_only": spec.originpro_only,
            "arguments": supplied,
            "theme": theme,
            "created_objects": sorted(after - before),
            "script": script,
            **result,
        }

    def fft_filter(
        self,
        *,
        worksheet: str | None = None,
        x_col: str | int | None = None,
        y_col: str | int | None = None,
        filter_type: str = "low",
        cutoff: float | None = None,
        lower_cutoff: float | None = None,
        upper_cutoff: float | None = None,
        pass_frequency: float | None = None,
        stop_frequency: float | None = None,
        threshold: float | None = None,
        keep_dc_offset: bool = True,
        output_book: str | None = None,
        output_sheet: str = "Filtered",
    ) -> dict[str, Any]:
        input_range = self._analysis_range(worksheet, x_col, y_col)
        if not input_range:
            raise OriginOperationError("FFT filtering requires an input range.")
        filter_key = filter_type.strip().lower()
        if filter_key in {"low", "high"} and cutoff is None:
            raise OriginOperationError(f"filter_type={filter_key!r} requires cutoff.")
        if filter_key in {"bandpass", "bandblock"} and (
            lower_cutoff is None or upper_cutoff is None or lower_cutoff >= upper_cutoff
        ):
            raise OriginOperationError(
                "Band filters require lower_cutoff < upper_cutoff.",
                error_code="invalid_request",
            )
        if filter_key == "threshold" and threshold is None:
            raise OriginOperationError("Threshold filtering requires threshold.")
        if filter_key == "lowpp" and (
            pass_frequency is None or stop_frequency is None or pass_frequency >= stop_frequency
        ):
            raise OriginOperationError(
                "Parabolic low-pass requires pass_frequency < stop_frequency.",
                error_code="invalid_request",
            )
        args: dict[str, Any] = {
            "iy": input_range,
            "filter": filter_key,
            "cutoff": cutoff,
            "freq1": lower_cutoff,
            "freq2": upper_cutoff,
            "pass": pass_frequency,
            "stop": stop_frequency,
            "threshold": threshold,
            "offset": keep_dc_offset,
        }
        output: dict[str, Any] | None = None
        if output_book:
            wks = self._new_sheet(book_name=output_book, sheet_name=output_sheet)
            ref = self._worksheet_ref(wks)
            args["oy"] = f"[{ref.book_name}]{ref.sheet_name}!(1,2)"
            output = ref.as_dict()
        result = self.run_xfunction("fft_filters", args)
        return {**result, "output_worksheet": output}

    def principal_component_analysis(
        self,
        *,
        variables_range: str | None = None,
        worksheet: str | None = None,
        columns: list[str | int] | None = None,
        matrix_type: str = "corr",
        components: int = 2,
        standardize_scores: bool = False,
        missing: str = "listwise",
        scree_plot: bool = True,
        loading_plot: bool = True,
        score_plot: bool = False,
        biplot: bool = True,
        report_output: str | None = None,
        scores_output: str | None = None,
    ) -> dict[str, Any]:
        if components < 1:
            raise OriginOperationError("components must be positive.")
        range_expr = variables_range or self._column_range(worksheet, columns)
        args: dict[str, Any] = {
            "irng": range_expr,
            "mtype": matrix_type,
            "npc": components,
            "std": standardize_scores,
            "missing": missing,
            "screeplot": scree_plot,
            "lplot": loading_plot,
            "splot": score_plot,
            "biplot": biplot,
            "rt": report_output,
            "rd": scores_output,
        }
        return self.run_xfunction("pca", args)

    def one_way_anova(
        self,
        *,
        worksheet: str,
        group_columns: list[str | int],
    ) -> dict[str, Any]:
        if len(group_columns) < 2:
            raise OriginOperationError(
                "Raw one-way ANOVA requires at least two group columns.",
                error_code="invalid_request",
            )
        wks = self._find_sheet_from_ref(worksheet)
        columns = self._worksheet_column_names(wks)
        resolved = [self._resolve_column(columns, col, 0) for col in group_columns]
        ranges = [wks.to_col_range(name) for name in resolved]
        before = self._project_object_names()
        assignments = " ".join(
            f'onewayGUI.GUI.InputData.Data.Factor_{index}$="{self._escape_labtalk(value)}";'
            for index, value in enumerate(ranges)
        )
        script = (
            "tree onewayGUI; "
            "xop execute:=init classname:=ANOVAOneWay iotrgui:=onewayGUI; "
            "onewayGUI.GUI.InputData.Use=1; "
            "xop execute:=update iotrgui:=onewayGUI; "
            f"{assignments} "
            "xop execute:=report iotrgui:=onewayGUI; "
            "xop execute:=cleanup;"
        )
        activate = getattr(wks, "activate", None)
        if callable(activate):
            activate()
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError("Origin rejected one-way ANOVA.")
        after = self._project_object_names()
        return {
            "worksheet": self._worksheet_ref(wks).as_dict(),
            "group_columns": resolved,
            "created_objects": sorted(after - before),
            "script": script,
            **result,
        }

    def _column_range(
        self,
        worksheet: str | None,
        columns: list[str | int] | None,
    ) -> str:
        if not worksheet or not columns or len(columns) < 2:
            raise OriginOperationError(
                "Provide variables_range or a worksheet with at least two columns.",
                error_code="invalid_request",
            )
        wks = self._find_sheet_from_ref(worksheet)
        available = self._worksheet_column_names(wks)
        indexes = [available.index(self._resolve_column(available, col, 0)) + 1 for col in columns]
        base = str(wks.lt_range(False)).rstrip("!")
        if indexes == list(range(min(indexes), max(indexes) + 1)):
            return f"{base}!({min(indexes)}:{max(indexes)})"
        return f"{base}!({','.join(str(index) for index in indexes)})"

    def _format_xfunction_value(self, spec: XFunctionArgument, value: Any) -> str:
        if spec.kind == "range":
            return self._safe_xfunction_range(str(value))
        if spec.kind == "string":
            return f'"{self._escape_labtalk(str(value))}"'
        if spec.kind == "enum":
            clean = str(value).strip().lower()
            if clean not in spec.choices:
                raise OriginOperationError(
                    f"Expected one of {list(spec.choices)}, got {value!r}.",
                    error_code="invalid_request",
                )
            return clean
        if spec.kind == "bool":
            if not isinstance(value, bool):
                raise OriginOperationError(
                    f"Expected a boolean, got {value!r}.", error_code="invalid_request"
                )
            return str(int(value))
        if spec.kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise OriginOperationError(
                    f"Expected an integer, got {value!r}.", error_code="invalid_request"
                )
            return str(value)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise OriginOperationError(
                f"Expected a number, got {value!r}.", error_code="invalid_request"
            )
        return str(float(value))

    @staticmethod
    def _safe_xfunction_range(value: str) -> str:
        clean = value.strip()
        if not clean or any(char in clean for char in (";", '"', "\n", "\r", "{", "}")):
            raise OriginOperationError(
                "X-Function ranges cannot contain script delimiters.",
                error_code="invalid_request",
            )
        return clean

    @staticmethod
    def _xfunction_spec_dict(spec: XFunctionSpec) -> dict[str, Any]:
        return {
            "name": spec.name,
            "category": spec.category,
            "description": spec.description,
            "originpro_only": spec.originpro_only,
            "arguments": {
                name: {"kind": arg.kind, "choices": list(arg.choices)}
                for name, arg in spec.arguments.items()
            },
        }
