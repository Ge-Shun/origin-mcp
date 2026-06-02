from __future__ import annotations

import base64
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ..errors import OriginOperationError
from ..image_quality import (
    export_looks_nonempty,
    export_quality_issues,
    file_sha256,
    image_dimensions,
    image_quality,
)
from .base import _OriginClientBase

# Most-recent preview files kept in the shared temp preview directory.
DEFAULT_PREVIEW_RETENTION = 20


class _ExportMixin(_OriginClientBase):
    """Graph export and exported image inspection methods."""

    def export_all_graphs(
        self,
        output_dir: Path,
        file_type: str = "png",
        overwrite: bool = True,
        width: int = 0,
    ) -> dict[str, Any]:
        output_dir = self._normalize_user_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.ensure_feature("graph_list", "Batch graph export")
        op = self.op
        graph_list = getattr(op, "graph_list", None)
        if not callable(graph_list):
            raise OriginOperationError("originpro.graph_list is not available.")
        exported = []
        for graph in graph_list("p", True):
            graph_name = self._object_name(graph, default="Graph")
            path = output_dir / f"{self._safe_filename(graph_name)}.{file_type.lstrip('.')}"
            if path.exists() and not overwrite:
                continue
            if hasattr(graph, "save_fig"):
                graph.save_fig(str(path), type=file_type, replace=overwrite, width=width)
            else:
                self.export_graph(path, graph=graph, overwrite=overwrite)
            exported.append(str(path))
        return {"count": len(exported), "paths": exported}

    def export_graph(
        self,
        path: Path,
        graph_name: str | None = None,
        graph: Any | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OriginOperationError(f"Export path already exists: {path}")

        if graph_name:
            self._suppress_graph_title_text(graph_name=graph_name, title=None)
            self.run_labtalk(self._export_graph_labtalk(path, graph_name))
        else:
            target = graph if graph is not None else self._find_or_active_graph(graph_name)
            self._suppress_graph_title_text(graph=target, graph_name=None, title=None)
            if not hasattr(target, "save_fig"):
                self.run_labtalk(self._export_graph_labtalk(path, None))
                return {"path": str(path)}
            target.save_fig(str(path))

        return {"path": str(path)}

    def _export_graph_labtalk(self, path: Path, graph_name: str | None) -> str:
        export_type = path.suffix.lower().lstrip(".") or "png"
        if export_type == "jpeg":
            export_type = "jpg"
        filename = path.stem
        safe_path = self._escape_labtalk(str(path.parent))
        safe_filename = self._escape_labtalk(filename)
        parts = []
        if graph_name:
            safe_graph_name = self._escape_labtalk(graph_name)
            parts.append(f'win -a "{safe_graph_name}";')
            parts.append(f'expGraph pages:="{safe_graph_name}"')
        else:
            parts.append("expGraph")
        parts.append(
            f'type:={export_type} path:="{safe_path}" '
            f'filename:="{safe_filename}" overwrite:=replace;'
        )
        return " ".join(parts)

    def export_preview(
        self,
        graph_name: str | None = None,
        output_dir: Path | None = None,
        file_type: str = "png",
        overwrite: bool = True,
    ) -> dict[str, Any]:
        suffix = file_type.lower().lstrip(".") or "png"
        # Track whether we are using the shared temp preview directory: only the
        # default directory is pruned, never a directory the caller chose.
        use_default_dir = output_dir is None
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "origin-mcp-previews"
        output_dir = self._normalize_user_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(graph_name or "active_graph")
        path = output_dir / f"{safe_name}_{uuid.uuid4().hex[:8]}.{suffix}"
        exported = self.export_graph(path, graph_name=graph_name, overwrite=overwrite)
        if use_default_dir:
            # export_preview returns a file path callers may still read, so keep
            # the most recent previews and only prune older ones to bound the
            # temp directory over a long session.
            self._prune_preview_dir(output_dir, keep=DEFAULT_PREVIEW_RETENTION)
        return {
            **exported,
            "preview": self.inspect_export(Path(exported["path"])),
        }

    @staticmethod
    def _prune_preview_dir(directory: Path, keep: int = DEFAULT_PREVIEW_RETENTION) -> None:
        """Delete all but the ``keep`` most recently modified files in a directory."""

        try:
            entries = [entry for entry in directory.iterdir() if entry.is_file()]
        except OSError:
            return
        if len(entries) <= keep:
            return
        entries.sort(key=lambda entry: entry.stat().st_mtime, reverse=True)
        for stale in entries[keep:]:
            try:
                stale.unlink()
            except OSError:
                pass

    def render_graph_png(
        self,
        graph_name: str | None = None,
        max_width: int = 1600,
    ) -> dict[str, Any]:
        """Render a graph to an in-memory PNG and return it base64-encoded.

        Unlike :meth:`export_graph` this leaves no file behind: the graph is
        written to a temporary path, read into memory, and the temp file is
        deleted before returning. ``max_width`` bounds the pixel width Origin
        renders at so the returned image stays small enough to hand back as an
        MCP image content block. The graph is rendered as-is (its title is not
        suppressed) so the preview faithfully reflects the current figure.
        """

        width = max(0, int(max_width))
        target = self._find_or_active_graph(graph_name)
        if not hasattr(target, "save_fig"):
            raise OriginOperationError(
                "This graph object does not support save_fig(); cannot render a preview image.",
                error_code="graph_render_unavailable",
            )
        tmp_dir = Path(tempfile.gettempdir()) / "origin-mcp-view"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"view_{uuid.uuid4().hex[:8]}.png"
        try:
            try:
                target.save_fig(str(tmp_path), type="png", replace=True, width=width)
            except TypeError:
                # Older originpro save_fig signatures may not accept these
                # keywords; fall back to the minimal call (loses width bounding).
                target.save_fig(str(tmp_path))
            if not tmp_path.exists():
                raise OriginOperationError(
                    "Origin did not produce a preview image for the graph.",
                    error_code="graph_render_failed",
                )
            dimensions = image_dimensions(tmp_path) or {}
            data = tmp_path.read_bytes()
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return {
            "graph_name": self._object_name(target, default=graph_name or "active_graph"),
            "format": "png",
            "size_bytes": len(data),
            "image_base64": base64.b64encode(data).decode("ascii"),
            **dimensions,
        }

    def _export_plot_command_graph(self, path: Path, graph_name: str) -> dict[str, Any]:
        try:
            return self.export_graph(path, graph_name=graph_name)
        except OriginOperationError as exc:
            if "Graph not found" not in str(exc):
                raise
            exported = self.export_graph(path)
            exported["warning"] = (
                f"Origin did not expose plot command output as {graph_name!r}; "
                "exported the active graph instead."
            )
            return exported

    def inspect_export(self, path: Path) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        if not path.exists():
            raise OriginOperationError(f"Export file does not exist: {path}")
        if not path.is_file():
            raise OriginOperationError(f"Export path is not a file: {path}")
        info: dict[str, Any] = {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "suffix": path.suffix.lower(),
            "sha256": file_sha256(path),
        }
        dimensions = image_dimensions(path)
        if dimensions:
            info.update(dimensions)
        quality = image_quality(path)
        if quality:
            info["image_quality"] = quality
        quality_issues = export_quality_issues(info)
        info["quality_issues"] = quality_issues
        info["quality_passed"] = not quality_issues
        info["looks_nonempty"] = export_looks_nonempty(info)
        return info
