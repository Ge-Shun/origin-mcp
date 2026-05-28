from __future__ import annotations

import argparse
import json
from pathlib import Path

from origin_mcp.official_docs import diff_record_sets, load_generated_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two generated OriginLab official documentation indexes."
    )
    parser.add_argument("old_index", type=Path, help="Older generated official docs JSON index.")
    parser.add_argument("new_index", type=Path, help="Newer generated official docs JSON index.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON diff output path. Prints to stdout when omitted.",
    )
    args = parser.parse_args()

    diff = diff_record_sets(
        load_generated_records(args.old_index),
        load_generated_records(args.new_index),
    )
    payload = json.dumps(diff, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote official docs diff to {args.output}")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
