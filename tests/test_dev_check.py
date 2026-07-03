from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_dev_check_module():
    spec = importlib.util.spec_from_file_location(
        "dev_check_test",
        ROOT / "scripts" / "dev_check.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_dev_checks_are_static_only() -> None:
    dev_check = load_dev_check_module()

    checks = dev_check.default_checks()
    names = [check.name for check in checks]

    assert names == ["ruff check", "ruff format", "mypy"]
    assert all("--cache-dir" in check.command for check in checks)


def test_dev_checks_can_include_tests() -> None:
    dev_check = load_dev_check_module()

    names = [check.name for check in dev_check.default_checks(include_tests=True)]

    assert names == ["ruff check", "ruff format", "mypy", "pytest"]


def test_run_checks_stops_on_first_failure(monkeypatch) -> None:
    dev_check = load_dev_check_module()
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 3)

    monkeypatch.setattr(dev_check.subprocess, "run", fake_run)
    checks = [
        dev_check.Check("first", ["first"]),
        dev_check.Check("second", ["second"]),
    ]

    assert dev_check.run_checks(checks) == 3
    assert calls == [["first"]]


def test_cli_adds_tests_step(monkeypatch) -> None:
    dev_check = load_dev_check_module()
    captured = {}

    def fake_run_checks(checks):
        captured["checks"] = checks
        return 0

    monkeypatch.setattr(dev_check, "run_checks", fake_run_checks)
    monkeypatch.setattr(dev_check.sys, "argv", ["dev_check.py", "--tests"])

    assert dev_check.main() == 0
    assert [check.name for check in captured["checks"]] == [
        "ruff check",
        "ruff format",
        "mypy",
        "pytest",
    ]
