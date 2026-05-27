from __future__ import annotations

import ast
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import origin_mcp.bridge as bridge
import origin_mcp.server as mcp_server
from origin_mcp.bridge import OriginBridgeServer, OriginEmbeddedBridgeServer
from origin_mcp.bridge_client import OriginBridgeClient, OriginBridgeConfig, OriginBridgeProxy
from origin_mcp.errors import OriginBridgeError
from origin_mcp.origin_client import GraphRef, WorksheetRef


class FakeOriginClient:
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
    return OriginBridgeClient(
        OriginBridgeConfig(host=host, port=port, token=token, timeout=2.0)
    )


def bridge_proxy(server: OriginBridgeServer, token: str | None = None) -> OriginBridgeProxy:
    host, port = server.server_address
    return OriginBridgeProxy(
        OriginBridgeConfig(host=host, port=port, token=token, timeout=2.0)
    )


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
    module = ast.parse(source)
    methods: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:
            if isinstance(node.value, ast.Name) and node.value.id == "client":
                methods.add(node.attr)
            self.generic_visit(node)

    Visitor().visit(module)

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
    assert any(task["task_id"] == task_id for task in listed["tasks"])


def test_bridge_task_lifecycle_supports_plot_table() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "plot_table", "params": {"path": "data.csv", "kind": "line"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")

    assert completed["result"]["worksheet"]["sheet_name"] == "Sheet1"
    assert completed["result"]["graph"]["graph_name"] == "Graph1"


def test_bridge_task_lifecycle_supports_run_analysis() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "run_analysis", "params": {"analysis": "smooth", "y_col": "y"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")

    assert completed["result"]["analysis"] == "smooth"
    assert completed["result"]["executed"] is True


def test_bridge_task_lifecycle_supports_project_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "save_project", "params": {"path": "saved.opju"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")

    assert completed["result"] == {"path": "saved.opju", "saved": True}


def test_bridge_task_lifecycle_supports_worksheet_methods() -> None:
    with running_bridge() as server:
        client = bridge_client(server)
        submitted = client.request(
            "submit_task",
            {"method": "read_worksheet", "params": {"book_name": "Book1"}},
        )
        task_id = submitted["task"]["task_id"]
        completed = wait_for_status(client, task_id, "completed")

    assert completed["result"]["rows"] == [{"x": 1, "y": 2}]


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
        second_task = client.request("task_status", {"task_id": second["task"]["task_id"]})[
            "task"
        ]

    assert cancelled["changed"] is True
    assert cancelled["interruptible"] is True
    assert first_task["status"] == "completed"
    assert second_task["status"] == "cancelled"
    assert second_task["cancel_requested"] is True


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
        mcp_server,
        "request_bridge",
        lambda method, **_kwargs: {"bridge": method, "version": "test"},
    )

    result = mcp_server.origin_bridge_status()

    assert result["ok"] is True
    assert result["data"]["bridge"] == "ping"


def test_server_bridge_status_reports_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise OriginBridgeError("bridge unavailable", "origin_bridge_unavailable")

    monkeypatch.setattr(mcp_server, "request_bridge", fail)

    result = mcp_server.origin_bridge_status()

    assert result["ok"] is False
    assert result["error_code"] == "origin_bridge_unavailable"


def test_server_bridge_submit_task_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"task": {"task_id": "abc", "status": "queued"}}

    monkeypatch.setattr(mcp_server, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_submit_task("run_labtalk", {"script": "type ok;"})

    assert result["ok"] is True
    assert result["data"]["task"]["task_id"] == "abc"
    assert calls == [("submit_task", {"method": "run_labtalk", "params": {"script": "type ok;"}})]


def test_server_bridge_plot_table_wraps_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method: str, params: dict[str, Any] | None = None, **_kwargs: Any):
        calls.append((method, params))
        return {"graph": {"graph_name": "Graph1"}}

    monkeypatch.setattr(mcp_server, "request_bridge", fake_request)

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

    monkeypatch.setattr(mcp_server, "request_bridge", fake_request)

    result = mcp_server.origin_bridge_run_analysis("smooth", y_col="signal")

    assert result["ok"] is True
    assert result["data"]["analysis"] == "smooth"
    assert calls[0][0] == "run_analysis"
    assert calls[0][1]["analysis"] == "smooth"
    assert calls[0][1]["y_col"] == "signal"
