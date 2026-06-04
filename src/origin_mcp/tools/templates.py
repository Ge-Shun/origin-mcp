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
def origin_rename_template(old_name: str, new_name: str) -> dict[str, Any]:
    """Rename a saved user template without redrawing the graph.

    Renames the template's .otpu/.json/.png files and updates the index. Returns
    ``renamed: false`` with a ``reason`` such as ``not_found`` or ``name_exists``.
    """

    def run() -> dict[str, Any]:
        result = template_library.rename_template(old_name, new_name)
        message = (
            f"Renamed template {old_name!r} to {new_name!r}."
            if result.get("renamed")
            else f"Could not rename template ({result.get('reason')})."
        )
        return _ok(message, **result)

    return _wrap(run)


@_mcp_tool()
def origin_update_template_metadata(
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    plot_types: list[str] | None = None,
    roles: list[str] | None = None,
    n_columns: int | None = None,
) -> dict[str, Any]:
    """Edit a saved template's searchable metadata in place (no redraw needed).

    Only the fields you pass are changed; omitted fields are left untouched. The
    .otpu template file itself is not modified. Use this to fix tags, description,
    or matching hints without re-saving from a graph. Returns ``updated: false``
    with reason ``not_found`` when no template carries ``name``.
    """

    def run() -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if description is not None:
            fields["description"] = description
        if tags is not None:
            fields["tags"] = tags
        if plot_types is not None:
            fields["plot_types"] = plot_types
        if roles is not None:
            fields["roles"] = roles
        if n_columns is not None:
            fields["n_columns"] = n_columns
        result = template_library.update_template_metadata(name, **fields)
        if not result.get("updated"):
            message = f"No Origin user template named {name!r}."
        elif result.get("changed"):
            message = f"Updated template {name!r} ({', '.join(result['changed'])})."
        else:
            message = f"No metadata fields provided; template {name!r} left unchanged."
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
