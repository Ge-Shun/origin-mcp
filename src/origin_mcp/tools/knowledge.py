from __future__ import annotations

from typing import Any

from origin_mcp.knowledge import browse_knowledge, query_knowledge

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_plot_type_coverage(
    origin_version: float | None = None,
    show: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    """Report documented Origin plot type coverage by Origin version and MCP support."""

    return _wrap(
        lambda: _ok(
            "Collected Origin plot type coverage information.",
            **client.plot_type_coverage(
                origin_version=origin_version,
                show=show,
                refresh=refresh,
            ),
        )
    )


@_mcp_tool()
def origin_browse_knowledge(
    collection: str | None = None,
    topic: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Browse the local Origin knowledge base by collection and path."""

    return _wrap(
        lambda: _ok(
            "Browsed Origin knowledge base.",
            **browse_knowledge(collection=collection, path=topic, version=version),
        )
    )


@_mcp_tool()
def origin_query_knowledge(
    query: str,
    collection: str | None = None,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search the local Origin knowledge base by keyword."""

    return _wrap(
        lambda: _ok(
            "Searched Origin knowledge base.",
            **query_knowledge(query=query, collection=collection, version=version, limit=limit),
        )
    )


@_mcp_tool()
def origin_browse_reference(topic: str | None = None, version: str | None = None) -> dict[str, Any]:
    """Browse Origin workflow reference notes, plot IDs, styles, and analysis adapters."""

    return _wrap(
        lambda: _ok(
            "Browsed Origin reference knowledge.",
            **browse_knowledge(collection="reference", path=topic, version=version),
        )
    )


@_mcp_tool()
def origin_query_reference(
    query: str,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Origin workflow reference notes, plot IDs, styles, and analysis adapters."""

    return _wrap(
        lambda: _ok(
            "Searched Origin reference knowledge.",
            **query_knowledge(query=query, collection="reference", version=version, limit=limit),
        )
    )


@_mcp_tool()
def origin_browse_python_api(api: str | None = None) -> dict[str, Any]:
    """Browse OriginPro Python API usage notes by dot path."""

    return _wrap(
        lambda: _ok(
            "Browsed OriginPro Python API knowledge.",
            **browse_knowledge(collection="python_api", path=api),
        )
    )


@_mcp_tool()
def origin_query_python_api(query: str, limit: int = 10) -> dict[str, Any]:
    """Search OriginPro Python API usage notes."""

    return _wrap(
        lambda: _ok(
            "Searched OriginPro Python API knowledge.",
            **query_knowledge(query=query, collection="python_api", limit=limit),
        )
    )


@_mcp_tool()
def origin_browse_labtalk(command: str | None = None, version: str | None = None) -> dict[str, Any]:
    """Browse LabTalk and X-Function knowledge used by origin-mcp."""

    return _wrap(
        lambda: _ok(
            "Browsed LabTalk knowledge.",
            **browse_knowledge(collection="labtalk", path=command, version=version),
        )
    )


@_mcp_tool()
def origin_query_labtalk(query: str, version: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Search LabTalk and X-Function knowledge used by origin-mcp."""

    return _wrap(
        lambda: _ok(
            "Searched LabTalk knowledge.",
            **query_knowledge(query=query, collection="labtalk", version=version, limit=limit),
        )
    )


@_mcp_tool()
def origin_browse_mcp_tools(tool: str | None = None) -> dict[str, Any]:
    """Browse origin-mcp tools by workflow group or tool path."""

    return _wrap(
        lambda: _ok(
            "Browsed origin-mcp tool knowledge.",
            **browse_knowledge(collection="mcp_tools", path=tool),
        )
    )


@_mcp_tool()
def origin_query_mcp_tools(query: str, limit: int = 10) -> dict[str, Any]:
    """Search origin-mcp tool knowledge."""

    return _wrap(
        lambda: _ok(
            "Searched origin-mcp tool knowledge.",
            **query_knowledge(query=query, collection="mcp_tools", limit=limit),
        )
    )


@_mcp_tool()
def origin_browse_official_docs(
    topic: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Browse indexed official OriginLab documentation entry points."""

    return _wrap(
        lambda: _ok(
            "Browsed official OriginLab documentation index.",
            **browse_knowledge(collection="official_docs", path=topic, version=version),
        )
    )


@_mcp_tool()
def origin_query_official_docs(
    query: str,
    version: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search indexed official OriginLab documentation entry points."""

    return _wrap(
        lambda: _ok(
            "Searched official OriginLab documentation index.",
            **query_knowledge(
                query=query,
                collection="official_docs",
                version=version,
                limit=limit,
            ),
        )
    )
