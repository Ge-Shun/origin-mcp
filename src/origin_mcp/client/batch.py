from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..errors import OriginOperationError
from .base import _OriginClientBase

_IMPORT_METHOD_RE = re.compile(r"(?:imp[A-Za-z0-9_]+|ImportWizard|Script)\Z", re.IGNORECASE)


class _BatchMixin(_OriginClientBase):
    """Analysis-template, batchprocess, and clone-import workflows."""

    def save_analysis_template(
        self,
        path: Path,
        book_name: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        target = self._normalize_user_path(path)
        if target.suffix.lower() not in {".ogw", ".ogwu"}:
            target = target.with_suffix(".ogwu")
        if target.exists() and not overwrite:
            raise OriginOperationError(
                f"Analysis template already exists: {target}", error_code="file_exists"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        if book_name:
            wks = self._find_sheet(book_name=book_name)
            book = wks.get_book()
            activate = getattr(book, "activate", None)
            if callable(activate):
                activate()
            else:
                wks.activate()
        script = f'save -ik "{self._escape_labtalk(str(target))}";'
        result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError("Origin rejected saving the analysis template.")
        if not target.exists():
            raise OriginOperationError(
                f"Origin did not create the analysis template: {target}",
                error_code="analysis_template_not_created",
            )
        return {"path": str(target), "saved": True, "book_name": book_name, **result}

    def open_analysis_template(self, path: Path) -> dict[str, Any]:
        source = self._normalize_user_path(path)
        self._validate_file(source)
        if source.suffix.lower() not in {".ogw", ".ogwu"}:
            raise OriginOperationError(
                "Analysis templates must use .ogw or .ogwu.", error_code="invalid_request"
            )
        result = self.run_labtalk(f'doc -a "{self._escape_labtalk(str(source))}";')
        if result.get("result") is False:
            raise OriginOperationError("Origin could not open the analysis template.")
        worksheet: dict[str, Any] | None = None
        try:
            worksheet = self._worksheet_ref(self._find_sheet()).as_dict()
        except OriginOperationError:
            pass
        return {"path": str(source), "opened": True, "worksheet": worksheet, **result}

    def batch_process(
        self,
        *,
        source_type: str = "files",
        files: list[Path | str] | None = None,
        folder: Path | str | None = None,
        extensions: str = "*.*",
        input_range: str | None = None,
        fixed_range: str | None = None,
        batch_range: str | None = None,
        worksheets: str | None = None,
        analysis_template: Path | str | None = None,
        mode: str = "template",
        data_sheet: str | None = None,
        result_sheet: str | None = None,
        output_sheet: str | None = None,
        dataset_identifier: str = "File Name",
        import_method: str = "impASC",
        theme: str | None = None,
        import_filter: str | None = None,
        import_script: str | None = None,
        remove_intermediate: bool = True,
        clear_output: bool = True,
        append_mode: str = "rows",
        before_script: str | None = None,
        loop_script: str | None = None,
        end_script: str | None = None,
    ) -> dict[str, Any]:
        source_key = source_type.strip().lower().replace("-", "_")
        source_values = {
            "files": "import",
            "folder": "folder",
            "existing_xy": "existingXY",
            "existing_xyz": "existingXYZ",
            "existing_worksheets": "existingwks",
            "existing_ranges": "existingRange",
        }
        if source_key not in source_values:
            raise OriginOperationError(
                "source_type must be files, folder, existing_xy, existing_xyz, "
                "existing_worksheets, or existing_ranges.",
                error_code="invalid_request",
            )
        mode_key = mode.strip().lower()
        if mode_key not in {"template", "active"}:
            raise OriginOperationError(
                "mode must be 'template' or 'active'.", error_code="invalid_request"
            )
        if not _IMPORT_METHOD_RE.fullmatch(import_method.strip()):
            raise OriginOperationError(
                "import_method must be ImportWizard, Script, or an imp* X-Function name.",
                error_code="invalid_request",
            )
        append_key = append_mode.strip().lower()
        if append_key not in {"rows", "columns", "cols"}:
            raise OriginOperationError(
                "append_mode must be rows or columns.", error_code="invalid_request"
            )

        args = [f"batch:={mode_key}", f"data:={source_values[source_key]}"]
        normalized_files: list[str] = []
        normalized_folder: str | None = None
        if source_key == "files":
            if not files:
                raise OriginOperationError(
                    "source_type='files' requires files.", error_code="invalid_request"
                )
            normalized_files = self._normalize_batch_files(files)
            args.append("fname:=fname$")
        elif source_key == "folder":
            if folder is None:
                raise OriginOperationError(
                    "source_type='folder' requires folder.", error_code="invalid_request"
                )
            folder_path = self._normalize_user_path(folder)
            if not folder_path.is_dir():
                raise OriginOperationError(f"Batch folder does not exist: {folder_path}")
            normalized_folder = str(folder_path)
            args.extend(
                [
                    self._quoted_xf_arg("path", normalized_folder),
                    self._quoted_xf_arg("ext", extensions),
                ]
            )
        elif source_key in {"existing_xy", "existing_xyz"}:
            if not input_range:
                raise OriginOperationError(
                    f"source_type={source_key!r} requires input_range.",
                    error_code="invalid_request",
                )
            args.append(
                f"{'iy' if source_key == 'existing_xy' else 'iz'}:="
                f"{self._batch_range_arg(input_range)}"
            )
        elif source_key == "existing_worksheets":
            if not worksheets:
                raise OriginOperationError(
                    "source_type='existing_worksheets' requires worksheets.",
                    error_code="invalid_request",
                )
            args.append(f"iw:={self._batch_range_arg(worksheets)}")
        else:
            if not batch_range:
                raise OriginOperationError(
                    "source_type='existing_ranges' requires batch_range.",
                    error_code="invalid_request",
                )
            args.append(f"irngb:={self._batch_range_arg(batch_range)}")
            if fixed_range:
                args.append(f"irngf:={self._batch_range_arg(fixed_range)}")

        template_path: str | None = None
        if mode_key == "template":
            if analysis_template is None:
                raise OriginOperationError(
                    "mode='template' requires analysis_template.",
                    error_code="invalid_request",
                )
            template = self._normalize_user_path(analysis_template)
            self._validate_file(template)
            if template.suffix.lower() not in {".ogw", ".ogwu"}:
                raise OriginOperationError(
                    "Analysis templates must use .ogw or .ogwu.",
                    error_code="invalid_request",
                )
            template_path = str(template)
            args.append(self._quoted_xf_arg("name", template_path))

        if source_key in {"files", "folder"}:
            args.append(self._quoted_xf_arg("method", import_method.strip()))
            if theme:
                args.append(self._quoted_xf_arg("theme", theme))
            if import_filter:
                args.append(self._quoted_xf_arg("filter", import_filter))
            if import_script:
                args.append(self._quoted_xf_arg("script", import_script))
        for key, value in (
            ("fill", data_sheet),
            ("append", result_sheet),
            ("ow", output_sheet),
            ("id", dataset_identifier),
        ):
            if value:
                args.append(self._quoted_xf_arg(key, value))
        args.extend(
            [
                f"remove:={int(remove_intermediate)}",
                f"clear:={int(clear_output)}",
                f"mode:={0 if append_key == 'rows' else 1}",
            ]
        )
        for key, value in (
            ("beforescript", before_script),
            ("loopscript", loop_script),
            ("endscript", end_script),
        ):
            if value:
                args.append(self._quoted_xf_arg(key, value))
        script = "batchprocess " + " ".join(args) + ";"
        if normalized_files:
            result = self._run_with_file_list(normalized_files, script)
        else:
            result = self.run_labtalk(script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected batch processing.", error_code="batch_processing_failed"
            )
        return {
            "source_type": source_key,
            "files": normalized_files,
            "folder": normalized_folder,
            "analysis_template": template_path,
            "mode": mode_key,
            "script": script,
            **result,
        }

    def clone_import(
        self,
        files: list[Path | str],
        book_name: str | None = None,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_files = self._normalize_batch_files(files)
        wks = self._find_sheet(book_name=book_name, sheet_name=sheet_name)
        lt_range = getattr(wks, "lt_range", None)
        if not callable(lt_range):
            raise OriginOperationError("Worksheet does not expose lt_range().")
        source_range = str(lt_range()).rstrip("!") + "!"
        script = f"cloneimport orng:={source_range};"
        result = self._run_with_file_list(normalized_files, script)
        if result.get("result") is False:
            raise OriginOperationError(
                "Origin rejected clone import.", error_code="clone_import_failed"
            )
        return {
            "source_range": source_range,
            "files": normalized_files,
            "script": script,
            **result,
        }

    def _normalize_batch_files(self, files: list[Path | str]) -> list[str]:
        if not files:
            raise OriginOperationError(
                "No batch files were provided.", error_code="invalid_request"
            )
        normalized: list[str] = []
        for file in files:
            path = self._normalize_user_path(file)
            self._validate_file(path)
            normalized.append(str(path))
        return normalized

    def _run_with_file_list(self, files: list[str], script: str) -> dict[str, Any]:
        """Set Origin's documented newline-delimited ``fname$`` then run a command."""

        setter = getattr(self.op, "set_lt_str", None)
        if not callable(setter):
            raise OriginOperationError(
                "originpro.set_lt_str is required for multi-file batch operations.",
                error_code="unsupported_origin_feature",
            )
        getter = getattr(self.op, "get_lt_str", None)
        previous = str(getter("fname") or "") if callable(getter) else ""
        file_list = "\r\n".join(files)
        if setter("fname", file_list) is False:
            raise OriginOperationError(
                "Origin could not initialize the batch file list.",
                error_code="batch_file_list_failed",
            )
        try:
            return self.run_labtalk(script)
        finally:
            setter("fname", previous)

    def _quoted_xf_arg(self, name: str, value: str) -> str:
        return f'{name}:="{self._escape_labtalk(value)}"'

    @staticmethod
    def _batch_range_arg(value: str) -> str:
        clean = value.strip()
        if not clean or any(char in clean for char in (";", '"', "\n", "\r", "{", "}")):
            raise OriginOperationError(
                "Origin range arguments cannot be empty or contain script delimiters.",
                error_code="invalid_request",
            )
        return clean
