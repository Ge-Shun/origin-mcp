from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ..compat import collect_capabilities, feature_available, plot_type_coverage
from ..errors import OriginOperationError
from .base import _OriginClientBase


class _LifecycleMixin(_OriginClientBase):
    """Connection, project lifecycle, and capability methods."""

    def connect(self, show: bool = True) -> dict[str, Any]:
        show_result = self._try_set_show(show)
        version = self._safe_eval("@V")
        return {
            "connected": True,
            "visible": show,
            "origin_version": version,
            **show_result,
        }

    def capabilities(self, show: bool = False, refresh: bool = False) -> dict[str, Any]:
        if self._capabilities is not None and not refresh:
            return self._capabilities
        connection = self.connect(show=show)
        self._capabilities = {
            **connection,
            **collect_capabilities(self.op, connection.get("origin_version")),
        }
        return self._capabilities

    def plot_type_coverage(
        self,
        origin_version: float | int | None = None,
        show: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if origin_version is None:
            origin_version = self.capabilities(show=show, refresh=refresh).get("origin_version")
        return plot_type_coverage(origin_version)

    def ensure_feature(self, feature: str, operation: str) -> None:
        caps = self.capabilities(show=False)
        if feature_available(caps, feature):
            return
        info = caps.get("features", {}).get(feature, {})
        minimum = info.get("minimum_origin_version")
        note = info.get("note") or "No compatible API was detected."
        version = caps.get("origin_version")
        requirement = f" Requires Origin >= {minimum}." if minimum else ""
        raise OriginOperationError(
            f"{operation} is not supported by this Origin/originpro environment. "
            f"Detected Origin version: {version}.{requirement} {note}",
            error_code="unsupported_origin_feature",
        )

    def new_project(self, show: bool = True) -> dict[str, Any]:
        op = self.op
        self._try_set_show(show)
        self._call_first_available(op, ["new", "new_project"], operation="create a new project")
        return {"created": True}

    def open_project(
        self,
        path: Path,
        readonly: bool = False,
        asksave: bool = False,
    ) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        self._validate_file(path)
        if path.suffix.lower() not in {".opju", ".opj"}:
            raise OriginOperationError(f"Not an Origin project file: {path}")

        op = self.op
        open_project = getattr(op, "open", None)
        if not callable(open_project):
            raise OriginOperationError("originpro.open is not available.")
        ok = open_project(str(path), readonly=readonly, asksave=asksave)
        return {"path": str(path), "opened": bool(ok)}

    def save_project(self, path: Path) -> dict[str, Any]:
        path = self._normalize_user_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        op = self.op

        if hasattr(op, "save"):
            op.save(str(path))
        else:
            self.run_labtalk(f'save -i "{path}";')
        return {"path": str(path)}

    def quit(self) -> dict[str, Any]:
        op = self.op
        for name in ("exit", "quit"):
            func = getattr(op, name, None)
            if callable(func):
                func()
                self._capabilities = None
                return {"closed": True}
        self.run_labtalk("exit;")
        self._capabilities = None
        return {"closed": True}

    def detach(self) -> dict[str, Any]:
        op = self.op
        detach = getattr(op, "detach", None)
        if callable(detach):
            detach()
            self._capabilities = None
            return {"detached": True, "closed": False}

        config = importlib.import_module("originpro.config")
        po = getattr(config, "po", None)
        release = getattr(po, "Exit", None)
        if callable(release):
            release(True)
            self._capabilities = None
            return {"detached": True, "closed": False}

        raise OriginOperationError("No Origin detach/release API is available.")

    def force_quit(self) -> dict[str, Any]:
        op = self.op
        config = importlib.import_module("originpro.config")
        po = getattr(config, "po", None)
        force_exit = getattr(po, "Exit", None)
        if callable(force_exit):
            force_exit(False)
            self._capabilities = None
            return {"closed": True, "forced": True}

        exit_func = getattr(op, "exit", None)
        if callable(exit_func):
            exit_func()
            self._capabilities = None
            return {"closed": True, "forced": False}

        self.run_labtalk("exit;")
        self._capabilities = None
        return {"closed": True, "forced": False}

    def run_labtalk(self, script: str) -> dict[str, Any]:
        if not script.strip():
            raise OriginOperationError("LabTalk script is empty.")

        op = self.op
        func = getattr(op, "lt_exec", None)
        if not callable(func):
            raise OriginOperationError(
                "originpro.lt_exec is not available in this environment.",
                error_code="labtalk_unavailable",
            )

        result = func(script)
        return {"result": result}

