# ruff: noqa: F401
from __future__ import annotations

import importlib
import pkgutil

from . import tools
from .tools._shared import (
    COMPACT_TOOL_NAMES,
    FULL_TOOL_PROFILE_VALUES,
    _error,
    _json_safe,
    _mcp_tool,
    _ok,
    _should_register_tool,
    _tool_profile,
    _wrap,
    client,
    mcp,
)


def _register_tools() -> None:
    """Import every ``origin_mcp.tools`` submodule to register its tools.

    Tool registration is purely an import side effect: importing a module runs
    its ``@_mcp_tool`` decorators, which register each tool with FastMCP subject
    to the active tool profile (see ``_shared._should_register_tool``). Importing
    the package's submodules here therefore replaces the long hand-maintained
    re-export block this module used to carry — adding a tool no longer requires
    editing ``server.py``.

    Each module's ``origin_*`` callables are also re-bound onto this module so
    they stay importable as ``origin_mcp.server.<tool>`` for code and tests that
    reference them directly. Every ``@_mcp_tool`` function is named ``origin_*``
    (enforced by ``tests/test_tool_registration.py``), so this binds the full
    tool surface.
    """

    for module_info in pkgutil.iter_modules(tools.__path__):
        name = module_info.name
        if name.startswith("_"):  # _shared holds no tools; skip private helpers.
            continue
        module = importlib.import_module(f"{tools.__name__}.{name}")
        for attr, value in vars(module).items():
            if attr.startswith("origin_") and callable(value):
                globals()[attr] = value


_register_tools()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
