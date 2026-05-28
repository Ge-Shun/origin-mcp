from __future__ import annotations

import json
import os
import socket
import threading
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
    """JSON-lines client for the Origin GUI bridge with a persistent connection.

    The client transparently reconnects when the server closes the socket, so it
    works with both the threaded bridge (which keeps the connection open) and the
    embedded cooperative bridge (which services one request per connection).
    """

    def __init__(self, config: OriginBridgeConfig | None = None) -> None:
        self.config = config or OriginBridgeConfig.from_env()
        self._lock = threading.Lock()
        self._socket: socket.socket | None = None
        self._stream: Any = None

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "id": request_id,
            "method": method,
            "params": _bridge_json_safe(params or {}),
        }
        if self.config.token:
            payload["token"] = self.config.token
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"

        with self._lock:
            line: bytes | None = None
            last_error: OSError | None = None
            for attempt in (1, 2):
                try:
                    self._ensure_connection_locked()
                    assert self._stream is not None
                    self._stream.write(encoded)
                    self._stream.flush()
                    line = self._stream.readline()
                    if not line:
                        # Server closed the socket. Retry once with a fresh connection.
                        self._close_locked()
                        if attempt == 1:
                            continue
                        raise OriginBridgeError(
                            "Origin bridge closed the connection without a response.",
                        )
                    break
                except OSError as exc:
                    last_error = exc
                    self._close_locked()
                    if attempt == 1:
                        continue
                    raise OriginBridgeError(
                        (
                            "Origin bridge is unavailable at "
                            f"{self.config.host}:{self.config.port}: {exc}"
                        ),
                        "origin_bridge_unavailable",
                    ) from exc
            if line is None:
                # Defensive: the loop above always sets line or raises.
                raise OriginBridgeError(
                    "Origin bridge did not return a response.",
                ) from last_error

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

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _ensure_connection_locked(self) -> None:
        if self._socket is not None:
            return
        connection = socket.create_connection(
            (self.config.host, self.config.port),
            timeout=self.config.timeout,
        )
        connection.settimeout(self.config.timeout)
        self._socket = connection
        self._stream = connection.makefile("rwb")

    def _close_locked(self) -> None:
        stream = self._stream
        sock = self._socket
        self._stream = None
        self._socket = None
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def __del__(self) -> None:  # best-effort cleanup
        try:
            self.close()
        except Exception:
            pass


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


_shared_client_lock = threading.Lock()
_shared_clients: dict[OriginBridgeConfig, OriginBridgeClient] = {}


def _shared_client(config: OriginBridgeConfig) -> OriginBridgeClient:
    with _shared_client_lock:
        client = _shared_clients.get(config)
        if client is None:
            client = OriginBridgeClient(config)
            _shared_clients[config] = client
        return client


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
    return _shared_client(config).request(method, params=params)


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
