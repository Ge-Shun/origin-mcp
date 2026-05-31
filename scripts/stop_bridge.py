"""Stop the Origin-embedded origin-mcp bridge from outside Origin.

Sends a ``shutdown`` request to the running bridge so the Origin Python console
returns to its prompt and the embedded Origin automation session is released.
The standard ``ORIGIN_MCP_BRIDGE_HOST`` / ``PORT`` / ``TOKEN`` / ``TIMEOUT``
environment variables are honored automatically; when they are unset, the
host/port/token are read from the bridge handshake file, so the auto-generated
token is picked up with no configuration.

Run it directly with ``python scripts/stop_bridge.py``, or double-click
``scripts/stop-bridge.cmd``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    # Allow running straight from a source checkout without installing the package.
    src = Path(__file__).resolve().parents[1] / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from origin_mcp.bridge_client import request_bridge
    from origin_mcp.errors import OriginBridgeError

    try:
        response = request_bridge("shutdown", {"release_origin": True})
    except OriginBridgeError as exc:
        print(f"Could not reach the Origin bridge (already stopped?): {exc}")
        return 1
    print("Origin bridge shutdown requested:", response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
