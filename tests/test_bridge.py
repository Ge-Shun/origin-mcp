from __future__ import annotations

import ast
import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import origin_mcp.bridge as bridge
import origin_mcp.bridge_client as bridge_client_module
import origin_mcp.logging_config as bridge_logging
import origin_mcp.server as mcp_server
import origin_mcp.tools.bridge as bridge_tools
from origin_mcp.bridge import OriginBridgeServer, OriginEmbeddedBridgeServer
from origin_mcp.bridge_client import OriginBridgeClient, OriginBridgeConfig, OriginBridgeProxy
from origin_mcp.errors import OriginBridgeError
from origin_mcp.origin_client import GraphRef, WorksheetRef


class FakeOriginClient:
    def __init__(self) -> None:
        self.detached = False
        self.force_closed = False

    def connect(self, show: bool = True) -> dict[str, Any]:
        return {"connected": True, "visible": show, "origin_version": 10.3}

    def capabilities(self, show: bool = False, refresh: bool = False) -> dict[str, Any]:
        return {"connected": True, "visible": show, "refresh": refresh}

    def new_project(self, show: bool = True) -> dict[str, Any]:
        return {"created": True, "visible": show}

    def open_project(
        self,
        path: Any,
        readonly: bool = False,
        asksave: bool = False,
    ) -> dict[str, Any]:
        return {"path": str(path), "opened": True, "readonly": readonly, "asksave": asksave}

    def save_project(self, path: Any) -> dict[str, Any]:
        return {"path": str(path), "saved": True}

    def list_project(self) -> dict[str, Any]:
        return {"workbooks": ["Book1"], "graphs": ["Graph1"]}

    def worksheet_info(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "worksheet": {"book_name": kwargs.get("book_name"), "sheet_name": "Sheet1"},
            "columns_count": 2,
            "labels": {"L": ["x", "y"]},
        }

    def read_worksheet(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "worksheet": {"book_name": kwargs.get("book_name"), "sheet_name": "Sheet1"},
            "columns": ["x", "y"],
            "start_row": kwargs.get("start_row", 0),
            "returned_rows": 1,
            "total_rows": 1,
            "rows": [{"x": 1, "y": 2}],
        }

    def write_worksheet(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "worksheet": {
                "book_name": kwargs.get("book_name") or "Book1",
                "sheet_name": kwargs.get("sheet_name") or "Sheet1",
                "rows": len(kwargs.get("rows") or []),
            }
        }

    def run_labtalk(self, script: str) -> dict[str, Any]:
        return {"result": script == "type ok;", "script": script}

    def detach(self) -> dict[str, Any]:
        self.detached = True
        return {"detached": True, "closed": False}

    def force_quit(self) -> dict[str, Any]:
        self.force_closed = True
        return {"closed": True, "forced": True}

    def import_csv(self, *_args: Any, **_kwargs: Any) -> WorksheetRef:
        return WorksheetRef("Book1", "Sheet1", ["x", "y"], 2)

    def import_table(self, *_args: Any, **_kwargs: Any) -> WorksheetRef:
        return WorksheetRef("Book1", "Sheet1", ["x", "y"], 2)

    def plot_table(self, **kwargs: Any) -> tuple[WorksheetRef, GraphRef]:
        export_path = kwargs.get("export_path")
        return (
            WorksheetRef("Book1", "Sheet1", ["x", "y"], 2),
            GraphRef(
                "Graph1",
                export_path=str(export_path) if export_path else None,
                style_mode=str(kwargs.get("style_mode") or "origin_default"),
            ),
        )

    def export_graph(
        self,
        path: Any,
        graph_name: str | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        return {"path": str(path), "graph_name": graph_name, "overwrite": overwrite}

    def inspect_export(self, path: Any) -> dict[str, Any]:
        return {"path": str(path), "looks_nonempty": True}

    def run_analysis(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "analysis": kwargs["analysis"],
            "executed": True,
            "worksheet": kwargs.get("worksheet"),
            "parameters": [],
            "metrics": {},
            "warnings": [],
        }


class BlockingOriginClient(FakeOriginClient):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def run_labtalk(self, script: str) -> dict[str, Any]:
        if script == "block":
            self.started.set()
            self.release.wait(timeout=2.0)
        return {"result": True, "script": script}


@contextmanager
def running_bridge(
    token: str | None = None,
    fake_client: FakeOriginClient | None = None,
    max_tasks: int = 200,
):
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        token=token,
        client=fake_client or FakeOriginClient(),
        max_tasks=max_tasks,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def bridge_client(server: OriginBridgeServer, token: str | None = None) -> OriginBridgeClient:
    host, port = server.server_address
    return OriginBridgeClient(OriginBridgeConfig(host=host, port=port, token=token, timeout=2.0))


def bridge_proxy(server: OriginBridgeServer, token: str | None = None) -> OriginBridgeProxy:
    host, port = server.server_address
    return OriginBridgeProxy(OriginBridgeConfig(host=host, port=port, token=token, timeout=2.0))


def wait_for_status(
    client: OriginBridgeClient,
    task_id: str,
    status: str,
    timeout: float = 2.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.request("task_status", {"task_id": task_id})["task"]
        if task["status"] == status:
            return task
        time.sleep(0.01)
    return client.request("task_status", {"task_id": task_id})["task"]


def test_bridge_client_pings_bridge() -> None:
    with running_bridge() as server:
        result = bridge_client(server).request("ping")

    assert result["bridge"] == "origin-mcp-bridge"
    assert result["runtime"]["implementation"]
    assert "run_labtalk" in result["taskable_methods"]
    assert result["max_tasks"] == 200


def test_request_does_not_retry_after_read_timeout() -> None:
    # A timeout while waiting for the response means the bridge may still be
    # executing the (non-idempotent) request, so the client must fail fast with
    # origin_bridge_timeout instead of re-sending and duplicating the work.
    class _FakeStream:
        def __init__(self) -> None:
            self.writes = 0

        def write(self, _data: bytes) -> None:
            self.writes += 1

        def flush(self) -> None:
            pass

        def readline(self) -> bytes:
            raise TimeoutError("timed out")

        def close(self) -> None:
            pass

    class _FakeSock:
        def close(self) -> None:
            pass

    client = OriginBridgeClient(OriginBridgeConfig(token=None, timeout=0.1))
    stream = _FakeStream()

    def fake_ensure() -> None:
        client._socket = _FakeSock()  # type: ignore[assignment]
        client._stream = stream

    client._ensure_connection_locked = fake_ensure  # type: ignore[method-assign]

    with pytest.raises(OriginBridgeError) as excinfo:
        client.request("ping")

    assert excinfo.value.error_code == "origin_bridge_timeout"
    assert stream.writes == 1  # no retry


def test_embedded_bridge_server_handles_request_without_handler_threads() -> None:
    server = OriginEmbeddedBridgeServer(
        ("127.0.0.1", 0),
        client=FakeOriginClient(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("ping")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result["bridge"] == "origin-mcp-bridge"
    assert result["max_tasks"] == 200


class ThreadRecordingClient(FakeOriginClient):
    def __init__(self) -> None:
        super().__init__()
        self.call_thread_ident: int | None = None

    def run_labtalk(self, script: str) -> dict[str, Any]:
        self.call_thread_ident = threading.get_ident()
        return {"result": True, "script": script}


def test_threaded_bridge_server_uses_task_worker_thread() -> None:
    server = OriginBridgeServer(("127.0.0.1", 0), client=FakeOriginClient())
    try:
        assert server.tasks_use_worker_thread is True
        assert server.tasks._worker is not None
        assert server.tasks._worker.is_alive()
    finally:
        server.server_close()


def test_embedded_bridge_runs_tasks_on_serving_thread() -> None:
    # originpro must run on Origin's UI thread. The embedded server therefore
    # owns no task worker thread and executes submit_task work on its serving
    # loop. This locks the thread affinity, not just mutual exclusion.
    client = ThreadRecordingClient()
    server = OriginEmbeddedBridgeServer(("127.0.0.1", 0), client=client)
    assert server.tasks_use_worker_thread is False
    assert server.tasks._worker is None

    serve_thread = threading.Thread(target=server.serve_forever, daemon=True)
    serve_thread.start()
    try:
        bclient = bridge_client(server)
        submitted = bclient.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "type ok;"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(bclient, task_id, "completed")
    finally:
        server.shutdown()
        server.server_close()
        serve_thread.join(timeout=2)

    assert completed["status"] == "completed"
    assert completed["result"]["script"] == "type ok;"
    # The Origin call ran on the serving (UI) thread, never a worker thread.
    assert client.call_thread_ident == serve_thread.ident


def test_bridge_client_calls_origin_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        ping = client.request("origin_ping", {"show": False})
        labtalk = client.request("run_labtalk", {"script": "type ok;"})

    assert ping["connected"] is True
    assert ping["visible"] is False
    assert labtalk["result"] is True


def test_bridge_client_calls_project_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        created = client.request("new_project", {"show": False})
        opened = client.request(
            "open_project",
            {"path": "project.opju", "readonly": True, "asksave": True},
        )
        saved = client.request("save_project", {"path": "saved.opju"})
        listed = client.request("list_project")

    assert created == {"created": True, "visible": False}
    assert opened["path"] == "project.opju"
    assert opened["readonly"] is True
    assert opened["asksave"] is True
    assert saved == {"path": "saved.opju", "saved": True}
    assert listed["graphs"] == ["Graph1"]


def test_bridge_client_calls_worksheet_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        info = client.request("worksheet_info", {"book_name": "Book1"})
        read = client.request("read_worksheet", {"book_name": "Book1", "max_rows": 1})
        written = client.request(
            "write_worksheet",
            {"rows": [{"x": 1, "y": 2}], "book_name": "Book1"},
        )

    assert info["columns_count"] == 2
    assert read["rows"] == [{"x": 1, "y": 2}]
    assert written["worksheet"]["rows"] == 1


def test_bridge_proxy_deserializes_origin_client_refs() -> None:
    with running_bridge() as server:
        proxy = bridge_proxy(server)
        worksheet = proxy.import_table("data.csv")
        worksheet_from_csv = proxy.import_csv("data.csv")
        worksheet_graph = proxy.plot_table(path="data.csv", kind="line")

    assert worksheet.as_dict()["book_name"] == "Book1"
    assert worksheet_from_csv.as_dict()["sheet_name"] == "Sheet1"
    assert worksheet_graph[0].as_dict()["columns"] == ["x", "y"]
    assert worksheet_graph[1].as_dict()["graph_name"] == "Graph1"


def test_bridge_proxy_routes_generic_graph_editing_method() -> None:
    class GraphEditingClient(FakeOriginClient):
        def format_graph(self, **kwargs: Any) -> dict[str, Any]:
            return {"graph_name": kwargs.get("graph_name"), "formatted": True}

    with running_bridge(fake_client=GraphEditingClient()) as server:
        result = bridge_proxy(server).format_graph(graph_name="Graph1")

    assert result == {"graph_name": "Graph1", "formatted": True}


def test_server_client_uses_bridge_proxy_for_unbranched_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class GraphEditingClient(FakeOriginClient):
        def format_graph(self, **kwargs: Any) -> dict[str, Any]:
            return {"graph_name": kwargs.get("graph_name"), "formatted": True}

    with running_bridge(fake_client=GraphEditingClient()) as server:
        host, port = server.server_address
        monkeypatch.setenv("ORIGIN_MCP_BRIDGE_HOST", str(host))
        monkeypatch.setenv("ORIGIN_MCP_BRIDGE_PORT", str(port))
        result = mcp_server.origin_format_graph(graph_name="Graph1")

    assert result["ok"] is True
    assert result["data"] == {"graph_name": "Graph1", "formatted": True}


def test_bridge_allowlist_covers_all_server_origin_client_calls() -> None:
    server_path = Path(mcp_server.__file__)
    source = server_path.read_text(encoding="utf-8")
    assert "OriginClient" not in source
    assert "_direct_client" not in source
    methods: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:
            if isinstance(node.value, ast.Name) and node.value.id == "client":
                methods.add(node.attr)
            self.generic_visit(node)

    tools_dir = server_path.with_name("tools")
    for path in tools_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        Visitor().visit(ast.parse(path.read_text(encoding="utf-8")))

    public_methods = {method for method in methods if not method.startswith("_")}
    assert public_methods <= bridge.ALLOWED_CLIENT_METHODS


def test_bridge_client_calls_high_level_origin_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        imported = client.request("import_table", {"path": "data.csv"})
        plotted = client.request(
            "plot_table",
            {
                "path": "data.csv",
                "kind": "scatter",
                "x_col": "x",
                "y_cols": ["y"],
                "export_path": "plot.png",
            },
        )
        exported = client.request(
            "export_graph",
            {"path": "plot.png", "graph_name": "Graph1", "overwrite": False},
        )
        analysis = client.request(
            "run_analysis",
            {"analysis": "smooth", "worksheet": "[Book1]Sheet1", "y_col": "y"},
        )

    assert imported["worksheet"]["book_name"] == "Book1"
    assert plotted["graph"]["graph_name"] == "Graph1"
    assert plotted["export_inspection"]["looks_nonempty"] is True
    assert exported["graph_name"] == "Graph1"
    assert exported["overwrite"] is False
    assert exported["inspection"]["looks_nonempty"] is True
    assert analysis["analysis"] == "smooth"
    assert analysis["executed"] is True


def test_bridge_rejects_invalid_token() -> None:
    with running_bridge(token="secret") as server:
        with pytest.raises(OriginBridgeError) as excinfo:
            bridge_client(server, token="wrong").request("ping")

    assert excinfo.value.error_code == "origin_bridge_unauthorized"


def test_bridge_rejects_missing_token_when_required() -> None:
    with running_bridge(token="secret") as server:
        with pytest.raises(OriginBridgeError) as excinfo:
            bridge_client(server, token=None).request("ping")

    assert excinfo.value.error_code == "origin_bridge_unauthorized"


def test_bridge_accepts_matching_token() -> None:
    with running_bridge(token="secret") as server:
        result = bridge_client(server, token="secret").request("ping")

    assert result["bridge"] == "origin-mcp-bridge"


def test_bridge_shutdown_stops_server_and_detaches_origin() -> None:
    fake_client = FakeOriginClient()
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        client=fake_client,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown")
        thread.join(timeout=2)
    finally:
        server.server_close()

    assert result["shutdown_requested"] is True
    assert result["release_origin"] is True
    assert result["close_origin"] is False
    assert result["origin_release_method"] == "detach"
    assert result["origin_release"] == {"detached": True, "closed": False}
    assert fake_client.detached is True
    assert fake_client.force_closed is False
    assert not thread.is_alive()


def test_bridge_shutdown_can_force_close_origin() -> None:
    fake_client = FakeOriginClient()
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        client=fake_client,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown", {"close_origin": True})
        thread.join(timeout=2)
    finally:
        server.server_close()

    assert result["shutdown_requested"] is True
    assert result["release_origin"] is True
    assert result["close_origin"] is True
    assert result["origin_release_method"] == "force_quit"
    assert result["origin_release"] == {"closed": True, "forced": True}
    assert fake_client.force_closed is True
    assert fake_client.detached is False
    assert not thread.is_alive()


def test_bridge_shutdown_can_keep_origin_alive() -> None:
    fake_client = FakeOriginClient()
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        client=fake_client,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown", {"release_origin": False})
        thread.join(timeout=2)
    finally:
        server.server_close()

    assert result == {
        "shutdown_requested": True,
        "release_origin": False,
        "close_origin": False,
        "external_origin": False,
    }


def test_bridge_shutdown_closes_spawned_external_origin() -> None:
    import types

    # Simulate external (OriginExt) mode: originpro is imported with config.oext
    # True, so the bridge drives a separately-spawned Origin. Shutdown should
    # close that spawned instance even though close_origin was not requested, so
    # it is not left as an orphan.
    fake_client = FakeOriginClient()
    op_mod = types.ModuleType("originpro")
    cfg = types.ModuleType("originpro.config")
    cfg.oext = True
    op_mod.config = cfg
    fake_client._op = op_mod  # type: ignore[attr-defined]

    server = OriginBridgeServer(("127.0.0.1", 0), client=fake_client)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown")
        thread.join(timeout=2)
    finally:
        server.server_close()

    assert result["external_origin"] is True
    assert result["close_origin"] is False
    assert result["origin_release_method"] == "force_quit"
    assert fake_client.force_closed is True
    assert fake_client.detached is False


def test_bridge_shutdown_closes_external_origin_when_po_exit_exists() -> None:
    import types

    class _FakePo:
        def Exit(self, _release_only: bool) -> None:
            pass

    # Origin 2026 embedded Python can still hold an OriginExt COM app object
    # even when config.oext is falsey. The po.Exit release handle is the
    # practical signal that shutdown must close the spawned -Embedding Origin.
    fake_client = FakeOriginClient()
    op_mod = types.ModuleType("originpro")
    cfg = types.ModuleType("originpro.config")
    cfg.oext = False
    cfg.po = _FakePo()
    op_mod.config = cfg
    fake_client._op = op_mod  # type: ignore[attr-defined]

    server = OriginBridgeServer(("127.0.0.1", 0), client=fake_client)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown")
        thread.join(timeout=2)
    finally:
        server.server_close()

    assert result["external_origin"] is True
    assert result["origin_release_method"] == "force_quit"
    assert fake_client.force_closed is True
    assert fake_client.detached is False


def test_bridge_shutdown_keeps_external_origin_when_opted_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import types

    monkeypatch.setenv("ORIGIN_MCP_KEEP_EXTERNAL", "1")
    fake_client = FakeOriginClient()
    op_mod = types.ModuleType("originpro")
    cfg = types.ModuleType("originpro.config")
    cfg.oext = True
    op_mod.config = cfg
    fake_client._op = op_mod  # type: ignore[attr-defined]

    server = OriginBridgeServer(("127.0.0.1", 0), client=fake_client)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = bridge_client(server).request("shutdown")
        thread.join(timeout=2)
    finally:
        server.server_close()

    # Opt-out: external instance is left running (detach), not force-closed.
    assert result["external_origin"] is True
    assert result["origin_release_method"] == "detach"
    assert fake_client.detached is True
    assert fake_client.force_closed is False
    assert not thread.is_alive()


def test_bridge_task_lifecycle_completes() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "type ok;"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")
        listed = client.request("list_tasks", {"limit": 5})

    assert completed["result"]["script"] == "type ok;"
    assert completed["result"]["result"] is True
    assert completed["progress"] == 1.0
    assert completed["current_step"] == "Completed"
    assert completed["updated_at"] >= completed["submitted_at"]
    assert "logs" not in completed
    assert any(task["task_id"] == task_id for task in listed["tasks"])
    listed_task = next(task for task in listed["tasks"] if task["task_id"] == task_id)
    assert "result" not in listed_task
    assert "logs" not in listed_task


def test_bridge_task_status_can_include_recent_logs_without_result() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "type ok;"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")
        status = client.request(
            "task_status",
            {"task_id": task_id, "include_logs": True, "log_limit": 2, "include_result": False},
        )["task"]

    assert completed["status"] == "completed"
    assert "result" not in status
    assert len(status["logs"]) <= 2
    assert status["logs"][-1]["message"] == "Task completed."
    assert status["current_step"] == "Completed"


@pytest.mark.parametrize(
    ("method", "params", "expected"),
    [
        ("plot_table", {"path": "data.csv", "kind": "line"}, ("graph", "graph_name", "Graph1")),
        ("run_analysis", {"analysis": "smooth", "y_col": "y"}, ("analysis", None, "smooth")),
        (
            "save_project",
            {"path": "saved.opju"},
            (None, None, {"path": "saved.opju", "saved": True}),
        ),
        ("read_worksheet", {"book_name": "Book1"}, ("rows", None, [{"x": 1, "y": 2}])),
    ],
)
def test_bridge_task_lifecycle_supports_taskable_methods(
    method: str,
    params: dict[str, Any],
    expected: tuple[str | None, str | None, Any],
) -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request("submit_task", {"method": method, "params": params})
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")

    key, nested_key, value = expected
    result = completed["result"]
    if key is None:
        assert result == value
    elif nested_key is None:
        assert result[key] == value
    else:
        assert result[key][nested_key] == value


def test_bridge_task_cancel_queued_task() -> None:
    fake_client = BlockingOriginClient()
    with running_bridge(fake_client=fake_client) as server:
        client = bridge_client(server)
        first = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "block"}},
        )
        assert fake_client.started.wait(timeout=2.0)
        second = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "queued"}},
        )
        cancelled = client.request("cancel_task", {"task_id": second["task"]["task_id"]})
        fake_client.release.set()
        first_task = wait_for_status(client, first["task"]["task_id"], "completed")
        second_task = client.request("task_status", {"task_id": second["task"]["task_id"]})["task"]

    assert cancelled["changed"] is True
    assert cancelled["interruptible"] is True
    assert first_task["status"] == "completed"
    assert second_task["status"] == "cancelled"
    assert second_task["cancel_requested"] is True
    assert second_task["current_step"] == "Cancelled before start"


def test_bridge_task_rejects_unsupported_method() -> None:
    with running_bridge() as server:
        with pytest.raises(OriginBridgeError) as excinfo:
            bridge_client(server).request("submit_task", {"method": "ping", "params": {}})

    assert excinfo.value.error_code == "unsupported_bridge_task_method"


def test_bridge_task_history_is_pruned() -> None:
    with running_bridge(max_tasks=1) as server:
        client = bridge_client(server)
        first = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "first"}},
        )
        wait_for_status(client, first["task"]["task_id"], "completed")
        second = client.request(
            "submit_task",
            {"method": "run_labtalk", "params": {"script": "second"}},
        )
        second_task = wait_for_status(client, second["task"]["task_id"], "completed")
        listed = client.request("list_tasks", {"limit": 10})

    assert second_task["result"]["script"] == "second"
    assert [task["task_id"] for task in listed["tasks"]] == [second["task"]["task_id"]]


def test_server_bridge_status_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bridge_tools,
        "request_bridge",
        lambda method, **_kwargs: {"bridge": method, "version": "test"},
    )

    result = mcp_server.origin_bridge_status()

    assert result["ok"] is True
    assert result["data"]["bridge"] == "ping"


def test_server_bridge_shutdown_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"shutdown_requested": True, "release_origin": True}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_shutdown()

    assert result["ok"] is True
    assert result["data"]["shutdown_requested"] is True
    assert calls == [("shutdown", {"release_origin": True, "close_origin": False})]


def test_server_bridge_shutdown_can_request_origin_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"shutdown_requested": True, "release_origin": True, "close_origin": True}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_shutdown(close_origin=True)

    assert result["ok"] is True
    assert result["data"]["close_origin"] is True
    assert calls == [("shutdown", {"release_origin": True, "close_origin": True})]


def test_request_bridge_shutdown_closes_shared_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeOriginClient()
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        client=fake_client,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        result = bridge_client_module.request_bridge(
            "shutdown",
            {"release_origin": False},
            host=str(host),
            port=int(port),
            timeout=2.0,
        )
        thread.join(timeout=2)
    finally:
        server.server_close()
        bridge_client_module.close_shared_bridge_clients()

    assert result["shutdown_requested"] is True
    assert bridge_client_module._shared_clients == {}
    assert not thread.is_alive()


def test_server_bridge_status_reports_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise OriginBridgeError("bridge unavailable", "origin_bridge_unavailable")

    monkeypatch.setattr(bridge_tools, "request_bridge", fail)

    result = mcp_server.origin_bridge_status()

    assert result["ok"] is False
    assert result["error_code"] == "origin_bridge_unavailable"


def test_origin_doctor_reports_reachable_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = []
    status_path = tmp_path / "origin-bridge.status.txt"
    status_path.write_text('{"running": true, "host": "127.0.0.1"}', encoding="utf-8")

    def fake_request(method: str, **_kwargs: Any) -> dict[str, Any]:
        calls.append(method)
        return {"bridge": "origin-mcp-bridge", "taskable_methods": ["run_labtalk"]}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_doctor(status_path=str(status_path))

    assert result["ok"] is True
    assert result["data"]["bridge"]["ok"] is True
    assert result["data"]["status_file"]["data"]["running"] is True
    assert result["data"]["recommendations"] == []
    assert calls == ["ping"]


def test_origin_doctor_reports_unavailable_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "origin-bridge.status.txt"
    status_path.write_text('{"running": false, "last_error": "missing pandas"}', encoding="utf-8")

    def fake_request(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise OriginBridgeError("bridge unavailable", "origin_bridge_unavailable")

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_doctor(status_path=str(status_path))

    assert result["ok"] is True
    assert result["data"]["bridge"]["ok"] is False
    assert result["data"]["bridge"]["error_code"] == "origin_bridge_unavailable"
    assert result["data"]["status_file"]["data"]["last_error"] == "missing pandas"
    assert any("last_error" in item for item in result["data"]["recommendations"])


def test_server_bridge_submit_task_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"task": {"task_id": "abc", "status": "queued"}}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_submit_task("run_labtalk", {"script": "type ok;"})

    assert result["ok"] is True
    assert result["data"]["task"]["task_id"] == "abc"
    assert calls == [("submit_task", {"method": "run_labtalk", "params": {"script": "type ok;"}})]


def test_server_bridge_plot_table_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"graph": {"graph_name": "Graph1"}}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_plot_table("data.csv", kind="scatter", y_cols=["y"])

    assert result["ok"] is True
    assert result["data"]["graph"]["graph_name"] == "Graph1"
    assert calls[0][0] == "plot_table"
    assert calls[0][1]["kind"] == "scatter"
    assert calls[0][1]["y_cols"] == ["y"]


def test_server_bridge_run_analysis_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"analysis": "smooth", "executed": True}

    monkeypatch.setattr(bridge_tools, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_run_analysis("smooth", y_col="signal")

    assert result["ok"] is True
    assert result["data"]["analysis"] == "smooth"
    assert calls[0][0] == "run_analysis"
    assert calls[0][1]["analysis"] == "smooth"
    assert calls[0][1]["y_col"] == "signal"


def test_bridge_writes_structured_log_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "bridge.log"
    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(log_path))
    bridge_logging.reset_for_tests()
    try:
        with running_bridge() as server:
            bridge_client(server).request("ping")
            with pytest.raises(OriginBridgeError):
                bridge_client(server).request("does_not_exist")
    finally:
        bridge_logging.reset_for_tests()

    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line]
    records = [json.loads(line) for line in lines]
    methods = [record["method"] for record in records]
    assert "ping" in methods
    assert "does_not_exist" in methods
    error_record = next(record for record in records if record["method"] == "does_not_exist")
    assert error_record["ok"] is False
    assert error_record["error_code"] == "unsupported_bridge_method"
    success_record = next(record for record in records if record["method"] == "ping")
    assert success_record["ok"] is True
    assert "duration_ms" in success_record


def test_bridge_logs_traceback_when_debug_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "bridge.log"
    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(log_path))
    monkeypatch.setenv("ORIGIN_MCP_DEBUG", "1")
    bridge_logging.reset_for_tests()
    try:
        with running_bridge() as server:
            with pytest.raises(OriginBridgeError):
                bridge_client(server).request("does_not_exist")
    finally:
        bridge_logging.reset_for_tests()

    records = [
        json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line
    ]
    error_record = next(record for record in records if record["method"] == "does_not_exist")
    assert error_record["ok"] is False
    assert "error_traceback" in error_record
    assert "Traceback (most recent call last)" in error_record["error_traceback"]


def test_bridge_omits_traceback_without_debug(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "bridge.log"
    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(log_path))
    monkeypatch.delenv("ORIGIN_MCP_DEBUG", raising=False)
    bridge_logging.reset_for_tests()
    try:
        with running_bridge() as server:
            with pytest.raises(OriginBridgeError):
                bridge_client(server).request("does_not_exist")
    finally:
        bridge_logging.reset_for_tests()

    records = [
        json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line
    ]
    error_record = next(record for record in records if record["method"] == "does_not_exist")
    assert error_record["ok"] is False
    # Default logging keeps the structured fields but no raw stack.
    assert "error_traceback" not in error_record
    assert error_record["error_code"] == "unsupported_bridge_method"


def test_origin_doctor_reports_log_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "bridge.log"
    log_path.write_text(
        '{"ts":"2026-01-01T00:00:00Z","method":"ping","ok":true,"duration_ms":1.0}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", str(log_path))
    bridge_logging.reset_for_tests()

    monkeypatch.setattr(
        bridge_tools,
        "request_bridge",
        lambda *_args, **_kwargs: {"bridge": "origin-mcp-bridge"},
    )

    try:
        result = mcp_server.origin_doctor()
    finally:
        bridge_logging.reset_for_tests()

    log_info = result["data"]["log"]
    assert log_info["enabled"] is True
    assert log_info["path"] == str(log_path)
    assert log_info["exists"] is True
    assert any("ping" in line for line in log_info["recent"])


def test_origin_doctor_log_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORIGIN_MCP_LOG_FILE", "-")
    bridge_logging.reset_for_tests()

    monkeypatch.setattr(
        bridge_tools,
        "request_bridge",
        lambda *_args, **_kwargs: {"bridge": "origin-mcp-bridge"},
    )

    try:
        result = mcp_server.origin_doctor()
    finally:
        bridge_logging.reset_for_tests()

    log_info = result["data"]["log"]
    assert log_info["enabled"] is False
    assert log_info["path"] is None
