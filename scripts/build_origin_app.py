"""Build the Origin App source folder for the origin-mcp bridge.

It vendors addon.py plus the source package so the installed App does not depend
on the developer checkout. The App is packed into an OPX with Origin's mkOPX
X-Function in its canonical ``app:=`` form, which requires the App folder to live
in Origin's per-user Apps directory (``%LOCALAPPDATA%/OriginLab/Apps/<AppName>``).
This script can copy the built folder there for you (``--install``); mkOPX then
stores the files relative to the Apps base so installs land cleanly in
``Apps/<AppName>`` on every machine. The older ``ini:=`` + ``SourcePath`` form is
not used because mkOPX did not honor the source path and nested installs under
the full build path.
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Origin MCP Bridge"
APP_VERSION = "0.1.2"
BUILD_ROOT = ROOT / "build" / "origin-app"
APP_DIR = BUILD_ROOT / APP_NAME
OPX_PATH = BUILD_ROOT / f"{APP_NAME}.opx"
COMMAND_PATH = BUILD_ROOT / "mkopx-command.txt"
OBSOLETE_OGS_PATH = BUILD_ROOT / "make-origin-mcp-bridge-opx.ogs"


def origin_apps_dir() -> Path | None:
    """Return Origin's per-user Apps folder for this App, when resolvable.

    Apps live under ``%LOCALAPPDATA%/OriginLab/Apps`` on Windows. Returns ``None``
    off Windows or when ``LOCALAPPDATA`` is unset so callers can skip the copy.
    """

    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None
    return Path(local_appdata) / "OriginLab" / "Apps" / APP_NAME


LAUNCH_OGS = r"""[Main]
run.section("%@AOrigin MCP Bridge\launch.ogs", Toggle);

[Toggle]
run -pyf "%@AOrigin MCP Bridge\toggle_bridge.py";
"""


TOGGLE_BRIDGE_PY = r'''"""Toggle the bundled origin-mcp bridge from an Origin App.

The button starts the bridge in *foreground* (cooperative) mode, which is the
most reliable mode across Origin embedded-Python builds -- a background serving
thread is not scheduled on every install, leaving the socket bound but never
answering. Starting blocks this click handler inside the cooperative serve
loop, but that loop pumps Windows messages so Origin stays responsive and a
later click can stop the bridge.

Stopping uses the in-process ``request_stop_origin_mcp_bridge`` (it only sets
the serve loop's shutdown event) instead of a TCP ``shutdown`` request, which
would deadlock: the second click runs re-entrantly on the serving thread, so
no one would be left to service the TCP request it is waiting on.
"""

from __future__ import annotations

import ctypes
import importlib.util
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
ADDON_PATH = APP_DIR / "addon.py"


def _message(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, "Origin MCP Bridge", 0x40)


def _load_addon():
    module = sys.modules.get("origin_mcp_addon")
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location("origin_mcp_addon", ADDON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {ADDON_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


addon = _load_addon()
src = APP_DIR / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

if addon.origin_mcp_bridge_status().get("running"):
    addon.request_stop_origin_mcp_bridge()
    _message("Bridge stop requested.")
else:
    # Serves cooperatively and blocks here until a later click stops it.
    # start_origin_mcp_bridge shows its own "Bridge is running" notice first.
    addon.start_origin_mcp_bridge(background=False)
'''


def _write_package_ini(path: Path) -> None:
    config = configparser.ConfigParser()
    config.optionxform = str
    config["Package"] = {
        "ID": "0",
        "Type": "1",
        "Name": APP_NAME,
        "Description": "Toggle the origin-mcp Origin GUI bridge.",
        "Version": APP_VERSION,
        "Author": "origin-mcp contributors",
        "Keywords": "mcp, ai, bridge, python, automation",
        "Category": "Import and Export",
        "License": "MIT",
        "Copyrightyear": "2026",
    }
    config["Log"] = {
        "v0.1.2": "Toggle starts the bridge in reliable foreground mode.",
        "v0.1.1": "Single-button bridge toggle with corrected OPX install root.",
        "v0.1.0": "Initial origin-mcp bridge launcher app.",
    }
    config["Origin"] = {"Version": "9.65", "Pro": "0"}
    config["App"] = {
        "Icon": "AppIcon.png",
        "ToolbarIcon": "",
        "LaunchScript": "launch.ogs",
        "Preview": "",
        "ScreenShot": "",
    }
    config["AppEnable"] = {
        "Always": "1",
        "Graph": "1",
        "Workbook": "1",
        "Matrixbook": "1",
        "Image": "1",
        "Excel": "1",
        "Layout": "1",
        "LabTalkExp": "",
    }
    config["Toolbar"] = {"ButtonGroupFile": "", "Create": "0"}
    config["LabTalk"] = {"BeforeInstall": "", "AfterInstall": "", "BeforeUninstall": ""}
    # No SourcePath/OPXFile: mkOPX app:= packs the App from its Apps-folder
    # location and the opx:= argument names the output.
    config["Files"] = {"EncryptC": "0", "LZ4": "0"}

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle, space_around_delimiters=False)


def _copy_tree(src: Path, dst: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".mypy_cache", ".pytest_cache")
    shutil.copytree(src, dst, ignore=ignore)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def _write_icon(path: Path) -> None:
    width = height = 32
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            border = x in {0, width - 1} or y in {0, height - 1}
            accent = 7 <= x <= 24 and 7 <= y <= 24 and (x - y) % 5 == 0
            if border:
                row.extend((34, 40, 49, 255))
            elif accent:
                row.extend((19, 116, 209, 255))
            else:
                row.extend((242, 245, 248, 255))
        rows.append(bytes(row))
    raw = b"".join(rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def _labtalk_path(path: Path) -> str:
    # Origin's mkOPX wants Windows-style backslashes. Forward slashes in a quoted
    # path can make mkOPX hang ("Not Responding") in the Command Window, so always
    # emit backslashes regardless of the platform that runs this builder.
    return str(path.resolve()).replace("/", "\\")


def _mkopx_command() -> str:
    # app:= packs the App from its Apps-folder location; opx:= names the output.
    return f'mkOPX app:="{APP_NAME}" opx:="{_labtalk_path(OPX_PATH)}";'


def build_app(force: bool = False) -> Path:
    if APP_DIR.exists():
        if not force:
            raise FileExistsError(f"{APP_DIR} already exists; pass --force to rebuild.")
        shutil.rmtree(APP_DIR)
    if force and OBSOLETE_OGS_PATH.exists():
        OBSOLETE_OGS_PATH.unlink()
    if force and OPX_PATH.exists():
        OPX_PATH.unlink()
    # Remove the obsolete package-root workaround folder from older builds.
    legacy_package_root = BUILD_ROOT / "package-root"
    if legacy_package_root.exists():
        shutil.rmtree(legacy_package_root)
    APP_DIR.mkdir(parents=True)

    shutil.copy2(ROOT / "addon.py", APP_DIR / "addon.py")
    _copy_tree(ROOT / "src", APP_DIR / "src")
    _write_package_ini(APP_DIR / "package.ini")
    (APP_DIR / "launch.ogs").write_text(LAUNCH_OGS, encoding="utf-8", newline="\n")
    (APP_DIR / "toggle_bridge.py").write_text(TOGGLE_BRIDGE_PY, encoding="utf-8", newline="\n")
    icon_source = ROOT / "docs" / "assets" / "origin-mcp-app-icon.png"
    if icon_source.is_file():
        shutil.copy2(icon_source, APP_DIR / "AppIcon.png")
    else:
        _write_icon(APP_DIR / "AppIcon.png")

    COMMAND_PATH.write_text(
        (
            "1. Copy this App folder into Origin's Apps directory (or run this\n"
            "   builder with --install):\n"
            f"   {APP_DIR}\n"
            "   -> %LOCALAPPDATA%\\OriginLab\\Apps\\" + APP_NAME + "\\\n\n"
            "2. Run this command in Origin's Command Window:\n\n"
            f"{_mkopx_command()}\n\n"
            "Expected OPX output:\n"
            f"{OPX_PATH}\n\n"
            "Next step: drag the OPX above into Origin to install it.\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    return APP_DIR


def install_into_apps(*, force: bool = True) -> Path | None:
    """Copy the built App folder into Origin's per-user Apps directory.

    Returns the destination path, or ``None`` when the Apps directory cannot be
    resolved (e.g. off Windows). Required before ``mkOPX app:=`` can find the App.
    """

    dest = origin_apps_dir()
    if dest is None:
        return None
    if dest.exists():
        if not force:
            raise FileExistsError(f"{dest} already exists; pass force=True to replace.")
        shutil.rmtree(dest)
    shutil.copytree(APP_DIR, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace an existing build folder")
    parser.add_argument(
        "--install",
        action="store_true",
        help="also copy the App into Origin's Apps folder (needed for mkOPX app:=)",
    )
    args = parser.parse_args()

    app_dir = build_app(force=args.force)
    print(f"Built Origin App source: {app_dir}")

    if args.install:
        dest = install_into_apps(force=True)
        if dest is None:
            print("Skipped --install: Origin Apps folder not resolvable (need Windows LOCALAPPDATA).")
        else:
            print(f"Installed App into Origin Apps folder: {dest}")
            print("Restart Origin to pick up the updated App; the button works from here.")
    else:
        print("To pack a distributable OPX, first copy this folder into:")
        print(f"  {origin_apps_dir() or '%LOCALAPPDATA%/OriginLab/Apps/' + APP_NAME}")
        print("  (or re-run this builder with --install)")

    print()
    print("Then, in Origin's Command Window, run:")
    print(_mkopx_command())
    print()
    print(f"Expected OPX output: {OPX_PATH}")
    print(f"Command copy saved to: {COMMAND_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
