"""Run the real-Origin release smoke gate.

Start the Origin bridge first, then run this script from the repository root.
It executes examples/smoke_bridge.py with deterministic output paths under
output/smoke and leaves a JSON report for release notes or troubleshooting.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "smoke"
DEFAULT_REPORT = DEFAULT_OUTPUT_DIR / "smoke-report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for PNG, OPJU, and JSON smoke outputs.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "examples" / "sample_data.csv",
        help="Input data file for the smoke workflow.",
    )
    parser.add_argument(
        "--keep-origin-open",
        action="store_true",
        help="Detach instead of quitting Origin after the smoke run.",
    )
    parser.add_argument(
        "--show-origin",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show the Origin GUI during the smoke run.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    report_path = output_dir / "smoke-report.json"
    command = [
        sys.executable,
        str(ROOT / "examples" / "smoke_bridge.py"),
        "--data",
        str(args.data.resolve()),
        "--output-dir",
        str(output_dir),
        "--report",
        str(report_path),
    ]
    command.append("--show-origin" if args.show_origin else "--no-show-origin")
    if args.keep_origin_open:
        command.append("--keep-origin-open")

    result = subprocess.run(command, cwd=ROOT, text=True, check=False)
    report = _read_report(report_path)
    ok = result.returncode == 0 and bool(report.get("ok"))
    print()
    print("Release smoke gate:", "PASS" if ok else "FAIL")
    print(f"Report: {report_path}")
    if report:
        print(f"Export: {report.get('paths', {}).get('export')}")
        print(f"Project: {report.get('paths', {}).get('project')}")
        print(f"Duration: {report.get('duration_sec')}s")
        if not report.get("ok"):
            print("Error:", (report.get("error") or {}).get("message"))
    return 0 if ok else 1


def _read_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
