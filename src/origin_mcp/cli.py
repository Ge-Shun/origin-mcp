"""Command-line entry point for the MCP server and setup helpers."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """Run the MCP server by default, or an explicitly requested setup command.

    Keeping the no-argument behavior identical to the historical console script
    means existing MCP client configurations continue to work unchanged.
    """

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        from .server import main as server_main

        server_main()
        return

    parser = argparse.ArgumentParser(prog="origin-mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)
    install = subparsers.add_parser(
        "install-origin-app",
        help="install the Origin MCP Bridge Start/Stop Apps for the current user",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="replace an existing Origin MCP Bridge App installation",
    )
    install.add_argument(
        "--destination",
        help="override the Origin Apps directory (primarily for testing)",
    )

    parsed = parser.parse_args(args)
    if parsed.command == "install-origin-app":
        from .app_installer import install_origin_apps

        installed = install_origin_apps(
            force=parsed.force,
            destination=parsed.destination,
        )
        print("Staged Origin App sources:")
        for path in installed:
            print(f"  {path}")
        print("In Origin's Command Window, pack the Apps with:")
        for path in installed:
            opx = path.with_suffix(".opx")
            print(f'mkOPX app:="{path.name}" opx:="{opx}";')
        print("Then drag both OPX files into Origin to register the Apps.")
