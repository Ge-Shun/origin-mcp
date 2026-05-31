from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    "柱状图": "column",
    "柱形图": "column",
    "柱图": "column",
    "条形图": "bar",
    "折线图": "line",
    "散点图": "scatter",
    "气泡图": "bubble",
    "箱线图": "box",
    "盒须图": "box",
    "热图": "heatmap",
    "等值线": "contour",
    "图片": "image",
    "图像": "image",
    "三维散点": "scatter3d",
    "三维曲面": "surface3d",
}


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
        }


PLOT_STYLE_CAPABILITIES: tuple[PlotStyleCapability, ...] = (
    PlotStyleCapability(
        name="color",
        controls="plot color for lines, markers, fills, and outlines where Origin supports it",
        aliases=("颜色", "线颜色", "填充色", "fill color", "line color", "marker color"),
        chart_types=COMMON_CHART_TYPES,
        status="implemented",
        setter="origin_set_plot_style(color=...)",
        origin_route="originpro Plot.color",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].color",
    ),
    PlotStyleCapability(
        name="line_width",
        controls="line, outline, or stroke width",
        aliases=("线宽", "线条粗细", "折线粗细", "边框线宽", "line thickness", "stroke width"),
        chart_types=(
            "line",
            "scatter",
            "line_symbol",
            "column",
            "bar",
            "area",
            "box",
            "bubble",
            "polar",
            "ternary",
            "vector",
            "errorbar",
            "contour",
        ),
        status="implemented",
        setter="origin_set_plot_style(line_width=...)",
        origin_route="LabTalk set -w / set -wp plus originpro line_width when available",
        value_semantics="points; origin-mcp also converts to Origin integer width units",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].line_width",
    ),
    PlotStyleCapability(
        name="line_style",
        controls="line dash/style pattern",
        aliases=("线型", "虚线", "dash", "line pattern"),
        chart_types=("line", "scatter", "line_symbol", "area", "polar", "ternary", "contour"),
        status="implemented",
        setter="origin_set_plot_style(line_style=...)",
        origin_route="LabTalk set -d",
        value_semantics="Origin integer line style code",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].line_style",
    ),
    PlotStyleCapability(
        name="symbol_kind",
        controls="marker/symbol shape",
        aliases=("符号", "点形状", "散点形状", "marker shape", "symbol shape"),
        chart_types=("scatter", "line_symbol", "bubble", "polar", "ternary", "scatter3d"),
        status="implemented",
        setter="origin_set_plot_style(symbol_kind=...)",
        origin_route="originpro Plot.symbol_kind",
        value_semantics="Origin integer symbol code",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].symbol_kind",
    ),
    PlotStyleCapability(
        name="symbol_size",
        controls="marker/symbol size",
        aliases=("点大小", "符号大小", "散点大小", "marker size", "symbol size"),
        chart_types=("scatter", "line_symbol", "bubble", "polar", "ternary", "scatter3d"),
        status="implemented",
        setter="origin_set_plot_style(symbol_size=...)",
        origin_route="originpro Plot.symbol_size",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].symbol_size",
    ),
    PlotStyleCapability(
        name="transparency",
        controls="plot transparency",
        aliases=("透明度", "alpha", "opacity"),
        chart_types=COMMON_CHART_TYPES,
        status="implemented",
        setter="origin_set_plot_style(transparency=...)",
        origin_route="originpro Plot.transparency",
        value_semantics="percent, 0 to 100",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].transparency",
    ),
    PlotStyleCapability(
        name="bar_gap",
        controls="2D column/bar visual width through inter-bar gap",
        aliases=(
            "柱宽",
            "柱子宽度",
            "柱子太宽",
            "柱间距",
            "条宽",
            "bar width",
            "column width",
            "bar gap",
            "gap",
        ),
        chart_types=("column", "bar", "grouped_column", "grouped_bar"),
        status="implemented",
        setter="origin_set_plot_style(bar_gap=...)",
        origin_route="LabTalk set -vg",
        value_semantics="gap percent; larger values make bars/columns narrower",
        readable=True,
        readable_field="get_graph_info.layers[].plots[].bar_gap",
    ),
    PlotStyleCapability(
        name="palette_name",
        controls="semantic palette selection during Nature-style formatting",
        aliases=("配色", "调色板", "颜色方案", "palette", "nature palette"),
        chart_types=COMMON_CHART_TYPES,
        status="implemented",
        setter="origin_apply_nature_style(palette_name=...)",
        origin_route="origin-mcp palette registry",
        notes="Use origin_palette_catalog to list available palettes.",
    ),
    PlotStyleCapability(
        name="colormap",
        controls="color map for heatmap, contour, image, and matrix color plots",
        aliases=("色带", "色标", "热图配色", "颜色映射", "color map", "colour map"),
        chart_types=("heatmap", "contour", "image", "matrix_heatmap"),
        status="planned",
        setter=None,
        origin_route=(
            "Origin colormap/palette properties; not yet exposed as a stable semantic tool"
        ),
        notes=(
            "Use origin_palette_catalog or LabTalk for now when exact colormap control is "
            "required."
        ),
    ),
    PlotStyleCapability(
        name="contour_levels",
        controls="contour level count and boundaries",
        aliases=("等值线级别", "等高线级别", "levels", "contour levels"),
        chart_types=("contour", "heatmap"),
        status="planned",
        setter=None,
        origin_route="Origin contour level settings; not yet exposed as a stable semantic tool",
    ),
    PlotStyleCapability(
        name="box_width",
        controls="box width in box/box-and-whisker plots",
        aliases=("箱体宽度", "箱线图宽度", "box width", "box gap"),
        chart_types=("box",),
        status="planned",
        setter=None,
        origin_route="Origin box plot spacing settings; not yet exposed as a stable semantic tool",
    ),
    PlotStyleCapability(
        name="errorbar_cap",
        controls="error bar cap width and cap style",
        aliases=("误差棒帽宽", "误差线帽", "error cap", "cap width"),
        chart_types=("errorbar", "line_symbol", "scatter"),
        status="planned",
        setter=None,
        origin_route="Origin error-bar plot details; not yet exposed as a stable semantic tool",
    ),
    PlotStyleCapability(
        name="image_panel_annotations",
        controls="image panel labels, scale bar labels, channel labels, and dark panel styling",
        aliases=("比例尺", "图像标注", "scale bar", "channel label", "panel label"),
        chart_types=("image", "heatmap", "matrix_heatmap"),
        status="implemented",
        setter="origin_apply_image_panel_style(...)",
        origin_route="origin-mcp graph labels and panel styling",
        notes="This controls image-panel annotations, not raw pixel contrast.",
    ),
)


def normalize_chart_type(chart_type: str | None) -> str | None:
    if chart_type is None:
        return None
    value = chart_type.strip().lower().replace("-", "_").replace(" ", "_")
    return CHART_TYPE_ALIASES.get(value, value)


def plot_style_capabilities(
    chart_type: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    normalized_chart = normalize_chart_type(chart_type)
    query_terms = _query_terms(query)
    matches = [
        item
        for item in PLOT_STYLE_CAPABILITIES
        if _matches_chart(item, normalized_chart) and _matches_query(item, query_terms)
    ]
    return {
        "chart_type": normalized_chart,
        "query": query,
        "count": len(matches),
        "capabilities": [item.as_dict() for item in matches],
    }


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


def _query_terms(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    normalized = query.lower().replace("/", " ").replace("_", " ").replace("-", " ")
    return tuple(term for term in normalized.split() if term)
