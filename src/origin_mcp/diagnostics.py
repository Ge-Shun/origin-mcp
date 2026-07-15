"""Shared Origin bridge diagnostics for MCP tools and the command-line interface."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bridge_client import OriginBridgeConfig, request_bridge
from .bridge_handshake import read_handshake
from .errors import OriginBridgeError
from .logging_config import active_log_path, tail_log

EXIT_HEALTHY = 0
EXIT_NOT_RUNNING = 1
EXIT_DEGRADED = 2
EXIT_DIAGNOSTIC_ERROR = 3
DEFAULT_STALE_AFTER_SECONDS = 15 * 60

_STARTING_PHASES = {
    "initializing",
    "checking_dependencies",
    "installing_dependencies",
    "dependencies_ready",
    "loading_bridge_server",
}


def _dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _configured_status_file_candidates(status_path: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    handshake = read_handshake() or {}
    for value in (
        status_path,
        os.environ.get("ORIGIN_MCP_BRIDGE_STATUS"),
        handshake.get("status_path"),
    ):
        if value:
            candidates.append(Path(value).expanduser())

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def status_file_candidates(status_path: str | None = None) -> list[Path]:
    """Return configured and conventional status-file candidates."""

    candidates = _configured_status_file_candidates(status_path)
    candidates.extend(
        [
            Path.cwd() / "origin-bridge.status.txt",
            Path(__file__).resolve().parents[2] / "origin-bridge.status.txt",
        ]
    )
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(
            Path(local_appdata)
            / "OriginLab"
            / "Apps"
            / "Origin MCP Bridge Start"
            / "origin-bridge.status.txt"
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def read_bridge_status(status_path: str | None = None) -> dict[str, Any]:
    """Read the first available bridge status file without raising on bad content."""

    candidates = status_file_candidates(status_path)
    configured = _configured_status_file_candidates(status_path)
    configured_keys = {os.path.normcase(str(path)) for path in configured}
    fallback_with_mtime: list[tuple[float, Path]] = []
    for candidate in candidates:
        if os.path.normcase(str(candidate)) in configured_keys or not candidate.exists():
            continue
        try:
            modified = candidate.stat().st_mtime
        except OSError:
            modified = float("-inf")
        fallback_with_mtime.append((modified, candidate))
    ordered = configured + [
        candidate
        for _, candidate in sorted(fallback_with_mtime, key=lambda item: item[0], reverse=True)
    ]

    for candidate in ordered:
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "path": str(candidate),
                "exists": True,
                "readable": False,
                "error": str(exc),
                "candidates": [str(path) for path in candidates],
            }
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        return {
            "path": str(candidate),
            "exists": True,
            "readable": True,
            "format": "json" if isinstance(data, dict) else "text",
            "data": data if isinstance(data, dict) else None,
            "raw_preview": None if isinstance(data, dict) else text[:1000],
            "candidates": [str(path) for path in candidates],
        }
    return {
        "path": str(candidates[0]) if candidates else None,
        "exists": False,
        "readable": False,
        "candidates": [str(path) for path in candidates],
    }


def _status_runtime_recommendations(status_data: dict[str, Any]) -> list[str]:
    probe = status_data.get("runtime_probe")
    if not isinstance(probe, dict):
        return []

    recommendations: list[str] = []
    if probe.get("inside_origin", probe.get("likely_origin_embedded_python")) is False:
        recommendations.append(
            "The status file does not look like it came from Origin's embedded Python. "
            "Start addon.py from Origin's Python Console or the Origin MCP Bridge Start App, "
            "not from a normal terminal Python."
        )
    inside_origin = probe.get("inside_origin", probe.get("likely_origin_embedded_python")) is True
    embedded_api = (
        probe.get(
            "embedded_api_available",
            probe.get("origin_host_api_available"),
        )
        is True
    )
    if probe.get("originpro_available") is False and not (inside_origin and embedded_api):
        recommendations.append(
            "originpro was not importable when addon.py wrote the status file. Start the "
            "bridge inside Origin, or allow addon.py to install missing runtime dependencies."
        )
    return recommendations


def status_diagnostics(status_data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the stable, user-relevant subset of a raw status payload."""

    if not isinstance(status_data, dict):
        return {}
    probe = status_data.get("runtime_probe")
    probe_data = probe if isinstance(probe, dict) else {}
    return {
        "message": status_data.get("message"),
        "running": status_data.get("running"),
        "install_phase": status_data.get("install_phase"),
        "last_successful_start": status_data.get("last_successful_start"),
        "last_error": status_data.get("last_error"),
        "last_error_type": status_data.get("last_error_type"),
        "inside_origin": probe_data.get(
            "inside_origin",
            probe_data.get("likely_origin_embedded_python"),
        ),
        "embedded_api_available": probe_data.get(
            "embedded_api_available",
            probe_data.get("origin_host_api_available"),
        ),
        "originpro_available": probe_data.get("originpro_available"),
        "originpro_source": probe_data.get("originpro_source"),
        "python_executable": status_data.get("python_executable"),
        "python_version": status_data.get("python_version"),
        "status_updated_at": status_data.get("updated_at"),
    }


def collect_diagnostics(
    *,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = 2.0,
    status_path: str | None = None,
    ping_origin: bool = False,
    config_metadata: dict[str, Any] | None = None,
    request_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Collect bridge, optional Origin, status-file, log, and recovery diagnostics."""

    config = OriginBridgeConfig.from_env(host=host, port=port, token=token, timeout=timeout)
    status_file = read_bridge_status(status_path)
    bridge_check: dict[str, Any] = {"ok": False}
    origin_check: dict[str, Any] | None = None
    recommendations: list[str] = []
    bridge_request = request_fn or request_bridge

    try:
        response = bridge_request(
            "ping",
            host=config.host,
            port=config.port,
            token=config.token,
            timeout=config.timeout,
        )
        bridge_check = {"ok": True, "response": response}
    except OriginBridgeError as exc:
        bridge_check = {
            "ok": False,
            "error_code": exc.error_code,
            "message": str(exc),
        }
        recommendations.append(
            "Start Origin and click the Origin MCP Bridge Start App. For manual startup, "
            "open Origin's Python Console and run the root addon.py."
        )
        recommendations.append(
            "If addon.py is already running, compare ORIGIN_MCP_BRIDGE_HOST and "
            "ORIGIN_MCP_BRIDGE_PORT with the status file."
        )

    if ping_origin and bridge_check["ok"]:
        try:
            origin_check = {
                "ok": True,
                "response": bridge_request(
                    "origin_ping",
                    {"show": True},
                    host=config.host,
                    port=config.port,
                    token=config.token,
                    timeout=max(float(config.timeout), 10.0),
                ),
            }
        except OriginBridgeError as exc:
            origin_check = {
                "ok": False,
                "error_code": exc.error_code,
                "message": str(exc),
            }
            recommendations.append(
                "The bridge responded, but Origin automation failed. Check the live Origin "
                "session and the status file last_error field."
            )

    status_data = status_file.get("data")
    if isinstance(status_data, dict) and status_data.get("last_error"):
        recommendations.append(
            "addon.py recorded last_error in the status file; inspect that field first."
        )
    if isinstance(status_data, dict):
        recommendations.extend(_status_runtime_recommendations(status_data))
    if not status_file.get("exists"):
        recommendations.append(
            "No bridge status file was found. Set ORIGIN_MCP_BRIDGE_STATUS or start addon.py "
            "from the checkout root."
        )

    log_path = active_log_path()
    log_info: dict[str, Any] = {
        "path": str(log_path) if log_path else None,
        "enabled": log_path is not None,
        "exists": bool(log_path and log_path.exists()),
        "recent": tail_log(20) if log_path and log_path.exists() else [],
    }
    config_info: dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "timeout": config.timeout,
        "token_configured": bool(config.token),
        "env": {
            "ORIGIN_MCP_BRIDGE_HOST": os.environ.get("ORIGIN_MCP_BRIDGE_HOST"),
            "ORIGIN_MCP_BRIDGE_PORT": os.environ.get("ORIGIN_MCP_BRIDGE_PORT"),
            "ORIGIN_MCP_BRIDGE_TIMEOUT": os.environ.get("ORIGIN_MCP_BRIDGE_TIMEOUT"),
            "ORIGIN_MCP_BRIDGE_STATUS": os.environ.get("ORIGIN_MCP_BRIDGE_STATUS"),
            "ORIGIN_MCP_BRIDGE_TOKEN": bool(os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN")),
            "ORIGIN_MCP_TOOL_PROFILE": os.environ.get("ORIGIN_MCP_TOOL_PROFILE"),
            "ORIGIN_MCP_LOG_FILE": os.environ.get("ORIGIN_MCP_LOG_FILE"),
        },
    }
    if config_metadata:
        config_info.update(config_metadata)

    return {
        "config": config_info,
        "status_file": status_file,
        "status_diagnostics": status_diagnostics(
            status_data if isinstance(status_data, dict) else None
        ),
        "bridge": bridge_check,
        "origin": origin_check,
        "log": log_info,
        "recommendations": _dedupe_strings(recommendations),
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def classify_diagnostics(
    report: dict[str, Any],
    *,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify a diagnostic report into a CLI state and stable exit code."""

    bridge = report.get("bridge")
    if not isinstance(bridge, dict) or "ok" not in bridge:
        return {
            "state": "diagnostic_error",
            "exit_code": EXIT_DIAGNOSTIC_ERROR,
            "status_age_seconds": None,
            "status_stale": False,
        }

    status_file = report.get("status_file")
    status_file_data = status_file if isinstance(status_file, dict) else {}
    raw_status = status_file_data.get("data")
    status_data = raw_status if isinstance(raw_status, dict) else {}
    updated_at = _parse_timestamp(status_data.get("updated_at"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age_seconds = (
        max(0.0, (current.astimezone(timezone.utc) - updated_at).total_seconds())
        if updated_at
        else None
    )
    stale = bool(age_seconds is not None and age_seconds > stale_after_seconds)

    if bridge.get("ok"):
        origin = report.get("origin")
        if isinstance(origin, dict) and not origin.get("ok"):
            state, exit_code = "degraded", EXIT_DEGRADED
        else:
            state, exit_code = "running", EXIT_HEALTHY
    elif status_data.get("last_error") or status_data.get("install_phase") == "failed":
        state, exit_code = "failed", EXIT_DEGRADED
    elif stale and status_file_data.get("exists"):
        state, exit_code = "stale", EXIT_NOT_RUNNING
    elif status_data.get("install_phase") in _STARTING_PHASES:
        state, exit_code = "starting", EXIT_DEGRADED
    elif status_data.get("running") is False and status_data.get("message") == "stopped":
        state, exit_code = "stopped", EXIT_NOT_RUNNING
    else:
        state, exit_code = "not_running", EXIT_NOT_RUNNING

    return {
        "state": state,
        "exit_code": exit_code,
        "status_age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        "status_stale": stale,
    }
