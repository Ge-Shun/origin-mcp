from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


class FakeNote:
    def __init__(self, op: FakeProjectOp, name: str) -> None:
        self.op = op
        self.name = name
        self.lname = name
        self.text = ""
        self.syntax = 0
        self.view = 0

    def append(self, text: str, newline: bool = True) -> None:
        self.text += text + ("\n" if newline else "")

    def load(self, fname: str, askreplace: bool = False) -> int:
        del askreplace
        self.text = Path(fname).read_text(encoding="utf-8")
        return 0

    def exp_html(self, fname: str) -> int:
        Path(fname).write_text(f"<html>{self.text}</html>", encoding="utf-8")
        return 0

    def destroy(self) -> None:
        self.op.notes.pop(self.name, None)
        if self.op.active_note is self:
            self.op.active_note = None


class FakeProjectExplorer:
    def __init__(self, op: FakeProjectOp) -> None:
        self.op = op
        self.current = "/UNTITLED"
        self.folders: dict[str, list[str]] = {self.current: []}
        self.moves: list[tuple[str, str, str]] = []

    def search(self, name: str = "", kind: int = 0) -> str:
        del name, kind
        return self.current

    def cd(self, path: str | None = None) -> str:
        if path is None:
            return self.current
        actual = "/UNTITLED" if path == "/" else path.rstrip("/")
        if actual not in self.folders:
            raise RuntimeError(f"folder not found: {actual}")
        self.current = actual
        return self.current

    def mkdir(self, path: str, chk: bool = False) -> str:
        target = f"{self.current.rstrip('/')}/{path}"
        if target in self.folders:
            if chk:
                return target
            counter = 2
            while f"{target}{counter}" in self.folders:
                counter += 1
            target = f"{target}{counter}"
        self.folders[target] = []
        self.folders[self.current].append(path)
        return target

    def move(self, name: str, path: str) -> None:
        self.moves.append((self.current, name, path))
        if name in self.folders[self.current]:
            self.folders[self.current].remove(name)
        self.folders[path].append(name)

    def root_folder(self) -> SimpleNamespace:
        return SimpleNamespace(path="/UNTITLED")


class FakeProjectOp:
    def __init__(self) -> None:
        self.notes: dict[str, FakeNote] = {}
        self.active_note: FakeNote | None = None
        self.pe = FakeProjectExplorer(self)
        self.lt_strings: dict[str, str] = {}
        self.calls: list[str] = []

    def new_notes(self, name: str = "") -> FakeNote:
        actual = name or f"Notes{len(self.notes) + 1}"
        note = FakeNote(self, actual)
        self.notes[actual] = note
        self.active_note = note
        return note

    def find_notes(self, name: str = "") -> FakeNote | None:
        return self.notes.get(name) if name else self.active_note

    def lt_exec(self, script: str) -> bool:
        self.calls.append(script)
        if "pe_dir" in script:
            self.lt_strings["__origin_mcp_pe_dir"] = "\n".join(self.pe.folders[self.pe.current])
        rename_value = re.search(r'string __origin_mcp_pe_new_name\$="([^"]*)";', script)
        rename = re.search(
            r'pe_rename old:="([^"]+)" newname:=__origin_mcp_pe_new_name\$;',
            script,
        )
        if rename and rename_value:
            old_name = rename.group(1)
            new_name = rename_value.group(1)
            entries = self.pe.folders[self.pe.current]
            entries[entries.index(old_name)] = new_name
        remove = re.search(r'pe_rmdir folder:="([^"]+)"', script)
        if remove:
            target = remove.group(1).rstrip("/")
            self.pe.folders.pop(target, None)
            parent, _, name = target.rpartition("/")
            parent = parent or "/UNTITLED"
            if parent in self.pe.folders and name in self.pe.folders[parent]:
                self.pe.folders[parent].remove(name)
        return True

    def get_lt_str(self, name: str) -> str:
        return self.lt_strings.get(name, "")


@pytest.fixture
def project_client() -> OriginClient:
    client = OriginClient()
    client._op = FakeProjectOp()
    return client


def test_notes_create_write_load_export_and_delete(
    project_client: OriginClient,
    tmp_path: Path,
) -> None:
    created = project_client.create_note(
        "Research Log",
        text="# Start",
        syntax="markdown",
        view="render",
    )
    assert created["syntax_name"] == "markdown"
    assert created["view_name"] == "render"
    assert created["text"] == "# Start"

    appended = project_client.write_note("Result A", name="Research Log", append=True)
    assert appended["text"] == "# StartResult A\n"

    source = tmp_path / "notes.md"
    source.write_text("## Loaded", encoding="utf-8")
    loaded = project_client.load_note(source, name="Research Log")
    assert loaded["text"] == "## Loaded"

    target = tmp_path / "notes.html"
    exported = project_client.export_note_html(target, name="Research Log")
    assert exported["exported"] is True
    assert target.read_text(encoding="utf-8") == "<html>## Loaded</html>"

    with pytest.raises(OriginOperationError, match="confirm=true"):
        project_client.delete_note("Research Log")
    deleted = project_client.delete_note("Research Log", confirm=True)
    assert deleted == {"name": "Research Log", "deleted": True}


def test_notes_create_if_missing_and_validation(project_client: OriginClient) -> None:
    created = project_client.write_note(
        "hello",
        name="Auto Note",
        syntax="html",
        create_if_missing=True,
    )
    assert created["syntax_name"] == "html"

    with pytest.raises(OriginOperationError, match="already exists"):
        project_client.create_note("Auto Note")
    with pytest.raises(OriginOperationError, match="Unsupported Notes syntax"):
        project_client.write_note("x", name="Auto Note", syntax="rst")


def test_project_folder_create_list_move_rename_and_delete(
    project_client: OriginClient,
) -> None:
    op: FakeProjectOp = project_client.op
    created = project_client.create_project_folder("Results", parent="/UNTITLED")
    assert created["path"] == "/UNTITLED/Results"
    assert op.pe.current == "/UNTITLED"

    project_client.create_project_folder("Archive")
    listing = project_client.list_project_folder("/UNTITLED")
    assert listing["entries"] == ["Results", "Archive"]
    assert op.pe.current == "/UNTITLED"

    folder_listing = project_client.list_project_folder("/UNTITLED", page_type="folder")
    assert folder_listing["entries"] == ["Results", "Archive"]
    folder_script = next(script for script in reversed(op.calls) if "pe_dir" in script)
    assert 'name:="*"' not in folder_script

    project_client.move_project_item("Archive", "/UNTITLED/Results")
    assert op.pe.moves[-1] == ("/UNTITLED", "Archive", "/UNTITLED/Results")
    project_client.rename_project_item("Archive", "Old Results", folder="/UNTITLED/Results")
    assert op.pe.folders["/UNTITLED/Results"] == ["Old Results"]

    with pytest.raises(OriginOperationError, match="not empty"):
        project_client.delete_project_folder(
            "/UNTITLED/Results",
            confirm=True,
        )
    deleted = project_client.delete_project_folder(
        "/UNTITLED/Results",
        recursive=True,
        confirm=True,
    )
    assert deleted["deleted"] is True


def test_project_folder_protects_root_and_script_boundaries(
    project_client: OriginClient,
) -> None:
    with pytest.raises(OriginOperationError, match="root folder"):
        project_client.delete_project_folder("/UNTITLED", recursive=True, confirm=True)
    with pytest.raises(OriginOperationError, match="unsupported"):
        project_client.create_project_folder('bad"; exit;')
    with pytest.raises(OriginOperationError, match="confirm=true"):
        project_client.delete_project_folder("/UNTITLED/Anything", recursive=True)
