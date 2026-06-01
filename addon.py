from __future__ import annotations

import importlib.util
import json
import os
import platform
import site
import sys
import sysconfig
import threading
import time
import traceback
import types
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47631
DEFAULT_MAX_TASKS = 200
RUNTIME_PACKAGES = {
    "originpro": "originpro>=1.1",
    "pandas": "pandas>=2.0",
    "openpyxl": "openpyxl>=3.1",
    "xlrd": "xlrd>=2.0",
}
_STATUS_STATE: dict[str, Any] = {}


def _register_control_module_alias() -> None:
    """Expose this running addon under a stable module name for Origin UI scripts."""

    current_module = sys.modules.get(__name__)
    if current_module is None:
        current_module = types.ModuleType(__name__)
        current_module.__dict__.update(globals())
        sys.modules[__name__] = current_module
    sys.modules["origin_mcp_addon"] = current_module


def _addon_dir() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent
    return Path.cwd()


def _status_path() -> Path:
    configured = os.environ.get("ORIGIN_MCP_BRIDGE_STATUS")
    if configured:
        return Path(configured).expanduser()
    return _addon_dir() / "origin-bridge.status.txt"


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


def _emit(message: str, fields: dict[str, Any] | None = None) -> None:
    _STATUS_STATE.update(
        {
            "status_version": 1,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": message,
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
    )
    if fields:
        _STATUS_STATE.update(fields)
    try:
        path = _status_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_STATE["status_path"] = str(path)
        path.write_text(
            json.dumps(_STATUS_STATE, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def _notify(message: str, fields: dict[str, Any] | None = None) -> None:
    _emit(message, fields=fields)
    if os.name != "nt":
        return

    def _show() -> None:
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

    # Show the box on a daemon thread so a modal popup never blocks the caller.
    # In foreground mode the caller goes straight into the cooperative serve
    # loop; a blocking MessageBox here would leave the socket bound but never
    # answering until the user dismissed the dialog.
    threading.Thread(target=_show, name="origin-mcp-notify", daemon=True).start()


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


def _candidate_src_dirs(src_dir: str | os.PathLike[str] | None = None) -> list[Path]:
    candidates: list[Path] = []
    for value in (src_dir, os.environ.get("ORIGIN_MCP_SRC")):
        if value:
            candidates.append(Path(value).expanduser())

    addon_dir = _addon_dir()
    candidates.extend(
        [
            addon_dir / "src",
            addon_dir.parent / "src",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _origin_mcp_source() -> str:
    spec = importlib.util.find_spec("origin_mcp")
    if spec is None:
        return "installed"
    if spec.origin:
        return str(Path(spec.origin).resolve().parent)
    locations = spec.submodule_search_locations
    if locations:
        return str(Path(next(iter(locations))).resolve())
    return "installed"


def _ensure_origin_mcp_importable(src_dir: str | os.PathLike[str] | None = None) -> str:
    _ensure_user_site_on_path()
    importlib.invalidate_caches()

    for src in _candidate_src_dirs(src_dir):
        if (src / "origin_mcp").is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))

    importlib.invalidate_caches()
    if importlib.util.find_spec("origin_mcp.bridge") is not None:
        return _origin_mcp_source()

    raise RuntimeError(
        "origin_mcp is not importable in Origin's embedded Python. "
        "Install origin-mcp into Origin's Python environment, run addon.py from the "
        "checkout root so its adjacent src directory can be detected, or set "
        "ORIGIN_MCP_SRC to the checkout src directory."
    )


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


def _path_is_writable(path: str) -> bool:
    probe = Path(path)
    try:
        probe.mkdir(parents=True, exist_ok=True)
        test_file = probe / ".origin-mcp-write-test"
        test_file.write_text("", encoding="utf-8")
        test_file.unlink()
        return True
    except Exception:
        return False


def _user_install_flag() -> list[str]:
    """Return ``['--user']`` when the global site-packages is not writable.

    Origin is frequently installed under ``C:\\Program Files`` where the
    embedded Python's site-packages requires administrator rights. Older pip
    versions do not always fall back to a user install on their own, so detect
    an unwritable target and request ``--user`` explicitly. ``--user`` is
    rejected by pip inside a virtual environment, so skip it there.
    """

    if sys.prefix != sys.base_prefix:
        return []
    try:
        target = sysconfig.get_path("purelib")
    except Exception:
        return []
    if not target or _path_is_writable(target):
        return []
    return ["--user"]


def _install_missing_runtime_packages() -> None:
    missing = _missing_runtime_packages()
    if not missing:
        return

    _emit("installing runtime dependencies into Origin Python: " + ", ".join(missing))
    status = _pip(["install", "--progress-bar", "off", *_user_install_flag(), *missing])
    if status:
        raise RuntimeError(
            "Failed to install origin-mcp runtime dependencies into Origin Python: "
            + ", ".join(missing)
            + f". pip exited with status {status}. "
            "Install them manually in Origin's embedded Python, or check network/proxy access."
        )
    _ensure_user_site_on_path()
    importlib.invalidate_caches()


def _missing_dependency_message(missing: list[str]) -> str:
    addon_path = _addon_dir() / "addon.py"
    return (
        "Origin's embedded Python is missing origin-mcp runtime dependencies: "
        + ", ".join(missing)
        + ".\nAutomatic installation is disabled by ORIGIN_MCP_INSTALL_MISSING=0. "
        "Install them into Origin's embedded Python yourself, or re-run this addon "
        "after enabling the built-in installer in Origin's Python Console:\n"
        "import os\n"
        'os.environ["ORIGIN_MCP_INSTALL_MISSING"] = "1"\n'
        "import runpy\n"
        f'runpy.run_path(r"{addon_path}", run_name="__main__")'
    )


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


def _clear_origin_mcp_imports() -> None:
    """Drop cached origin_mcp modules before starting a fresh bridge.

    Origin's Python Console commonly stays alive while addon.py is rerun during
    development. Without clearing these modules, a restarted bridge can keep
    serving old code from sys.modules even though the checkout on disk changed.
    """

    for module_name in list(sys.modules):
        if module_name == "origin_mcp" or module_name.startswith("origin_mcp."):
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
    while not _bridge_shutdown_requested(server):
        server.handle_request()
        # Run queued async tasks on this (Origin UI) thread. The embedded task
        # manager has no worker thread precisely because originpro must stay on
        # the UI thread, so submit_task work is drained here between requests.
        pump = getattr(server, "_pump_cooperative_tasks", None)
        if callable(pump):
            pump()
        _pump_windows_messages()
        time.sleep(0.001)


def _serve_background(server: Any) -> None:
    try:
        server.serve_forever()
    finally:
        _finalize_bridge_stopped(server)


def _bridge_shutdown_requested(server: Any) -> bool:
    event = getattr(server, "shutdown_requested", None)
    return bool(event is not None and event.is_set())


def _finalize_bridge_stopped(server: Any) -> None:
    """Close the server socket, clear module globals, and record the stop."""

    try:
        server.server_close()
    except Exception:
        pass
    handshake_path = globals().get("_origin_mcp_handshake_path")
    if handshake_path is not None:
        try:
            from origin_mcp.bridge_handshake import clear_handshake

            clear_handshake(path=handshake_path)
        except Exception:
            pass
    globals()["_origin_mcp_handshake_path"] = None
    globals()["_origin_mcp_bridge_server"] = None
    globals()["_origin_mcp_bridge_thread"] = None
    _emit("stopped", fields={"running": False})


def _load_bridge_server(install_missing: bool) -> Any:
    _ensure_user_site_on_path()
    try:
        from origin_mcp.bridge import OriginEmbeddedBridgeServer

        return OriginEmbeddedBridgeServer
    except ModuleNotFoundError as exc:
        # A runtime dependency (originpro/pandas/...) pulled in while importing
        # the bridge is missing. ModuleNotFoundError subclasses ImportError, so
        # this clause must stay ahead of the generic ImportError handler below.
        missing = exc.name or str(exc)
        if missing not in RUNTIME_PACKAGES:
            raise
        if not install_missing:
            raise RuntimeError(_missing_dependency_message(_missing_runtime_packages())) from exc
        _install_missing_runtime_packages()
    except ImportError as exc:
        # A stale or partially imported bridge module that lacks the expected
        # symbol; clearing it and retrying usually resolves the import.
        if "OriginEmbeddedBridgeServer" not in str(exc):
            raise

    _clear_failed_imports()
    importlib.invalidate_caches()
    from origin_mcp.bridge import OriginEmbeddedBridgeServer

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
    """Start origin-mcp bridge inside the running Origin Python process.

    ``install_missing`` defaults to ``True``. When the embedded Python is
    missing required packages the addon attempts to install them with ``pip``
    inside Origin's embedded Python automatically. Set
    ``ORIGIN_MCP_INSTALL_MISSING=0`` to disable automatic installation and fail
    fast with an explicit message listing what to install.
    """

    existing = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    if existing is not None and (thread is None or getattr(thread, "is_alive", lambda: False)()):
        actual_host, actual_port = existing.server_address
        _notify(
            "Bridge is already running inside Origin.",
            fields={"host": actual_host, "port": actual_port},
        )
        return {"running": True, "host": actual_host, "port": actual_port, "already_running": True}

    _emit(
        "starting inside Origin Python",
        fields={
            "running": False,
            "host": host,
            "port": port,
            "max_tasks": max_tasks,
            "background": background,
            "last_error": None,
        },
    )
    try:
        # Drop any stale cached origin_mcp modules first -- Origin's Python
        # Console commonly reruns this addon during development -- then resolve
        # src onto sys.path and confirm the bridge import. Clearing before
        # resolving is what lets a restarted bridge pick up an adjacent src
        # checkout instead of continuing to serve an older installed copy.
        _clear_origin_mcp_imports()
        package_source = _ensure_origin_mcp_importable(src_dir)
        from origin_mcp.bridge_handshake import generate_token

        if token is None and not _env_bool("ORIGIN_MCP_BRIDGE_NO_AUTH", False):
            # Generate a per-session token so the bridge is not reachable by any
            # local process by default. The MCP server reads it back from the
            # handshake file (see origin_mcp.bridge_handshake) with no config.
            token = generate_token()
        if install_missing:
            _install_missing_runtime_packages()
        else:
            still_missing = _missing_runtime_packages()
            if still_missing:
                raise RuntimeError(_missing_dependency_message(still_missing))
        OriginBridgeServer = _load_bridge_server(install_missing=install_missing)
        server = OriginBridgeServer((host, port), token=token, max_tasks=max_tasks)
    except Exception as exc:
        _emit(
            "failed to start inside Origin Python",
            fields={
                "running": False,
                "last_error": str(exc),
                "last_error_type": type(exc).__name__,
                "last_traceback": traceback.format_exc(),
            },
        )
        _notify(
            "Bridge failed to start inside Origin. See the status file for details.",
        )
        raise

    globals()["_origin_mcp_bridge_server"] = server

    actual_host, actual_port = server.server_address
    auth_enabled = bool(token)
    handshake_path: Any = None
    if auth_enabled:
        try:
            from origin_mcp.bridge_handshake import write_handshake

            handshake_path = write_handshake(actual_host, actual_port, token)
        except Exception as exc:  # pragma: no cover - defensive
            _emit(
                "failed to write bridge handshake file",
                fields={"handshake_error": str(exc)},
            )
    globals()["_origin_mcp_handshake_path"] = handshake_path
    result = {
        "running": True,
        "host": actual_host,
        "port": actual_port,
        "package_source": package_source,
        "max_tasks": max_tasks,
        "background": background,
        "auth_enabled": auth_enabled,
    }
    _notify(
        "Bridge is running inside Origin.",
        fields={
            "host": actual_host,
            "port": actual_port,
            "package_source": package_source,
            "max_tasks": max_tasks,
            "background": background,
            "running": True,
            "auth_enabled": auth_enabled,
            "handshake_path": str(handshake_path) if handshake_path else None,
            "last_error": None,
        },
    )
    if not auth_enabled:
        _notify(
            "WARNING: the Origin bridge is running WITHOUT authentication "
            "(ORIGIN_MCP_BRIDGE_NO_AUTH is set). Any local process can drive "
            "Origin, including running arbitrary LabTalk. Unset the variable to "
            "restore the auto-generated token.",
        )
    if background:
        thread = threading.Thread(
            target=_serve_background,
            args=(server,),
            name="origin-mcp-bridge",
            daemon=True,
        )
        thread.start()
        globals()["_origin_mcp_bridge_thread"] = thread
        return result

    globals()["_origin_mcp_bridge_thread"] = None
    _emit("serving requests cooperatively; keep this Python Console running")
    try:
        _serve_foreground_cooperative(server)
    finally:
        _finalize_bridge_stopped(server)
    return result


def stop_origin_mcp_bridge() -> dict[str, Any]:
    """Stop the Origin-embedded origin-mcp bridge started by this addon."""

    server = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    if server is None:
        return {"stopped": False, "reason": "not_running"}

    server.shutdown()
    if thread is not None:
        thread.join(timeout=2)
    return {"stopped": True}


def request_stop_origin_mcp_bridge() -> dict[str, Any]:
    """Signal the foreground bridge loop to stop, without tearing it down here.

    Safe to call from inside Origin while ``start_origin_mcp_bridge`` is serving
    in the foreground -- for example from a toolbar button whose click is
    dispatched through the message pump and therefore runs re-entrantly on the
    serving thread. It only sets the shutdown event; the serving loop performs
    the single teardown in its ``finally`` block. Use ``stop_origin_mcp_bridge``
    instead for the background-thread case where the caller owns teardown.
    """

    server = globals().get("_origin_mcp_bridge_server")
    if server is None:
        return {"stop_requested": False, "reason": "not_running"}
    server.request_shutdown()
    return {"stop_requested": True}


def origin_mcp_bridge_status() -> dict[str, Any]:
    """Return local status for the Origin-embedded bridge thread."""

    server = globals().get("_origin_mcp_bridge_server")
    thread = globals().get("_origin_mcp_bridge_thread")
    running = bool(server is not None and (thread is None or thread.is_alive()))
    if not running:
        return {"running": False}
    actual_host, actual_port = server.server_address
    return {"running": True, "host": actual_host, "port": actual_port}


_register_control_module_alias()


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
