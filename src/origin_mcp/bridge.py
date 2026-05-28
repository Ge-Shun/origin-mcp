from __future__ import annotations

import argparse
import hmac
import inspect
import json
import math
import os
import queue
import socketserver
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import __version__
from .errors import OriginMcpError, OriginOperationError
from .logging_config import log_bridge_event
from .origin_client import GraphRef, OriginClient, WorksheetRef
from .runtime import python_runtime_profile

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47631
DEFAULT_MAX_TASKS = 200
ALLOWED_CLIENT_METHODS = {
    "connect",
    "capabilities",
    "plot_type_coverage",
    "default_plot_config",
    "new_project",
    "open_project",
    "save_project",
    "quit",
    "detach",
    "force_quit",
    "run_labtalk",
    "import_csv",
    "import_table",
    "import_file_connector",
    "append_table",
    "worksheet_info",
    "read_worksheet",
    "write_worksheet",
    "add_calculated_column",
    "sort_worksheet",
    "get_cell_value",
    "set_cell_value",
    "delete_columns",
    "clear_worksheet",
    "export_worksheet_csv",
    "plot_table",
    "plot_table_by_id",
    "plot_matrix_by_id",
    "list_project",
    "rename_object",
    "delete_object",
    "set_axis",
    "set_plot_style",
    "apply_publication_style",
    "apply_nature_style",
    "diagnose_graph",
    "recommend_chart",
    "plot_auto",
    "chart_atlas_route",
    "plot_chart_atlas",
    "apply_image_panel_style",
    "add_plot_to_graph",
    "remove_plot_from_graph",
    "change_plot_type",
    "change_plot_data",
    "set_graph_page",
    "arrange_layers",
    "add_graph_label",
    "add_reference_line",
    "set_column_labels",
    "set_column_designations",
    "format_legend",
    "linear_fit_result",
    "export_all_graphs",
    "plot_range",
    "batch_plot_from_template",
    "list_graph_templates",
    "get_graph_info",
    "get_layer_info",
    "list_fit_functions",
    "nonlinear_fit_structured",
    "run_analysis",
    "format_graph",
    "export_graph",
    "export_preview",
    "inspect_export",
}
TASKABLE_METHODS = {
    "origin_ping",
    "origin_capabilities",
    *ALLOWED_CLIENT_METHODS,
}
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class BridgeTask:
    task_id: str
    method: str
    params: dict[str, Any]
    status: str = "queued"
    submitted_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancel_requested: bool = False

    def as_dict(self, include_result: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "task_id": self.task_id,
            "method": self.method,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancel_requested,
        }
        if include_result:
            if self.result is not None:
                data["result"] = self.result
            if self.error is not None:
                data["error"] = self.error
        return data


class BridgeTaskManager:
    def __init__(self, client: OriginClient, max_tasks: int = DEFAULT_MAX_TASKS) -> None:
        self._client = client
        self._max_tasks = max(1, max_tasks)
        self._tasks: dict[str, BridgeTask] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, daemon=True, name="origin-mcp-bridge")
        self._worker.start()

    def submit(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in TASKABLE_METHODS:
            raise OriginOperationError(
                f"Unsupported bridge task method: {method}",
                error_code="unsupported_bridge_task_method",
            )
        task = BridgeTask(task_id=str(uuid.uuid4()), method=method, params=params)
        with self._lock:
            self._tasks[task.task_id] = task
            self._prune_locked()
        self._queue.put(task.task_id)
        return {"task": task.as_dict(include_result=False)}

    def status(self, task_id: str) -> dict[str, Any]:
        return {"task": self._get_task(task_id).as_dict()}

    def cancel(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise OriginOperationError(
                    f"Bridge task not found: {task_id}",
                    error_code="bridge_task_not_found",
                )
            was_queued = task.status == "queued"
            if task.status == "queued":
                task.status = "cancelled"
                task.cancel_requested = True
                task.finished_at = time.time()
                changed = True
            elif task.status in TERMINAL_TASK_STATUSES:
                changed = False
            else:
                task.cancel_requested = True
                changed = True
            return {
                "cancel_requested": task.cancel_requested,
                "changed": changed,
                "interruptible": was_queued,
                "task": task.as_dict(),
            }

    def list_tasks(self, limit: int = 20) -> dict[str, Any]:
        if limit < 1:
            raise OriginOperationError("Task list limit must be at least 1.")
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda task: task.submitted_at,
                reverse=True,
            )[: min(limit, 100)]
            return {"tasks": [task.as_dict(include_result=False) for task in tasks]}

    def _get_task(self, task_id: str) -> BridgeTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise OriginOperationError(
                    f"Bridge task not found: {task_id}",
                    error_code="bridge_task_not_found",
                )
            return task

    def _work(self) -> None:
        while True:
            task_id = self._queue.get()
            try:
                task = self._start_task(task_id)
                if task is None:
                    continue
                try:
                    result = _call_origin_method(self._client, task.method, task.params)
                except Exception as exc:
                    self._finish_task(task_id, error=exc)
                else:
                    self._finish_task(task_id, result=result)
            finally:
                self._queue.task_done()

    def _start_task(self, task_id: str) -> BridgeTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != "queued":
                return None
            task.status = "running"
            task.started_at = time.time()
            return task

    def _finish_task(
        self,
        task_id: str,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.finished_at = time.time()
            if error is not None:
                task.status = "failed"
                task.error = {
                    "message": str(error),
                    "error_code": _error_code(error),
                    "error_type": type(error).__name__,
                }
            else:
                task.status = "completed"
                task.result = _json_safe(result or {})
            self._prune_locked()

    def _prune_locked(self) -> None:
        overflow = len(self._tasks) - self._max_tasks
        if overflow <= 0:
            return
        removable = sorted(
            (
                task
                for task in self._tasks.values()
                if task.status in TERMINAL_TASK_STATUSES
            ),
            key=lambda task: task.submitted_at,
        )
        for task in removable[:overflow]:
            self._tasks.pop(task.task_id, None)


class _OriginBridgeServerState:
    def _init_bridge_state(
        self,
        token: str | None = None,
        client: OriginClient | None = None,
        max_tasks: int = DEFAULT_MAX_TASKS,
    ) -> None:
        self.token = token
        self.client = client or OriginClient()
        self.tasks = BridgeTaskManager(self.client, max_tasks=max_tasks)
        self.max_tasks = max(1, max_tasks)


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
            duration_ms = (time.monotonic() - started_at) * 1000.0
            ok = bool(response.get("ok"))
            log_bridge_event(
                method_for_log,
                request_id=request_id,
                ok=ok,
                duration_ms=duration_ms,
                error_code=None if ok else response.get("error_code"),
                error_type=None if ok else response.get("error_type"),
                error_message=None if ok else response.get("message"),
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
        return {"id": request_id, "ok": True, "result": _json_safe(result)}

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
            return self.server.tasks.status(str(params.get("task_id") or ""))
        if method == "cancel_task":
            return self.server.tasks.cancel(str(params.get("task_id") or ""))
        if method == "list_tasks":
            return self.server.tasks.list_tasks(limit=int(params.get("limit", 20)))
        if method == "call_client":
            client_method = str(params.get("method") or "")
            args = params.get("args") or []
            kwargs = params.get("kwargs") or {}
            if not isinstance(args, list) or not isinstance(kwargs, dict):
                raise OriginOperationError("Bridge client call args/kwargs are invalid.")
            value = _call_client_method(self.server.client, client_method, args, kwargs)
            return {"value": _serialize_bridge_value(value)}
        if method in TASKABLE_METHODS:
            return _call_origin_method(self.server.client, method, params)
        raise OriginOperationError(
            f"Unsupported bridge method: {method}",
            error_code="unsupported_bridge_method",
        )

    @staticmethod
    def _error_response(request_id: Any, exc: Exception) -> dict[str, Any]:
        return {
            "id": request_id,
            "ok": False,
            "message": str(exc),
            "error_code": _error_code(exc),
            "error_type": type(exc).__name__,
        }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        json.dumps(value, allow_nan=False)
        return value
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        return str(value)


def _restore_bridge_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__origin_mcp_type__") == "Path":
            return Path(str(value["value"]))
        return {key: _restore_bridge_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_bridge_value(item) for item in value]
    return value


def _serialize_bridge_value(value: Any) -> Any:
    if isinstance(value, WorksheetRef):
        return {"__origin_mcp_type__": "WorksheetRef", "data": value.as_dict()}
    if isinstance(value, GraphRef):
        return {"__origin_mcp_type__": "GraphRef", "data": value.as_dict()}
    if isinstance(value, Path):
        return {"__origin_mcp_type__": "Path", "value": str(value)}
    if isinstance(value, dict):
        return {str(key): _serialize_bridge_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_bridge_value(item) for item in value]
    return value


def _public_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return _json_safe(value)
    if isinstance(value, WorksheetRef):
        return {"worksheet": value.as_dict()}
    if isinstance(value, GraphRef):
        return {"graph": value.as_dict()}
    return {"result": _json_safe(_serialize_bridge_value(value))}


def _call_client_method(
    client: OriginClient,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any],
) -> Any:
    if method not in ALLOWED_CLIENT_METHODS:
        raise OriginOperationError(
            f"Unsupported bridge client method: {method}",
            error_code="unsupported_bridge_client_method",
        )
    func = getattr(client, method, None)
    if not callable(func):
        raise OriginOperationError(
            f"Origin client method is not available: {method}",
            error_code="origin_client_method_unavailable",
        )
    restored_args = [_restore_bridge_value(arg) for arg in args]
    restored_kwargs = {key: _restore_bridge_value(value) for key, value in kwargs.items()}
    coerced_args, coerced_kwargs = _coerce_path_args(func, restored_args, restored_kwargs)
    return func(*coerced_args, **coerced_kwargs)


def _coerce_path_args(
    func: Any,
    args: list[Any],
    kwargs: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    signature = inspect.signature(func)
    path_names = {"path", "output_dir", "template_dir", "export_path"}
    coerced_args = list(args)
    params = list(signature.parameters.values())
    for index, value in enumerate(coerced_args):
        if index >= len(params):
            break
        if params[index].name in path_names and isinstance(value, str):
            coerced_args[index] = Path(value)
    coerced_kwargs = dict(kwargs)
    for key, value in list(coerced_kwargs.items()):
        if key in path_names and isinstance(value, str):
            coerced_kwargs[key] = Path(value)
    return coerced_args, coerced_kwargs


def _call_origin_method(
    client: OriginClient,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    if method == "origin_ping":
        return client.connect(show=bool(params.get("show", True)))
    if method == "origin_capabilities":
        return client.capabilities(
            show=bool(params.get("show", False)),
            refresh=bool(params.get("refresh", False)),
        )
    if method == "run_labtalk":
        script = str(params.get("script") or "")
        return client.run_labtalk(script)
    if method == "import_table":
        worksheet = client.import_table(
            Path(str(params.get("path") or "")),
            book_name=params.get("book_name"),
            sheet_name=params.get("sheet_name"),
            excel_sheet=params.get("excel_sheet", 0),
            delimiter=params.get("delimiter"),
            encoding=params.get("encoding"),
            header=params.get("header", 0),
            skiprows=params.get("skiprows"),
            nrows=params.get("nrows"),
            na_values=params.get("na_values"),
        )
        return {"worksheet": worksheet.as_dict()}
    if method == "plot_table":
        export_path = params.get("export_path")
        worksheet, graph = client.plot_table(
            path=Path(str(params.get("path") or "")),
            kind=str(params.get("kind") or "line"),
            x_col=params.get("x_col"),
            y_cols=params.get("y_cols"),
            book_name=params.get("book_name"),
            sheet_name=params.get("sheet_name"),
            excel_sheet=params.get("excel_sheet", 0),
            delimiter=params.get("delimiter"),
            encoding=params.get("encoding"),
            header=params.get("header", 0),
            skiprows=params.get("skiprows"),
            nrows=params.get("nrows"),
            na_values=params.get("na_values"),
            graph_name=params.get("graph_name"),
            template=params.get("template"),
            title=params.get("title"),
            x_label=params.get("x_label"),
            y_label=params.get("y_label"),
            z_col=params.get("z_col"),
            y_error_col=params.get("y_error_col"),
            x_error_col=params.get("x_error_col"),
            show_legend=bool(params.get("show_legend", True)),
            style_mode=str(params.get("style_mode") or "origin_default"),
            export_path=Path(str(export_path)) if export_path else None,
        )
        graph_data = graph.as_dict()
        response = {"worksheet": worksheet.as_dict(), "graph": graph_data}
        if graph_data.get("export_path"):
            response["export_inspection"] = client.inspect_export(Path(graph_data["export_path"]))
        return response
    if method == "export_graph":
        exported = client.export_graph(
            Path(str(params.get("path") or "")),
            graph_name=params.get("graph_name"),
            overwrite=bool(params.get("overwrite", True)),
        )
        return {
            **exported,
            "inspection": client.inspect_export(Path(str(exported["path"]))),
        }
    if method == "run_analysis":
        return client.run_analysis(
            analysis=str(params.get("analysis") or ""),
            worksheet=params.get("worksheet"),
            x_col=params.get("x_col"),
            y_col=params.get("y_col"),
            output_sheet=params.get("output_sheet"),
            options=params.get("options") or {},
            include_output=bool(params.get("include_output", False)),
            output_max_rows=int(params.get("output_max_rows", 100)),
        )
    if method == "new_project":
        return client.new_project(show=bool(params.get("show", True)))
    if method == "open_project":
        return client.open_project(
            Path(str(params.get("path") or "")),
            readonly=bool(params.get("readonly", False)),
            asksave=bool(params.get("asksave", False)),
        )
    if method == "save_project":
        return client.save_project(Path(str(params.get("path") or "")))
    if method == "list_project":
        return client.list_project()
    if method == "worksheet_info":
        return client.worksheet_info(
            book_name=params.get("book_name"),
            sheet_name=params.get("sheet_name"),
            label_types=params.get("label_types"),
        )
    if method == "read_worksheet":
        return client.read_worksheet(
            book_name=params.get("book_name"),
            sheet_name=params.get("sheet_name"),
            start_row=int(params.get("start_row", 0)),
            max_rows=int(params.get("max_rows", 100)),
            columns=params.get("columns"),
        )
    if method == "write_worksheet":
        return client.write_worksheet(
            rows=params.get("rows") or [],
            columns=params.get("columns"),
            book_name=params.get("book_name"),
            sheet_name=params.get("sheet_name"),
            start_col=params.get("start_col", 0),
            create=bool(params.get("create", False)),
        )
    if method in ALLOWED_CLIENT_METHODS:
        return _public_result(_call_client_method(client, method, [], params))
    raise OriginOperationError(f"Unsupported bridge method: {method}")


def _error_code(exc: Exception) -> str:
    if isinstance(exc, OriginMcpError):
        return exc.error_code
    return "unexpected_error"


def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token: str | None = None,
    max_tasks: int = DEFAULT_MAX_TASKS,
) -> None:
    with OriginBridgeServer((host, port), token=token, max_tasks=max_tasks) as server:
        actual_host, actual_port = server.server_address
        print(
            f"origin-mcp-bridge listening on {actual_host}:{actual_port}",
            file=sys.stderr,
            flush=True,
        )
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the optional origin-mcp GUI bridge.")
    parser.add_argument("--host", default=os.environ.get("ORIGIN_MCP_BRIDGE_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ORIGIN_MCP_BRIDGE_PORT", DEFAULT_PORT)),
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN"),
        help="Optional shared token required from MCP bridge clients.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=int(os.environ.get("ORIGIN_MCP_BRIDGE_MAX_TASKS", DEFAULT_MAX_TASKS)),
        help="Maximum number of bridge task records to retain.",
    )
    args = parser.parse_args()
    serve(host=args.host, port=args.port, token=args.token, max_tasks=args.max_tasks)


if __name__ == "__main__":
    main()
