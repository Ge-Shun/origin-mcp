from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ORIGIN_UNICODE_ESCAPES = {
    "µ": r"\x(00B5)",
    "μ": r"\x(00B5)",
    "°": r"\x(00B0)",
    "Ω": r"\x(03A9)",
    "Å": r"\x(00C5)",
    "×": r"\x(00D7)",
    "−": r"\x(2212)",
}

FIELD_WORD_ALIASES = {
    "api": "API",
    "cpu": "CPU",
    "gpu": "GPU",
    "id": "ID",
    "mcp": "MCP",
    "rms": "RMS",
    "sd": "SD",
    "sem": "SEM",
    "url": "URL",
}

FIELD_UNIT_SUFFIXES = {
    "s": "s",
    "ms": "ms",
    "us": "µs",
    "µs": "µs",
    "μs": "µs",
    "ns": "ns",
    "um": "µm",
    "µm": "µm",
    "μm": "µm",
    "nm": "nm",
    "uM": "µM",
    "µM": "µM",
    "μM": "µM",
    "Hz": "Hz",
    "kHz": "kHz",
    "MHz": "MHz",
    "GHz": "GHz",
    "degC": "°C",
    "C": "°C",
    "K": "K",
    "Pa": "Pa",
    "kPa": "kPa",
    "MPa": "MPa",
    "V": "V",
    "mV": "mV",
    "A": "A",
    "mA": "mA",
    "W": "W",
    "kW": "kW",
    "pct": "%",
    "percent": "%",
}

FIELD_UNIT_TOKEN_SUFFIXES = {(token,): unit for token, unit in FIELD_UNIT_SUFFIXES.items()} | {
    ("mg", "dL"): "mg/dL",
    ("mg", "L"): "mg/L",
    ("g", "L"): "g/L",
    ("kg", "m3"): "kg/m³",
    ("m", "s"): "m/s",
}

STAT_ROLE_ALIASES = {
    "mean": "Mean",
    "avg": "Mean",
    "average": "Mean",
    "median": "Median",
    "std": "SD",
    "sd": "SD",
    "stdev": "SD",
    "sem": "SEM",
    "stderr": "SEM",
    "min": "Minimum",
    "max": "Maximum",
    "lower": "Lower",
    "upper": "Upper",
}

GENERIC_VALUE_TOKENS = {"value", "values", "measurement", "measure", "result"}
SERIES_CONTAINER_TOKENS = {
    "channel",
    "compound",
    "condition",
    "group",
    "replicate",
    "sample",
    "sensor",
    "series",
    "treatment",
}
SERIES_DIMENSION_TOKENS = {
    "baseline",
    "control",
    "placebo",
    "reference",
    "treated",
    "treatment",
}
TITLE_STOP_TOKENS = {
    "across",
    "and",
    "by",
    "chart",
    "comparison",
    "distribution",
    "figure",
    "over",
    "plot",
    "relationship",
    "trend",
    "versus",
    "vs",
}
TABLE_METRIC_COLUMNS = {"measure", "measurement", "metric", "parameter", "variable"}
TABLE_UNIT_COLUMNS = {"measurement_unit", "unit", "units"}


@dataclass(frozen=True)
class FieldSemantics:
    raw: str
    tokens: tuple[str, ...]
    metric_tokens: tuple[str, ...]
    statistic_roles: tuple[str, ...]
    unit: str | None


@dataclass(frozen=True)
class AxisTitleInference:
    label: str
    metric: str
    unit: str | None
    reason: str
    source: str = "smart_default"


SUPERSCRIPT_CHARS = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁺": "+",
    "⁻": "-",
    "⁼": "=",
    "⁽": "(",
    "⁾": ")",
    "ⁿ": "n",
    "ⁱ": "i",
}

SUBSCRIPT_CHARS = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "₊": "+",
    "₋": "-",
    "₌": "=",
    "₍": "(",
    "₎": ")",
    "ₐ": "a",
    "ₑ": "e",
    "ₕ": "h",
    "ᵢ": "i",
    "ⱼ": "j",
    "ₖ": "k",
    "ₗ": "l",
    "ₘ": "m",
    "ₙ": "n",
    "ₒ": "o",
    "ₚ": "p",
    "ᵣ": "r",
    "ₛ": "s",
    "ₜ": "t",
    "ᵤ": "u",
    "ᵥ": "v",
    "ₓ": "x",
}

SUPERSCRIPT_PATTERN = re.compile("[" + re.escape("".join(SUPERSCRIPT_CHARS)) + "]+")
SUBSCRIPT_PATTERN = re.compile("[" + re.escape("".join(SUBSCRIPT_CHARS)) + "]+")
HTML_SUB_PATTERN = re.compile(r"<sub>(.*?)</sub>", re.IGNORECASE | re.DOTALL)
HTML_SUP_PATTERN = re.compile(r"<sup>(.*?)</sup>", re.IGNORECASE | re.DOTALL)
BRACED_SUB_PATTERN = re.compile(r"_\{([^{}]+)\}")
BRACED_SUP_PATTERN = re.compile(r"\^\{([^{}]+)\}")
NUMERIC_SUB_PATTERN = re.compile(r"_(?!\{)([+-]?\d+(?:\.\d+)?)")
NUMERIC_SUP_PATTERN = re.compile(r"\^(?!\{)([+-]?\d+(?:\.\d+)?)")
SINGLE_LETTER_SUB_PATTERN = re.compile(r"_(?!\{)([A-Za-z])(?![A-Za-z0-9_])")


def origin_rich_text(text: str) -> str:
    """Convert common subscript/superscript notation to Origin escape sequences."""

    formatted = normalize_label_text(text)
    for character, escape in ORIGIN_UNICODE_ESCAPES.items():
        formatted = formatted.replace(character, escape)
    formatted = HTML_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = HTML_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = BRACED_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = BRACED_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = SINGLE_LETTER_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = NUMERIC_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = NUMERIC_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = SUBSCRIPT_PATTERN.sub(
        lambda match: _origin_sub(_translate(match.group(0), SUBSCRIPT_CHARS)),
        formatted,
    )
    formatted = SUPERSCRIPT_PATTERN.sub(
        lambda match: _origin_super(_translate(match.group(0), SUPERSCRIPT_CHARS)),
        formatted,
    )
    return formatted


def humanize_field_name(name: str) -> str:
    """Turn a machine-oriented field name into an Origin-ready display label."""

    value = normalize_label_text(str(name)).strip()
    if not value:
        return value
    if " " in value or "(" in value or ")" in value:
        return origin_rich_text(value)

    tokens = _split_field_tokens(value)
    if not tokens:
        return origin_rich_text(value)
    tokens, unit = _extract_field_unit(tokens)

    words = [FIELD_WORD_ALIASES.get(token.lower(), token.lower()) for token in tokens]
    if words:
        first = words[0]
        words[0] = first if first.isupper() else first[:1].upper() + first[1:]
    label = " ".join(words) or value
    if unit is not None:
        label = f"{label} ({unit})"
    return origin_rich_text(label)


def parse_field_semantics(name: str) -> FieldSemantics:
    """Split a field into metric words, statistical roles, and a unit."""

    raw = normalize_label_text(str(name)).strip()
    tokens, unit = _extract_field_unit(_split_field_tokens(raw))
    metric_tokens: list[str] = []
    statistic_roles: list[str] = []
    for token in tokens:
        role = STAT_ROLE_ALIASES.get(token.lower())
        if role is None:
            metric_tokens.append(token.lower())
        elif role not in statistic_roles:
            statistic_roles.append(role)
    return FieldSemantics(
        raw=raw,
        tokens=tuple(tokens),
        metric_tokens=tuple(metric_tokens),
        statistic_roles=tuple(statistic_roles),
        unit=unit,
    )


def infer_axis_title(
    field_names: list[str] | tuple[str, ...],
    *,
    explicit: str | None = None,
    table: Any = None,
    title_hint: str | None = None,
    x_name: str | None = None,
    fallback: str = "Value",
) -> AxisTitleInference:
    """Infer one concise axis title from one or more data fields."""

    if explicit is not None:
        label = origin_rich_text(explicit)
        return AxisTitleInference(
            label=label,
            metric=explicit,
            unit=None,
            reason="explicit_user_value",
            source="user",
        )

    parsed = [parse_field_semantics(name) for name in field_names if str(name).strip()]
    if not parsed:
        return AxisTitleInference(
            label=origin_rich_text(fallback),
            metric=fallback,
            unit=None,
            reason="generic_value_fallback",
        )

    units = [item.unit for item in parsed]
    shared_unit = units[0] if all(unit == units[0] for unit in units) else None
    common_metric = _common_metric_tokens(parsed)
    generic_fields = all(
        not item.metric_tokens or set(item.metric_tokens).issubset(GENERIC_VALUE_TOKENS)
        for item in parsed
    )
    table_metric = _constant_table_value(table, TABLE_METRIC_COLUMNS) if generic_fields else None
    table_unit = _constant_table_value(table, TABLE_UNIT_COLUMNS) if generic_fields else None
    if table_metric:
        common_metric = tuple(_split_field_tokens(table_metric))
    if table_unit:
        shared_unit = _normalize_unit_value(table_unit)

    reason = "shared_metric_and_unit" if len(parsed) > 1 else "field_semantics"
    if table_metric or table_unit:
        reason = "table_metric_unit_columns"
    if not common_metric or set(common_metric).issubset(
        GENERIC_VALUE_TOKENS | SERIES_CONTAINER_TOKENS | SERIES_DIMENSION_TOKENS
    ):
        common_metric = _title_metric_tokens(title_hint, x_name)
        if common_metric:
            reason = "chart_title_context"
    if not common_metric:
        common_metric = tuple(_split_field_tokens(fallback))
        reason = "generic_value_fallback"
    if len(set(units)) > 1 and any(unit is not None for unit in units):
        reason = "mixed_units_metric_only"

    metric = _format_field_words(list(common_metric)) or fallback
    label = f"{metric} ({shared_unit})" if shared_unit else metric
    return AxisTitleInference(
        label=origin_rich_text(label),
        metric=metric,
        unit=shared_unit,
        reason=reason,
    )


def infer_series_labels(
    field_names: list[str] | tuple[str, ...],
    *,
    omit_units_when_metrics_differ: bool = False,
) -> list[str]:
    """Return legend labels that omit metric/unit text already carried by an axis."""

    parsed = [parse_field_semantics(name) for name in field_names]
    if len(parsed) <= 1:
        return [humanize_field_name(item.raw) for item in parsed]
    common_metric = _common_metric_tokens(parsed)
    if not common_metric or set(common_metric).issubset(
        SERIES_CONTAINER_TOKENS | SERIES_DIMENSION_TOKENS | GENERIC_VALUE_TOKENS
    ):
        if omit_units_when_metrics_differ:
            labels = [
                origin_rich_text(_format_field_words([*item.metric_tokens, *item.statistic_roles]))
                for item in parsed
            ]
            if all(labels) and len({label.casefold() for label in labels}) == len(labels):
                return labels
        return [humanize_field_name(item.raw) for item in parsed]

    labels: list[str] = []
    for item in parsed:
        residual = _subtract_tokens(item.metric_tokens, common_metric)
        label_tokens = [*residual, *item.statistic_roles]
        if not label_tokens:
            labels.append(humanize_field_name(item.raw))
            continue
        labels.append(origin_rich_text(_format_field_words(label_tokens)))
    if len({label.casefold() for label in labels}) != len(labels):
        return [humanize_field_name(item.raw) for item in parsed]
    return labels


def _split_field_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[_\-\s]+", value) if token]


def _extract_field_unit(tokens: list[str]) -> tuple[list[str], str | None]:
    for suffix, unit in sorted(
        FIELD_UNIT_TOKEN_SUFFIXES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        length = len(suffix)
        if len(tokens) > length and tuple(tokens[-length:]) == suffix:
            return tokens[:-length], unit
    return tokens, None


def _common_metric_tokens(parsed: list[FieldSemantics]) -> tuple[str, ...]:
    if not parsed:
        return ()
    common = set(parsed[0].metric_tokens)
    for item in parsed[1:]:
        common.intersection_update(item.metric_tokens)
    return tuple(token for token in parsed[0].metric_tokens if token in common)


def _title_metric_tokens(title_hint: str | None, x_name: str | None) -> tuple[str, ...]:
    if not title_hint:
        return ()
    x_tokens = set(parse_field_semantics(x_name).metric_tokens) if x_name else set()
    candidates = [
        token.lower()
        for token in _split_field_tokens(title_hint)
        if token.lower() not in TITLE_STOP_TOKENS and token.lower() not in x_tokens
    ]
    candidates = [
        token
        for token in candidates
        if token not in SERIES_CONTAINER_TOKENS | SERIES_DIMENSION_TOKENS
    ]
    return tuple(candidates[-2:])


def _constant_table_value(table: Any, aliases: set[str]) -> str | None:
    columns = getattr(table, "columns", None)
    if columns is None:
        return None
    for column in columns:
        normalized = str(column).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized not in aliases:
            continue
        try:
            values = table[column].dropna().astype(str).str.strip()
            unique = [value for value in values.unique().tolist() if value]
        except Exception:
            continue
        if len(unique) == 1:
            return unique[0]
    return None


def _normalize_unit_value(value: str) -> str:
    aliases = {
        "C": "°C",
        "degC": "°C",
        "pct": "%",
        "percent": "%",
        "uM": "µM",
        "μM": "µM",
    }
    return aliases.get(value.strip(), value.strip())


def _format_field_words(tokens: list[str] | tuple[str, ...]) -> str:
    words = [FIELD_WORD_ALIASES.get(token.lower(), token.lower()) for token in tokens]
    if not words:
        return ""
    first = words[0]
    words[0] = first if first.isupper() else first[:1].upper() + first[1:]
    return " ".join(words)


def _subtract_tokens(
    tokens: tuple[str, ...],
    removed: tuple[str, ...],
) -> list[str]:
    remaining = list(tokens)
    for token in removed:
        if token in remaining:
            remaining.remove(token)
    return remaining


def normalize_label_text(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ")


def _translate(value: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(char, char) for char in value)


def _origin_sub(value: str) -> str:
    return f"\\-({_escape_group(value)})"


def _origin_super(value: str) -> str:
    return f"\\+({_escape_group(value)})"


def _escape_group(value: str) -> str:
    return normalize_label_text(value).replace(")", r"\)")
