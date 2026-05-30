from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_addon_module():
    spec = importlib.util.spec_from_file_location("origin_mcp_addon_test", ROOT / "addon.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_addon_status_path_defaults_next_to_addon(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.delenv("ORIGIN_MCP_BRIDGE_STATUS", raising=False)

    assert addon._status_path() == ROOT / "origin-bridge.status.txt"


def test_addon_installs_missing_dependencies_by_default(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.delenv("ORIGIN_MCP_INSTALL_MISSING", raising=False)

    assert addon._env_bool("ORIGIN_MCP_INSTALL_MISSING", True) is True
    signature = inspect.signature(addon.start_origin_mcp_bridge)
    assert signature.parameters["install_missing"].default is True


def test_addon_can_disable_dependency_install(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.setenv("ORIGIN_MCP_INSTALL_MISSING", "0")

    assert addon._env_bool("ORIGIN_MCP_INSTALL_MISSING", True) is False


def test_addon_auto_detects_adjacent_src(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.delenv("ORIGIN_MCP_SRC", raising=False)

    assert ROOT / "src" in addon._candidate_src_dirs()
    assert addon._ensure_origin_mcp_importable().endswith("origin_mcp")


def test_request_stop_reports_not_running_when_no_server() -> None:
    addon = load_addon_module()

    assert addon.request_stop_origin_mcp_bridge() == {
        "stop_requested": False,
        "reason": "not_running",
    }


def test_request_stop_only_signals_shutdown_event() -> None:
    addon = load_addon_module()

    class FakeServer:
        def __init__(self) -> None:
            self.shutdown_requested_called = False
            self.closed = False

        def request_shutdown(self) -> None:
            self.shutdown_requested_called = True

        def server_close(self) -> None:  # would run on full teardown
            self.closed = True

    server = FakeServer()
    addon._origin_mcp_bridge_server = server
    try:
        assert addon.request_stop_origin_mcp_bridge() == {"stop_requested": True}
    finally:
        addon._origin_mcp_bridge_server = None

    assert server.shutdown_requested_called is True
    assert server.closed is False


def test_addon_status_file_is_json(monkeypatch, tmp_path) -> None:
    addon = load_addon_module()
    status_path = tmp_path / "bridge-status.json"
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_STATUS", str(status_path))

    addon._emit("testing", fields={"running": True, "host": "127.0.0.1", "port": 1234})

    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["message"] == "testing"
    assert data["running"] is True
    assert data["host"] == "127.0.0.1"
    assert data["port"] == 1234
    assert data["status_path"] == str(status_path)
    assert data["python_executable"]


def test_missing_dependency_message_includes_origin_console_retry_snippet() -> None:
    addon = load_addon_module()

    message = addon._missing_dependency_message(["pandas>=2.0"])

    assert "Origin's embedded Python is missing" in message
    assert "Automatic installation is disabled" in message
    assert 'os.environ["ORIGIN_MCP_INSTALL_MISSING"] = "1"' in message
    assert "runpy.run_path" in message
    assert str(ROOT / "addon.py") in message
