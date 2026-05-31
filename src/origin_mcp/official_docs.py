from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

BASE_OFFICIAL_DOC_VERSION = "2026"
SUPPORTED_OFFICIAL_DOC_VERSIONS = ("2024", "2025", "2026")
GENERATED_INDEX_PATH = Path(__file__).with_name("official_docs.generated.json")
VERSION_DIFFS_PATH = Path(__file__).with_name("official_docs.version_diffs.json")
ORIGINLAB_DOC_HOSTS = {"docs.originlab.com", "www.originlab.com"}


@dataclass(frozen=True)
class OfficialDocRecord:
    path: str
    title: str
    summary: str
    url: str
    doc_family: str
    doc_kind: str
    keywords: tuple[str, ...] = ()
    body: str | None = None
    versions: tuple[str, ...] = ("2026",)
    locale: str = "en"
    version_status: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> OfficialDocRecord:
        return cls(
            path=str(data["path"]),
            title=str(data["title"]),
            summary=str(data["summary"]),
            url=str(data["url"]),
            doc_family=str(data["doc_family"]),
            doc_kind=str(data["doc_kind"]),
            keywords=tuple(str(item) for item in data.get("keywords", ())),
            body=data.get("body"),
            versions=tuple(str(item) for item in data.get("versions", ("2026",))),
            locale=str(data.get("locale", "en")),
            version_status=data.get("version_status"),
        )

    def as_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["keywords"] = list(self.keywords)
        data["versions"] = list(self.versions)
        if self.body is None:
            data.pop("body")
        if self.version_status is None:
            data.pop("version_status")
        return data


LABTALK_COMMAND_CATEGORIES = {
    "data-manipulation-and-calculation",
    "display-control",
    "project-management",
    "control-flow",
    "input-and-output",
    "script-management",
    "external-access",
    "time",
}

XFUNCTION_CATEGORY_SLUGS = {
    "data-exploration",
    "data-manipulation",
    "database-access",
    "fitting",
    "graph-manipulation",
    "image",
    "import-and-export",
    "mathematics",
    "miscellaneous",
    "plotting",
    "signal-processing",
    "spectroscopy",
    "statistics",
    "utilities",
    "vision",
}


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value for key, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self._active_href = href
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_href:
            text = " ".join("".join(self._active_text).split())
            self.links.append((self._active_href, text))
            self._active_href = None
            self._active_text = []


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkExtractor()
    parser.feed(html)
    links: list[tuple[str, str]] = []
    for href, text in parser.links:
        absolute_url = urljoin(base_url, href)
        url, _fragment = urldefrag(absolute_url)
        if is_originlab_doc_url(url):
            links.append((url, text))
    return _dedupe_links(links)


def classify_originlab_doc_url(
    url: str,
    text: str = "",
    *,
    versions: tuple[str, ...] = ("2026",),
) -> OfficialDocRecord | None:
    parsed = urlparse(url)
    if not is_originlab_doc_url(url):
        return None

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if parsed.netloc == "www.originlab.com" and parts[:2] == ["doc", "python"]:
        return _classify_external_python_url(url, text, versions)
    if parts[:2] == ["x-function", "ref"]:
        return _classify_xfunction_url(url, parts[2:], text, versions)
    if parts[:2] == ["labtalk", "ref"]:
        return _classify_labtalk_url(url, parts[2:], text, versions)
    if parts and parts[0] == "externalpython":
        return OfficialDocRecord(
            path="python/external-python",
            title=_clean_title(text) or "External Python",
            summary="Official documentation for controlling Origin from external Python.",
            url=url,
            doc_family="python",
            doc_kind="guide",
            keywords=("external python", "originpro", "automation"),
            versions=versions,
        )
    if parts and parts[0] == "python":
        return _classify_python_url(url, parts[1:], text, versions)
    if parts and parts[0] == "originpro":
        return _classify_originpro_url(url, parts[1:], text, versions)
    return None


def discover_records_from_html(
    html: str,
    base_url: str,
    *,
    versions: tuple[str, ...] = ("2026",),
) -> list[OfficialDocRecord]:
    records = []
    for url, text in extract_links(html, base_url):
        record = classify_originlab_doc_url(url, text, versions=versions)
        if record is not None and _is_xfunction_root_function(record):
            category = _xfunction_category_from_url(base_url)
            if category:
                slug = record.path.rsplit("/", 1)[-1]
                record = OfficialDocRecord(
                    path=f"x-function/{category}/{slug}",
                    title=record.title,
                    summary=f"Official X-Function page in {category}: {record.title}.",
                    url=record.url,
                    doc_family=record.doc_family,
                    doc_kind="xfunction",
                    keywords=(category, *record.keywords),
                    versions=record.versions,
                    locale=record.locale,
                )
        if record is None:
            labtalk_category = _labtalk_command_category_from_url(base_url)
            labtalk_command = _labtalk_command_from_url(url)
            if labtalk_category and labtalk_command:
                title = _clean_title(text) or labtalk_command
                record = OfficialDocRecord(
                    path=f"labtalk/commands/{labtalk_category}/{labtalk_command}",
                    title=title,
                    summary=f"Official LabTalk command page in {labtalk_category}: {title}.",
                    url=url,
                    doc_family="labtalk",
                    doc_kind="command",
                    keywords=(
                        "labtalk",
                        "command",
                        labtalk_category,
                        labtalk_command,
                        *_keywords_from_text(text),
                    ),
                    versions=versions,
                )
        if record is not None:
            records.append(record)
    return dedupe_records(records)


def discover_originpro_members_from_html(
    html: str,
    class_record: OfficialDocRecord,
) -> list[OfficialDocRecord]:
    if class_record.doc_family != "originpro_api" or class_record.doc_kind != "class":
        return []
    records: list[OfficialDocRecord] = []
    for member_name in _extract_doxygen_member_names(html):
        records.append(
            OfficialDocRecord(
                path=f"{class_record.path}/{member_name}",
                title=f"{class_record.title}.{member_name}",
                summary=f"Official originpro member documented on {class_record.title}.",
                url=class_record.url,
                doc_family="originpro_api",
                doc_kind="member",
                keywords=(
                    "originpro",
                    "api",
                    "member",
                    member_name,
                    *_keywords_from_path(class_record.path),
                ),
                versions=class_record.versions,
                locale=class_record.locale,
            )
        )
    return dedupe_records(records)


def load_generated_records(path: Path | None = None) -> list[OfficialDocRecord]:
    index_path = path or GENERATED_INDEX_PATH
    if not index_path.exists():
        return []
    data = json.loads(index_path.read_text(encoding="utf-8"))
    pages = data["pages"] if isinstance(data, dict) else data
    records = [OfficialDocRecord.from_mapping(item) for item in pages]
    validate_records(records)
    return records


def load_version_diffs(path: Path | None = None) -> dict[str, Any]:
    diff_path = path or VERSION_DIFFS_PATH
    if not diff_path.exists():
        return {"base_version": BASE_OFFICIAL_DOC_VERSION, "versions": {}, "diffs": {}}
    data = json.loads(diff_path.read_text(encoding="utf-8"))
    if data.get("base_version") != BASE_OFFICIAL_DOC_VERSION:
        raise ValueError(
            "official docs version diff base_version does not match "
            f"{BASE_OFFICIAL_DOC_VERSION}: {data.get('base_version')!r}"
        )
    return data


def records_for_version(
    base_records: list[OfficialDocRecord],
    version: str | None,
    diff_data: dict[str, Any] | None = None,
) -> list[OfficialDocRecord]:
    if version is None:
        return base_records
    if version not in SUPPORTED_OFFICIAL_DOC_VERSIONS:
        return []

    records = {
        record.path: _record_for_version(record, version, "baseline") for record in base_records
    }
    if version == BASE_OFFICIAL_DOC_VERSION:
        return [records[path] for path in sorted(records)]

    data = diff_data if diff_data is not None else load_version_diffs()
    diff = (data.get("diffs") or {}).get(version, {})
    for path in diff.get("removed", []):
        records.pop(str(path), None)
    for item in diff.get("changed", []):
        record = OfficialDocRecord.from_mapping(item)
        records[record.path] = _record_for_version(record, version, "changed")
    for item in diff.get("added", []):
        record = OfficialDocRecord.from_mapping(item)
        records[record.path] = _record_for_version(record, version, "added")
    return [records[path] for path in sorted(records)]


def merge_records(
    seed_records: list[OfficialDocRecord],
    generated_records: list[OfficialDocRecord],
) -> list[OfficialDocRecord]:
    merged = {record.path: record for record in seed_records}
    for record in generated_records:
        merged[record.path] = record
    return [merged[path] for path in sorted(merged)]


def dedupe_records(records: list[OfficialDocRecord]) -> list[OfficialDocRecord]:
    deduped: dict[str, OfficialDocRecord] = {}
    for record in records:
        deduped.setdefault(record.path, record)
    return [deduped[path] for path in sorted(deduped)]


def validate_records(records: list[OfficialDocRecord]) -> None:
    seen_paths: set[str] = set()
    for record in records:
        if not record.path or record.path.startswith("/") or "//" in record.path:
            raise ValueError(f"Invalid official docs path: {record.path!r}")
        if record.path in seen_paths:
            raise ValueError(f"Duplicate official docs path: {record.path}")
        seen_paths.add(record.path)
        if not is_originlab_doc_url(record.url):
            raise ValueError(f"Unsupported official docs URL for {record.path}: {record.url}")
        if not record.doc_family or not record.doc_kind:
            raise ValueError(f"Missing doc metadata for {record.path}")
        if not record.versions:
            raise ValueError(f"Missing versions metadata for {record.path}")


def diff_record_sets(
    old_records: list[OfficialDocRecord],
    new_records: list[OfficialDocRecord],
) -> dict[str, list[dict[str, Any]]]:
    old_by_path = {record.path: record for record in old_records}
    new_by_path = {record.path: record for record in new_records}
    added = sorted(set(new_by_path) - set(old_by_path))
    removed = sorted(set(old_by_path) - set(new_by_path))
    common = sorted(set(old_by_path) & set(new_by_path))
    changed = [
        path
        for path in common
        if _diffable_record_fields(old_by_path[path]) != _diffable_record_fields(new_by_path[path])
    ]
    return {
        "added": [_record_diff_summary(new_by_path[path]) for path in added],
        "removed": [_record_diff_summary(old_by_path[path]) for path in removed],
        "changed": [
            {
                "path": path,
                "old": _record_diff_summary(old_by_path[path]),
                "new": _record_diff_summary(new_by_path[path]),
            }
            for path in changed
        ],
    }


def build_version_diff_overlay(
    base_records: list[OfficialDocRecord],
    version_records: list[OfficialDocRecord],
) -> dict[str, Any]:
    base_by_path = {record.path: record for record in base_records}
    version_by_path = {record.path: record for record in version_records}
    added = sorted(set(version_by_path) - set(base_by_path))
    removed = sorted(set(base_by_path) - set(version_by_path))
    changed = [
        path
        for path in sorted(set(base_by_path) & set(version_by_path))
        if _diffable_record_fields(base_by_path[path])
        != _diffable_record_fields(version_by_path[path])
    ]
    return {
        "added": [version_by_path[path].as_json_dict() for path in added],
        "removed": removed,
        "changed": [version_by_path[path].as_json_dict() for path in changed],
    }


def is_originlab_doc_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in ORIGINLAB_DOC_HOSTS


def _classify_python_url(
    url: str,
    parts: list[str],
    text: str,
    versions: tuple[str, ...],
) -> OfficialDocRecord | None:
    if not parts:
        return OfficialDocRecord(
            path="python",
            title=_clean_title(text) or "OriginLab Python documentation",
            summary="Official overview of Python automation in Origin.",
            url=url,
            doc_family="python",
            doc_kind="chapter",
            keywords=("python", "originpro", "embedded python", "external python"),
            versions=versions,
        )
    slug = _slug("/".join(parts))
    path = f"python/{slug}"
    if "run-python-in-origin" in slug:
        path = "python/embedded-python"
        title = "Embedded Python"
    elif "running_python_code" in slug or "running-python-code" in slug:
        path = "python/running-python-code"
        title = "Running Python Code"
    elif "examples" in slug:
        path = "python/code-samples"
        title = "Python Code Samples"
    else:
        title = _clean_title(text) or _title_from_slug(slug)
    return OfficialDocRecord(
        path=path,
        title=title,
        summary=f"Official OriginLab Python documentation page: {title}.",
        url=url,
        doc_family="python",
        doc_kind="guide",
        keywords=("python", *_keywords_from_path(path), *_keywords_from_text(text)),
        versions=versions,
    )


def _classify_external_python_url(
    url: str,
    text: str,
    versions: tuple[str, ...],
) -> OfficialDocRecord:
    return OfficialDocRecord(
        path="python/external-python",
        title=_clean_title(text) or "External Python",
        summary="Official documentation for controlling Origin from external Python.",
        url=url,
        doc_family="python",
        doc_kind="guide",
        keywords=("external python", "originpro", "automation"),
        versions=versions,
    )


def _classify_originpro_url(
    url: str,
    parts: list[str],
    text: str,
    versions: tuple[str, ...],
) -> OfficialDocRecord | None:
    filename = parts[-1] if parts else ""
    if filename == "annotated.html":
        return OfficialDocRecord(
            path="python/originpro-api",
            title="originpro API class list",
            summary="Official Doxygen-style class list for the originpro Python package.",
            url=url,
            doc_family="originpro_api",
            doc_kind="class_index",
            keywords=("originpro", "api", "class list"),
            versions=versions,
        )

    match = re.match(r"classoriginpro_1_1(.+)\.html$", filename)
    if not match:
        return None

    module_parts = [part for part in match.group(1).split("_1_1") if part]
    if not module_parts:
        return None
    class_name = module_parts[-1]
    module_path = "/".join(module_parts[:-1])
    path = (
        f"python/originpro-api/{module_path}/{class_name}"
        if module_path
        else (f"python/originpro-api/{class_name}")
    )
    title = f"originpro.{'.'.join(module_parts)}"
    return OfficialDocRecord(
        path=path,
        title=title,
        summary=f"Official class page for {title}.",
        url=url,
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "api", *module_parts, *_keywords_from_text(text)),
        versions=versions,
    )


def _classify_labtalk_url(
    url: str,
    parts: list[str],
    text: str,
    versions: tuple[str, ...],
) -> OfficialDocRecord | None:
    if not parts:
        return OfficialDocRecord(
            path="labtalk",
            title="LabTalk language reference",
            summary="Official LabTalk language reference.",
            url=url,
            doc_family="labtalk",
            doc_kind="chapter",
            keywords=("labtalk", "commands", "functions", "objects"),
            versions=versions,
        )

    slug_parts = [_slug(part) for part in parts]
    first = slug_parts[0]
    if first == "command-reference-by-category":
        return OfficialDocRecord(
            path="labtalk/commands",
            title="LabTalk command reference by category",
            summary="Official command categories for LabTalk scripts.",
            url=url,
            doc_family="labtalk",
            doc_kind="category_index",
            keywords=("labtalk", "commands", "category"),
            versions=versions,
        )
    if first in LABTALK_COMMAND_CATEGORIES:
        path = f"labtalk/commands/{'/'.join(slug_parts)}"
        doc_kind = "command_category" if len(slug_parts) == 1 else "command"
        title = _clean_title(text) or _title_from_slug(slug_parts[-1])
        return OfficialDocRecord(
            path=path,
            title=title,
            summary=f"Official LabTalk {doc_kind.replace('_', ' ')} page: {title}.",
            url=url,
            doc_family="labtalk",
            doc_kind=doc_kind,
            keywords=("labtalk", doc_kind, *slug_parts, *_keywords_from_text(text)),
            versions=versions,
        )
    if first.startswith("function-reference"):
        return OfficialDocRecord(
            path="labtalk/functions",
            title=_clean_title(text) or "LabTalk function reference",
            summary="Official function reference grouped by function category.",
            url=url,
            doc_family="labtalk",
            doc_kind="function_index",
            keywords=("labtalk", "functions"),
            versions=versions,
        )
    if first.startswith("object-reference"):
        return OfficialDocRecord(
            path="labtalk/objects",
            title=_clean_title(text) or "LabTalk object reference",
            summary="Official reference for LabTalk objects, properties, and methods.",
            url=url,
            doc_family="labtalk",
            doc_kind="object_index",
            keywords=("labtalk", "objects", "properties", "methods"),
            versions=versions,
        )
    return None


def _classify_xfunction_url(
    url: str,
    parts: list[str],
    text: str,
    versions: tuple[str, ...],
) -> OfficialDocRecord | None:
    if not parts:
        return OfficialDocRecord(
            path="x-function",
            title="X-Function reference",
            summary="Official category index for Origin X-Functions.",
            url=url,
            doc_family="x_function",
            doc_kind="category_index",
            keywords=("x-function", "fitting", "plotting", "statistics"),
            versions=versions,
        )

    slug_parts = [_slug(part) for part in parts]
    first = slug_parts[0]
    if first == "function-list":
        return OfficialDocRecord(
            path="x-function/alphabetic-list",
            title="Alphabetic List to X-Functions",
            summary="Official alphabetic X-Function lookup.",
            url=url,
            doc_family="x_function",
            doc_kind="alphabetic_index",
            keywords=("x-function", "alphabetic", "lookup"),
            versions=versions,
        )
    if first == "function-details":
        path = "x-function/function-details"
        doc_kind = "detail_index"
    elif first in XFUNCTION_CATEGORY_SLUGS:
        path = f"x-function/{'/'.join(slug_parts)}"
        doc_kind = "xfunction_category" if len(slug_parts) == 1 else "xfunction"
    else:
        path = f"x-function/functions/{'/'.join(slug_parts)}"
        doc_kind = "xfunction"

    title = _clean_title(text) or _title_from_slug(slug_parts[-1])
    return OfficialDocRecord(
        path=path,
        title=title,
        summary=f"Official X-Function {doc_kind.replace('_', ' ')} page: {title}.",
        url=url,
        doc_family="x_function",
        doc_kind=doc_kind,
        keywords=("x-function", doc_kind, *slug_parts, *_keywords_from_text(text)),
        versions=versions,
    )


def _is_xfunction_root_function(record: OfficialDocRecord) -> bool:
    return record.doc_family == "x_function" and record.path.startswith("x-function/functions/")


def _xfunction_category_from_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if len(parts) >= 3 and parts[:2] == ["x-function", "ref"]:
        slug = _slug(parts[2])
        if slug in XFUNCTION_CATEGORY_SLUGS:
            return slug
    return None


def _labtalk_command_category_from_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if len(parts) >= 3 and parts[:2] == ["labtalk", "ref"]:
        slug = _slug(parts[2])
        if slug in LABTALK_COMMAND_CATEGORIES:
            return slug
    return None


def _labtalk_command_from_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if len(parts) >= 3 and parts[:2] == ["labtalk", "ref"]:
        slug = _slug(parts[2])
        if slug.endswith("-cmd"):
            return slug.removesuffix("-cmd")
        if slug == "document_options_to_append":
            return "document-t"
        if slug == "selection-cmd":
            return "select"
    return None


def _dedupe_links(links: list[tuple[str, str]]) -> list[tuple[str, str]]:
    deduped: dict[str, str] = {}
    for url, text in links:
        deduped.setdefault(url, text)
    return [(url, deduped[url]) for url in sorted(deduped)]


def _clean_title(text: str) -> str:
    title = " ".join(text.split())
    return title.strip(" -|")


def _slug(text: str) -> str:
    return text.strip().strip("/").lower()


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _keywords_from_path(path: str) -> tuple[str, ...]:
    return tuple(part for part in re.split(r"[/_.-]+", path.lower()) if part)


def _keywords_from_text(text: str) -> tuple[str, ...]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{1,}", text)
    return tuple(dict.fromkeys(word for word in words[:8]))


def _diffable_record_fields(record: OfficialDocRecord) -> tuple[str, str, str, str]:
    return (record.title, record.summary, record.url, record.doc_kind)


def _record_diff_summary(record: OfficialDocRecord) -> dict[str, Any]:
    return {
        "path": record.path,
        "title": record.title,
        "url": record.url,
        "doc_family": record.doc_family,
        "doc_kind": record.doc_kind,
        "versions": list(record.versions),
    }


def _record_for_version(
    record: OfficialDocRecord,
    version: str,
    version_status: str,
) -> OfficialDocRecord:
    return OfficialDocRecord(
        path=record.path,
        title=record.title,
        summary=record.summary,
        url=record.url,
        doc_family=record.doc_family,
        doc_kind=record.doc_kind,
        keywords=record.keywords,
        versions=(version,),
        body=record.body,
        locale=record.locale,
        version_status=version_status,
    )


def _extract_doxygen_member_names(html: str) -> list[str]:
    names: list[str] = []
    rows = re.findall(
        r'<td class="memItemLeft"[^>]*>(.*?)</td>\s*'
        r'<td class="memItemRight"[^>]*>(.*?)</td>',
        html,
        re.S,
    )
    for left, right in rows:
        text = _strip_html(f"{left} {right}")
        match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
        if match:
            names.append(match.group(1))
    return list(dict.fromkeys(names))


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text).replace("\xa0", " ")
    return " ".join(text.split())
