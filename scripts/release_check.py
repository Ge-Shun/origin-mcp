"""Run the standard origin-mcp release checks from one command."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_CACHE_ROOT = ROOT / "pytest-tmp-release-check"


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-origin-smoke",
        action="store_true",
        help="Also run the real-Origin smoke gate. Start the Origin bridge first.",
    )
    parser.add_argument(
        "--real-origin-health",
        action="store_true",
        help="Also run the lightweight real-Origin bridge health gate.",
    )
    parser.add_argument(
        "--keep-origin-open",
        action="store_true",
        help="Pass --keep-origin-open to the real-Origin smoke gate.",
    )
    parser.add_argument(
        "--show-origin",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show the Origin GUI during the real-Origin smoke gate.",
    )
    args = parser.parse_args()

    checks = default_checks()
    if args.real_origin_health:
        health = [
            sys.executable,
            "scripts\\real_origin_health.py",
            "--show-origin" if args.show_origin else "--no-show-origin",
        ]
        checks.append(Check("real Origin health", health))
    if args.real_origin_smoke:
        smoke = [
            sys.executable,
            "scripts\\real_origin_smoke.py",
            "--show-origin" if args.show_origin else "--no-show-origin",
        ]
        if args.keep_origin_open:
            smoke.append("--keep-origin-open")
        checks.append(Check("real Origin smoke", smoke))

    return run_checks(checks)


def default_checks() -> list[Check]:
    return [
        Check("pytest", [sys.executable, "-m", "pytest"]),
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
            "mypy", [sys.executable, "-m", "mypy", "--cache-dir", str(CHECK_CACHE_ROOT / "mypy")]
        ),
        Check(
            "release consistency",
            [sys.executable, "scripts\\check_release_consistency.py"],
        ),
    ]


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
            print(f"Release checks failed after {time.monotonic() - started:.1f}s.")
            return result.returncode
        print(f"{check.name}: PASS ({duration:.1f}s)")
    print(f"Release checks passed in {time.monotonic() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
