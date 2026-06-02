from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .analysis_adapters import ANALYSIS_ADAPTERS
from .compat import PLOT_TYPE_CATALOG
from .knowledge_entries import (
    COLLECTIONS,
    LABTALK_ENTRIES,
    OFFICIAL_DOC_ENTRIES,
    OFFICIAL_DOC_PAGES,
    OFFICIAL_DOC_VERIFIED,
    OFFICIAL_URLS,
    PYTHON_API_ENTRIES,
    REFERENCE_ENTRIES,
    TOOL_GROUP_SUMMARIES,
    XFUNCTION_ENTRIES,
    KnowledgeEntry,
    _official_doc_entries,
    _official_doc_pages,
    _originpro_class_entries,
)
from .plot_style_registry import (
    all_plot_style_capabilities,
    all_plot_type_style_profiles,
    plot_style_capability_count,
)

__all__ = [
    "COLLECTIONS",
    "LABTALK_ENTRIES",
    "OFFICIAL_DOC_ENTRIES",
    "OFFICIAL_DOC_PAGES",
    "OFFICIAL_DOC_VERIFIED",
    "OFFICIAL_URLS",
    "PYTHON_API_ENTRIES",
    "REFERENCE_ENTRIES",
    "TOOL_GROUP_SUMMARIES",
    "XFUNCTION_ENTRIES",
    "KnowledgeEntry",
    "browse_knowledge",
    "query_knowledge",
    "_official_doc_entries",
    "_official_doc_pages",
    "_originpro_class_entries",
]


def browse_knowledge(
    collection: str | None = None,
    path: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    if collection is None:
        return {
            "collections": [
                {"name": name, "summary": summary} for name, summary in sorted(COLLECTIONS.items())
            ]
        }

    collection = _normalize_collection(collection)
    entries = _entries(official_docs_version=version if collection == "official_docs" else None)
    path_key = _normalize_path(path)
    scoped = [entry for entry in entries if entry.collection == collection]
    if version:
        scoped = [entry for entry in scoped if _entry_supports_version(entry, version)]

    exact = next((entry for entry in scoped if _normalize_path(entry.path) == path_key), None)
    children = _children(scoped, path_key)
    if exact:
        return {
            "collection": collection,
            "path": exact.path,
            "entry": exact.as_dict(include_body=True),
            "children": children,
        }
    if children or not path_key:
        return {"collection": collection, "path": path or "", "children": children}

    raise ValueError(f"Knowledge path not found: {collection}/{path}")


def query_knowledge(
    query: str,
    collection: str | None = None,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    query_text = query.strip()
    if not query_text:
        raise ValueError("query is empty.")
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    if collection is not None:
        collection = _normalize_collection(collection)
    entries = _entries(official_docs_version=version if collection == "official_docs" else None)
    if collection is not None:
        entries = [entry for entry in entries if entry.collection == collection]
    if version:
        entries = [entry for entry in entries if _entry_supports_version(entry, version)]

    scored = []
    for entry in entries:
        score = _score_entry(entry, query_text)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].collection, item[1].path))

    limit_actual = min(limit, 50)
    return {
        "query": query_text,
        "collection": collection,
        "version": version,
        "count": len(scored[:limit_actual]),
        "results": [
            entry.as_dict(include_body=False) | {"score": score}
            for score, entry in scored[:limit_actual]
        ],
    }


def _entries(official_docs_version: str | None = None) -> list[KnowledgeEntry]:
    return [
        *_tool_entries(),
        *REFERENCE_ENTRIES,
        *_official_doc_entries(official_docs_version),
        *_plot_style_entries(),
        *_plot_type_entries(),
        *_analysis_entries(),
        *PYTHON_API_ENTRIES,
        *_originpro_class_entries(),
        *LABTALK_ENTRIES,
        *XFUNCTION_ENTRIES,
    ]


def _tool_entries() -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    tool_docs = _server_tool_docs()
    groups: dict[str, list[dict[str, str]]] = {group: [] for group in TOOL_GROUP_SUMMARIES}
    for item in tool_docs:
        groups.setdefault(item["group"], []).append(item)

    for group, summary in TOOL_GROUP_SUMMARIES.items():
        tools = groups.get(group, [])
        entries.append(
            KnowledgeEntry(
                collection="mcp_tools",
                path=group,
                title=group.replace("_", " ").title(),
                summary=summary,
                body=f"{summary} Tools: {', '.join(item['name'] for item in tools)}.",
                keywords=(group, *(item["name"] for item in tools)),
                metadata={"tool_count": len(tools)},
            )
        )
        for item in tools:
            tool = item["name"]
            description = item["doc"] or f"{tool} is an origin-mcp tool."
            entries.append(
                KnowledgeEntry(
                    collection="mcp_tools",
                    path=f"{group}/{tool}",
                    title=tool,
                    summary=description,
                    body=(
                        f"{tool} belongs to the {group} workflow group. {description} "
                        "Use docs/tools.md and the MCP tool schema for parameter-level details."
                    ),
                    keywords=(tool, group, tool.removeprefix("origin_")),
                    metadata={"group": group, "source": "src/origin_mcp/tools/*.py"},
                )
            )
    return entries


def _server_tool_docs() -> list[dict[str, str]]:
    tools = []
    tools_dir = Path(__file__).with_name("tools")
    for tool_path in sorted(tools_dir.glob("*.py")):
        if tool_path.name.startswith("_"):
            continue
        module = ast.parse(tool_path.read_text(encoding="utf-8"))
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("origin_"):
                tools.append(
                    {
                        "name": node.name,
                        "doc": ast.get_docstring(node) or "",
                        "group": _tool_group_for_name(node.name),
                    }
                )
    return tools


def _tool_group_for_name(name: str) -> str:
    if name in {
        "origin_browse_knowledge",
        "origin_query_knowledge",
        "origin_browse_reference",
        "origin_query_reference",
        "origin_browse_python_api",
        "origin_query_python_api",
        "origin_browse_labtalk",
        "origin_query_labtalk",
        "origin_browse_mcp_tools",
        "origin_query_mcp_tools",
        "origin_browse_official_docs",
        "origin_query_official_docs",
        "origin_plot_style_capabilities",
        "origin_plot_style_setter_coverage",
    }:
        return "knowledge"
    if name.startswith(("origin_import_", "origin_append_", "origin_read_", "origin_write_")):
        return "worksheet"
    if name.startswith(("origin_get_worksheet", "origin_set_column", "origin_export_worksheet")):
        return "worksheet"
    if name in {
        "origin_add_calculated_column",
        "origin_add_calculated_columns",
        "origin_sort_worksheet",
        "origin_get_cell_value",
        "origin_set_cell_value",
        "origin_delete_columns",
        "origin_clear_worksheet",
        "origin_diagnose_worksheet",
        "origin_filter_rows",
        "origin_drop_duplicates",
        "origin_fill_missing",
        "origin_transpose_worksheet",
        "origin_merge_worksheets",
        "origin_concat_worksheets",
        "origin_pivot_worksheet",
        "origin_melt_worksheet",
    }:
        return "worksheet"
    if name.startswith("origin_plot_") or name in {
        "origin_recommend_chart",
        "origin_chart_atlas_route",
    }:
        return "plotting"
    if name.startswith("origin_export_") or name in {
        "origin_inspect_export",
        "origin_run_labtalk",
        "origin_quit",
        "origin_detach",
        "origin_release",
        "origin_force_quit",
    }:
        return "export_lifecycle"
    if name in {
        "origin_get_graph_info",
        "origin_get_layer_info",
        "origin_format_graph",
        "origin_set_axis",
        "origin_set_axis_break",
        "origin_set_plot_style",
        "origin_set_plot_property",
        "origin_apply_nature_style",
        "origin_diagnose_graph",
        "origin_apply_image_panel_style",
        "origin_add_plot_to_graph",
        "origin_add_inset",
        "origin_remove_plot_from_graph",
        "origin_change_plot_type",
        "origin_change_plot_data",
        "origin_set_graph_page",
        "origin_arrange_layers",
        "origin_add_graph_label",
        "origin_add_reference_line",
        "origin_format_legend",
    }:
        return "graph_editing"
    if name in {
        "origin_run_analysis",
        "origin_linear_fit",
        "origin_polynomial_fit",
        "origin_smooth",
        "origin_peak_find",
        "origin_differentiate",
        "origin_integrate",
        "origin_descriptive_stats",
        "origin_nonlinear_fit",
        "origin_list_fit_functions",
        "origin_nonlinear_fit_structured",
        "origin_interpolate",
        "origin_normalize",
        "origin_ttest_one_sample",
        "origin_ttest_two_sample",
        "origin_ttest_paired",
        "origin_fft",
        "origin_ifft",
        "origin_correlation",
    }:
        return "analysis"
    return "core"


def _plot_style_entries() -> list[KnowledgeEntry]:
    entries = [
        KnowledgeEntry(
            collection="reference",
            path="plot-style-capabilities",
            title="Plot style capability registry",
            summary=("Semantic registry for plot style controls across common Origin chart types."),
            body=(
                "This registry is the source of truth for semantic style controls exposed by "
                "origin-mcp. It maps user terms such as 柱宽, 折线粗细, 点大小, 色带, and "
                "误差棒帽宽 to MCP tools, Origin routes, supported chart types, and "
                "implementation status. Use origin_plot_style_capabilities for structured "
                "tool output. Use origin_set_plot_property when you want a single "
                "registry-backed style property applied only if a safe setter exists."
            ),
            keywords=(
                "plot style",
                "capability",
                "registry",
                "柱宽",
                "折线粗细",
                "点大小",
                "色带",
                "bar width",
                "colormap",
            ),
            metadata={"capability_count": plot_style_capability_count()},
        )
    ]
    for profile in all_plot_type_style_profiles():
        entries.append(
            KnowledgeEntry(
                collection="reference",
                path=f"plot-style-capabilities/plot-types/{profile['id']}",
                title=f"Plot Type {profile['id']} style profile",
                summary=(f"{profile['name']} maps to style chart type {profile['chart_type']}."),
                body=(
                    f"Origin Plot Type ID {profile['id']} ({profile['name']}) belongs to "
                    f"category {profile['category']} and uses input {profile['input']}. "
                    f"Templates: {', '.join(profile['templates']) or 'not specified'}. "
                    f"Style chart type: {profile['chart_type']}. "
                    f"Style sources: {', '.join(profile['style_sources']) or 'core only'}."
                ),
                keywords=(
                    "plot style",
                    "plot type id",
                    str(profile["id"]),
                    str(profile["name"]),
                    str(profile["category"]),
                    str(profile["chart_type"]),
                    *(profile["templates"]),
                    *(profile["style_sources"]),
                ),
                metadata=profile,
            )
        )
    for item in all_plot_style_capabilities():
        entries.append(
            KnowledgeEntry(
                collection="reference",
                path=f"plot-style-capabilities/{item.name}",
                title=item.name,
                summary=f"{item.name}: {item.controls}. Status: {item.status}.",
                body=(
                    f"{item.name} controls {item.controls}. "
                    f"Aliases: {', '.join(item.aliases)}. "
                    f"Chart types: {', '.join(item.chart_types)}. "
                    f"Status: {item.status}. "
                    f"Setter: {item.setter or 'not exposed as a stable semantic setter yet'}. "
                    f"Origin route: {item.origin_route or 'not specified'}. "
                    f"Value semantics: {item.value_semantics or 'not specified'}. "
                    "Readable field: "
                    f"{item.readable_field or 'not readable through get_graph_info'}. "
                    f"{item.notes or ''}"
                ).strip(),
                keywords=(
                    "plot style",
                    "style capability",
                    item.name,
                    item.controls,
                    item.status,
                    *(item.aliases),
                    *(item.chart_types),
                    *((item.setter,) if item.setter else ()),
                    *((item.origin_route,) if item.origin_route else ()),
                ),
                metadata=item.as_dict(),
            )
        )
    return entries


def _plot_type_entries() -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = [
        KnowledgeEntry(
            collection="reference",
            path="plot-types",
            title="Origin Plot Type IDs",
            summary="Catalog of documented Origin Plot Type ID routes covered by origin-mcp.",
            body=(
                "Each Plot Type ID entry records the Origin graph type name, expected input "
                "shape, templates, category, and the direct MCP tool when one is available."
            ),
            keywords=("plot type id", "template", "coverage", "plot"),
        )
    ]
    for item in PLOT_TYPE_CATALOG:
        direct_tool = item.get("direct_tool")
        templates = item.get("templates") or []
        entries.append(
            KnowledgeEntry(
                collection="reference",
                path=f"plot-types/{item['id']}",
                title=f"{item['id']} {item['name']}",
                summary=f"{item['name']} ({item['category']}); input: {item['input']}.",
                body=(
                    f"Origin Plot Type ID {item['id']} creates {item['name']}. "
                    f"Category: {item['category']}. Input shape: {item['input']}. "
                    f"Templates: {', '.join(templates) or 'not specified'}. "
                    "Direct MCP tool: "
                    f"{direct_tool or 'origin_plot_table_id/origin_plot_matrix_id'}."
                ),
                keywords=(
                    "plot type id",
                    str(item["id"]),
                    str(item["name"]),
                    str(item["category"]),
                    str(item["input"]),
                    *(str(template) for template in templates),
                    *(("direct_tool", direct_tool) if direct_tool else ()),
                ),
                metadata={
                    "plot_type_id": item["id"],
                    "category": item["category"],
                    "input": item["input"],
                    "templates": templates,
                    "direct_tool": direct_tool,
                },
            )
        )
    return entries


def _analysis_entries() -> list[KnowledgeEntry]:
    entries = [
        KnowledgeEntry(
            collection="reference",
            path="analysis/adapters",
            title="Analysis adapters",
            summary="Normalized Origin analysis names mapped to X-Functions.",
            body=(
                "origin_run_analysis resolves a supported analysis name or alias to an adapter, "
                "builds an X-Function command, runs it, and optionally reads structured output."
            ),
            keywords=("analysis", "x-function", "adapter", "fit"),
        )
    ]
    for adapter in ANALYSIS_ADAPTERS.values():
        entries.append(
            KnowledgeEntry(
                collection="reference",
                path=f"analysis/adapters/{adapter.name}",
                title=adapter.name,
                summary=f"Runs Origin X-Function {adapter.x_function}.",
                body=(
                    f"{adapter.name} maps to X-Function {adapter.x_function}. "
                    f"Aliases: {', '.join(adapter.aliases) or 'none'}. "
                    f"Range required: {adapter.range_required}. "
                    f"Minimum Origin version: {adapter.minimum_origin_version or 'not specified'}. "
                    f"{adapter.note}"
                ).strip(),
                keywords=("analysis", adapter.name, adapter.x_function, *adapter.aliases),
                metadata={
                    "x_function": adapter.x_function,
                    "aliases": list(adapter.aliases),
                    "minimum_origin_version": adapter.minimum_origin_version,
                    "range_required": adapter.range_required,
                    "input_option": adapter.input_option,
                    "output_option": adapter.output_option,
                    "option_aliases": adapter.option_aliases,
                    "symbol_options": list(adapter.symbol_options),
                },
            )
        )
    return entries


def _children(entries: list[KnowledgeEntry], path_key: str) -> list[dict[str, Any]]:
    child_map: dict[str, dict[str, Any]] = {}
    collection = entries[0].collection if entries else ""
    separator = "." if collection == "python_api" else "/"
    prefix = f"{path_key}{separator}" if path_key else ""
    for entry in entries:
        key = _normalize_path(entry.path)
        if path_key and not key.startswith(prefix):
            continue
        rest = key[len(prefix) :]
        if not rest:
            continue
        child_name = rest.split(separator, 1)[0]
        child_path = f"{prefix}{child_name}".strip(separator)
        exact_child = next(
            (item for item in entries if _normalize_path(item.path) == child_path),
            None,
        )
        child_map[child_path] = {
            "path": exact_child.path if exact_child else child_path,
            "title": exact_child.title if exact_child else child_name,
            "summary": exact_child.summary if exact_child else "Category",
            "kind": "entry" if exact_child else "category",
        }
    return [child_map[key] for key in sorted(child_map)]


def _score_entry(entry: KnowledgeEntry, query: str) -> int:
    terms = [term for term in query.lower().replace("/", " ").replace("_", " ").split() if term]
    title_path = f"{entry.title} {entry.path}".lower()
    summary_keywords = f"{entry.summary} {' '.join(entry.keywords)}".lower()
    body = entry.body.lower()
    score = 0
    for term in terms:
        if term in title_path:
            score += 5
        if term in summary_keywords:
            score += 3
        if term in body:
            score += 1
    phrase = query.lower()
    if phrase in title_path:
        score += 5
    if phrase in summary_keywords:
        score += 3
    return score


def _normalize_collection(collection: str) -> str:
    normalized = collection.strip().lower().replace("-", "_")
    aliases = {
        "tools": "mcp_tools",
        "mcp": "mcp_tools",
        "api": "python_api",
        "python": "python_api",
        "refs": "reference",
        "labtalk_xfunction": "labtalk",
        "xfunction": "labtalk",
        "x_function": "labtalk",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in COLLECTIONS:
        supported = ", ".join(sorted(COLLECTIONS))
        raise ValueError(f"Unsupported knowledge collection: {collection}. Supported: {supported}.")
    return normalized


def _normalize_path(path: str | None) -> str:
    if path is None:
        return ""
    return path.strip().strip("/").replace("\\", "/").lower()


def _entry_supports_version(entry: KnowledgeEntry, version: str) -> bool:
    versions = entry.metadata.get("versions")
    return not versions or str(version) in {str(item) for item in versions}
