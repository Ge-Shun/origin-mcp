from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_release_check_module():
    spec = importlib.util.spec_from_file_location(
        "release_check_test",
        ROOT / "scripts" / "release_check.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_release_checks_include_static_and_metadata_steps() -> None:
    release_check = load_release_check_module()

    checks = release_check.default_checks()
    names = [check.name for check in checks]

    assert names == ["pytest", "ruff check", "ruff format", "mypy", "release consistency"]
    assert "--cache-dir" in checks[1].command
    assert "--cache-dir" in checks[2].command
    assert "--cache-dir" in checks[3].command


def test_run_checks_stops_on_first_failure(monkeypatch) -> None:
    release_check = load_release_check_module()
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(release_check.subprocess, "run", fake_run)
    checks = [
        release_check.Check("first", ["first"]),
        release_check.Check("second", ["second"]),
    ]

    assert release_check.run_checks(checks) == 7
    assert calls == [["first"]]


def test_cli_adds_real_origin_smoke_step(monkeypatch) -> None:
    release_check = load_release_check_module()
    captured = {}

    def fake_run_checks(checks):
        captured["checks"] = checks
        return 0

    monkeypatch.setattr(release_check, "run_checks", fake_run_checks)
    monkeypatch.setattr(
        release_check.sys,
        "argv",
        [
            "release_check.py",
            "--real-origin-smoke",
            "--keep-origin-open",
            "--no-show-origin",
        ],
    )

    assert release_check.main() == 0
    smoke = captured["checks"][-1]
    assert smoke.name == "real Origin smoke"
    assert smoke.command == [
        sys.executable,
        "scripts\\real_origin_smoke.py",
        "--no-show-origin",
        "--keep-origin-open",
    ]


def test_cli_adds_real_origin_health_before_smoke(monkeypatch) -> None:
    release_check = load_release_check_module()
    captured = {}

    def fake_run_checks(checks):
        captured["checks"] = checks
        return 0

    monkeypatch.setattr(release_check, "run_checks", fake_run_checks)
    monkeypatch.setattr(
        release_check.sys,
        "argv",
        [
            "release_check.py",
            "--real-origin-health",
            "--real-origin-smoke",
            "--no-show-origin",
        ],
    )

    assert release_check.main() == 0
    names = [check.name for check in captured["checks"][-2:]]
    assert names == ["real Origin health", "real Origin smoke"]
    assert captured["checks"][-2].command == [
        sys.executable,
        "scripts\\real_origin_health.py",
        "--no-show-origin",
    ]
