"""Install the bundled Origin Start/Stop Apps for the current user."""

from __future__ import annotations

import configparser
import os
import shutil
import uuid
from pathlib import Path

from . import __version__

START_APP_NAME = "Origin MCP Bridge Start"
STOP_APP_NAME = "Origin MCP Bridge Stop"
APP_NAMES = (START_APP_NAME, STOP_APP_NAME)

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

START_BRIDGE_PY = r'''"""Start the bridge from Origin's embedded Python."""

from __future__ import annotations

import ctypes
import importlib.util
import sys
import threading
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def _message(text: str) -> None:
    def _show() -> None:
        ctypes.windll.user32.MessageBoxW(None, text, "Origin MCP Bridge Start", 0x40)

    threading.Thread(target=_show, name="origin-mcp-app-notify", daemon=True).start()


def _load_addon():
    module = sys.modules.get("origin_mcp_addon")
    if module is not None:
        try:
            if module.origin_mcp_bridge_status().get("running"):
                return module
        except Exception:
            pass
        # A stopped bridge may leave its control module cached for the lifetime
        # of Origin. Drop it so App upgrades take effect on the next Start click.
        sys.modules.pop("origin_mcp_addon", None)
    path = APP_DIR / "addon.py"
    spec = importlib.util.spec_from_file_location("origin_mcp_addon", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


src = APP_DIR / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
addon = _load_addon()
if addon.origin_mcp_bridge_status().get("running"):
    _message("Bridge is already running.")
else:
    addon.start_origin_mcp_bridge(background=False)
'''

STOP_BRIDGE_PS1 = r"""$ErrorActionPreference = "Stop"

function Show-BridgeMessage {
    param([string]$Text)
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Text, "Origin MCP Bridge Stop", "OK", "Information"
        ) | Out-Null
    } catch {}
}

$client = $null
$stream = $null
$writer = $null
$reader = $null
try {
    $handshakePath = $env:ORIGIN_MCP_BRIDGE_HANDSHAKE
    if ([string]::IsNullOrWhiteSpace($handshakePath)) {
        $handshakePath = Join-Path ([System.IO.Path]::GetTempPath()) "origin-mcp\bridge.json"
    }
    if (-not (Test-Path -LiteralPath $handshakePath)) { throw "No bridge handshake file found." }
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
        id = "origin-mcp-stop-button-" + [System.Guid]::NewGuid().ToString("N")
        method = "shutdown"
        params = @{ release_origin = $true; close_origin = $false }
        token = [string]$handshake.token
        client_id = "origin-mcp-stop-app"
        generation = [string]$handshake.generation
        lease_id = [string]$handshake.lease_id
    }
    $writer.WriteLine(($request | ConvertTo-Json -Compress -Depth 5))
    $raw = $reader.ReadLine()
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "Bridge returned an empty response." }
    $response = $raw | ConvertFrom-Json
    if (-not $response.ok) { throw "Bridge refused shutdown: $raw" }
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
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "
cmd = cmd & Chr(34) & ps1 & Chr(34)
shell.Run cmd, 0, False
"""


def _default_apps_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError(
            "LOCALAPPDATA is not set; pass --destination with the Origin Apps folder."
        )
    return Path(local_appdata) / "OriginLab" / "Apps"


def _write_package_ini(path: Path, app_name: str, description: str) -> None:
    config = configparser.ConfigParser()
    config.optionxform = str  # type: ignore[method-assign, assignment]
    config["Package"] = {
        "ID": "0",
        "Type": "1",
        "Name": app_name,
        "Description": description,
        "Version": __version__,
        "Author": "origin-mcp contributors",
        "Keywords": "mcp, ai, bridge, python, automation",
        "Category": "Import and Export",
        "License": "MIT",
        "Copyrightyear": "2026",
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
    config["Files"] = {"EncryptC": "0", "LZ4": "0"}
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle, space_around_delimiters=False)


def _icon_asset(filename: str) -> Path:
    package_dir = Path(__file__).resolve().parent
    candidates = (
        package_dir / "app_assets" / filename,
        package_dir.parents[1] / "docs" / "assets" / filename,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"The installed distribution is missing its bundled {filename} asset.")


def _copy_package(destination: Path) -> None:
    package_dir = Path(__file__).resolve().parent
    shutil.copytree(
        package_dir,
        destination / "src" / "origin_mcp",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def _render_apps(root: Path) -> tuple[Path, Path]:
    start = root / START_APP_NAME
    stop = root / STOP_APP_NAME
    start.mkdir(parents=True)
    stop.mkdir(parents=True)
    package_dir = Path(__file__).resolve().parent
    addon = package_dir / "app_assets" / "addon.py"
    if not addon.is_file():
        # hatch force-includes this asset in built wheels. This fallback keeps
        # the command directly runnable from a source checkout as well.
        addon = package_dir.parents[1] / "addon.py"
    if not addon.is_file():
        raise RuntimeError("The installed distribution is missing its bundled addon.py asset.")
    shutil.copy2(addon, start / "addon.py")
    _copy_package(start)
    (start / "start_bridge.py").write_text(START_BRIDGE_PY, encoding="utf-8", newline="\n")
    (start / "launch.ogs").write_text(START_LAUNCH_OGS, encoding="utf-8", newline="\n")
    (stop / "stop_bridge.ps1").write_text(STOP_BRIDGE_PS1, encoding="utf-8", newline="\n")
    (stop / "stop_bridge.vbs").write_text(STOP_BRIDGE_VBS, encoding="utf-8", newline="\n")
    (stop / "launch.ogs").write_text(STOP_LAUNCH_OGS, encoding="utf-8", newline="\n")
    _write_package_ini(start / "package.ini", START_APP_NAME, "Start the origin-mcp bridge.")
    _write_package_ini(stop / "package.ini", STOP_APP_NAME, "Stop the origin-mcp bridge.")
    shutil.copy2(_icon_asset("origin-mcp-start-icon.png"), start / "AppIcon.png")
    shutil.copy2(_icon_asset("origin-mcp-stop-icon.png"), stop / "AppIcon.png")
    return start, stop


def install_origin_apps(
    *,
    force: bool = False,
    destination: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path]:
    """Install self-contained Start/Stop App folders and return their paths."""

    apps_root = Path(destination) if destination is not None else _default_apps_root()
    apps_root.mkdir(parents=True, exist_ok=True)
    destinations = (apps_root / START_APP_NAME, apps_root / STOP_APP_NAME)
    existing = [path for path in destinations if path.exists()]
    if existing and not force:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Origin App already exists: {names}; pass --force to replace it.")

    transaction = uuid.uuid4().hex
    stage = apps_root / f".origin-mcp-stage-{transaction}"
    backups: list[tuple[Path, Path]] = []
    installed_targets: list[Path] = []
    try:
        staged = _render_apps(stage)
        for target in existing:
            backup = apps_root / f".{target.name}.backup-{transaction}"
            target.replace(backup)
            backups.append((target, backup))
        for source, target in zip(staged, destinations, strict=True):
            source.replace(target)
            installed_targets.append(target)
    except Exception:
        for target in installed_targets:
            if target.exists():
                shutil.rmtree(target)
        for original, backup in reversed(backups):
            if backup.exists():
                backup.replace(original)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    for _, backup in backups:
        if backup.exists():
            shutil.rmtree(backup)
    return destinations
