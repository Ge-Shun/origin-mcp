from __future__ import annotations

import hmac
import importlib
import json
import os
import socketserver
import threading
import time
import traceback
from typing import TYPE_CHECKING, Any

from . import __version__
from ._bridge_dispatch import TASKABLE_METHODS, call_client_method, call_origin_method
from ._bridge_protocol import error_code, json_safe, serialize_bridge_value
from ._bridge_tasks import DEFAULT_MAX_TASKS, BridgeTaskManager
from .errors import OriginOperationError
from .logging_config import debug_logging_enabled, log_bridge_event
from .origin_client import OriginClient
from .runtime import python_runtime_profile


def _keep_external_origin() -> bool:
    """Opt out of closing the spawned external Origin on bridge shutdown."""

    return os.environ.get("ORIGIN_MCP_KEEP_EXTERNAL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47631


if TYPE_CHECKING:
    # This state class is only ever mixed into a socketserver base (see the two
    # concrete servers below), so at type-check time give it that base to expose
    # ``timeout``/``handle_request`` and avoid mixin-isolation false positives.
    # At runtime it stays a plain object to keep the real MRO intact.
    _StateBase = socketserver.BaseServer
else:
    _StateBase = object


class _OriginBridgeServerState(_StateBase):
    # Whether the task manager owns a background worker thread. The cooperative
    # embedded server overrides this to False so Origin calls run on its serving
    # (UI) thread; see ``serve_forever`` and ``_pump_cooperative_tasks``.
    tasks_use_worker_thread: bool = True

    def _init_bridge_state(
        self,
        token: str | None = None,
        client: OriginClient | None = None,
        max_tasks: int = DEFAULT_MAX_TASKS,
    ) -> None:
        self.token = token
        self.client = client or OriginClient()
        self.tasks = BridgeTaskManager(
            self.client,
            max_tasks=max_tasks,
            use_worker_thread=self.tasks_use_worker_thread,
        )
        self.max_tasks = max(1, max_tasks)
        self.shutdown_requested = threading.Event()

    def request_shutdown(self) -> None:
        self.shutdown_requested.set()

    def shutdown(self) -> None:
        self.request_shutdown()

    def _pump_cooperative_tasks(self) -> None:
        """Drain queued async tasks on the calling thread when no worker exists.

        A no-op for the threaded server (its worker thread runs tasks). For the
        embedded server this is what executes ``submit_task`` work on the
        serving thread, keeping originpro on Origin's UI thread.
        """

        if not self.tasks_use_worker_thread:
            self.tasks.pump_pending()

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        previous_timeout = self.timeout
        self.timeout = poll_interval
        try:
            while not self.shutdown_requested.is_set():
                self.handle_request()
                self._pump_cooperative_tasks()
        finally:
            self.timeout = previous_timeout


class OriginBridgeServer(_OriginBridgeServerState, socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    persistent_connections = True

    def __init__(
        self,
        server_address: tuple[str, int],
        token: str | None = None,
        client: OriginClient | None = None,
        max_tasks: int = DEFAULT_MAX_TASKS,
    ) -> None:
        super().__init__(server_address, OriginBridgeHandler)
        self._init_bridge_state(token=token, client=client, max_tasks=max_tasks)


class OriginEmbeddedBridgeServer(_OriginBridgeServerState, socketserver.TCPServer):
    allow_reuse_address = True
    # The embedded server is polled cooperatively from Origin's UI thread via
    # handle_request(); each handler invocation must service one request and
    # return so the message pump keeps running.
    persistent_connections = False
    # originpro must run on Origin's UI thread, so async tasks are executed on
    # the serving loop (no background worker) via pump_pending().
    tasks_use_worker_thread = False

    def __init__(
        self,
        server_address: tuple[str, int],
        token: str | None = None,
        client: OriginClient | None = None,
        max_tasks: int = DEFAULT_MAX_TASKS,
    ) -> None:
        super().__init__(server_address, OriginBridgeHandler)
        self._init_bridge_state(token=token, client=client, max_tasks=max_tasks)


class OriginBridgeHandler(socketserver.StreamRequestHandler):
    server: OriginBridgeServer

    def handle(self) -> None:
        persistent = bool(getattr(self.server, "persistent_connections", False))
        while True:
            line = self.rfile.readline()
            if not line:
                return
            request_id = None
            method_for_log = "<invalid_request>"
            started_at = time.monotonic()
            error_traceback: str | None = None
            try:
                request = json.loads(line.decode("utf-8"))
                if isinstance(request, dict):
                    request_id = request.get("id")
                    raw_method = request.get("method")
                    if isinstance(raw_method, str) and raw_method:
                        method_for_log = raw_method
                response = self._dispatch(request)
            except Exception as exc:
                response = self._error_response(request_id, exc)
                # Capture the stack here, while the exception is live. The
                # response intentionally omits it (never leak internals to the
                # client); it is logged locally below only when debug is on.
                error_traceback = traceback.format_exc()
            duration_ms = (time.monotonic() - started_at) * 1000.0
            ok = bool(response.get("ok"))
            extra = (
                {"error_traceback": error_traceback}
                if (not ok and error_traceback and debug_logging_enabled())
                else None
            )
            log_bridge_event(
                method_for_log,
                request_id=request_id,
                ok=ok,
                duration_ms=duration_ms,
                error_code=None if ok else response.get("error_code"),
                error_type=None if ok else response.get("error_type"),
                error_message=None if ok else response.get("message"),
                extra=extra,
            )
            try:
                self.wfile.write(json.dumps(response, separators=(",", ":")).encode("utf-8"))
                self.wfile.write(b"\n")
                self.wfile.flush()
            except OSError:
                return
            if not persistent:
                return

    def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        if not isinstance(request, dict):
            raise OriginOperationError("Bridge request must be a JSON object.")
        if self.server.token:
            supplied = request.get("token")
            if not isinstance(supplied, str) or not hmac.compare_digest(
                supplied, self.server.token
            ):
                raise OriginOperationError(
                    "Invalid Origin bridge token.",
                    error_code="origin_bridge_unauthorized",
                )
        method = request.get("method")
        params = request.get("params") or {}
        if not isinstance(method, str) or not method:
            raise OriginOperationError("Bridge request method is required.")
        if not isinstance(params, dict):
            raise OriginOperationError("Bridge request params must be a JSON object.")
        result = self._call(method, params)
        return {"id": request_id, "ok": True, "result": json_safe(result)}

    def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "ping":
            return {
                "bridge": "origin-mcp-bridge",
                "version": __version__,
                "runtime": python_runtime_profile().as_dict(),
                "taskable_methods": sorted(TASKABLE_METHODS),
                "max_tasks": self.server.max_tasks,
            }
        if method == "submit_task":
            task_method = str(params.get("method") or "")
            task_params = params.get("params") or {}
            if not isinstance(task_params, dict):
                raise OriginOperationError("Bridge task params must be a JSON object.")
            return self.server.tasks.submit(task_method, task_params)
        if method == "task_status":
            return self.server.tasks.status(
                str(params.get("task_id") or ""),
                include_logs=bool(params.get("include_logs", False)),
                log_limit=int(params.get("log_limit", 20)),
                include_result=bool(params.get("include_result", True)),
            )
        if method == "cancel_task":
            return self.server.tasks.cancel(str(params.get("task_id") or ""))
        if method == "list_tasks":
            return self.server.tasks.list_tasks(limit=int(params.get("limit", 20)))
        if method == "shutdown":
            return self._shutdown_bridge(params)
        if method == "call_client":
            client_method = str(params.get("method") or "")
            args = params.get("args") or []
            kwargs = params.get("kwargs") or {}
            if not isinstance(args, list) or not isinstance(kwargs, dict):
                raise OriginOperationError("Bridge client call args/kwargs are invalid.")
            value = call_client_method(self.server.client, client_method, args, kwargs)
            return {"value": serialize_bridge_value(value)}
        if method in TASKABLE_METHODS:
            return call_origin_method(self.server.client, method, params)
        raise OriginOperationError(
            f"Unsupported bridge method: {method}",
            error_code="unsupported_bridge_method",
        )

    def _bridge_is_external_origin(self) -> bool:
        """True when originpro is driving a separately-spawned OriginExt instance.

        Prefer the already-imported originpro module on the client, then fall
        back to ``originpro.config`` only after originpro has been loaded by a
        real client call. Some Origin 2026 embedded sessions expose
        ``config.oext`` as falsey even while ``originpro.config.po`` holds a
        COM APP object for a spawned ``Origin64.exe -Embedding`` instance. In
        that state a plain detach leaves the spawned Origin alive, so treat an
        available ``po.Exit`` release handle as external automation too.
        """

        op = getattr(self.server.client, "_op", None)
        if op is None:
            return False
        config = getattr(op, "config", None) if op is not None else None
        if config is None:
            try:
                config = importlib.import_module("originpro.config")
            except Exception:
                config = None
        if config is None:
            return False
        if bool(getattr(config, "oext", False)):
            return True
        po = getattr(config, "po", None)
        return callable(getattr(po, "Exit", None))

    def _shutdown_bridge(self, params: dict[str, Any]) -> dict[str, Any]:
        release_origin = bool(params.get("release_origin", True))
        close_origin = bool(params.get("close_origin", False))
        external = self._bridge_is_external_origin()
        result: dict[str, Any] = {
            "shutdown_requested": True,
            "release_origin": release_origin,
            "close_origin": close_origin,
            "external_origin": external,
        }
        if release_origin:
            # In external mode the bridge drives a SEPARATE spawned Origin holding
            # the data; a plain detach leaves it running as an orphan (toward the
            # license cap), so close it on shutdown. In embedded mode originpro is
            # the user's host Origin, so only close it when explicitly asked.
            # Opt out of the external auto-close with ORIGIN_MCP_KEEP_EXTERNAL=1.
            close_spawned = close_origin or (external and not _keep_external_origin())
            release_method = "force_quit" if close_spawned else "detach"
            release = getattr(self.server.client, release_method, None)
            if callable(release):
                try:
                    result["origin_release"] = release()
                    result["origin_release_method"] = release_method
                except Exception as exc:
                    result["origin_release_error"] = {
                        "message": str(exc),
                        "error_code": error_code(exc),
                        "error_type": type(exc).__name__,
                    }
            else:
                result["origin_release_error"] = {
                    "message": f"Origin client does not provide {release_method}().",
                    "error_code": "origin_release_unavailable",
                    "error_type": "AttributeError",
                }
        self.server.request_shutdown()
        return result

    @staticmethod
    def _error_response(request_id: Any, exc: Exception) -> dict[str, Any]:
        return {
            "id": request_id,
            "ok": False,
            "message": str(exc),
            "error_code": error_code(exc),
            "error_type": type(exc).__name__,
        }
