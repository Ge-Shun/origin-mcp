from __future__ import annotations

from typing import Any

from origin_mcp import template_library
from origin_mcp.models import SaveGraphTemplateRequest, SearchTemplatesRequest

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_save_graph_template(
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    plot_types: list[str] | None = None,
    roles: list[str] | None = None,
    n_columns: int | None = None,
    graph_name: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Save a finished graph as a reusable user template with searchable metadata.

    The template is stored in the user template library (default
    ``~/.origin-mcp/templates``). Reuse it later by passing ``template=<name>``
    to any plotting tool. Provide ``plot_types``, ``roles``, and ``n_columns``
    to make the template easier to find via ``origin_search_templates``.
    """

    def run() -> dict[str, Any]:
        request = SaveGraphTemplateRequest(
            name=name,
            description=description,
            tags=tags or [],
            plot_types=plot_types or [],
            roles=roles or [],
            n_columns=n_columns,
            graph_name=graph_name,
            overwrite=overwrite,
        )
        result = client.save_graph_template(
            name=request.name,
            description=request.description,
            tags=request.tags,
            plot_types=request.plot_types,
            roles=request.roles,
            n_columns=request.n_columns,
            graph_name=request.graph_name,
            overwrite=request.overwrite,
        )
        return _ok("Saved Origin graph template.", **result)

    return _wrap(run)


@_mcp_tool()
def origin_search_templates(
    query: str | None = None,
    plot_type: str | None = None,
    n_columns: int | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search the user template library for templates matching an intended plot.

    Ranks saved templates by plot type, data shape, tags, and keywords. Call
    this before plotting to reuse a matching style; each result carries a
    ``score`` and ``match_reasons``. Returns an empty list when nothing matches.
    """

    def run() -> dict[str, Any]:
        request = SearchTemplatesRequest(
            query=query,
            plot_type=plot_type,
            n_columns=n_columns,
            tags=tags or [],
            limit=limit,
        )
        results = template_library.search_templates(
            query=request.query,
            plot_type=request.plot_type,
            n_columns=request.n_columns,
            tags=request.tags,
            limit=request.limit,
        )
        return _ok(
            "Searched Origin template library.",
            template_dir=str(template_library.template_root()),
            count=len(results),
            templates=results,
        )

    return _wrap(run)


@_mcp_tool()
def origin_delete_template(name: str) -> dict[str, Any]:
    """Delete a saved user template (its .otpu/.json/.png) and drop it from the index.

    Returns ``deleted: false`` with reason ``not_found`` when no template carries
    that name.
    """

    def run() -> dict[str, Any]:
        result = template_library.delete_template(name)
        message = (
            f"Deleted Origin user template {name!r}."
            if result.get("deleted")
            else f"No Origin user template named {name!r}."
        )
        return _ok(message, **result)

    return _wrap(run)


@_mcp_tool()
def origin_list_user_templates() -> dict[str, Any]:
    """List every saved user template, most recent first."""

    def run() -> dict[str, Any]:
        records = template_library.load_index()
        records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return _ok(
            "Listed Origin user templates.",
            template_dir=str(template_library.template_root()),
            count=len(records),
            templates=records,
        )

    return _wrap(run)
