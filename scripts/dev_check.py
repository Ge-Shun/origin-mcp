"""Run fast local development checks with isolated tool caches."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_CACHE_ROOT = ROOT / "pytest-tmp-dev-check"


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tests",
        action="store_true",
        help="Also run pytest after the fast static checks.",
    )
    args = parser.parse_args()
    return run_checks(default_checks(include_tests=args.tests))


def default_checks(*, include_tests: bool = False) -> list[Check]:
    checks = [
        Check(
            "ruff check",
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                ".",
                "--cache-dir",
                str(CHECK_CACHE_ROOT / "ruff-cache"),
            ],
        ),
        Check(
            "ruff format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                ".",
                "--cache-dir",
                str(CHECK_CACHE_ROOT / "ruff-cache"),
            ],
        ),
        Check(
            "mypy",
            [sys.executable, "-m", "mypy", "--cache-dir", str(CHECK_CACHE_ROOT / "mypy")],
        ),
    ]
    if include_tests:
        checks.append(Check("pytest", [sys.executable, "-m", "pytest"]))
    return checks


def run_checks(checks: list[Check]) -> int:
    started = time.monotonic()
    for index, check in enumerate(checks, start=1):
        print(f"[{index}/{len(checks)}] {check.name}")
        print(" ".join(check.command))
        step_started = time.monotonic()
        result = subprocess.run(check.command, cwd=ROOT, check=False)
        duration = time.monotonic() - step_started
        if result.returncode != 0:
            print(f"{check.name}: FAIL ({duration:.1f}s)")
            print(f"Development checks failed after {time.monotonic() - started:.1f}s.")
            return result.returncode
        print(f"{check.name}: PASS ({duration:.1f}s)")
    print(f"Development checks passed in {time.monotonic() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
