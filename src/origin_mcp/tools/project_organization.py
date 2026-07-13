from __future__ import annotations

from pathlib import Path
from typing import Any

from ._shared import _mcp_tool, _ok, _wrap, client


@_mcp_tool()
def origin_create_note(
    name: str,
    text: str = "",
    syntax: str | int = "text",
    view: str | int = "text",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create an Origin Notes window with plain text, HTML, Markdown, or rich text."""

    return _wrap(
        lambda: _ok(
            "Created Origin Notes window.",
            note=client.create_note(
                name=name,
                text=text,
                syntax=syntax,
                view=view,
                overwrite=overwrite,
            ),
        )
    )


@_mcp_tool()
def origin_get_note(name: str | None = None, include_text: bool = True) -> dict[str, Any]:
    """Read an Origin Notes window and its syntax/view metadata."""

    return _wrap(
        lambda: _ok(
            "Read Origin Notes window.",
            note=client.note_info(name=name, include_text=include_text),
        )
    )


@_mcp_tool()
def origin_write_note(
    text: str,
    name: str | None = None,
    append: bool = False,
    newline: bool = True,
    syntax: str | int | None = None,
    view: str | int | None = None,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    """Replace or append Notes text, optionally changing syntax and rendered view."""

    return _wrap(
        lambda: _ok(
            "Updated Origin Notes window.",
            note=client.write_note(
                text=text,
                name=name,
                append=append,
                newline=newline,
                syntax=syntax,
                view=view,
                create_if_missing=create_if_missing,
            ),
        )
    )


@_mcp_tool()
def origin_load_note(
    path: Path,
    name: str | None = None,
    ask_replace: bool = False,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    """Load a local text, HTML, or Markdown file into an Origin Notes window."""

    return _wrap(
        lambda: _ok(
            "Loaded file into Origin Notes window.",
            note=client.load_note(
                path=path,
                name=name,
                ask_replace=ask_replace,
                create_if_missing=create_if_missing,
            ),
        )
    )


@_mcp_tool()
def origin_export_note_html(path: Path, name: str | None = None) -> dict[str, Any]:
    """Export an Origin Notes window as HTML."""

    return _wrap(
        lambda: _ok(
            "Exported Origin Notes window as HTML.",
            **client.export_note_html(path=path, name=name),
        )
    )


@_mcp_tool()
def origin_delete_note(name: str, confirm: bool = False) -> dict[str, Any]:
    """Delete an Origin Notes window. Requires confirm=true."""

    return _wrap(
        lambda: _ok(
            "Deleted Origin Notes window.",
            **client.delete_note(name=name, confirm=confirm),
        )
    )


@_mcp_tool()
def origin_list_project_folder(
    path: str | None = None,
    page_type: str | None = None,
    recursive: bool = False,
) -> dict[str, Any]:
    """List Project Explorer contents, optionally filtering by Origin page type."""

    return _wrap(
        lambda: _ok(
            "Listed Origin project folder.",
            folder=client.list_project_folder(
                path=path,
                page_type=page_type,
                recursive=recursive,
            ),
        )
    )


@_mcp_tool()
def origin_set_project_folder(path: str) -> dict[str, Any]:
    """Change the active Origin Project Explorer folder."""

    return _wrap(
        lambda: _ok(
            "Changed active Origin project folder.",
            **client.set_project_folder(path=path),
        )
    )


@_mcp_tool()
def origin_create_project_folder(
    name: str,
    parent: str | None = None,
    activate: bool = False,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Create a Project Explorer folder, optionally below a chosen parent."""

    return _wrap(
        lambda: _ok(
            "Created Origin project folder.",
            **client.create_project_folder(
                name=name,
                parent=parent,
                activate=activate,
                reuse_existing=reuse_existing,
            ),
        )
    )


@_mcp_tool()
def origin_move_project_item(
    name: str,
    destination: str,
    source_folder: str | None = None,
) -> dict[str, Any]:
    """Move an Origin page or subfolder to another Project Explorer folder."""

    return _wrap(
        lambda: _ok(
            "Moved Origin project item.",
            **client.move_project_item(
                name=name,
                destination=destination,
                source_folder=source_folder,
            ),
        )
    )


@_mcp_tool()
def origin_rename_project_item(
    old_name: str,
    new_name: str,
    folder: str | None = None,
) -> dict[str, Any]:
    """Rename a page or subfolder within an Origin Project Explorer folder."""

    return _wrap(
        lambda: _ok(
            "Renamed Origin project item.",
            **client.rename_project_item(
                old_name=old_name,
                new_name=new_name,
                folder=folder,
            ),
        )
    )


@_mcp_tool()
def origin_delete_project_folder(
    path: str,
    recursive: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a Project Explorer folder; recursive deletion requires explicit confirmation."""

    return _wrap(
        lambda: _ok(
            "Deleted Origin project folder.",
            **client.delete_project_folder(
                path=path,
                recursive=recursive,
                confirm=confirm,
            ),
        )
    )
