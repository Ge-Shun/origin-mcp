"""Logging configuration for origin-mcp.

The bridge writes structured JSON-lines records to a rotating log file so
operators can inspect MCP tool calls after the fact. The default location is
``%TEMP%/origin-mcp/bridge.log`` on Windows or ``$TMPDIR/origin-mcp/bridge.log``
elsewhere. Override with ``ORIGIN_MCP_LOG_FILE`` (set to ``-`` or ``off`` to
disable file logging entirely). The active path is exposed by ``origin_doctor``.

Set ``ORIGIN_MCP_DEBUG=1`` to also record the Python traceback of failed bridge
dispatches in the log file (under an ``error_traceback`` field). It stays in the
local log only and is never returned to the MCP client, so it is safe to enable
when diagnosing opaque originpro/Origin failures.

Unexpected errors raised inside MCP tool handlers run in the separate MCP server
process, so they are logged to a sibling ``server.log`` (next to ``bridge.log``)
with full Python tracebacks. Using a separate file avoids two processes
rotating the same log. ``ORIGIN_MCP_LOG_FILE=-``/``off`` disables both.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "origin_mcp.bridge"
TOOLS_LOGGER_NAME = "origin_mcp.tools"
_DEFAULT_BASENAME = "bridge.log"
_SERVER_BASENAME = "server.log"
_DEFAULT_DIRNAME = "origin-mcp"
_MAX_BYTES = 1_048_576  # 1 MiB per file
_BACKUP_COUNT = 3
_DISABLED_VALUES = {"-", "", "0", "off", "false", "no", "none"}
_DEBUG_TRUE_VALUES = {"1", "true", "yes", "on"}

_lock = threading.Lock()
_configured = False
_active_log_path: Path | None = None
_server_configured = False
_server_log_path: Path | None = None


def resolved_log_path() -> Path | None:
    """Return the path the bridge logger writes to, or None if disabled."""

    configured = os.environ.get("ORIGIN_MCP_LOG_FILE")
    if configured is not None:
        normalized = configured.strip()
        if normalized.lower() in _DISABLED_VALUES:
            return None
        return Path(normalized).expanduser()
    return Path(tempfile.gettempdir()) / _DEFAULT_DIRNAME / _DEFAULT_BASENAME


def debug_logging_enabled() -> bool:
    """Return True when ORIGIN_MCP_DEBUG requests verbose diagnostic logging."""

    value = os.environ.get("ORIGIN_MCP_DEBUG")
    return value is not None and value.strip().lower() in _DEBUG_TRUE_VALUES


def resolved_server_log_path() -> Path | None:
    """Return the path the MCP-server tools logger writes to, or None if disabled.

    It is a sibling of the bridge log (same directory, ``server.log`` basename),
    so disabling logging via ``ORIGIN_MCP_LOG_FILE`` disables both and a custom
    log path relocates both to the same directory.
    """

    bridge_path = resolved_log_path()
    if bridge_path is None:
        return None
    return bridge_path.with_name(_SERVER_BASENAME)


def get_bridge_logger() -> logging.Logger:
    """Return a configured logger for bridge handler events."""

    logger = logging.getLogger(LOGGER_NAME)
    _ensure_configured(logger)
    return logger


def get_tools_logger() -> logging.Logger:
    """Return a configured logger for MCP-server-side tool handler errors.

    Unlike the bridge logger this writes human-readable records (with rendered
    tracebacks) to ``server.log`` so unexpected failures inside tool handlers
    are persisted locally instead of relying on the host capturing stderr.
    """

    logger = logging.getLogger(TOOLS_LOGGER_NAME)
    _ensure_server_configured(logger)
    return logger


def active_log_path() -> Path | None:
    _ensure_configured(logging.getLogger(LOGGER_NAME))
    return _active_log_path


def tail_log(max_lines: int = 20) -> list[str]:
    """Read up to ``max_lines`` trailing lines from the bridge log."""

    path = active_log_path()
    if path is None or not path.exists() or max_lines <= 0:
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            block = 4096
            data = b""
            while size > 0 and data.count(b"\n") <= max_lines:
                step = min(block, size)
                size -= step
                handle.seek(size)
                data = handle.read(step) + data
        text = data.decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    return lines[-max_lines:]


def log_bridge_event(
    method: str,
    *,
    request_id: Any = None,
    ok: bool,
    duration_ms: float,
    error_code: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a single JSON-line event for a bridge dispatch."""

    record: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": method,
        "ok": ok,
        "duration_ms": round(duration_ms, 3),
    }
    if request_id is not None:
        record["request_id"] = str(request_id)
    if not ok:
        if error_code:
            record["error_code"] = error_code
        if error_type:
            record["error_type"] = error_type
        if error_message:
            record["error_message"] = error_message
    if extra:
        record.update({key: value for key, value in extra.items() if key not in record})
    get_bridge_logger().info(json.dumps(record, separators=(",", ":"), default=str))


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def _ensure_configured(logger: logging.Logger) -> None:
    global _configured, _active_log_path
    if _configured:
        return
    with _lock:
        if _configured:
            return
        logger.setLevel(logging.INFO)
        logger.propagate = False

        path = resolved_log_path()
        if path is None:
            logger.addHandler(logging.NullHandler())
            _active_log_path = None
            _configured = True
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = RotatingFileHandler(
                str(path),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
                delay=True,
            )
        except OSError:
            handler = logging.NullHandler()
            path = None
        handler.setFormatter(_JsonLineFormatter())
        logger.addHandler(handler)
        _active_log_path = path
        _configured = True


def _ensure_server_configured(logger: logging.Logger) -> None:
    global _server_configured, _server_log_path
    if _server_configured:
        return
    with _lock:
        if _server_configured:
            return
        logger.setLevel(logging.INFO)
        logger.propagate = False

        path = resolved_server_log_path()
        if path is None:
            logger.addHandler(logging.NullHandler())
            _server_log_path = None
            _server_configured = True
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = RotatingFileHandler(
                str(path),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
                delay=True,
            )
        except OSError:
            logger.addHandler(logging.NullHandler())
            _server_log_path = None
            _server_configured = True
            return
        # A standard formatter renders ``exc_info`` (the traceback) automatically
        # when callers use ``logger.exception(...)``.
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        _server_log_path = path
        _server_configured = True


def reset_for_tests() -> None:
    """Reset cached state so tests can monkeypatch ORIGIN_MCP_LOG_FILE."""

    global _configured, _active_log_path, _server_configured, _server_log_path
    with _lock:
        for name in (LOGGER_NAME, TOOLS_LOGGER_NAME):
            logger = logging.getLogger(name)
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
        _configured = False
        _active_log_path = None
        _server_configured = False
        _server_log_path = None
