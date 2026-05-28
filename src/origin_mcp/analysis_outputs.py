"""Pure helpers for normalising Origin analysis-output payloads.

These functions take raw fit/analysis dictionaries (as returned by Origin's
output worksheets or fit objects) and turn them into a stable
``{parameters, metrics, sections}`` shape that MCP responses can consume.
None of them touch ``originpro``; ``OriginClient`` delegates to them.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

_LABEL_KEYS = {
    "parameter",
    "parameters",
    "param",
    "name",
    "term",
    "coefficient",
    "coef",
    "quantity",
    "item",
}
_VALUE_KEYS = {
    "value",
    "estimate",
    "estimatedvalue",
    "fitvalue",
    "coefficientvalue",
    "coefvalue",
    "result",
}
_METRIC_KEYS = {
    "r",
    "rsquare",
    "rsquared",
    "r2",
    "adjrsquare",
    "adjrsquared",
    "adjustedrsquare",
    "adjustedrsquared",
    "chisqr",
    "chisquare",
    "reducedchisqr",
    "reducedchisquare",
    "rss",
    "residualsumofsquares",
    "rmse",
    "mse",
    "dof",
    "n",
    "pvalue",
    "prob",
}
_STDERR_KEYS = {
    "stderr",
    "standarderror",
    "standarderr",
    "stddev",
    "se",
}
_FIT_PARAMETER_TOKENS = ("parameter", "param", "coef", "coefficient")
_FIT_METRIC_KEYS = {"r", "r-square", "r_squared", "rsquare", "adjrsquare", "reducedchisqr"}


def analysis_key(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def is_analysis_metric_name(value: str) -> bool:
    return analysis_key(value) in _METRIC_KEYS


def is_analysis_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def serialize_analysis_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): serialize_analysis_value(val) for key, val in value.items()}
    if isinstance(value, list | tuple):
        return [serialize_analysis_value(item) for item in value]
    if hasattr(value, "items"):
        try:
            return {str(key): serialize_analysis_value(val) for key, val in value.items()}
        except Exception:
            pass
    if hasattr(value, "__dict__") and not isinstance(value, type):
        public = {key: val for key, val in vars(value).items() if not key.startswith("_")}
        if public:
            return serialize_analysis_value(public)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def analysis_row_label(row: dict[str, Any]) -> str | None:
    for key, value in row.items():
        if analysis_key(key) in _LABEL_KEYS and value not in (None, ""):
            return str(value)
    return None


def analysis_row_named_value(row: dict[str, Any], keys: set[str]) -> Any:
    for key, value in row.items():
        if analysis_key(key) in keys:
            return value
    return None


def analysis_row_value(row: dict[str, Any]) -> Any:
    named = analysis_row_named_value(row, _VALUE_KEYS)
    if named is not None:
        return named
    for key, value in row.items():
        normalized = analysis_key(key)
        if normalized not in {"parameter", "parameters", "param", "name", "term", "item"}:
            if is_analysis_number(value):
                return value
    return None


def analysis_row_metrics(row: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    label = analysis_row_label(row)
    value = analysis_row_value(row)
    if label and is_analysis_metric_name(label) and is_analysis_number(value):
        metrics[label] = value

    for key, candidate in row.items():
        if is_analysis_metric_name(str(key)) and is_analysis_number(candidate):
            metrics[str(key)] = candidate
    return metrics


def analysis_row_parameter(row: dict[str, Any], index: int) -> dict[str, Any] | None:
    name = analysis_row_label(row)
    value = analysis_row_value(row)
    if not name or not is_analysis_number(value):
        return None
    if is_analysis_metric_name(name):
        return None

    parameter = {
        "name": name,
        "path": f"output.rows.{index}",
        "value": value,
    }
    stderr = analysis_row_named_value(row, _STDERR_KEYS)
    if is_analysis_number(stderr):
        parameter["stderr"] = stderr
    return parameter


def analysis_output_rows(output: Any) -> list[dict[str, Any]]:
    data = serialize_analysis_value(output)
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def flatten_mapping(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        rows: list[tuple[tuple[str, ...], Any]] = []
        for key, child in value.items():
            rows.extend(flatten_mapping(child, (*path, str(key))))
        return rows
    if isinstance(value, list):
        rows = []
        for index, child in enumerate(value):
            rows.extend(flatten_mapping(child, (*path, str(index))))
        return rows
    return [(path, value)]


def looks_like_fit_parameter(path: tuple[str, ...], value: Any) -> bool:
    if not isinstance(value, int | float):
        return False
    joined = ".".join(path).lower()
    return any(token in joined for token in _FIT_PARAMETER_TOKENS)


def structure_analysis_output(analysis: str, output: Any) -> dict[str, Any]:
    if analysis not in {"linear_fit", "polynomial_fit", "nonlinear_fit"}:
        return {"parameters": [], "metrics": {}, "sections": {}}

    rows = analysis_output_rows(output)
    parameters: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}

    for index, row in enumerate(rows):
        row_metrics = analysis_row_metrics(row)
        metrics.update(row_metrics)
        parameter = analysis_row_parameter(row, index)
        if parameter is not None and parameter["name"] not in row_metrics:
            parameters.append(parameter)

    return {"parameters": parameters, "metrics": metrics, "sections": {}}


def structure_fit_result(raw: Any) -> dict[str, Any]:
    data = serialize_analysis_value(raw)
    flattened = list(flatten_mapping(data))
    parameters = []
    metrics: dict[str, Any] = {}
    sections: dict[str, Any] = {}

    for path, value in flattened:
        key = path[-1].lower() if path else ""
        joined = ".".join(path).lower()
        if looks_like_fit_parameter(path, value):
            parameters.append({"name": path[-1], "path": ".".join(path), "value": value})
        elif key in _FIT_METRIC_KEYS:
            metrics[path[-1]] = value
        elif key in {"slope", "intercept"} and isinstance(value, int | float):
            parameters.append({"name": path[-1], "path": ".".join(path), "value": value})
        elif "anova" in joined or "statistics" in joined or "summary" in joined:
            sections[".".join(path)] = value

    return {
        "parameters": parameters,
        "metrics": metrics,
        "sections": sections,
        "data": data,
    }
