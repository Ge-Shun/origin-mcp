import ast
from pathlib import Path

import origin_mcp.server as server
from origin_mcp.knowledge import browse_knowledge, query_knowledge


def test_browse_knowledge_lists_collections() -> None:
    result = browse_knowledge()

    names = {item["name"] for item in result["collections"]}
    assert {"mcp_tools", "reference", "python_api", "labtalk", "official_docs"} <= names


def test_mcp_tool_knowledge_covers_all_server_origin_tools() -> None:
    tool_names = _tool_module_function_names()

    groups = browse_knowledge("mcp_tools")["children"]
    indexed = set()
    for group in groups:
        group_result = browse_knowledge("mcp_tools", group["path"])
        indexed.update(
            item["title"]
            for item in group_result["children"]
            if item["title"].startswith("origin_")
        )

    assert tool_names <= indexed


def _tool_module_function_names() -> set[str]:
    tools_dir = Path(server.__file__).with_name("tools")
    names: set[str] = set()
    for path in tools_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        module = ast.parse(path.read_text(encoding="utf-8"))
        names.update(
            node.name
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("origin_")
        )
    return names


def test_browse_reference_plot_type_entry() -> None:
    result = browse_knowledge("reference", "plot-types/200")

    entry = result["entry"]
    assert entry["metadata"]["plot_type_id"] == 200
    assert entry["metadata"]["direct_tool"] == "origin_plot_line"
    assert "Line" in entry["title"]


def test_browse_reference_plotting_entrypoints() -> None:
    result = browse_knowledge("reference", "plotting/recommended-entrypoints")

    entry = result["entry"]
    assert "origin_plot_auto" in entry["metadata"]["compact_tools"]
    assert entry["metadata"]["expert_profile"] == "ORIGIN_MCP_TOOL_PROFILE=full"


def test_browse_reference_tool_profiles() -> None:
    result = browse_knowledge("reference", "tool-profiles")

    entry = result["entry"]
    assert entry["metadata"]["default_profile"] == "compact"
    assert entry["metadata"]["full_profile_env"] == "ORIGIN_MCP_TOOL_PROFILE=full"


def test_browse_reference_documentation_sources_of_truth() -> None:
    result = browse_knowledge("reference", "documentation/sources-of-truth")

    entry = result["entry"]
    assert entry["metadata"]["tool_catalog"] == "mcp_tools knowledge collection"
    assert entry["metadata"]["workflow_guidance"] == "reference knowledge collection"


def test_browse_reference_bridge_startup() -> None:
    result = browse_knowledge("reference", "bridge/startup")

    entry = result["entry"]
    assert entry["metadata"]["addon"] == "addon.py"
    assert "ORIGIN_MCP_BRIDGE_PORT" in entry["metadata"]["env"]


def test_browse_reference_bridge_tasks() -> None:
    result = browse_knowledge("reference", "bridge/tasks")

    entry = result["entry"]
    assert "running" in entry["metadata"]["states"]
    assert entry["metadata"]["status_tool"] == "origin_bridge_task_status"


def test_browse_reference_bridge_diagnostics() -> None:
    result = browse_knowledge("reference", "bridge/diagnostics")

    entry = result["entry"]
    assert entry["metadata"]["primary_tool"] == "origin_doctor"


def test_browse_reference_bridge_file_to_figure() -> None:
    result = browse_knowledge("reference", "bridge/file-to-figure")

    entry = result["entry"]
    assert entry["metadata"]["script"] == "examples/smoke_bridge.py"
    assert entry["metadata"]["failure_diagnostic"] == "origin_doctor"


def test_query_reference_finds_heatmap_plot_type() -> None:
    result = query_knowledge("heatmap plot type id", collection="reference", limit=5)

    paths = [item["path"] for item in result["results"]]
    assert "plot-types/105" in paths
    assert result["count"] <= 5


def test_query_reference_finds_plot_style_registry_by_chinese_terms() -> None:
    result = query_knowledge("柱子太宽", collection="reference", limit=5)

    paths = [item["path"] for item in result["results"]]
    assert "plot-style-capabilities/bar_gap" in paths
    entry = browse_knowledge("reference", "plot-style-capabilities/bar_gap")["entry"]
    assert entry["metadata"]["origin_route"] == "LabTalk set -vg"
    assert entry["metadata"]["value_semantics"] == (
        "gap percent; larger values make bars/columns narrower"
    )


def test_query_reference_finds_style_registry_for_other_chart_types() -> None:
    line = query_knowledge("折线粗细", collection="reference", limit=5)
    symbol = query_knowledge("点大小", collection="reference", limit=5)
    colormap = query_knowledge("热图 色带", collection="reference", limit=5)

    assert "plot-style-capabilities/line_width" in [item["path"] for item in line["results"]]
    assert "plot-style-capabilities/symbol_size" in [item["path"] for item in symbol["results"]]
    assert "plot-style-capabilities/colormap" in [item["path"] for item in colormap["results"]]


def test_browse_reference_has_plot_type_style_profile() -> None:
    result = browse_knowledge("reference", "plot-style-capabilities/plot-types/203")

    entry = result["entry"]
    assert entry["metadata"]["id"] == 203
    assert entry["metadata"]["chart_type"] == "column"
    assert entry["metadata"]["style_sources"] == ["column_bar.json"]


def test_browse_python_api_by_dot_path() -> None:
    result = browse_knowledge("python_api", "originpro.find_graph")

    assert result["entry"]["path"] == "originpro.find_graph"
    assert "Graph lookup" in result["entry"]["body"]


def test_browse_python_api_root_shows_dot_path_children() -> None:
    result = browse_knowledge("python_api", "originpro")

    child_paths = {item["path"] for item in result["children"]}
    assert "originpro.analysis" in child_paths
    assert "originpro.find_graph" in child_paths
    assert "originpro.find_sheet" in child_paths


def test_query_python_api_finds_official_class_index() -> None:
    result = query_knowledge("NLFit nonlinear fitting", collection="python_api", limit=5)

    assert any(item["path"] == "originpro.analysis.NLFit" for item in result["results"])


def test_browse_labtalk_command_category() -> None:
    result = browse_knowledge("labtalk", "commands/display-control")

    assert "axis" in result["entry"]["keywords"]
    assert "legend" in result["entry"]["keywords"]
    assert result["entry"]["metadata"]["official_url"].endswith("/display-control/")


def test_query_official_docs_finds_xfunction_reference() -> None:
    result = query_knowledge("x-function plotting", collection="official_docs", limit=5)

    assert any(item["path"] == "x-function/plotting" for item in result["results"])


def test_browse_official_docs_has_versioned_labtalk_category() -> None:
    result = browse_knowledge("official_docs", "labtalk/commands/display-control", version="2026")

    entry = result["entry"]
    assert entry["metadata"]["doc_family"] == "labtalk"
    assert entry["metadata"]["doc_kind"] == "command_category"
    assert entry["metadata"]["versions"] == ["2026"]
    assert entry["metadata"]["official_url"].rstrip("/").endswith("/display-control")


def test_browse_official_docs_root_exposes_fine_grained_children() -> None:
    result = browse_knowledge("official_docs", "python/originpro-api")

    child_paths = {item["path"] for item in result["children"]}
    assert "python/originpro-api/analysis" in child_paths
    assert "python/originpro-api/graph" in child_paths
    assert "python/originpro-api/worksheet" in child_paths


def test_query_official_docs_filters_by_version() -> None:
    current = query_knowledge("originpro Axis", collection="official_docs", version="2026", limit=5)
    old = query_knowledge("originpro Axis", collection="official_docs", version="2025", limit=5)
    unsupported = query_knowledge(
        "originpro Axis",
        collection="official_docs",
        version="2023",
        limit=5,
    )

    assert any(item["path"] == "python/originpro-api/graph/Axis" for item in current["results"])
    assert any(item["path"] == "python/originpro-api/graph/Axis" for item in old["results"])
    assert old["results"][0]["metadata"]["versions"] == ["2025"]
    assert old["results"][0]["metadata"]["version_status"] == "baseline"
    assert unsupported["results"] == []


def test_generated_official_docs_include_xfunction_function() -> None:
    result = browse_knowledge("official_docs", "x-function/plotting/plotxy", version="2026")

    assert result["entry"]["metadata"]["doc_kind"] == "xfunction"
    assert result["entry"]["metadata"]["official_url"].endswith("/plotxy/")


def test_generated_official_docs_include_labtalk_command() -> None:
    result = browse_knowledge("official_docs", "labtalk/commands/display-control/legend")

    assert result["entry"]["metadata"]["doc_kind"] == "command"
    assert result["entry"]["metadata"]["official_url"].endswith("/legend-cmd/")


def test_generated_official_docs_include_originpro_member() -> None:
    result = browse_knowledge("official_docs", "python/originpro-api/graph/Axis/scale")

    assert result["entry"]["metadata"]["doc_kind"] == "member"
    assert result["entry"]["metadata"]["doc_family"] == "originpro_api"


def test_query_tool_alias_collection() -> None:
    result = query_knowledge("legend font position", collection="tools", limit=3)

    assert result["collection"] == "mcp_tools"
    assert any(item["path"].endswith("origin_format_legend") for item in result["results"])


def test_server_reference_wrapper_returns_tool_result() -> None:
    result = server.origin_query_reference("legend", limit=1)

    assert result["ok"] is True
    assert result["data"]["results"][0]["path"] == "graph/legend"


def test_server_rejects_unknown_knowledge_path() -> None:
    result = server.origin_browse_reference("missing/topic")

    assert result["ok"] is False
    assert result["error_code"] == "invalid_request"
