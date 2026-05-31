from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from .compat import PLOT_TYPE_CATALOG

COMMON_CHART_TYPES = (
    "line",
    "scatter",
    "line_symbol",
    "column",
    "bar",
    "area",
    "histogram",
    "box",
    "bubble",
    "polar",
    "ternary",
    "vector",
    "heatmap",
    "contour",
    "image",
    "matrix_heatmap",
    "scatter3d",
    "surface3d",
    "waterfall",
    "ribbon3d",
    "pie",
)


CHART_TYPE_ALIASES = {
    "columns": "column",
    "grouped_column": "column",
    "column_stack": "column",
    "stack_column": "column",
    "stacked_column": "column",
    "grouped_bar": "bar",
    "floating_bar": "bar",
    "stack_bar": "bar",
    "stacked_bar": "bar",
    "stack_area": "area",
    "stacked_area": "area",
    "color_mapped": "scatter",
    "ternary_contour": "contour",
    "smith": "smith",
    "smith_chart": "smith",
    "high_low_close": "financial",
    "ohlc": "financial",
    "candlestick": "financial",
    "dendrogram": "dendrogram",
    "3d_vector": "vector3d",
    "3d_bars": "bar3d",
    "柱状图": "column",
    "柱形图": "column",
    "柱图": "column",
    "条形图": "bar",
    "折线图": "line",
    "散点图": "scatter",
    "气泡图": "bubble",
    "箱线图": "box",
    "盒须图": "box",
    "直方图": "histogram",
    "热图": "heatmap",
    "等值线": "contour",
    "等高线": "contour",
    "图片": "image",
    "图像": "image",
    "三维散点": "scatter3d",
    "三维曲面": "surface3d",
    "三维柱": "bar3d",
    "三维矢量": "vector3d",
}


EXTENSIONS_BY_CHART_TYPE = {
    "column": ("column_bar.json",),
    "bar": ("column_bar.json",),
    "bar3d": ("column_bar.json", "three_d.json"),
    "area": ("area_pie.json",),
    "pie": ("area_pie.json",),
    "histogram": ("distribution.json",),
    "box": ("distribution.json",),
    "dendrogram": ("distribution.json", "specialized.json"),
    "line_symbol": ("errorbar.json",),
    "scatter": ("errorbar.json",),
    "bubble": ("errorbar.json",),
    "errorbar": ("errorbar.json",),
    "heatmap": ("field_color.json", "image.json"),
    "contour": ("field_color.json",),
    "image": ("field_color.json", "image.json"),
    "matrix_heatmap": ("field_color.json", "image.json"),
    "scatter3d": ("three_d.json",),
    "surface3d": ("field_color.json", "three_d.json"),
    "waterfall": ("three_d.json",),
    "ribbon3d": ("three_d.json",),
    "vector": ("specialized.json",),
    "vector3d": ("specialized.json", "three_d.json"),
    "polar": ("specialized.json",),
    "smith": ("specialized.json",),
    "ternary": ("specialized.json",),
    "financial": ("financial.json",),
}


STYLE_CAPABILITY_PACKAGE = "origin_mcp.style_capabilities"
CORE_RESOURCE = "core.json"


@dataclass(frozen=True)
class PlotStyleCapability:
    name: str
    controls: str
    aliases: tuple[str, ...]
    chart_types: tuple[str, ...]
    status: str
    setter: str | None = None
    origin_route: str | None = None
    value_semantics: str | None = None
    readable: bool = False
    readable_field: str | None = None
    notes: str | None = None
    source: str = CORE_RESOURCE

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str) -> PlotStyleCapability:
        return cls(
            name=str(data["name"]),
            controls=str(data["controls"]),
            aliases=tuple(str(item) for item in data.get("aliases", [])),
            chart_types=tuple(str(item) for item in data.get("chart_types", [])),
            status=str(data["status"]),
            setter=data.get("setter"),
            origin_route=data.get("origin_route"),
            value_semantics=data.get("value_semantics"),
            readable=bool(data.get("readable", False)),
            readable_field=data.get("readable_field"),
            notes=data.get("notes"),
            source=source,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "controls": self.controls,
            "aliases": list(self.aliases),
            "chart_types": list(self.chart_types),
            "status": self.status,
            "setter": self.setter,
            "origin_route": self.origin_route,
            "value_semantics": self.value_semantics,
            "readable": self.readable,
            "readable_field": self.readable_field,
            "notes": self.notes,
            "source": self.source,
        }


def normalize_chart_type(chart_type: str | None) -> str | None:
    if chart_type is None:
        return None
    value = chart_type.strip().lower().replace("-", "_").replace(" ", "_")
    return CHART_TYPE_ALIASES.get(value, value)


def plot_style_capabilities(
    chart_type: str | None = None,
    plot_type_id: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    plot_type_profile = plot_type_style_profile(plot_type_id) if plot_type_id is not None else None
    normalized_chart = normalize_chart_type(chart_type) or (
        plot_type_profile["chart_type"] if plot_type_profile else None
    )
    query_terms = _query_terms(query)
    resources_to_load = _resources_for_query(normalized_chart, query_terms)
    capabilities = _load_capabilities(resources_to_load)
    matches = [
        item
        for item in capabilities
        if _matches_chart(item, normalized_chart) and _matches_query(item, query_terms)
    ]
    return {
        "chart_type": normalized_chart,
        "plot_type": plot_type_profile,
        "query": query,
        "loaded_sources": list(resources_to_load),
        "count": len(matches),
        "capabilities": [item.as_dict() for item in matches],
    }


def resolve_plot_style_capability(
    property_name: str,
    chart_type: str | None = None,
    plot_type_id: int | None = None,
) -> dict[str, Any]:
    property_key = property_name.strip().lower().replace("-", "_").replace(" ", "_")
    if not property_key:
        raise ValueError("property_name is empty.")
    result = plot_style_capabilities(chart_type=chart_type, plot_type_id=plot_type_id)
    matches = [
        item for item in result["capabilities"] if _capability_name_matches(item, property_key)
    ]
    if not matches:
        raise ValueError(f"Unsupported plot style property: {property_name}.")
    if len(matches) > 1:
        implemented = [item for item in matches if item["status"] == "implemented"]
        if len(implemented) == 1:
            matches = implemented
        else:
            names = ", ".join(item["name"] for item in matches)
            raise ValueError(f"Ambiguous plot style property {property_name!r}: {names}.")
    capability = matches[0]
    return {
        **result,
        "capability": capability,
    }


def all_plot_style_capabilities() -> tuple[PlotStyleCapability, ...]:
    return _load_capabilities(_all_resources())


def plot_style_capability_count() -> int:
    return len(all_plot_style_capabilities())


def plot_type_style_profile(plot_type_id: int | None) -> dict[str, Any] | None:
    if plot_type_id is None:
        return None
    item = next((plot for plot in PLOT_TYPE_CATALOG if plot["id"] == plot_type_id), None)
    if item is None:
        return None
    chart_type = _chart_type_for_plot_type(item)
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "input": item["input"],
        "templates": item.get("templates", []),
        "chart_type": chart_type,
        "style_sources": list(_dedupe(EXTENSIONS_BY_CHART_TYPE.get(chart_type, ()))),
    }


def all_plot_type_style_profiles() -> tuple[dict[str, Any], ...]:
    return tuple(
        profile
        for profile in (plot_type_style_profile(item["id"]) for item in PLOT_TYPE_CATALOG)
        if profile is not None
    )


def _resources_for_query(
    chart_type: str | None,
    query_terms: tuple[str, ...],
) -> tuple[str, ...]:
    if chart_type:
        return _dedupe((CORE_RESOURCE, *EXTENSIONS_BY_CHART_TYPE.get(chart_type, ())))
    if query_terms:
        return _all_resources()
    return (CORE_RESOURCE,)


def _all_resources() -> tuple[str, ...]:
    extension_resources = {item for items in EXTENSIONS_BY_CHART_TYPE.values() for item in items}
    return _dedupe((CORE_RESOURCE, *sorted(extension_resources)))


def _dedupe(resources_to_load: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    result = []
    for name in resources_to_load:
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return tuple(result)


@cache
def _load_capabilities(resources_to_load: tuple[str, ...]) -> tuple[PlotStyleCapability, ...]:
    capabilities: list[PlotStyleCapability] = []
    for resource_name in resources_to_load:
        capabilities.extend(_load_resource(resource_name))
    return tuple(capabilities)


@cache
def _load_resource(resource_name: str) -> tuple[PlotStyleCapability, ...]:
    resource = resources.files(STYLE_CAPABILITY_PACKAGE).joinpath(resource_name)
    data = json.loads(resource.read_text(encoding="utf-8"))
    return tuple(PlotStyleCapability.from_dict(item, source=resource_name) for item in data)


def _matches_chart(item: PlotStyleCapability, chart_type: str | None) -> bool:
    return chart_type is None or chart_type in item.chart_types or "common" in item.chart_types


def _matches_query(item: PlotStyleCapability, query_terms: tuple[str, ...]) -> bool:
    if not query_terms:
        return True
    haystack = " ".join(
        (
            item.name,
            item.controls,
            " ".join(item.aliases),
            " ".join(item.chart_types),
            item.status,
            item.setter or "",
            item.origin_route or "",
            item.value_semantics or "",
            item.notes or "",
        )
    ).lower()
    return all(term in haystack for term in query_terms)


def _capability_name_matches(capability: dict[str, Any], property_key: str) -> bool:
    names = [
        str(capability["name"]),
        *(str(alias) for alias in capability.get("aliases", [])),
    ]
    normalized = {
        item.strip().lower().replace("-", "_").replace(" ", "_") for item in names if item.strip()
    }
    return property_key in normalized


def _query_terms(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    normalized = query.lower().replace("/", " ").replace("_", " ").replace("-", " ")
    return tuple(term for term in normalized.split() if term)


def _chart_type_for_plot_type(item: dict[str, Any]) -> str:
    plot_id = int(item["id"])
    explicit = {
        101: "scatter3d",
        103: "surface3d",
        105: "matrix_heatmap",
        108: "dendrogram",
        183: "vector3d",
        184: "scatter3d",
        185: "contour",
        186: "polar",
        191: "smith",
        192: "polar",
        193: "bubble",
        194: "bubble",
        205: "financial",
        208: "vector",
        210: "waterfall",
        211: "ribbon3d",
        212: "bar3d",
        218: "vector",
        220: "image",
        221: "financial",
        225: "pie",
        226: "contour",
        231: "errorbar",
        233: "errorbar",
        240: "scatter3d",
        242: "surface3d",
        243: "contour",
        245: "ternary",
        247: "scatter",
        248: "bubble",
    }
    if plot_id in explicit:
        return explicit[plot_id]
    name = str(item["name"]).lower()
    templates = " ".join(str(template).lower() for template in item.get("templates", []))
    text = f"{name} {templates}"
    if "column" in text:
        return "column"
    if "bar" in text:
        return "bar"
    if "area" in text:
        return "area"
    if "box" in text:
        return "box"
    if "hist" in text:
        return "histogram"
    if "contour" in text:
        return "contour"
    if "scatter" in text:
        return "scatter"
    if "line" in text:
        return "line"
    return normalize_chart_type(str(item.get("category", ""))) or "line"
