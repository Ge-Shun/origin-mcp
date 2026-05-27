from __future__ import annotations

import importlib.util
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


def test_addon_auto_detects_adjacent_src(monkeypatch) -> None:
    addon = load_addon_module()
    monkeypatch.delenv("ORIGIN_MCP_SRC", raising=False)

    assert ROOT / "src" in addon._candidate_src_dirs()
    assert addon._ensure_origin_mcp_importable().endswith("origin_mcp")


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
