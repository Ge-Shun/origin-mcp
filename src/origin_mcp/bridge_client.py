from __future__ import annotations

import json
import os
import socket
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bridge_handshake import read_handshake
from .errors import OriginBridgeError
from .refs import GraphRef, WorksheetRef

DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 47631
# Origin runs every request on its single UI thread, and a heavy plot + export +
# style pass can take well over 10s — especially once a project accumulates many
# windows. A short timeout makes the client give up on requests the bridge is
# still executing; see request() for why those must not be retried.
DEFAULT_BRIDGE_TIMEOUT = 30.0


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
        """Build a config from explicit args, env vars, then the handshake file.

        For each field the precedence is: explicit argument, then the matching
        ``ORIGIN_MCP_BRIDGE_*`` environment variable, then the value the running
        bridge published in its handshake file (see ``bridge_handshake``), then
        the built-in default. The handshake fallback is what makes the bridge's
        auto-generated token reach this client with no configuration.
        """

        env = os.environ
        handshake = read_handshake() or {}

        resolved_host = host or env.get("ORIGIN_MCP_BRIDGE_HOST")
        if not resolved_host:
            resolved_host = str(handshake.get("host") or DEFAULT_BRIDGE_HOST)

        resolved_port = port
        if resolved_port is None:
            env_port = env.get("ORIGIN_MCP_BRIDGE_PORT")
            if env_port:
                resolved_port = int(env_port)
            elif handshake.get("port"):
                resolved_port = int(handshake["port"])
            else:
                resolved_port = DEFAULT_BRIDGE_PORT

        if token is not None:
            resolved_token: str | None = token
        elif "ORIGIN_MCP_BRIDGE_TOKEN" in env:
            resolved_token = env["ORIGIN_MCP_BRIDGE_TOKEN"] or None
        else:
            handshake_token = handshake.get("token")
            resolved_token = handshake_token if isinstance(handshake_token, str) else None

        resolved_timeout = (
            timeout
            if timeout is not None
            else float(env.get("ORIGIN_MCP_BRIDGE_TIMEOUT", DEFAULT_BRIDGE_TIMEOUT))
        )

        return cls(
            host=resolved_host,
            port=resolved_port,
            token=resolved_token,
            timeout=resolved_timeout,
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
                wrote = False
                try:
                    self._ensure_connection_locked()
                    assert self._stream is not None
                    self._stream.write(encoded)
                    self._stream.flush()
                    wrote = True
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
                except TimeoutError as exc:
                    # A read timeout after the request was sent is ambiguous: the
                    # bridge may still be executing it on Origin's single UI
                    # thread. Retrying would re-run non-idempotent work (e.g.
                    # duplicate a plot) and pile more load on an already-slow
                    # bridge, snowballing into a backlog. Fail fast instead.
                    self._close_locked()
                    if wrote:
                        raise OriginBridgeError(
                            (
                                "Origin bridge did not respond within "
                                f"{self.config.timeout:g}s; it may still be busy "
                                "processing the request or blocked on a dialog."
                            ),
                            "origin_bridge_timeout",
                        ) from exc
                    last_error = exc
                    if attempt == 1:
                        continue
                    raise OriginBridgeError(
                        (
                            "Origin bridge is unavailable at "
                            f"{self.config.host}:{self.config.port}: {exc}"
                        ),
                        "origin_bridge_unavailable",
                    ) from exc
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
    """Proxy object with OriginClient-like methods backed by the bridge.

    The proxy holds only its config and resolves the socket from the shared
    client pool on each call rather than owning a private ``OriginBridgeClient``.
    This keeps a single source of truth for live connections: a bridge shutdown
    (``request_bridge("shutdown")`` -> ``close_shared_bridge_clients``) discards
    the pooled socket, and the proxy's next call transparently reconnects a fresh
    one instead of clinging to a stale connection.
    """

    def __init__(self, config: OriginBridgeConfig | None = None) -> None:
        self._config = config or OriginBridgeConfig.from_env()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args: Any, **kwargs: Any) -> Any:
            response = _shared_client(self._config).request(
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


def close_shared_bridge_clients(config: OriginBridgeConfig | None = None) -> None:
    """Close cached bridge client sockets.

    Tool calls reuse persistent sockets for normal bridge traffic. After a
    bridge shutdown request those sockets should be discarded immediately so
    this MCP process cannot keep stale connections or retry against a stopped
    bridge instance.
    """

    with _shared_client_lock:
        if config is None:
            clients = list(_shared_clients.values())
            _shared_clients.clear()
        else:
            client = _shared_clients.pop(config, None)
            clients = [] if client is None else [client]
    for client in clients:
        client.close()


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
    try:
        return _shared_client(config).request(method, params=params)
    finally:
        if method == "shutdown":
            close_shared_bridge_clients(config)


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
