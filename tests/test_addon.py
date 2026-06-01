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


def test_addon_registers_stable_control_module_alias() -> None:
    addon = load_addon_module()
    control_module = addon.sys.modules["origin_mcp_addon"]

    assert control_module.request_stop_origin_mcp_bridge is not None
    assert control_module.origin_mcp_bridge_status is not None


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


def test_stop_background_bridge_waits_for_thread_cleanup() -> None:
    addon = load_addon_module()

    class FakeServer:
        def __init__(self) -> None:
            self.shutdown_called = False
            self.close_count = 0

        def shutdown(self) -> None:
            self.shutdown_called = True

        def server_close(self) -> None:
            self.close_count += 1

    class FakeThread:
        def __init__(self) -> None:
            self.joined = False

        def join(self, timeout: float | None = None) -> None:
            self.joined = True

    server = FakeServer()
    thread = FakeThread()
    addon._origin_mcp_bridge_server = server
    addon._origin_mcp_bridge_thread = thread
    try:
        result = addon.stop_origin_mcp_bridge()
    finally:
        addon._origin_mcp_bridge_server = None
        addon._origin_mcp_bridge_thread = None

    assert result == {"stopped": True}
    assert server.shutdown_called is True
    assert thread.joined is True
    assert server.close_count == 0


def test_background_bridge_finalizes_when_serve_loop_exits(monkeypatch, tmp_path) -> None:
    addon = load_addon_module()
    status_path = tmp_path / "bridge-status.json"
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_STATUS", str(status_path))

    class FakeServer:
        def __init__(self) -> None:
            self.close_count = 0

        def serve_forever(self) -> None:
            return None

        def server_close(self) -> None:
            self.close_count += 1

    server = FakeServer()

    addon._origin_mcp_bridge_server = server
    addon._origin_mcp_bridge_thread = object()
    try:
        addon._serve_background(server)
    finally:
        addon._origin_mcp_bridge_server = None
        addon._origin_mcp_bridge_thread = None

    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert server.close_count == 1
    assert data["message"] == "stopped"
    assert data["running"] is False
    assert addon._origin_mcp_bridge_server is None
    assert addon._origin_mcp_bridge_thread is None


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


def test_user_install_flag_added_when_site_packages_not_writable(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.setattr(addon.sys, "prefix", addon.sys.base_prefix, raising=False)
    monkeypatch.setattr(addon, "_path_is_writable", lambda path: False)

    assert addon._user_install_flag() == ["--user"]


def test_user_install_flag_skipped_when_site_packages_writable(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.setattr(addon.sys, "prefix", addon.sys.base_prefix, raising=False)
    monkeypatch.setattr(addon, "_path_is_writable", lambda path: True)

    assert addon._user_install_flag() == []


def test_user_install_flag_skipped_in_virtualenv(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.setattr(addon.sys, "base_prefix", "/base", raising=False)
    monkeypatch.setattr(addon.sys, "prefix", "/venv", raising=False)
    monkeypatch.setattr(addon, "_path_is_writable", lambda path: False)

    assert addon._user_install_flag() == []


def test_install_missing_uses_user_flag_when_not_writable(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.setattr(addon, "_missing_runtime_packages", lambda: ["pandas>=2.0"])
    monkeypatch.setattr(addon, "_user_install_flag", lambda: ["--user"])
    monkeypatch.setattr(addon, "_ensure_user_site_on_path", lambda: None)
    captured: dict[str, list[str]] = {}

    def fake_pip(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(addon, "_pip", fake_pip)
    addon._install_missing_runtime_packages()

    assert captured["args"] == ["install", "--progress-bar", "off", "--user", "pandas>=2.0"]


def test_missing_dependency_message_includes_origin_console_retry_snippet() -> None:
    addon = load_addon_module()

    message = addon._missing_dependency_message(["pandas>=2.0"])

    assert "Origin's embedded Python is missing" in message
    assert "Automatic installation is disabled" in message
    assert 'os.environ["ORIGIN_MCP_INSTALL_MISSING"] = "1"' in message
    assert "runpy.run_path" in message
    assert str(ROOT / "addon.py") in message
