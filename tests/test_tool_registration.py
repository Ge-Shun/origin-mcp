"""Consistency checks tying MCP tool *registration* back to the source.

The server registers tools purely as an import side effect: every
``@_mcp_tool()``-decorated function must be imported into
``origin_mcp.server`` (see the long re-export block there) before
``FastMCP`` ever sees it. A tool that is defined but never imported
silently disappears with no error, and the compact allow-list in
``COMPACT_TOOL_NAMES`` is a hand-maintained set of strings that can drift
away from the real function names.

These tests scan the tool source with ``ast`` to discover the intended
tool surface and assert the runtime registration matches it, so adding a
tool without wiring it up (or misspelling a compact name) fails loudly
instead of going unnoticed.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import origin_mcp.server as server
from origin_mcp.analysis_adapters import ANALYSIS_ADAPTERS
from origin_mcp.knowledge import COLLECTIONS
from origin_mcp.tools._shared import (
    ANALYSIS_TOOL_NAMES,
    DATA_TOOL_NAMES,
    PLOT_TOOL_NAMES,
    STANDARD_TOOL_NAMES,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOLS_DIR = _REPO_ROOT / "src" / "origin_mcp" / "tools"


def _is_mcp_tool_decorator(decorator: ast.expr) -> bool:
    """True for an ``@_mcp_tool()`` (or ``@_mcp_tool``) decorator node."""

    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(target, ast.Name) and target.id == "_mcp_tool"


def _discover_decorated_tools() -> dict[str, Path]:
    """Map every ``@_mcp_tool``-decorated function name to its source file."""

    discovered: dict[str, Path] = {}
    duplicates: list[str] = []
    for path in sorted(_TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not any(_is_mcp_tool_decorator(dec) for dec in node.decorator_list):
                continue
            if node.name in discovered:
                duplicates.append(node.name)
            discovered[node.name] = path
    assert not duplicates, f"Duplicate @_mcp_tool function names: {sorted(set(duplicates))}"
    return discovered


def _registered_tool_names(profile: str) -> set[str]:
    """Tool names FastMCP registers for the given ``ORIGIN_MCP_TOOL_PROFILE``.

    Run in a subprocess so the module-import-time registration happens under
    the requested profile without mutating this interpreter's already-imported
    ``origin_mcp.server``.
    """

    env = {**os.environ, "ORIGIN_MCP_TOOL_PROFILE": profile}
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            (
                "import asyncio, json, origin_mcp.server as s; "
                "print(json.dumps([t.name for t in asyncio.run(s.mcp.list_tools())]))"
            ),
        ],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
    )
    return set(json.loads(output.strip()))


def test_every_decorated_tool_is_imported_into_server() -> None:
    """A tool defined but missing from server.py's import block never registers."""

    decorated = _discover_decorated_tools()
    missing = {
        name: str(path.relative_to(_REPO_ROOT))
        for name, path in decorated.items()
        if not hasattr(server, name)
    }
    assert not missing, (
        "These @_mcp_tool functions are not imported into origin_mcp.server, "
        f"so they will never be registered as MCP tools: {missing}"
    )


def test_full_profile_registers_exactly_the_decorated_tools() -> None:
    """The full profile surface is derived from source, not a magic count."""

    decorated = set(_discover_decorated_tools())
    registered = _registered_tool_names("full")
    assert registered == decorated, {
        "defined_but_not_registered": sorted(decorated - registered),
        "registered_but_not_defined": sorted(registered - decorated),
    }


def test_compact_tool_names_reference_real_tools() -> None:
    """Every name in COMPACT_TOOL_NAMES must be an actual decorated tool."""

    decorated = set(_discover_decorated_tools())
    unknown = set(server.COMPACT_TOOL_NAMES) - decorated
    assert not unknown, f"COMPACT_TOOL_NAMES references unknown tools: {sorted(unknown)}"


def test_compact_profile_registers_exactly_the_compact_allow_list() -> None:
    """In-process compact registration matches the declared allow-list."""

    names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert names == set(server.COMPACT_TOOL_NAMES)


def test_focused_profiles_register_their_declared_allow_lists() -> None:
    expected = {
        "data": DATA_TOOL_NAMES,
        "plot": PLOT_TOOL_NAMES,
        "analysis": ANALYSIS_TOOL_NAMES,
        "standard": STANDARD_TOOL_NAMES,
    }

    for profile, names in expected.items():
        assert _registered_tool_names(profile) == set(names)


def test_plot_profile_includes_template_tools() -> None:
    """The focused plot profile includes the user template library."""

    names = _registered_tool_names("plot")
    assert {
        "origin_save_graph_template",
        "origin_search_templates",
        "origin_list_user_templates",
        "origin_delete_template",
        "origin_rename_template",
        "origin_update_template_metadata",
    } <= names


def test_analysis_profile_includes_analysis_wrappers() -> None:
    """Analysis mode exposes the generic dispatcher plus the structured fits.

    The other named analyses (polynomial_fit, smooth, the t-tests, fft, ...) are
    reachable via origin_run_analysis(analysis=...) and live in the full profile
    only, so the compact surface stays small.
    """

    names = _registered_tool_names("analysis")

    assert {
        "origin_run_analysis",
        "origin_linear_fit",
        "origin_nonlinear_fit_structured",
        "origin_list_fit_functions",
    } <= names

    # These specialized wrappers are intentionally full-profile only now.
    assert not (
        {
            "origin_polynomial_fit",
            "origin_smooth",
            "origin_descriptive_stats",
            "origin_differentiate",
            "origin_integrate",
            "origin_peak_find",
            "origin_interpolate",
            "origin_normalize",
            "origin_ttest_one_sample",
            "origin_ttest_two_sample",
            "origin_ttest_paired",
            "origin_fft",
            "origin_ifft",
            "origin_correlation",
            "origin_nonlinear_fit",
        }
        & names
    )


def test_compact_profile_stays_bounded() -> None:
    names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}

    assert len(names) == 25
    assert "origin_plot" in names
    assert "origin_run_analysis" in names
    assert "origin_plot_line" not in names
    assert "origin_linear_fit" not in names


def test_compact_tool_schemas_describe_every_top_level_parameter() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    missing = {
        tool.name: [
            name
            for name, schema in tool.inputSchema.get("properties", {}).items()
            if not schema.get("description")
        ]
        for tool in tools
    }

    assert not {name: params for name, params in missing.items() if params}


def test_compact_dispatchers_publish_finite_choices() -> None:
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}

    analysis_schema = tools["origin_run_analysis"].inputSchema["properties"]["analysis"]
    assert set(analysis_schema["enum"]) == set(ANALYSIS_ADAPTERS)
    assert (
        "polynomial_fit uses order"
        in tools["origin_run_analysis"].inputSchema["properties"]["options"]["description"]
    )

    plot_schema = tools["origin_plot"].inputSchema["properties"]
    assert {"line", "scatter", "bar", "ternary", "vector_3d"} <= set(plot_schema["kind"]["enum"])
    assert set(plot_schema["style_mode"]["enum"]) == {
        "origin_default",
        "template",
        "theme",
        "none",
        "nature",
    }

    browse_schema = tools["origin_browse_knowledge"].inputSchema["properties"]
    assert set(browse_schema["collection"]["enum"]) == set(COLLECTIONS)


def test_figure_spec_tools_expose_the_nested_model_schema() -> None:
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}

    for name in ("origin_plan_figure_spec", "origin_execute_figure_spec"):
        schema = tools[name].inputSchema
        assert schema["properties"]["spec"]["$ref"] == "#/$defs/FigureSpec"
        figure_properties = schema["$defs"]["FigureSpec"]["properties"]
        assert {"figure", "data", "page", "layers", "plots", "style", "export"} <= set(
            figure_properties
        )


def test_request_model_descriptions_and_constraints_reach_tool_schema() -> None:
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}

    import_schema = tools["origin_import_table"].inputSchema["properties"]
    assert import_schema["path"]["description"].startswith("Absolute path")
    assert import_schema["header"]["anyOf"][0]["minimum"] == 0
    assert import_schema["nrows"]["anyOf"][0]["minimum"] == 0

    analysis_schema = tools["origin_run_analysis"].inputSchema["properties"]
    assert analysis_schema["output_max_rows"]["minimum"] == 1
    assert analysis_schema["output_max_rows"]["maximum"] == 10_000

    diagnose_schema = tools["origin_diagnose_worksheet"].inputSchema["properties"]
    assert diagnose_schema["high_missing_threshold"]["minimum"] == 0
    assert diagnose_schema["high_missing_threshold"]["maximum"] == 1
