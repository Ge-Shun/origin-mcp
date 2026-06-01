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
START_APP_NAME = "Origin MCP Bridge Start"
STOP_APP_NAME = "Origin MCP Bridge Stop"
APP_NAMES = (START_APP_NAME, STOP_APP_NAME)
APP_NAME = START_APP_NAME
LEGACY_APP_NAME = "Origin MCP Bridge"
APP_VERSION = "0.1.2"
BUILD_ROOT = ROOT / "build" / "origin-app"
APP_DIR = BUILD_ROOT / START_APP_NAME
START_APP_DIR = BUILD_ROOT / START_APP_NAME
STOP_APP_DIR = BUILD_ROOT / STOP_APP_NAME
OPX_PATH = BUILD_ROOT / f"{START_APP_NAME}.opx"
STOP_OPX_PATH = BUILD_ROOT / f"{STOP_APP_NAME}.opx"
COMMAND_PATH = BUILD_ROOT / "mkopx-command.txt"
OBSOLETE_OGS_PATH = BUILD_ROOT / "make-origin-mcp-bridge-opx.ogs"


def origin_apps_dir() -> Path | None:
    """Return Origin's per-user Apps folder for the Start App, when resolvable.

    Apps live under ``%LOCALAPPDATA%/OriginLab/Apps`` on Windows. Returns ``None``
    off Windows or when ``LOCALAPPDATA`` is unset so callers can skip the copy.
    """

    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None
    return Path(local_appdata) / "OriginLab" / "Apps" / START_APP_NAME


def origin_app_dirs() -> list[Path] | None:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None
    root = Path(local_appdata) / "OriginLab" / "Apps"
    return [root / name for name in APP_NAMES]


START_LAUNCH_OGS = r"""[Main]
run.section("%@AOrigin MCP Bridge Start\launch.ogs", Start);

[Start]
run -pyf "%@AOrigin MCP Bridge Start\start_bridge.py";
"""


STOP_LAUNCH_OGS = r"""[Main]
run.section("%@AOrigin MCP Bridge Stop\launch.ogs", Stop);

[Stop]
run -e wscript.exe "%@AOrigin MCP Bridge Stop\stop_bridge.vbs";
"""


START_BRIDGE_PY = r'''"""Start the bundled origin-mcp bridge from an Origin App.

The Start button uses foreground cooperative serving, which is the reliable
mode for Origin's embedded Python on this machine. The separate Stop button
runs as a second App entry point and requests this foreground loop to exit.
"""

from __future__ import annotations

import ctypes
import importlib.util
import sys
import threading
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
ADDON_PATH = APP_DIR / "addon.py"


def _message(text: str) -> None:
    def _show() -> None:
        ctypes.windll.user32.MessageBoxW(None, text, "Origin MCP Bridge Start", 0x40)

    threading.Thread(target=_show, name="origin-mcp-app-notify", daemon=True).start()


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
    _message("Bridge is already running.")
else:
    addon.start_origin_mcp_bridge(background=False)
'''


# The Stop button launches stop_bridge.vbs (hidden) -> stop_bridge.ps1, which
# connects to the bridge over TCP and requests shutdown. An external process is
# used on purpose: while the Start button serves in the foreground, Origin's
# script engine is busy, so a re-entrant in-process stop is not reliable.
STOP_BRIDGE_PS1 = r"""$ErrorActionPreference = "Stop"

function Show-BridgeMessage {
    param([string]$Text)
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Text,
            "Origin MCP Bridge Stop",
            "OK",
            "Information"
        ) | Out-Null
    } catch {
    }
}

$client = $null
$stream = $null
$writer = $null
$reader = $null

try {
    $handshakePath = Join-Path ([System.IO.Path]::GetTempPath()) "origin-mcp\bridge.json"
    if (-not (Test-Path -LiteralPath $handshakePath)) {
        throw "No bridge handshake file found."
    }

    $handshake = Get-Content -LiteralPath $handshakePath -Raw | ConvertFrom-Json
    $client = [System.Net.Sockets.TcpClient]::new()
    $connect = $client.BeginConnect([string]$handshake.host, [int]$handshake.port, $null, $null)
    if (-not $connect.AsyncWaitHandle.WaitOne(2000)) {
        $client.Close()
        throw "Timed out connecting to bridge."
    }
    $client.EndConnect($connect)
    $client.ReceiveTimeout = 2000
    $client.SendTimeout = 2000

    $stream = $client.GetStream()
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $writer = [System.IO.StreamWriter]::new($stream, $utf8)
    $writer.NewLine = "`n"
    $writer.AutoFlush = $true
    $reader = [System.IO.StreamReader]::new($stream, $utf8)

    $request = @{
        id = "origin-mcp-stop-button"
        method = "shutdown"
        params = @{
            release_origin = $true
            close_origin = $false
        }
        token = [string]$handshake.token
    }
    $writer.WriteLine(($request | ConvertTo-Json -Compress -Depth 5))
    $raw = $reader.ReadLine()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "Bridge returned an empty response."
    }

    $response = $raw | ConvertFrom-Json
    if (-not $response.ok) {
        throw "Bridge refused shutdown: $raw"
    }
    Show-BridgeMessage "Bridge stop requested."
} catch {
    Show-BridgeMessage "Bridge stop not requested: $($_.Exception.Message)"
    exit 1
} finally {
    if ($reader) { $reader.Dispose() }
    if ($writer) { $writer.Dispose() }
    if ($stream) { $stream.Dispose() }
    if ($client) { $client.Dispose() }
}
"""


STOP_BRIDGE_VBS = r"""Option Explicit

Dim fso, shell, scriptDir, ps1, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = fso.BuildPath(scriptDir, "stop_bridge.ps1")
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass "
cmd = cmd & "-WindowStyle Hidden -File " & Chr(34) & ps1 & Chr(34)

shell.Run cmd, 0, False
"""


def _write_package_ini(path: Path, app_name: str, description: str) -> None:
    config = configparser.ConfigParser()
    config.optionxform = str
    config["Package"] = {
        "ID": "0",
        "Type": "1",
        "Name": app_name,
        "Description": description,
        "Version": APP_VERSION,
        "Author": "origin-mcp contributors",
        "Keywords": "mcp, ai, bridge, python, automation",
        "Category": "Import and Export",
        "License": "MIT",
        "Copyrightyear": "2026",
    }
    config["Log"] = {
        "v0.1.2": "Split bridge startup and shutdown into two App buttons.",
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
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", checksum)


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


def _copy_app_icon(app_dir: Path, specific_icon: Path) -> None:
    fallback_icon = ROOT / "docs" / "assets" / "origin-mcp-app-icon.png"
    if specific_icon.is_file():
        shutil.copy2(specific_icon, app_dir / "AppIcon.png")
    elif fallback_icon.is_file():
        shutil.copy2(fallback_icon, app_dir / "AppIcon.png")
    else:
        _write_icon(app_dir / "AppIcon.png")


def _labtalk_path(path: Path) -> str:
    # Origin's mkOPX wants Windows-style backslashes. Forward slashes in a quoted
    # path can make mkOPX hang ("Not Responding") in the Command Window, so always
    # emit backslashes regardless of the platform that runs this builder.
    return str(path.resolve()).replace("/", "\\")


def _mkopx_command(app_name: str = START_APP_NAME, opx_path: Path | None = None) -> str:
    # app:= packs the App from its Apps-folder location; opx:= names the output.
    return f'mkOPX app:="{app_name}" opx:="{_labtalk_path(opx_path or OPX_PATH)}";'


def build_app(force: bool = False) -> Path:
    for app_dir in (START_APP_DIR, STOP_APP_DIR):
        if app_dir.exists():
            if not force:
                raise FileExistsError(f"{app_dir} already exists; pass --force to rebuild.")
            shutil.rmtree(app_dir)
    if force and OBSOLETE_OGS_PATH.exists():
        OBSOLETE_OGS_PATH.unlink()
    if force:
        for opx_path in (OPX_PATH, STOP_OPX_PATH):
            if opx_path.exists():
                opx_path.unlink()
    # Remove the obsolete package-root workaround folder from older builds.
    legacy_package_root = BUILD_ROOT / "package-root"
    if legacy_package_root.exists():
        shutil.rmtree(legacy_package_root)
    START_APP_DIR.mkdir(parents=True)
    STOP_APP_DIR.mkdir(parents=True)

    shutil.copy2(ROOT / "addon.py", START_APP_DIR / "addon.py")
    _copy_tree(ROOT / "src", START_APP_DIR / "src")
    _write_package_ini(
        START_APP_DIR / "package.ini",
        START_APP_NAME,
        "Start the origin-mcp Origin GUI bridge.",
    )
    _write_package_ini(
        STOP_APP_DIR / "package.ini",
        STOP_APP_NAME,
        "Stop the origin-mcp Origin GUI bridge.",
    )
    (START_APP_DIR / "launch.ogs").write_text(
        START_LAUNCH_OGS,
        encoding="utf-8",
        newline="\n",
    )
    (STOP_APP_DIR / "launch.ogs").write_text(
        STOP_LAUNCH_OGS,
        encoding="utf-8",
        newline="\n",
    )
    (START_APP_DIR / "start_bridge.py").write_text(
        START_BRIDGE_PY,
        encoding="utf-8",
        newline="\n",
    )
    (STOP_APP_DIR / "stop_bridge.ps1").write_text(
        STOP_BRIDGE_PS1,
        encoding="utf-8",
        newline="\n",
    )
    (STOP_APP_DIR / "stop_bridge.vbs").write_text(
        STOP_BRIDGE_VBS,
        encoding="utf-8",
        newline="\n",
    )
    asset_dir = ROOT / "docs" / "assets"
    _copy_app_icon(START_APP_DIR, asset_dir / "origin-mcp-start-icon.png")
    _copy_app_icon(STOP_APP_DIR, asset_dir / "origin-mcp-stop-icon.png")

    COMMAND_PATH.write_text(
        (
            "1. Copy these App folders into Origin's Apps directory (or run this\n"
            "   builder with --install):\n"
            f"   {START_APP_DIR}\n"
            f"   {STOP_APP_DIR}\n"
            "   -> %LOCALAPPDATA%\\OriginLab\\Apps\\\n\n"
            "2. Run this command in Origin's Command Window:\n\n"
            f"{_mkopx_command()}\n"
            f"{_mkopx_command(STOP_APP_NAME, STOP_OPX_PATH)}\n\n"
            "Expected OPX output:\n"
            f"{OPX_PATH}\n"
            f"{STOP_OPX_PATH}\n\n"
            "Next step: drag both OPX files above into Origin to install them.\n"
        ),
        encoding="utf-8",
        newline="\n",
    )
    return START_APP_DIR


def install_into_apps(*, force: bool = True) -> Path | None:
    """Copy the built App folder into Origin's per-user Apps directory.

    Returns the destination path, or ``None`` when the Apps directory cannot be
    resolved (e.g. off Windows). Required before ``mkOPX app:=`` can find the App.
    """

    destinations = origin_app_dirs()
    if destinations is None:
        return None
    root = destinations[0].parent
    legacy = root / LEGACY_APP_NAME
    for dest in [legacy, *destinations]:
        if dest.exists():
            if not force:
                raise FileExistsError(f"{dest} already exists; pass force=True to replace.")
            shutil.rmtree(dest)
    for src_dir, dest in zip((START_APP_DIR, STOP_APP_DIR), destinations, strict=True):
        shutil.copytree(src_dir, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destinations[0]


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
            print(
                "Skipped --install: Origin Apps folder not resolvable (need Windows LOCALAPPDATA)."
            )
        else:
            print(f"Copied App folders into Origin Apps folder: {dest.parent}")
            print("This only lets mkOPX app:= find them; a bare folder is NOT registered.")
            print("Pack both OPX (below), then drag them into Origin to install/register.")
    else:
        print("To pack a distributable OPX, first copy this folder into:")
        print(f"  {origin_app_dirs() or '%LOCALAPPDATA%/OriginLab/Apps/<Start and Stop>'}")
        print("  (or re-run this builder with --install)")

    print()
    print("Then, in Origin's Command Window, run:")
    print(_mkopx_command())
    print(_mkopx_command(STOP_APP_NAME, STOP_OPX_PATH))
    print()
    print(f"Expected OPX output: {OPX_PATH}")
    print(f"Expected OPX output: {STOP_OPX_PATH}")
    print(f"Command copy saved to: {COMMAND_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
