from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import OriginBridgeError
from .origin_client import GraphRef, WorksheetRef

DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 47631
DEFAULT_BRIDGE_TIMEOUT = 10.0


@dataclass(frozen=True)
class OriginBridgeConfig:
    host: str = DEFAULT_BRIDGE_HOST
    port: int = DEFAULT_BRIDGE_PORT
    token: str | None = None
    timeout: float = DEFAULT_BRIDGE_TIMEOUT

    @classmethod
    def from_env(
        cls,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> OriginBridgeConfig:
        return cls(
            host=host or os.environ.get("ORIGIN_MCP_BRIDGE_HOST", DEFAULT_BRIDGE_HOST),
            port=port or int(os.environ.get("ORIGIN_MCP_BRIDGE_PORT", DEFAULT_BRIDGE_PORT)),
            token=token if token is not None else os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN"),
            timeout=(
                timeout
                if timeout is not None
                else float(os.environ.get("ORIGIN_MCP_BRIDGE_TIMEOUT", DEFAULT_BRIDGE_TIMEOUT))
            ),
        )


class OriginBridgeClient:
    """Small JSON-lines client for the Origin GUI bridge."""

    def __init__(self, config: OriginBridgeConfig | None = None) -> None:
        self.config = config or OriginBridgeConfig.from_env()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "id": request_id,
            "method": method,
            "params": _bridge_json_safe(params or {}),
        }
        if self.config.token:
            payload["token"] = self.config.token

        try:
            with socket.create_connection(
                (self.config.host, self.config.port),
                timeout=self.config.timeout,
            ) as connection:
                connection.settimeout(self.config.timeout)
                with connection.makefile("rwb") as stream:
                    stream.write(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
                    stream.write(b"\n")
                    stream.flush()
                    line = stream.readline()
        except OSError as exc:
            raise OriginBridgeError(
                (
                    "Origin bridge is unavailable at "
                    f"{self.config.host}:{self.config.port}: {exc}"
                ),
                "origin_bridge_unavailable",
            ) from exc

        if not line:
            raise OriginBridgeError("Origin bridge closed the connection without a response.")
        try:
            response = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OriginBridgeError("Origin bridge returned invalid JSON.") from exc

        if response.get("id") != request_id:
            raise OriginBridgeError("Origin bridge returned a response with the wrong id.")
        if not response.get("ok", False):
            raise OriginBridgeError(
                str(response.get("message") or "Origin bridge request failed."),
                str(response.get("error_code") or "origin_bridge_failed"),
            )
        result = response.get("result")
        return result if isinstance(result, dict) else {"result": result}


class OriginBridgeProxy:
    """Proxy object with OriginClient-like methods backed by the bridge."""

    def __init__(self, config: OriginBridgeConfig | None = None) -> None:
        self._client = OriginBridgeClient(config)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args: Any, **kwargs: Any) -> Any:
            response = self._client.request(
                "call_client",
                {
                    "method": name,
                    "args": list(args),
                    "kwargs": kwargs,
                },
            )
            return _deserialize_bridge_value(response.get("value"))

        return call


def request_bridge(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    config = OriginBridgeConfig.from_env(host=host, port=port, token=token, timeout=timeout)
    return OriginBridgeClient(config).request(method, params=params)


def _bridge_json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return {"__origin_mcp_type__": "Path", "value": str(value)}
    if isinstance(value, dict):
        return {str(key): _bridge_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_bridge_json_safe(item) for item in value]
    return value


def _deserialize_bridge_value(value: Any) -> Any:
    if isinstance(value, dict):
        value_type = value.get("__origin_mcp_type__")
        if value_type == "WorksheetRef":
            data = value["data"]
            return WorksheetRef(
                book_name=data["book_name"],
                sheet_name=data["sheet_name"],
                columns=list(data.get("columns", [])),
                rows=int(data.get("rows", 0)),
            )
        if value_type == "GraphRef":
            data = value["data"]
            return GraphRef(
                graph_name=data["graph_name"],
                export_path=data.get("export_path"),
                template=data.get("template"),
                style_mode=data.get("style_mode", "origin_default"),
                requested_graph_name=data.get("requested_graph_name"),
                display_name=data.get("display_name"),
            )
        if value_type == "Path":
            return Path(str(value["value"]))
        return {key: _deserialize_bridge_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deserialize_bridge_value(item) for item in value]
    return value
