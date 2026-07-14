from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..errors import OriginOperationError
from .base import _OriginClientBase

ArgumentKind = Literal["range", "string", "enum", "bool", "int", "number", "vector"]


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
    "kmeans": XFunctionSpec(
        "kmeans",
        "multivariate",
        "K-means clustering.",
        {
            "ir": _a("range"),
            "labelr": _a("range"),
            "std": _a("enum", "none", "snd", "range"),
            "num": _a("int"),
            "specify": _a("bool"),
            "iinitial": _a("range"),
            "iter": _a("int"),
            "oinitial": _a("bool"),
            "anova": _a("bool"),
            "member": _a("bool"),
            "distance": _a("bool"),
            "clusterPlot": _a("bool"),
            "plot": _a("bool"),
            "iy": _a("range"),
            "rt": _a("range"),
            "rd": _a("range"),
            "rdplot": _a("range"),
        },
        originpro_only=True,
    ),
    "hcluster": XFunctionSpec(
        "hcluster",
        "multivariate",
        "Hierarchical cluster analysis.",
        {
            "irng": _a("range"),
            "label": _a("range"),
            "obj": _a("int"),
            "link": _a("enum", "near", "furth", "group", "centroid", "median", "ward"),
            "dist1": _a("enum", "euc", "squ", "city"),
            "dist2": _a("enum", "corr", "abs"),
            "std": _a("enum", "none", "snd", "range"),
            "number": _a("int"),
            "stat": _a("enum", "sd", "md", "ssd"),
            "dissimilarity": _a("bool"),
            "stage": _a("bool"),
            "center": _a("bool"),
            "distc2c": _a("bool"),
            "disto2c": _a("bool"),
            "dendrogram": _a("bool"),
            "ngraph": _a("int"),
            "orient": _a("int"),
            "rt": _a("range"),
            "rd": _a("range"),
            "rddist": _a("range"),
            "rdplot": _a("range"),
        },
        originpro_only=True,
    ),
    "discrim": XFunctionSpec(
        "discrim",
        "multivariate",
        "Linear or quadratic discriminant analysis.",
        {
            "group": _a("range"),
            "var": _a("range"),
            "test": _a("bool"),
            "pvar": _a("range"),
            "prior": _a("int"),
            "method": _a("int"),
            "candisc": _a("bool"),
            "cv": _a("bool"),
            "stat": _a("bool"),
            "dmat": _a("bool"),
            "anova": _a("bool"),
            "equal": _a("bool"),
            "pcov": _a("bool"),
            "gcov": _a("bool"),
            "dcoeff": _a("bool"),
            "cstruct": _a("bool"),
            "ccoeff": _a("bool"),
            "cscore": _a("bool"),
            "prob": _a("bool"),
            "dist": _a("bool"),
            "ai": _a("bool"),
            "cstat": _a("bool"),
            "cplot": _a("bool"),
            "fplot": _a("bool"),
            "splot": _a("bool"),
            "rt": _a("range"),
            "rdtrain": _a("range"),
            "rdtest": _a("range"),
            "rdscore": _a("range"),
            "rdplot": _a("range"),
        },
        originpro_only=True,
    ),
    "pls": XFunctionSpec(
        "pls",
        "multivariate",
        "Partial least-squares regression.",
        {
            "ix": _a("range"),
            "iy": _a("range"),
            "label": _a("range"),
            "predict": _a("bool"),
            "irng": _a("range"),
            "method": _a("enum", "svd", "wold"),
            "scale": _a("bool"),
            "factor": _a("int"),
            "cv": _a("bool"),
            "rt": _a("range"),
            "rdres": _a("range"),
            "rdload": _a("range"),
            "rdscore": _a("range"),
            "rdplot": _a("range"),
        },
        originpro_only=True,
    ),
    **{
        name: XFunctionSpec(
            xfunction,
            "nonparametric",
            description,
            {
                "type": _a("int"),
                "irng": _a("range"),
                "alpha": _a("number"),
                "tail": _a("enum", "two", "upper", "lower"),
                "median": _a("number"),
                "exact": _a("bool"),
                "rt": _a("range"),
            },
            originpro_only=True,
        )
        for name, xfunction, description in (
            ("friedman", "friedman", "Friedman ANOVA."),
            ("kstest2", "kstest2", "Two-sample Kolmogorov-Smirnov test."),
            ("kwanova", "kwanova", "Kruskal-Wallis ANOVA."),
            ("mediantest", "mediantest", "Independent-samples median test."),
            ("mwtest", "mwtest", "Mann-Whitney test."),
            ("sign2", "sign2", "Paired-sample sign test."),
            ("signrank1", "signrank1", "One-sample Wilcoxon signed-rank test."),
            ("signrank2", "signrank2", "Paired-sample Wilcoxon signed-rank test."),
        )
    },
    "kaplanmeier": XFunctionSpec(
        "kaplanmeier",
        "survival",
        "Kaplan-Meier survival analysis.",
        {
            "irng": _a("range"),
            "censor": _a("vector"),
            "summary": _a("bool"),
            "survfunc": _a("bool"),
            "quartile": _a("bool"),
            "mean": _a("bool"),
            "conf": _a("number"),
            "sf": _a("bool"),
            "sfci": _a("bool"),
            "omsf": _a("bool"),
            "hazard": _a("bool"),
            "lsf": _a("bool"),
            "cmark": _a("bool"),
            "plotinone": _a("bool"),
            "logrank": _a("bool"),
            "breslow": _a("bool"),
            "tarone": _a("bool"),
            "pairwise": _a("bool"),
            "rd": _a("range"),
            "rt": _a("range"),
        },
        originpro_only=True,
    ),
    "phm_cox": XFunctionSpec(
        "phm_Cox",
        "survival",
        "Cox proportional-hazards regression.",
        {
            "irng": _a("range"),
            "censor": _a("vector"),
            "summary": _a("bool"),
            "cov": _a("bool"),
            "corr": _a("bool"),
            "sf": _a("bool"),
            "hazard": _a("bool"),
            "rd": _a("range"),
            "rt": _a("range"),
        },
        originpro_only=True,
    ),
    "weibullfit": XFunctionSpec(
        "weibullfit",
        "survival",
        "Censored Weibull survival fitting.",
        {
            "irng": _a("range"),
            "censor": _a("vector"),
            "method": _a("int"),
            "conf": _a("number"),
            "cov": _a("bool"),
            "pplot": _a("bool"),
            "sf": _a("bool"),
            "hazard": _a("bool"),
            "xmin": _a("number"),
            "xmax": _a("number"),
            "rt": _a("range"),
            "rd": _a("range"),
        },
        originpro_only=True,
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

    def multivariate_analysis(
        self,
        *,
        method: str,
        worksheet: str | None = None,
        columns: list[str | int] | None = None,
        variables_range: str | None = None,
        group_col: str | int | None = None,
        dependent_columns: list[str | int] | None = None,
        options: dict[str, Any] | None = None,
        output_book: str | None = None,
    ) -> dict[str, Any]:
        method_key = method.strip().lower().replace("-", "_")
        aliases = {
            "k_means": "kmeans",
            "hierarchical": "hcluster",
            "hierarchical_cluster": "hcluster",
            "discriminant": "discrim",
            "partial_least_squares": "pls",
        }
        function = aliases.get(method_key, method_key)
        if function not in {"kmeans", "hcluster", "discrim", "pls"}:
            raise OriginOperationError(
                f"Unsupported multivariate method: {method}.", error_code="invalid_request"
            )
        args = dict(options or {})
        if function in {"kmeans", "hcluster"}:
            args["ir" if function == "kmeans" else "irng"] = variables_range or self._column_range(
                worksheet, columns
            )
        elif function == "discrim":
            args["var"] = variables_range or self._column_range(worksheet, columns)
            args["group"] = self._single_column_range(worksheet, group_col)
        else:
            args["ix"] = variables_range or self._column_range(worksheet, columns)
            args["iy"] = self._column_range(worksheet, dependent_columns, minimum=1)
        if output_book:
            args.setdefault("rt", self._report_output_ref(output_book))
        result = self.run_xfunction(function, args)
        return {"method": function, "output_book": output_book, **result}

    def nonparametric_test(
        self,
        *,
        test: str,
        worksheet: str | None = None,
        columns: list[str | int] | None = None,
        input_range: str | None = None,
        input_form: str = "raw",
        alpha: float = 0.05,
        tail: str = "two",
        test_median: float = 0.0,
        exact: bool = False,
        options: dict[str, Any] | None = None,
        output_book: str | None = None,
    ) -> dict[str, Any]:
        aliases = {
            "kruskal_wallis": "kwanova",
            "mann_whitney": "mwtest",
            "ks_two_sample": "kstest2",
            "wilcoxon_one_sample": "signrank1",
            "wilcoxon_paired": "signrank2",
            "paired_sign": "sign2",
            "median": "mediantest",
        }
        function = aliases.get(test.strip().lower().replace("-", "_"), test.strip().lower())
        supported = {
            "friedman",
            "kstest2",
            "kwanova",
            "mediantest",
            "mwtest",
            "sign2",
            "signrank1",
            "signrank2",
        }
        if function not in supported:
            raise OriginOperationError(
                f"Unsupported nonparametric test: {test}.", error_code="invalid_request"
            )
        form_key = input_form.strip().lower()
        if form_key not in {"raw", "indexed"}:
            raise OriginOperationError(
                "input_form must be raw or indexed.", error_code="invalid_request"
            )
        minimum = 1 if function == "signrank1" else 2
        args = dict(options or {})
        args.update(
            {
                "irng": input_range or self._column_range(worksheet, columns, minimum=minimum),
                "alpha": alpha,
            }
        )
        if function != "signrank1":
            args["type"] = 1 if form_key == "raw" else 0
        if function in {"kstest2", "mwtest", "signrank1", "signrank2", "sign2"}:
            args.setdefault("tail", tail)
        if function == "signrank1":
            args.setdefault("median", test_median)
        if function == "mwtest":
            args.setdefault("exact", exact)
        if output_book:
            args.setdefault("rt", self._report_output_ref(output_book))
        result = self.run_xfunction(function, args)
        return {"test": function, "output_book": output_book, **result}

    def survival_analysis(
        self,
        *,
        method: str,
        worksheet: str | None = None,
        time_col: str | int | None = None,
        censor_col: str | int | None = None,
        group_col: str | int | None = None,
        covariate_columns: list[str | int] | None = None,
        input_range: str | None = None,
        censor_values: list[int | float] | None = None,
        options: dict[str, Any] | None = None,
        output_book: str | None = None,
    ) -> dict[str, Any]:
        aliases = {
            "kaplan_meier": "kaplanmeier",
            "cox": "phm_cox",
            "cox_regression": "phm_cox",
            "weibull": "weibullfit",
        }
        function = aliases.get(method.strip().lower().replace("-", "_"), method.strip().lower())
        if function not in {"kaplanmeier", "phm_cox", "weibullfit"}:
            raise OriginOperationError(
                f"Unsupported survival method: {method}.", error_code="invalid_request"
            )
        if input_range:
            range_expr = input_range
        else:
            selected: list[str | int] = []
            if time_col is not None:
                selected.append(time_col)
            if censor_col is not None:
                selected.append(censor_col)
            if function == "kaplanmeier" and group_col is not None:
                selected.append(group_col)
            if function == "phm_cox":
                selected.extend(covariate_columns or [])
            range_expr = self._column_range(
                worksheet,
                selected,
                minimum=2,
                collapse_contiguous=False,
            )
        args = dict(options or {})
        args["irng"] = range_expr
        args["censor"] = censor_values or [0]
        if output_book:
            args.setdefault("rt", self._report_output_ref(output_book))
        result = self.run_xfunction(function, args)
        return {"method": function, "output_book": output_book, **result}

    def _column_range(
        self,
        worksheet: str | None,
        columns: list[str | int] | None,
        minimum: int = 2,
        collapse_contiguous: bool = True,
    ) -> str:
        if not worksheet or not columns or len(columns) < minimum:
            raise OriginOperationError(
                f"Provide a worksheet with at least {minimum} selected column(s).",
                error_code="invalid_request",
            )
        wks = self._find_sheet_from_ref(worksheet)
        available = self._worksheet_column_names(wks)
        indexes = [available.index(self._resolve_column(available, col, 0)) + 1 for col in columns]
        base = str(wks.lt_range(False)).rstrip("!")
        if collapse_contiguous and indexes == list(range(min(indexes), max(indexes) + 1)):
            return f"{base}!({min(indexes)}:{max(indexes)})"
        return f"{base}!({','.join(str(index) for index in indexes)})"

    def _single_column_range(
        self,
        worksheet: str | None,
        column: str | int | None,
    ) -> str:
        if not worksheet or column is None:
            raise OriginOperationError(
                "worksheet and group_col are required.", error_code="invalid_request"
            )
        wks = self._find_sheet_from_ref(worksheet)
        available = self._worksheet_column_names(wks)
        resolved = self._resolve_column(available, column, 0)
        return wks.to_col_range(resolved)

    def _report_output_ref(self, output_book: str) -> str:
        clean = output_book.strip()
        if not clean or any(char in clean for char in (";", '"', "[", "]", "\n", "\r")):
            raise OriginOperationError("Invalid output_book name.", error_code="invalid_request")
        return f"[{clean}]<new>"

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
        if spec.kind == "vector":
            values = value if isinstance(value, (list, tuple)) else [value]
            if not values or any(
                isinstance(item, bool) or not isinstance(item, (int, float)) for item in values
            ):
                raise OriginOperationError(
                    f"Expected a numeric vector, got {value!r}.", error_code="invalid_request"
                )
            rendered = [str(float(item)) for item in values]
            if len(rendered) == 1:
                return rendered[0]
            return "{" + ",".join(rendered) + "}"
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
