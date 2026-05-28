from __future__ import annotations

import argparse
import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from origin_mcp.official_docs import (
    GENERATED_INDEX_PATH,
    OfficialDocRecord,
    classify_originlab_doc_url,
    dedupe_records,
    discover_originpro_members_from_html,
    discover_records_from_html,
    extract_links,
    is_originlab_doc_url,
    validate_records,
)

ROOT_URLS = (
    "https://docs.originlab.com/python/",
    "https://docs.originlab.com/originpro/annotated.html",
    "https://docs.originlab.com/labtalk/ref/command-reference-by-category",
    "https://docs.originlab.com/labtalk/ref/function-reference",
    "https://docs.originlab.com/labtalk/ref/object-reference",
    "https://docs.originlab.com/x-function/ref/",
    "https://docs.originlab.com/x-function/ref/function-list",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the generated OriginLab official documentation index."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_INDEX_PATH,
        help="JSON index output path.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=300,
        help="Maximum official pages to fetch while discovering links.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum crawl depth from each root page.",
    )
    parser.add_argument(
        "--version",
        default="2026",
        help="Origin documentation version label to attach to generated records.",
    )
    args = parser.parse_args()

    records = crawl_records(
        root_urls=ROOT_URLS,
        version=args.version,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
    )
    validate_records(records)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "OriginLab official documentation",
        "pages": [record.as_json_dict() for record in records],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.output}")


def crawl_records(
    *,
    root_urls: tuple[str, ...],
    version: str,
    max_pages: int,
    max_depth: int,
) -> list[OfficialDocRecord]:
    versions = (version,)
    queue = deque((url, 0) for url in root_urls)
    seen_urls: set[str] = set()
    records: list[OfficialDocRecord] = []

    while queue and len(seen_urls) < max_pages:
        url, depth = queue.popleft()
        if url in seen_urls or not is_originlab_doc_url(url):
            continue
        seen_urls.add(url)

        direct_record = classify_originlab_doc_url(url, versions=versions)
        if direct_record is not None:
            records.append(direct_record)

        if depth >= max_depth:
            continue
        try:
            html = fetch_text(url)
        except RuntimeError as exc:
            print(f"warning: {exc}")
            continue

        records.extend(discover_records_from_html(html, url, versions=versions))
        if direct_record is not None:
            records.extend(discover_originpro_members_from_html(html, direct_record))
        for link_url, _text in extract_links(html, url):
            if should_follow(link_url) and link_url not in seen_urls:
                queue.append((link_url, depth + 1))

    return dedupe_records(records)


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "origin-mcp-doc-indexer"})
    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type and "text" not in content_type:
                raise RuntimeError(f"skipping non-HTML URL {url}: {content_type}")
            return response.read().decode("utf-8", errors="replace")
    except (OSError, URLError) as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc


def should_follow(url: str) -> bool:
    if not is_originlab_doc_url(url):
        return False
    return any(
        marker in url
        for marker in (
            "/python/",
            "/externalpython",
            "/originpro/",
            "/labtalk/ref/",
            "/x-function/ref/",
        )
    )


if __name__ == "__main__":
    main()
