from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import pytest

import origin_mcp.cli as cli
import origin_mcp.diagnostics as diagnostics
from origin_mcp.diagnostics import (
    EXIT_DEGRADED,
    EXIT_DIAGNOSTIC_ERROR,
    EXIT_HEALTHY,
    EXIT_NOT_RUNNING,
    classify_diagnostics,
    status_file_candidates,
)


def diagnostic_report(
    *,
    bridge_ok: bool,
    origin: dict[str, Any] | None = None,
    status_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": {"host": "127.0.0.1", "port": 47631, "timeout": 2.0},
        "bridge": (
            {"ok": True, "response": {"bridge": "origin-mcp-bridge"}}
            if bridge_ok
            else {
                "ok": False,
                "error_code": "origin_bridge_unavailable",
                "message": "connection refused",
            }
        ),
        "origin": origin,
        "status_file": {
            "path": r"C:\Temp\origin-mcp\status.json",
            "exists": status_data is not None,
            "readable": status_data is not None,
            "data": status_data,
        },
        "status_diagnostics": status_data or {},
        "log": {"enabled": True, "exists": False, "path": r"C:\Temp\bridge.log"},
        "recommendations": ["Click the Origin MCP Bridge Start App."],
    }


def test_cli_without_arguments_starts_mcp_server(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_server_main() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("origin_mcp.server.main", fake_server_main)

    assert cli.main([]) == EXIT_HEALTHY
    assert called is True


def test_status_prints_human_summary(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    report = diagnostic_report(bridge_ok=True)
    monkeypatch.setattr(cli, "collect_diagnostics", lambda **_kwargs: report)

    exit_code = cli.main(["status"])
    output = capsys.readouterr().out

    assert exit_code == EXIT_HEALTHY
    assert "Origin MCP bridge: RUNNING" in output
    assert "Bridge: reachable" in output
    assert "Address: 127.0.0.1:47631" in output


def test_status_json_reports_not_running(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    report = diagnostic_report(bridge_ok=False)
    monkeypatch.setattr(cli, "collect_diagnostics", lambda **_kwargs: report)

    exit_code = cli.main(["status", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_NOT_RUNNING
    assert payload["state"] == "not_running"
    assert payload["exit_code"] == EXIT_NOT_RUNNING
    assert payload["diagnostics"]["bridge"]["ok"] is False


def test_doctor_forwards_ping_origin_and_reports_degraded(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    captured: dict[str, Any] = {}
    report = diagnostic_report(
        bridge_ok=True,
        origin={
            "ok": False,
            "error_code": "origin_operation_failed",
            "message": "Origin is busy",
        },
    )

    def fake_collect(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return report

    monkeypatch.setattr(cli, "collect_diagnostics", fake_collect)

    exit_code = cli.main(["doctor", "--ping-origin"])
    output = capsys.readouterr().out

    assert exit_code == EXIT_DEGRADED
    assert captured["ping_origin"] is True
    assert "Origin MCP doctor: DEGRADED" in output
    assert "Origin: failed (origin_operation_failed)" in output


def test_diagnostics_command_failure_has_stable_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    def fail(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("bad configuration")

    monkeypatch.setattr(cli, "collect_diagnostics", fail)

    exit_code = cli.main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_DIAGNOSTIC_ERROR
    assert payload == {
        "state": "diagnostic_error",
        "exit_code": EXIT_DIAGNOSTIC_ERROR,
        "error_type": "RuntimeError",
        "message": "bad configuration",
    }


def test_status_candidates_include_installed_start_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setattr("origin_mcp.diagnostics.read_handshake", lambda: None)

    candidates = status_file_candidates()

    expected = (
        local_appdata
        / "OriginLab"
        / "Apps"
        / "Origin MCP Bridge Start"
        / "origin-bridge.status.txt"
    ).resolve()
    assert expected in candidates


def test_read_status_prefers_newest_conventional_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    older = tmp_path / "older.json"
    newer = tmp_path / "newer.json"
    older.write_text('{"message": "older"}', encoding="utf-8")
    newer.write_text('{"message": "newer"}', encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    monkeypatch.setattr(diagnostics, "status_file_candidates", lambda _path=None: [older, newer])
    monkeypatch.setattr(
        diagnostics,
        "_configured_status_file_candidates",
        lambda _path=None: [],
    )

    result = diagnostics.read_bridge_status()

    assert result["path"] == str(newer)
    assert result["data"]["message"] == "newer"


@pytest.mark.parametrize(
    ("status_data", "expected_state", "expected_exit"),
    [
        ({"install_phase": "checking_dependencies"}, "starting", EXIT_DEGRADED),
        (
            {"install_phase": "failed", "last_error": "pip failed"},
            "failed",
            EXIT_DEGRADED,
        ),
        ({"running": False, "message": "stopped"}, "stopped", EXIT_NOT_RUNNING),
        (
            {"updated_at": "2026-01-01T00:00:00Z"},
            "stale",
            EXIT_NOT_RUNNING,
        ),
    ],
)
def test_classify_non_running_states(
    status_data: dict[str, Any],
    expected_state: str,
    expected_exit: int,
) -> None:
    report = diagnostic_report(bridge_ok=False, status_data=status_data)

    result = classify_diagnostics(
        report,
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert result["state"] == expected_state
    assert result["exit_code"] == expected_exit
