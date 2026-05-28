from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from .client.analysis import _AnalysisMixin
from .client.base import GraphRef, WorksheetRef
from .client.graph_formatting import _GraphFormattingMixin
from .client.lifecycle import _LifecycleMixin
from .client.plot import _PlotMixin
from .client.worksheet import _WorksheetMixin
from .errors import OriginOperationError
from .image_quality import (
    export_looks_nonempty,
    export_quality_issues,
    file_sha256,
    image_dimensions,
    image_quality,
)

__all__ = ["GraphRef", "OriginClient", "WorksheetRef"]


class OriginClient(
    _LifecycleMixin,
    _WorksheetMixin,
    _PlotMixin,
    _GraphFormattingMixin,
    _AnalysisMixin,
):
    """Small wrapper around the `originpro` package.

    The import is intentionally lazy so the MCP server can start and list tools even
    on machines where Origin is not installed yet.
    """
































































    def export_all_graphs(
        self,
        output_dir: Path,
        file_type: str = "png",
        overwrite: bool = True,
        width: int = 0,
    ) -> dict[str, Any]:
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
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
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
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
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "origin-mcp-previews"
        output_dir = output_dir.expanduser().resolve()
        self._check_path_allowed(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(graph_name or "active_graph")
        path = output_dir / f"{safe_name}_{uuid.uuid4().hex[:8]}.{suffix}"
        exported = self.export_graph(path, graph_name=graph_name, overwrite=overwrite)
        return {
            **exported,
            "preview": self.inspect_export(Path(exported["path"])),
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
        path = path.expanduser().resolve()
        self._check_path_allowed(path)
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






























































































