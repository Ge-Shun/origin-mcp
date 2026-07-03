from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "release_consistency_test",
        ROOT / "scripts" / "check_release_consistency.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_consistency_passes_for_current_metadata() -> None:
    checker = load_checker_module()

    assert checker.check_release_consistency() == []


def test_release_consistency_detects_app_version_drift(monkeypatch) -> None:
    checker = load_checker_module()
    monkeypatch.setattr(checker, "read_package_version", lambda: "1.2.3")
    monkeypatch.setattr(checker, "read_app_builder_version", lambda: "1.2.4")

    problems = checker.check_release_consistency()

    assert any("does not match package version" in problem for problem in problems)
