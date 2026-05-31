"""Zero-config authentication handshake between the bridge and MCP server.

The Origin bridge listens on ``127.0.0.1`` but, historically, ran without
authentication unless the operator set ``ORIGIN_MCP_BRIDGE_TOKEN`` in *both*
processes. That left any local process able to drive Origin (including the
arbitrary-code ``run_labtalk`` surface).

To close that gap with no configuration, the bridge now generates a random
token at startup and records it — together with the host/port it actually
bound — in a small JSON file in a per-user temporary directory. The MCP
server, the ``stop_bridge`` helper, and any other client compute the same
path and read the token automatically. An explicit ``ORIGIN_MCP_BRIDGE_TOKEN``
environment variable always wins, so existing setups keep working.

The default location mirrors ``logging_config`` (``%TEMP%/origin-mcp`` or
``$TMPDIR/origin-mcp``), so both cooperating processes resolve it identically
on the same machine and user without any shared configuration. Override with
``ORIGIN_MCP_BRIDGE_HANDSHAKE``.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any

_DEFAULT_DIRNAME = "origin-mcp"
_DEFAULT_BASENAME = "bridge.json"


def default_handshake_path() -> Path:
    """Return the shared handshake file path used by both processes."""

    configured = os.environ.get("ORIGIN_MCP_BRIDGE_HANDSHAKE")
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / _DEFAULT_DIRNAME / _DEFAULT_BASENAME


def generate_token() -> str:
    """Return a fresh URL-safe random bridge token."""

    return secrets.token_urlsafe(32)


def write_handshake(
    host: str,
    port: int,
    token: str,
    *,
    path: Path | None = None,
) -> Path:
    """Atomically write the bridge handshake file and return its path.

    The file is written to a temporary sibling and ``os.replace``-d into place
    so a concurrent reader never observes a half-written file. Permissions are
    tightened to owner-only on platforms that honor ``chmod``.
    """

    target = path or default_handshake_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "handshake_version": 1,
        "host": host,
        "port": int(port),
        "token": token,
        "pid": os.getpid(),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tmp = target.with_name(target.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, target)
    return target


def read_handshake(*, path: Path | None = None) -> dict[str, Any] | None:
    """Return the parsed handshake payload, or ``None`` when unavailable.

    Any read/parse failure (missing file, partial write, invalid JSON) yields
    ``None`` so callers can transparently fall back to defaults.
    """

    target = path or default_handshake_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def read_handshake_token(*, path: Path | None = None) -> str | None:
    """Return just the token from the handshake file, if present."""

    data = read_handshake(path=path)
    if not data:
        return None
    token = data.get("token")
    return token if isinstance(token, str) and token else None


def clear_handshake(*, path: Path | None = None) -> None:
    """Remove the handshake file; best-effort, ignores a missing file."""

    target = path or default_handshake_path()
    try:
        target.unlink()
    except OSError:
        pass
