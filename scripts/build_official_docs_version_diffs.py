from __future__ import annotations

import argparse
import json
from pathlib import Path

from origin_mcp.official_docs import build_version_diff_overlay, load_generated_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a compact version-diff overlay from generated official docs indexes."
    )
    parser.add_argument("--base", type=Path, required=True, help="Baseline generated index JSON.")
    parser.add_argument(
        "--version-index",
        action="append",
        nargs=2,
        metavar=("VERSION", "PATH"),
        required=True,
        help="Version label and generated index JSON to diff against the base.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Version diff JSON output path.")
    args = parser.parse_args()

    base_records = load_generated_records(args.base)
    diffs = {}
    versions = []
    for version, path_text in args.version_index:
        versions.append(version)
        version_records = load_generated_records(Path(path_text))
        diffs[version] = build_version_diff_overlay(base_records, version_records)

    payload = {
        "schema_version": 1,
        "base_version": "2026",
        "versions": sorted({*versions, "2026"}),
        "diffs": diffs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote official docs version diffs to {args.output}")


if __name__ == "__main__":
    main()
