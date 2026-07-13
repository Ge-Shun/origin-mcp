from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase

NOTE_SYNTAXES = {
    "text": 0,
    "plain": 0,
    "normal": 0,
    "html": 1,
    "markdown": 2,
    "md": 2,
    "origin_rich_text": 3,
    "rich_text": 3,
    "rich": 3,
}
NOTE_VIEWS = {"text": 0, "source": 0, "render": 1, "rendered": 1}
PROJECT_PAGE_TYPES = {
    "workbook": "W",
    "worksheet": "W",
    "graph": "G",
    "matrix": "M",
    "layout": "L",
    "notes": "N",
    "note": "N",
    "image": "I",
}


class _ProjectOrganizationMixin(_OriginClientBase):
    """Origin Notes windows and Project Explorer folder operations."""

    def create_note(
        self,
        name: str,
        text: str = "",
        syntax: str | int = "text",
        view: str | int = "text",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        clean_name = self._validate_project_name(name, label="note name")
        existing = self._find_note(clean_name, required=False)
        if existing is not None and not overwrite:
            raise OriginOperationError(
                f"Notes window already exists: {clean_name}",
                error_code="object_already_exists",
            )
        note = existing
        if note is None:
            creator = getattr(self.op, "new_notes", None)
            if not callable(creator):
                raise OriginOperationError(
                    "originpro.new_notes is not available.",
                    error_code="unsupported_origin_feature",
                )
            note = creator(clean_name)
        if note is None:
            raise OriginOperationError(f"Origin could not create Notes window: {clean_name}")
        note.text = text
        note.syntax = self._note_syntax_value(syntax)
        note.view = self._note_view_value(view)
        return self._note_info(note, include_text=True)

    def note_info(self, name: str | None = None, include_text: bool = True) -> dict[str, Any]:
        note = self._find_note(name, required=True)
        return self._note_info(note, include_text=include_text)

    def write_note(
        self,
        text: str,
        name: str | None = None,
        append: bool = False,
        newline: bool = True,
        syntax: str | int | None = None,
        view: str | int | None = None,
        create_if_missing: bool = False,
    ) -> dict[str, Any]:
        note = self._find_note(name, required=not create_if_missing)
        if note is None:
            if not name:
                raise OriginOperationError(
                    "name is required when create_if_missing is true.",
                    error_code="invalid_request",
                )
            return self.create_note(
                name=name,
                text=text,
                syntax=syntax if syntax is not None else "text",
                view=view if view is not None else "text",
            )
        if append:
            append_text = getattr(note, "append", None)
            if callable(append_text):
                append_text(text, newline=newline)
            else:
                note.text = f"{note.text}{text}{self._newline_if_requested(newline)}"
        else:
            note.text = text
        if syntax is not None:
            note.syntax = self._note_syntax_value(syntax)
        if view is not None:
            note.view = self._note_view_value(view)
        return self._note_info(note, include_text=True)

    def load_note(
        self,
        path: Path,
        name: str | None = None,
        ask_replace: bool = False,
        create_if_missing: bool = False,
    ) -> dict[str, Any]:
        source = self._normalize_user_path(path)
        self._validate_file(source)
        note = self._find_note(name, required=not create_if_missing)
        if note is None:
            if not name:
                raise OriginOperationError(
                    "name is required when create_if_missing is true.",
                    error_code="invalid_request",
                )
            self.create_note(name)
            note = self._find_note(name, required=True)
        loader = getattr(note, "load", None)
        if not callable(loader):
            raise OriginOperationError("This Notes wrapper does not support load().")
        error_code = loader(str(source), askreplace=ask_replace)
        if error_code is not None and error_code != 0:
            raise OriginOperationError(
                f"Origin failed to load the Notes file (error {error_code}): {source}",
                error_code="note_load_failed",
            )
        return {
            **self._note_info(note, include_text=True),
            "source": str(source),
            "load_error_code": error_code,
        }

    def export_note_html(self, path: Path, name: str | None = None) -> dict[str, Any]:
        target = self._normalize_user_path(path)
        if target.suffix.lower() not in {".html", ".htm"}:
            raise OriginOperationError(
                "Notes HTML export path must end in .html or .htm.",
                error_code="invalid_request",
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        note = self._find_note(name, required=True)
        exporter = getattr(note, "exp_html", None)
        if not callable(exporter):
            raise OriginOperationError("This Notes wrapper does not support exp_html().")
        error_code = exporter(str(target))
        if error_code is not None and error_code != 0:
            raise OriginOperationError(
                f"Origin failed to export Notes HTML (error {error_code}): {target}",
                error_code="note_export_failed",
            )
        return {
            "name": self._object_name(note, default=name or ""),
            "path": str(target),
            "exported": True,
            "export_error_code": error_code,
        }

    def delete_note(self, name: str, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            raise OriginOperationError(
                "Deleting a Notes window requires confirm=true.",
                error_code="confirmation_required",
            )
        note = self._find_note(name, required=True)
        actual_name = self._object_name(note, default=name)
        destroy = getattr(note, "destroy", None)
        if not callable(destroy):
            raise OriginOperationError("This Notes wrapper does not support destroy().")
        destroy()
        return {"name": actual_name, "deleted": True}

    def list_project_folder(
        self,
        path: str | None = None,
        page_type: str | None = None,
        recursive: bool = False,
    ) -> dict[str, Any]:
        pe = self._project_explorer()
        original = str(pe.search())
        target = original
        try:
            if path is not None:
                target = str(pe.cd(self._validate_project_path(path)))
            page_code = self._project_page_type(page_type)
            variable = "__origin_mcp_pe_dir"
            folder_only = page_type is not None and page_type.strip().lower() in {
                "folder",
                "folders",
            }
            args = [] if page_code in {None, ""} else ['name:="*"']
            if page_code:
                args.append(f"page:={page_code}")
            args.extend(
                [
                    f"recursive:={int(recursive)}",
                    "display:=2",
                    f"oname:={variable}",
                ]
            )
            script_parts = [f"string {variable}$;"]
            if path is not None:
                script_parts.append(f'pe_cd path:="{self._escape_labtalk(target)}";')
            script_parts.append(f"pe_dir {' '.join(args)};")
            if path is not None and original:
                script_parts.append(f'pe_cd path:="{self._escape_labtalk(original)}";')
            self.run_labtalk(" ".join(script_parts))
            getter = getattr(self.op, "get_lt_str", None)
            if not callable(getter):
                raise OriginOperationError(
                    "originpro.get_lt_str is required to read pe_dir output.",
                    error_code="unsupported_origin_feature",
                )
            raw = str(getter(variable) or "")
            entries = self._split_project_entries(raw)
            if folder_only and any(entry.lower().startswith("<folder>") for entry in entries):
                entries = [entry for entry in entries if entry.lower().startswith("<folder>")]
            return {
                "path": target,
                "page_type": page_type or "all",
                "recursive": recursive,
                "entries": entries,
                "count": len(entries),
                "raw": raw,
            }
        finally:
            if path is not None and original:
                pe.cd(original)

    def set_project_folder(self, path: str) -> dict[str, Any]:
        pe = self._project_explorer()
        requested = self._validate_project_path(path)
        current = str(pe.cd(requested))
        result = self.run_labtalk(f'pe_cd path:="{self._escape_labtalk(current)}";')
        if result.get("result") is False:
            raise OriginOperationError(
                f"Origin could not activate project folder: {requested}",
                error_code="project_folder_activate_failed",
            )
        return {"path": current, "requested_path": requested, "activated": True}

    def create_project_folder(
        self,
        name: str,
        parent: str | None = None,
        activate: bool = False,
        reuse_existing: bool = True,
    ) -> dict[str, Any]:
        pe = self._project_explorer()
        clean_name = self._validate_project_name(name, label="folder name")
        original = str(pe.search())
        if parent is not None:
            pe.cd(self._validate_project_path(parent))
        try:
            created_path = str(pe.mkdir(clean_name, chk=reuse_existing))
            if activate:
                current = str(pe.cd(created_path))
            else:
                current = original if parent is not None else str(pe.search())
            return {
                "name": clean_name,
                "path": created_path,
                "active_path": current,
                "activated": activate,
                "reuse_existing": reuse_existing,
            }
        finally:
            if parent is not None and not activate and original:
                pe.cd(original)

    def move_project_item(
        self,
        name: str,
        destination: str,
        source_folder: str | None = None,
    ) -> dict[str, Any]:
        pe = self._project_explorer()
        clean_name = self._validate_project_name(name, label="page or folder name")
        clean_destination = self._validate_project_path(destination)
        original = str(pe.search())
        if source_folder is not None:
            pe.cd(self._validate_project_path(source_folder))
        try:
            pe.move(clean_name, clean_destination)
        finally:
            if source_folder is not None and original:
                pe.cd(original)
        return {"name": clean_name, "destination": clean_destination, "moved": True}

    def rename_project_item(
        self,
        old_name: str,
        new_name: str,
        folder: str | None = None,
    ) -> dict[str, Any]:
        pe = self._project_explorer()
        old_clean = self._validate_project_name(old_name, label="existing item name")
        new_clean = self._validate_project_name(new_name, label="new item name")
        original = str(pe.search())
        if folder is not None:
            target = str(pe.cd(self._validate_project_path(folder)))
        else:
            target = original
        try:
            new_name_variable = "__origin_mcp_pe_new_name"
            script_parts = [f'string {new_name_variable}$="{self._escape_labtalk(new_clean)}";']
            if target:
                script_parts.append(f'pe_cd path:="{self._escape_labtalk(target)}";')
            script_parts.append(f'pe_rename old:="{old_clean}" newname:={new_name_variable}$;')
            if folder is not None and original:
                script_parts.append(f'pe_cd path:="{self._escape_labtalk(original)}";')
            result = self.run_labtalk(" ".join(script_parts))
            if result.get("result") is False:
                raise OriginOperationError(
                    f"Origin could not rename project item {old_clean!r}.",
                    error_code="project_rename_failed",
                )
        finally:
            if folder is not None and original:
                pe.cd(original)
        return {"old_name": old_clean, "new_name": new_clean, "renamed": True, **result}

    def delete_project_folder(
        self,
        path: str,
        recursive: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        clean_path = self._validate_project_path(path)
        root_path = self._project_root_path()
        if (
            clean_path.rstrip("/") in {"", "."}
            or clean_path == "/"
            or clean_path.rstrip("/").lower() == root_path.rstrip("/").lower()
        ):
            raise OriginOperationError(
                "The Project Explorer root folder cannot be deleted.",
                error_code="invalid_request",
            )
        if not confirm:
            raise OriginOperationError(
                "Deleting a project folder requires confirm=true.",
                error_code="confirmation_required",
            )
        if not recursive:
            contents = self.list_project_folder(path=clean_path, recursive=False)
            if contents["entries"]:
                raise OriginOperationError(
                    "Project folder is not empty; pass recursive=true to delete its contents.",
                    error_code="folder_not_empty",
                )
        result = self.run_labtalk(f'pe_rmdir folder:="{clean_path}" folpromt:=0 pgpromt:=0;')
        if result.get("result") is False:
            raise OriginOperationError(
                f"Origin could not delete project folder: {clean_path}",
                error_code="project_folder_delete_failed",
            )
        return {"path": clean_path, "recursive": recursive, "deleted": True, **result}

    def _find_note(self, name: str | None, required: bool) -> Any:
        finder = getattr(self.op, "find_notes", None)
        if not callable(finder):
            raise OriginOperationError(
                "originpro.find_notes is not available.",
                error_code="unsupported_origin_feature",
            )
        clean_name = self._validate_project_name(name, label="note name") if name else ""
        note = finder(clean_name)
        if note is None and required:
            label = clean_name or "active Notes window"
            raise OriginOperationError(f"Notes window not found: {label}", error_code="not_found")
        return note

    def _note_info(self, note: Any, include_text: bool) -> dict[str, Any]:
        text = str(getattr(note, "text", "") or "")
        syntax = int(getattr(note, "syntax", 0))
        view = int(getattr(note, "view", 0))
        info: dict[str, Any] = {
            "name": self._object_name(note, default=""),
            "long_name": self._object_long_name(note),
            "syntax": syntax,
            "syntax_name": self._note_syntax_name(syntax),
            "view": view,
            "view_name": "render" if view == 1 else "text",
            "text_length": len(text),
        }
        if include_text:
            info["text"] = text
        return info

    def _project_explorer(self) -> Any:
        pe = getattr(self.op, "pe", None)
        if pe is None or not all(callable(getattr(pe, name, None)) for name in ("search", "cd")):
            raise OriginOperationError(
                "originpro.pe project-folder APIs are not available.",
                error_code="unsupported_origin_feature",
            )
        return pe

    def _project_root_path(self) -> str:
        pe = self._project_explorer()
        root_getter = getattr(pe, "root_folder", None)
        if not callable(root_getter):
            root_getter = getattr(self.op, "root_folder", None)
        if not callable(root_getter):
            return "/"
        root = root_getter()
        value = getattr(root, "path", "/")
        if callable(value):
            value = value()
        return str(value or "/")

    @staticmethod
    def _note_syntax_value(value: str | int) -> int:
        if isinstance(value, bool):
            raise OriginOperationError("Notes syntax must be 0, 1, 2, 3, or a syntax name.")
        if isinstance(value, int):
            if value in {0, 1, 2, 3}:
                return value
            raise OriginOperationError("Notes syntax integer must be between 0 and 3.")
        key = value.strip().lower().replace("-", "_").replace(" ", "_")
        try:
            return NOTE_SYNTAXES[key]
        except KeyError as exc:
            raise OriginOperationError(
                f"Unsupported Notes syntax: {value!r}. Supported: {sorted(NOTE_SYNTAXES)}.",
                error_code="invalid_request",
            ) from exc

    @staticmethod
    def _note_view_value(value: str | int) -> int:
        if isinstance(value, bool):
            raise OriginOperationError("Notes view must be 0, 1, text, or render.")
        if isinstance(value, int):
            if value in {0, 1}:
                return value
            raise OriginOperationError("Notes view integer must be 0 or 1.")
        key = value.strip().lower()
        try:
            return NOTE_VIEWS[key]
        except KeyError as exc:
            raise OriginOperationError(
                f"Unsupported Notes view: {value!r}. Supported: {sorted(NOTE_VIEWS)}.",
                error_code="invalid_request",
            ) from exc

    @staticmethod
    def _note_syntax_name(value: int) -> str:
        return {0: "text", 1: "html", 2: "markdown", 3: "origin_rich_text"}.get(value, "unknown")

    @staticmethod
    def _project_page_type(value: str | None) -> str | None:
        if value is None or value.strip().lower() in {"", "all"}:
            return None
        key = value.strip().lower()
        if key in {"folder", "folders"}:
            return ""
        try:
            return PROJECT_PAGE_TYPES[key]
        except KeyError as exc:
            raise OriginOperationError(
                f"Unsupported project page type: {value!r}. "
                f"Supported: all, folder, {', '.join(sorted(PROJECT_PAGE_TYPES))}.",
                error_code="invalid_request",
            ) from exc

    @staticmethod
    def _validate_project_name(value: str, label: str) -> str:
        clean = str(value).strip()
        if not clean:
            raise OriginOperationError(f"{label} cannot be empty.", error_code="invalid_request")
        if any(char in clean for char in ('"', "'", ";", "\r", "\n", "/", "\\")):
            raise OriginOperationError(
                f"{label} contains unsupported path or script characters.",
                error_code="invalid_request",
            )
        return clean

    @staticmethod
    def _validate_project_path(value: str) -> str:
        clean = str(value).strip()
        if not clean:
            raise OriginOperationError("Project folder path cannot be empty.")
        if any(char in clean for char in ('"', "'", ";", "\r", "\n")):
            raise OriginOperationError(
                "Project folder path contains unsupported script characters.",
                error_code="invalid_request",
            )
        return clean

    @staticmethod
    def _split_project_entries(raw: str) -> list[str]:
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
        return [item.strip() for item in normalized.split("\n") if item.strip()]

    @staticmethod
    def _newline_if_requested(enabled: bool) -> str:
        return "\n" if enabled else ""
