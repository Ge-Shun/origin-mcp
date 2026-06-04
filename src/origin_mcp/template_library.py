"""User graph-template library: storage, indexing, and search.

This module is intentionally free of any ``originpro``/Origin dependency so it
can be imported from both processes: the MCP server core (which only searches
and lists) and the Origin-embedded bridge (which saves templates). Both share
the same on-disk library because they run on the same machine.

Layout under :func:`template_root` (default ``~/.origin-mcp/templates``):

* ``<slug>.otpu`` -- the Origin graph template written by ``template_saveas``.
* ``<slug>.json`` -- a :class:`~origin_mcp.models.TemplateRecord` sidecar with
  searchable metadata.
* ``<slug>.png``  -- an optional preview thumbnail.
* ``index.json``  -- an aggregate list of every record, rebuilt from the
  sidecars if it goes missing or is corrupted.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# NOTE: this module is imported by the Origin-embedded bridge, whose Python does
# not ship pydantic. Keep it dependency-light -- the record is a plain dataclass,
# not a pydantic model (those live in models.py and are used only server-side).


@dataclass
class TemplateRecord:
    """Searchable metadata sidecar for one saved user graph template."""

    name: str
    slug: str
    otpu_path: str
    created_at: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    plot_types: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    n_columns: int | None = None
    layer_count: int | None = None
    plots_count: int | None = None
    source_graph: str | None = None
    thumbnail_path: str | None = None


INDEX_FILENAME = "index.json"
TEMPLATE_SUFFIXES = (".otpu", ".otp")

# Plot kinds that are close enough that a template for one is a reasonable
# starting point for another. Families may overlap (line_symbol bridges line and
# scatter): two kinds count as related only when one family contains both, so a
# plain line template is not offered for a scatter request and vice versa.
_PLOT_FAMILIES: tuple[frozenset[str], ...] = (
    frozenset({"line", "line_symbol"}),
    frozenset({"scatter", "line_symbol", "bubble"}),
    frozenset({"column", "bar", "histogram"}),
    frozenset({"contour", "heatmap"}),
    frozenset({"box", "violin"}),
    frozenset({"scatter3d", "surface3d"}),
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def template_root() -> Path:
    """Directory holding the user's template library.

    Honors ``ORIGIN_MCP_TEMPLATE_DIR``; otherwise defaults to
    ``~/.origin-mcp/templates``. The path is not created here.
    """

    configured = os.environ.get("ORIGIN_MCP_TEMPLATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".origin-mcp" / "templates"


def slugify(name: str) -> str:
    """Turn a template name into a filesystem-safe stem.

    Keeps ASCII letters, digits, dash, and underscore; collapses every other
    run of characters into a single underscore. Falls back to ``template`` when
    nothing usable remains (e.g. a name that is purely punctuation or CJK).
    """

    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return slug or "template"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def index_path(root: Path | None = None) -> Path:
    return (root or template_root()) / INDEX_FILENAME


def load_index(root: Path | None = None) -> list[dict[str, Any]]:
    """Return every template record.

    Reads ``index.json`` when present and valid; otherwise rebuilds the list by
    scanning the directory's ``*.json`` sidecars so a deleted or corrupted index
    self-heals on the next read.
    """

    root = root or template_root()
    path = index_path(root)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except (json.JSONDecodeError, OSError):
            pass
    return _rebuild_index_from_sidecars(root)


def _rebuild_index_from_sidecars(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for sidecar in sorted(root.glob("*.json")):
        if sidecar.name == INDEX_FILENAME:
            continue
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("name"):
            records.append(data)
    return records


def write_template_record(record: TemplateRecord, root: Path | None = None) -> dict[str, Any]:
    """Persist a record's sidecar and upsert it into the index by ``name``.

    Returns the written record as a plain dict.
    """

    root = root or template_root()
    root.mkdir(parents=True, exist_ok=True)
    payload = asdict(record)

    sidecar = root / f"{record.slug}.json"
    sidecar.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    index = [item for item in load_index(root) if item.get("name") != record.name]
    index.append(payload)
    index.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    index_path(root).write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def _write_index(index: list[dict[str, Any]], root: Path) -> None:
    if index:
        index_path(root).write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return
    # Nothing left: drop the index file so an empty library leaves no stale index.
    try:
        index_path(root).unlink(missing_ok=True)
    except OSError:
        pass


def delete_template(name: str, root: Path | None = None) -> dict[str, Any]:
    """Delete a saved template (its .otpu/.json/.png) and drop it from the index.

    Returns ``{"deleted": False, "reason": "not_found"}`` when no template carries
    that name. Missing files are skipped silently so a partially-removed template
    still cleans up its index entry.
    """

    root = root or template_root()
    index = load_index(root)
    removed = [item for item in index if item.get("name") == name]
    if not removed:
        return {"deleted": False, "reason": "not_found", "name": name}

    deleted_files: list[str] = []
    seen: set[Path] = set()
    for item in removed:
        slug = str(item.get("slug") or slugify(name))
        candidates = [root / f"{slug}{suffix}" for suffix in (".otpu", ".otp", ".json", ".png")]
        for key in ("otpu_path", "thumbnail_path"):
            value = item.get(key)
            if value:
                candidates.append(Path(str(value)))
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            try:
                if path.is_file():
                    path.unlink()
                    deleted_files.append(str(path))
            except OSError:
                pass

    remaining = [item for item in index if item.get("name") != name]
    _write_index(remaining, root)
    return {
        "deleted": True,
        "name": name,
        "removed_files": deleted_files,
        "remaining": len(remaining),
    }


def _existing_otpu(root: Path, slug: str) -> str:
    """Path string of ``<slug>``'s template file, preferring .otpu over .otp."""

    for suffix in TEMPLATE_SUFFIXES:
        candidate = root / f"{slug}{suffix}"
        if candidate.is_file():
            return str(candidate)
    return str(root / f"{slug}.otpu")


def _persist_record(record: dict[str, Any], index: list[dict[str, Any]], root: Path) -> None:
    """Write ``record``'s sidecar and upsert it into ``index`` by name."""

    slug = str(record.get("slug") or slugify(str(record.get("name", ""))))
    (root / f"{slug}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    merged = [item for item in index if item.get("name") != record.get("name")]
    merged.append(record)
    merged.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    _write_index(merged, root)


def rename_template(old_name: str, new_name: str, root: Path | None = None) -> dict[str, Any]:
    """Rename a saved template's files, slug, and index entry. No Origin needed.

    Returns ``{"renamed": False, "reason": ...}`` for ``not_found`` (no template
    named ``old_name``), ``same_name``, ``name_exists`` (another template already
    uses ``new_name``), or ``slug_exists`` (the new slug would clobber unrelated
    files).
    """

    root = root or template_root()
    if not new_name.strip():
        return {"renamed": False, "reason": "invalid_name", "name": new_name}
    index = load_index(root)
    target = next((item for item in index if item.get("name") == old_name), None)
    if target is None:
        return {"renamed": False, "reason": "not_found", "name": old_name}
    if old_name == new_name:
        return {"renamed": False, "reason": "same_name", "name": new_name}
    if any(item.get("name") == new_name for item in index):
        return {"renamed": False, "reason": "name_exists", "name": new_name}

    old_slug = str(target.get("slug") or slugify(old_name))
    new_slug = slugify(new_name)
    suffixes = (".otpu", ".otp", ".png")
    if new_slug != old_slug and any((root / f"{new_slug}{s}").exists() for s in suffixes):
        return {"renamed": False, "reason": "slug_exists", "slug": new_slug}

    if new_slug != old_slug:
        for suffix in suffixes:
            src = root / f"{old_slug}{suffix}"
            if src.is_file():
                src.replace(root / f"{new_slug}{suffix}")
        (root / f"{old_slug}.json").unlink(missing_ok=True)

    updated = dict(target)
    updated["name"] = new_name
    updated["slug"] = new_slug
    updated["otpu_path"] = _existing_otpu(root, new_slug)
    thumb = root / f"{new_slug}.png"
    updated["thumbnail_path"] = str(thumb) if thumb.is_file() else None

    remaining = [item for item in index if item.get("name") != old_name]
    _persist_record(updated, remaining, root)
    return {"renamed": True, "old_name": old_name, "new_name": new_name, "template": updated}


_UNSET: Any = object()


def update_template_metadata(
    name: str,
    description: Any = _UNSET,
    tags: Any = _UNSET,
    plot_types: Any = _UNSET,
    roles: Any = _UNSET,
    n_columns: Any = _UNSET,
    root: Path | None = None,
) -> dict[str, Any]:
    """Edit a template's searchable metadata in place. No Origin / redraw needed.

    Only the fields you pass are changed; omitted fields are left untouched. The
    ``.otpu`` template file itself is not modified. Returns
    ``{"updated": False, "reason": "not_found"}`` when no template carries ``name``.
    """

    root = root or template_root()
    index = load_index(root)
    target = next((item for item in index if item.get("name") == name), None)
    if target is None:
        return {"updated": False, "reason": "not_found", "name": name}

    updated = dict(target)
    changed: list[str] = []
    if description is not _UNSET:
        updated["description"] = description
        changed.append("description")
    if tags is not _UNSET:
        updated["tags"] = [str(tag) for tag in (tags or []) if str(tag).strip()]
        changed.append("tags")
    if plot_types is not _UNSET:
        updated["plot_types"] = [
            str(value).strip().lower() for value in (plot_types or []) if str(value).strip()
        ]
        changed.append("plot_types")
    if roles is not _UNSET:
        updated["roles"] = [
            str(role).strip().lower() for role in (roles or []) if str(role).strip()
        ]
        changed.append("roles")
    if n_columns is not _UNSET:
        updated["n_columns"] = n_columns
        changed.append("n_columns")

    if changed:
        remaining = [item for item in index if item.get("name") != name]
        _persist_record(updated, remaining, root)
    return {"updated": True, "name": name, "changed": changed, "template": updated}


def resolve_template_name(name: str, root: Path | None = None) -> Path | None:
    """Resolve a bare template name to a saved ``.otpu``/``.otp`` path.

    Tries the name verbatim, then its slug, then an index lookup by ``name``.
    Returns ``None`` when the library has no matching template file so callers
    can fall back to Origin's own template resolution.
    """

    root = root or template_root()
    if not root.is_dir():
        return None
    for stem in _dedupe((name, slugify(name))):
        for suffix in TEMPLATE_SUFFIXES:
            candidate = root / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    for item in load_index(root):
        if item.get("name") == name:
            otpu = item.get("otpu_path")
            if otpu and Path(otpu).is_file():
                return Path(otpu)
    return None


def search_templates(
    query: str | None = None,
    plot_type: str | None = None,
    n_columns: int | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Rank the library against an intended plot and return the best matches.

    With no criteria, returns the whole library most-recent-first. Each result
    carries ``score`` and ``match_reasons`` so the assistant can explain why a
    template was suggested.
    """

    records = load_index(root)
    has_criteria = bool(query or plot_type or n_columns is not None or tags)
    tag_terms = [tag.strip().lower() for tag in (tags or []) if tag.strip()]
    query_terms = set(_WORD_RE.findall(query.lower())) if query else set()

    scored: list[tuple[float, dict[str, Any]]] = []
    for record in records:
        score, reasons = _score_record(record, query_terms, plot_type, n_columns, tag_terms)
        if has_criteria and score <= 0:
            continue
        enriched = {**record, "score": round(score, 2), "match_reasons": reasons}
        scored.append((score, enriched))

    scored.sort(key=lambda item: (item[0], str(item[1].get("created_at", ""))), reverse=True)
    return [record for _, record in scored[: max(1, limit)]]


def _score_record(
    record: dict[str, Any],
    query_terms: set[str],
    plot_type: str | None,
    n_columns: int | None,
    tag_terms: list[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    record_plot_types = {str(value).lower() for value in record.get("plot_types") or []}
    record_tags = {str(value).lower() for value in record.get("tags") or []}

    if plot_type:
        wanted = plot_type.strip().lower()
        if wanted in record_plot_types:
            score += 100
            reasons.append(f"plot_type matches {wanted}")
        elif _same_family(wanted, record_plot_types):
            score += 40
            reasons.append(f"plot_type {wanted} is in the same family")

    if n_columns is not None and record.get("n_columns") is not None:
        delta = abs(int(record["n_columns"]) - int(n_columns))
        if delta == 0:
            score += 30
            reasons.append(f"column count matches ({n_columns})")
        elif delta == 1:
            score += 15
            reasons.append(f"column count within 1 of {n_columns}")

    matched_tags = [tag for tag in tag_terms if tag in record_tags]
    if matched_tags:
        score += 20 * len(matched_tags)
        reasons.append(f"tags match: {', '.join(matched_tags)}")

    if query_terms:
        haystack = _record_terms(record)
        overlap = query_terms & haystack
        if overlap:
            score += 10 * len(overlap)
            reasons.append(f"keywords match: {', '.join(sorted(overlap))}")

    return score, reasons


def _record_terms(record: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for key in ("name", "description"):
        value = record.get(key)
        if value:
            terms.update(_WORD_RE.findall(str(value).lower()))
    for collection in ("tags", "plot_types", "roles"):
        for value in record.get(collection) or []:
            terms.update(_WORD_RE.findall(str(value).lower()))
    return terms


def _same_family(plot_type: str, record_plot_types: set[str]) -> bool:
    for family in _PLOT_FAMILIES:
        if plot_type in family and record_plot_types & family:
            return True
    return False


def _dedupe(values: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
