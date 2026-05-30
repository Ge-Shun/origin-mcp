from __future__ import annotations

from typing import Any

from ._shared import (
    _mcp_tool,
    _ok,
    _wrap,
    client,
)


@_mcp_tool()
def origin_run_labtalk(script: str, capture_log: bool = True) -> dict[str, Any]:
    """Execute LabTalk script text inside Origin and optionally return captured output."""

    return _wrap(
        lambda: _ok(
            "Executed LabTalk script.",
            **client.run_labtalk(script, capture_log=capture_log),
        )
    )


@_mcp_tool()
def origin_quit() -> dict[str, Any]:
    """Close Origin/OriginPro."""

    return _wrap(lambda: _ok("Closed Origin.", **client.quit()))


@_mcp_tool()
def origin_detach() -> dict[str, Any]:
    """Release the external Origin automation connection without closing Origin."""

    return _wrap(lambda: _ok("Released Origin automation connection.", **client.detach()))


@_mcp_tool()
def origin_release() -> dict[str, Any]:
    """Alias for origin_detach."""

    return origin_detach()


@_mcp_tool()
def origin_force_quit() -> dict[str, Any]:
    """Ask the bridge to force-close Origin/OriginPro."""

    return _wrap(lambda: _ok("Force-closed Origin.", **client.force_quit()))
