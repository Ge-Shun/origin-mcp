"""Tests for the user template library: storage, indexing, search, and save."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_origin import FakeOp

from origin_mcp import template_library
from origin_mcp.origin_client import OriginClient
from origin_mcp.template_library import TemplateRecord


@pytest.fixture
def library_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "templates"
    monkeypatch.setenv("ORIGIN_MCP_TEMPLATE_DIR", str(root))
    yield root


def _record(name: str, **overrides: object) -> TemplateRecord:
    payload: dict[str, object] = {
        "name": name,
        "slug": template_library.slugify(name),
        "otpu_path": f"/tmp/{template_library.slugify(name)}.otpu",
        "created_at": template_library.now_iso(),
    }
    payload.update(overrides)
    return TemplateRecord(**payload)  # type: ignore[arg-type]


def test_template_root_honors_env(library_dir: Path) -> None:
    assert template_library.template_root() == library_dir


def test_slugify_sanitizes_names() -> None:
    assert template_library.slugify("My Nature Scatter!") == "My_Nature_Scatter"
    # A purely non-ASCII name still yields a usable stem.
    assert template_library.slugify("散点图") == "template"


def test_write_record_creates_sidecar_and_index(library_dir: Path) -> None:
    template_library.write_template_record(_record("alpha", plot_types=["scatter"]))

    sidecar = library_dir / "alpha.json"
    assert sidecar.is_file()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["name"] == "alpha"

    index = json.loads((library_dir / "index.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in index] == ["alpha"]


def test_write_record_upserts_by_name(library_dir: Path) -> None:
    template_library.write_template_record(_record("alpha", description="first"))
    template_library.write_template_record(_record("alpha", description="second"))

    index = template_library.load_index()
    assert len(index) == 1
    assert index[0]["description"] == "second"


def test_load_index_rebuilds_from_sidecars_when_corrupt(library_dir: Path) -> None:
    template_library.write_template_record(_record("alpha"))
    template_library.write_template_record(_record("beta"))
    (library_dir / "index.json").write_text("{ not json", encoding="utf-8")

    names = {item["name"] for item in template_library.load_index()}
    assert names == {"alpha", "beta"}


def test_resolve_template_name(library_dir: Path, tmp_path: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    otpu = library_dir / "alpha.otpu"
    otpu.write_text("x", encoding="utf-8")
    template_library.write_template_record(_record("alpha", otpu_path=str(otpu)))

    assert template_library.resolve_template_name("alpha") == otpu
    # Slugged lookup also resolves a spaced display name.
    spaced = library_dir / "My_Plot.otpu"
    spaced.write_text("x", encoding="utf-8")
    assert template_library.resolve_template_name("My Plot") == spaced
    # Unknown names fall through to None so callers use Origin's own resolution.
    assert template_library.resolve_template_name("missing") is None


def test_delete_template_removes_files_and_index_entry(library_dir: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    for suffix in (".otpu", ".png"):
        (library_dir / f"alpha{suffix}").write_text("x", encoding="utf-8")
    template_library.write_template_record(
        _record("alpha", otpu_path=str(library_dir / "alpha.otpu"))
    )
    template_library.write_template_record(_record("beta"))

    result = template_library.delete_template("alpha")
    assert result["deleted"] is True
    assert result["remaining"] == 1
    assert not (library_dir / "alpha.otpu").exists()
    assert not (library_dir / "alpha.png").exists()
    assert not (library_dir / "alpha.json").exists()
    assert {item["name"] for item in template_library.load_index()} == {"beta"}


def test_delete_template_missing_is_not_found(library_dir: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    result = template_library.delete_template("nope")
    assert result == {"deleted": False, "reason": "not_found", "name": "nope"}


def test_delete_last_template_clears_index_file(library_dir: Path) -> None:
    template_library.write_template_record(_record("only"))
    template_library.delete_template("only")
    assert not (library_dir / "index.json").exists()
    assert template_library.load_index() == []


def test_rename_template_moves_files_and_updates_index(library_dir: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    for suffix in (".otpu", ".png"):
        (library_dir / f"alpha{suffix}").write_text("x", encoding="utf-8")
    template_library.write_template_record(
        _record(
            "alpha",
            otpu_path=str(library_dir / "alpha.otpu"),
            thumbnail_path=str(library_dir / "alpha.png"),
        )
    )

    result = template_library.rename_template("alpha", "Renamed Plot")
    assert result["renamed"] is True
    rec = result["template"]
    assert rec["name"] == "Renamed Plot"
    assert rec["slug"] == "Renamed_Plot"
    assert rec["otpu_path"] == str(library_dir / "Renamed_Plot.otpu")
    assert rec["thumbnail_path"] == str(library_dir / "Renamed_Plot.png")

    assert not (library_dir / "alpha.otpu").exists()
    assert not (library_dir / "alpha.json").exists()
    assert (library_dir / "Renamed_Plot.otpu").is_file()
    assert (library_dir / "Renamed_Plot.png").is_file()
    assert {item["name"] for item in template_library.load_index()} == {"Renamed Plot"}
    # Searchable under the new name's slug resolution.
    assert template_library.resolve_template_name("Renamed Plot") == (
        library_dir / "Renamed_Plot.otpu"
    )


def test_rename_template_guards(library_dir: Path) -> None:
    template_library.write_template_record(_record("alpha"))
    template_library.write_template_record(_record("beta"))

    assert template_library.rename_template("missing", "x")["reason"] == "not_found"
    assert template_library.rename_template("alpha", "alpha")["reason"] == "same_name"
    assert template_library.rename_template("alpha", "beta")["reason"] == "name_exists"
    assert template_library.rename_template("alpha", "   ")["reason"] == "invalid_name"


def test_update_template_metadata_changes_only_passed_fields(library_dir: Path) -> None:
    template_library.write_template_record(
        _record("alpha", description="old", tags=["a"], plot_types=["scatter"], n_columns=2)
    )

    result = template_library.update_template_metadata(
        "alpha", description="new", tags=["X", "Y"], plot_types=["Line"]
    )
    assert result["updated"] is True
    assert set(result["changed"]) == {"description", "tags", "plot_types"}
    rec = result["template"]
    assert rec["description"] == "new"
    assert rec["tags"] == ["X", "Y"]
    assert rec["plot_types"] == ["line"]  # normalized
    assert rec["n_columns"] == 2  # untouched

    # Persisted and searchable by the new tag.
    reloaded = {item["name"]: item for item in template_library.load_index()}["alpha"]
    assert reloaded["description"] == "new"
    found = template_library.search_templates(tags=["x"])
    assert found and found[0]["name"] == "alpha"


def test_update_template_metadata_not_found_and_noop(library_dir: Path) -> None:
    assert template_library.update_template_metadata("missing")["reason"] == "not_found"
    template_library.write_template_record(_record("alpha", description="keep"))
    noop = template_library.update_template_metadata("alpha")
    assert noop["updated"] is True
    assert noop["changed"] == []
    assert noop["template"]["description"] == "keep"


def test_search_ranks_exact_plot_type_first(library_dir: Path) -> None:
    template_library.write_template_record(
        _record("scatter_nature", plot_types=["scatter"], tags=["nature"], n_columns=2)
    )
    template_library.write_template_record(_record("line_basic", plot_types=["line"], n_columns=2))

    results = template_library.search_templates(plot_type="scatter")
    assert results[0]["name"] == "scatter_nature"
    assert results[0]["score"] >= 100
    assert any("plot_type" in reason for reason in results[0]["match_reasons"])
    # The line template does not match a scatter request at all.
    assert all(item["name"] != "line_basic" for item in results)


def test_search_same_family_and_columns_and_tags(library_dir: Path) -> None:
    template_library.write_template_record(
        _record("line_symbol_fig", plot_types=["line_symbol"], tags=["paper"], n_columns=3)
    )

    results = template_library.search_templates(plot_type="scatter", n_columns=3, tags=["paper"])
    assert results[0]["name"] == "line_symbol_fig"
    reasons = " ".join(results[0]["match_reasons"])
    assert "same family" in reasons
    assert "column count matches" in reasons
    assert "tags match" in reasons


def test_search_keyword_overlap(library_dir: Path) -> None:
    template_library.write_template_record(
        _record(
            "volcano",
            description="Differential expression volcano plot",
            plot_types=["scatter"],
        )
    )
    results = template_library.search_templates(query="volcano expression")
    assert results[0]["name"] == "volcano"
    assert any("keywords match" in reason for reason in results[0]["match_reasons"])


def test_search_without_criteria_returns_all_recent_first(library_dir: Path) -> None:
    template_library.write_template_record(_record("old", created_at="2026-01-01T00:00:00Z"))
    template_library.write_template_record(_record("new", created_at="2026-06-01T00:00:00Z"))

    results = template_library.search_templates()
    assert [item["name"] for item in results] == ["new", "old"]


def test_save_graph_template_persists_everything(
    library_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    op = FakeOp()
    op.add_graph("Graph1")
    client = OriginClient()
    client._op = op

    result = client.save_graph_template(
        name="My Scatter",
        description="nature style",
        tags=["nature", "scatter"],
        plot_types=["Scatter"],
        roles=["x", "y"],
        n_columns=2,
        graph_name="Graph1",
    )

    assert result["saved"] is True
    record = result["template"]
    assert record["slug"] == "My_Scatter"
    assert record["plot_types"] == ["scatter"]  # normalized to lower-case
    assert record["source_graph"] == "Graph1"

    assert (library_dir / "My_Scatter.otpu").is_file()
    assert (library_dir / "My_Scatter.json").is_file()
    assert (library_dir / "My_Scatter.png").is_file()
    assert record["thumbnail_path"] == str(library_dir / "My_Scatter.png")

    saved_scripts = [args[0] for name, args in op.calls if name == "lt_exec"]
    assert any("template_saveas" in script for script in saved_scripts)

    # The saved record is searchable by its plot type.
    found = template_library.search_templates(plot_type="scatter")
    assert found[0]["name"] == "My Scatter"


def test_save_graph_template_refuses_overwrite(
    library_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    op = FakeOp()
    op.add_graph("Graph1")
    client = OriginClient()
    client._op = op

    client.save_graph_template(name="dup", graph_name="Graph1")
    with pytest.raises(Exception, match="already exists"):
        client.save_graph_template(name="dup", graph_name="Graph1")

    # overwrite=True succeeds.
    again = client.save_graph_template(name="dup", graph_name="Graph1", overwrite=True)
    assert again["saved"] is True
