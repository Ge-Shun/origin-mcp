from __future__ import annotations

import importlib.util
import os
import site
import sys
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47631
DEFAULT_MAX_TASKS = 200
STATUS_PATH = Path(
    os.environ.get("ORIGIN_MCP_BRIDGE_STATUS", r"D:\origin-mcp\origin-bridge.status.txt")
)
RUNTIME_PACKAGES = {
    "originpro": "originpro>=1.1",
    "pandas": "pandas>=2.0",
    "openpyxl": "openpyxl>=3.1",
    "xlrd": "xlrd>=2.0",
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {value!r}.") from exc


def _emit(message: str) -> None:
    text = f"[origin-mcp-bridge] {message}"
    try:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(text + "\n", encoding="utf-8")
    except Exception:
        pass


def _notify(message: str) -> None:
    _emit(message)
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "origin-mcp bridge",
            0x00000040,
        )
    except Exception:
        pass


class _StdioCompat:
    def __init__(self, stream: Any) -> None:
        self._stream = stream

    def write(self, value: str) -> Any:
        return self._stream.write(value)

    def flush(self) -> Any:
        flush = getattr(self._stream, "flush", None)
        if callable(flush):
            return flush()
        return None

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return -1

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


def _default_src_dir() -> Path:
    try:
        return Path(__file__).resolve().parents[1] / "src"
    except NameError:
        return Path(os.environ.get("ORIGIN_MCP_SRC", r"D:\origin-mcp\src"))


def _ensure_origin_mcp_on_path(src_dir: str | os.PathLike[str] | None = None) -> Path:
    src = Path(src_dir or os.environ.get("ORIGIN_MCP_SRC") or _default_src_dir()).resolve()
    if not (src / "origin_mcp").is_dir():
        raise RuntimeError(
            f"origin_mcp package was not found under {src}. "
            "Set ORIGIN_MCP_SRC to the checkout src directory."
        )
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return src


def _ensure_user_site_on_path() -> None:
    try:
        user_site = site.getusersitepackages()
    except Exception:
        return
    if user_site and user_site not in sys.path:
        site.addsitedir(user_site)


def _missing_runtime_packages() -> list[str]:
    _ensure_user_site_on_path()
    importlib.invalidate_caches()
    return [
        requirement
        for module_name, requirement in RUNTIME_PACKAGES.items()
        if importlib.util.find_spec(module_name) is None
    ]


def _pip(args: list[str]) -> int:
    try:
        from pip._internal.cli.main import main as pip_main
    except ModuleNotFoundError:
        import ensurepip

        ensurepip.bootstrap(upgrade=True)
        from pip._internal.cli.main import main as pip_main

    original_stdin = sys.stdin
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdin = _StdioCompat(original_stdin)
    sys.stdout = _StdioCompat(original_stdout)
    sys.stderr = _StdioCompat(original_stderr)
    try:
        return int(
            pip_main(
                [
                    "--disable-pip-version-check",
                    "--no-color",
                    *args,
                ]
            )
            or 0
        )
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
        sys.stderr = original_stderr


def _install_missing_runtime_packages() -> None:
    missing = _missing_runtime_packages()
    if not missing:
        return

    _emit(
        "installing runtime dependencies into Origin Python: "
        + ", ".join(missing)
    )
    status = _pip(["install", "--progress-bar", "off", *missing])
    if status:
        raise RuntimeError(
            "Failed to install origin-mcp runtime dependencies into Origin Python. "
            f"pip exited with status {status}."
        )
    _ensure_user_site_on_path()
    importlib.invalidate_caches()


def _clear_failed_imports() -> None:
    for module_name in (
        "origin_mcp.bridge",
        "origin_mcp.origin_client",
        "originpro",
        "pandas",
        "openpyxl",
        "xlrd",
    ):
        sys.modules.pop(module_name, None)


def _pump_windows_messages() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return

    user32 = ctypes.windll.user32
    msg = wintypes.MSG()
    pm_remove = 0x0001
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, pm_remove):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def _serve_foreground_cooperative(server: Any) -> None:
    server.timeout = 0.05
    while True:
        server.handle_request()
        _pump_windows_messages()
        time.sleep(0.001)


def _load_bridge_server(install_missing: bool) -> Any:
    _ensure_user_site_on_path()
    try:
        from origin_mcp.bridge import OriginEmbeddedBridgeServer
    except ImportError as exc:
        if "OriginEmbeddedBridgeServer" not in str(exc):
            raise
        _clear_failed_imports()
        importlib.invalidate_caches()
        from origin_mcp.bridge import OriginEmbeddedBridgeServer

        return OriginEmbeddedBridgeServer
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        if install_missing and missing in RUNTIME_PACKAGES:
            _install_missing_runtime_packages()
            _clear_failed_imports()
            from origin_mcp.bridge import OriginEmbeddedBridgeServer

            return OriginEmbeddedBridgeServer
        raise RuntimeError(
            f"Origin's embedded Python is missing dependency '{missing}'. "
            "Install origin-mcp runtime dependencies into Origin's embedded Python, "
            "or run this addon with install_missing=True."
        ) from exc
    return OriginEmbeddedBridgeServer


def start_origin_mcp_bridge(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token: str | None = None,
    max_tasks: int = DEFAULT_MAX_TASKS,
    src_dir: str | os.PathLike[str] | None = None,
    install_missing: bool = True,
    background: bool = False,
) -> dict[str, Any]:
    """Start origin-mcp bridge inside the running Origin Python process."""

    existing = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    if existing is not None and (
        thread is None or getattr(thread, "is_alive", lambda: False)()
    ):
        actual_host, actual_port = existing.server_address
        _notify(f"Bridge is already running on {actual_host}:{actual_port}.")
        return {"running": True, "host": actual_host, "port": actual_port, "already_running": True}

    _emit("starting inside Origin Python")
    src = _ensure_origin_mcp_on_path(src_dir)
    if install_missing:
        _install_missing_runtime_packages()
    OriginBridgeServer = _load_bridge_server(install_missing=install_missing)

    server = OriginBridgeServer((host, port), token=token, max_tasks=max_tasks)
    globals()["_origin_mcp_bridge_server"] = server

    actual_host, actual_port = server.server_address
    result = {
        "running": True,
        "host": actual_host,
        "port": actual_port,
        "src": str(src),
        "max_tasks": max_tasks,
        "background": background,
    }
    _notify(f"Bridge is running inside Origin on {actual_host}:{actual_port}.")
    if background:
        thread = threading.Thread(
            target=server.serve_forever,
            name="origin-mcp-bridge",
            daemon=True,
        )
        thread.start()
        globals()["_origin_mcp_bridge_thread"] = thread
        return result

    globals()["_origin_mcp_bridge_thread"] = None
    _emit(
        "serving requests cooperatively; keep this Python Console running"
    )
    _serve_foreground_cooperative(server)
    return result


def stop_origin_mcp_bridge() -> dict[str, Any]:
    """Stop the Origin-embedded origin-mcp bridge started by this addon."""

    server = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    if server is None:
        return {"stopped": False, "reason": "not_running"}

    if thread is not None and thread.is_alive():
        server.shutdown()
    server.server_close()
    if thread is not None:
        thread.join(timeout=2)
    globals()["_origin_mcp_bridge_server"] = None
    globals()["_origin_mcp_bridge_thread"] = None
    _emit("stopped")
    return {"stopped": True}


def origin_mcp_bridge_status() -> dict[str, Any]:
    """Return local status for the Origin-embedded bridge thread."""

    server = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    running = bool(server is not None and (thread is None or thread.is_alive()))
    if not running:
        return {"running": False}
    actual_host, actual_port = server.server_address
    return {"running": True, "host": actual_host, "port": actual_port}


if __name__ == "__main__":
    _emit("loading addon")
    start_origin_mcp_bridge(
        host=os.environ.get("ORIGIN_MCP_BRIDGE_HOST", DEFAULT_HOST),
        port=_env_int("ORIGIN_MCP_BRIDGE_PORT", DEFAULT_PORT),
        token=os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN") or None,
        max_tasks=_env_int("ORIGIN_MCP_BRIDGE_MAX_TASKS", DEFAULT_MAX_TASKS),
        src_dir=os.environ.get("ORIGIN_MCP_SRC") or None,
        install_missing=_env_bool("ORIGIN_MCP_INSTALL_MISSING", True),
        background=_env_bool("ORIGIN_MCP_BRIDGE_BACKGROUND", False),
    )
