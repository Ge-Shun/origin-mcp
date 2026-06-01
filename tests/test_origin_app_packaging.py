from __future__ import annotations

import configparser
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_builder_module():
    spec = importlib.util.spec_from_file_location(
        "origin_mcp_app_builder_test",
        ROOT / "scripts" / "build_origin_app.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_origin_app_sources() -> None:
    builder = load_builder_module()
    builder.BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    builder.OPX_PATH.write_text("stale opx", encoding="utf-8")
    builder.STOP_OPX_PATH.write_text("stale stop opx", encoding="utf-8")
    app_dir = builder.build_app(force=True)
    stop_app_dir = builder.BUILD_ROOT / builder.STOP_APP_NAME

    assert not builder.OPX_PATH.exists()
    assert not builder.STOP_OPX_PATH.exists()
    assert (app_dir / "addon.py").is_file()
    assert (app_dir / "start_bridge.py").is_file()
    assert (stop_app_dir / "stop_bridge.ps1").is_file()
    assert (stop_app_dir / "stop_bridge.vbs").is_file()
    # Stop runs via vbs -> ps1 only; there is no Python stop entry point.
    assert not (stop_app_dir / "stop_bridge.py").exists()
    assert (app_dir / "src" / "origin_mcp" / "bridge.py").is_file()
    assert (app_dir / "launch.ogs").is_file()
    assert (stop_app_dir / "launch.ogs").is_file()
    assert (app_dir / "AppIcon.png").is_file()
    assert (stop_app_dir / "AppIcon.png").is_file()
    assert (app_dir / "AppIcon.png").read_bytes() == (
        ROOT / "docs" / "assets" / "origin-mcp-start-icon.png"
    ).read_bytes()
    assert (stop_app_dir / "AppIcon.png").read_bytes() == (
        ROOT / "docs" / "assets" / "origin-mcp-stop-icon.png"
    ).read_bytes()
    assert (app_dir / "AppIcon.png").read_bytes() != (stop_app_dir / "AppIcon.png").read_bytes()

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(app_dir / "package.ini", encoding="utf-8")

    assert config["Package"]["Name"] == builder.START_APP_NAME
    assert config["Package"]["Version"] == "0.1.2"
    assert config["Package"]["Description"] == "Start the origin-mcp Origin GUI bridge."
    assert config["App"]["LaunchScript"] == "launch.ogs"
    assert config["AppEnable"]["Always"] == "1"

    launch = (app_dir / "launch.ogs").read_text(encoding="utf-8")
    assert "run -pyf" in launch
    assert "start_bridge.py" in launch
    assert 'run.section("%@AOrigin MCP Bridge Start\\launch.ogs", Start)' in launch
    assert "[Start]" in launch
    assert "[Stop]" not in launch
    assert "[Toggle]" not in launch

    stop_config = configparser.ConfigParser()
    stop_config.optionxform = str
    stop_config.read(stop_app_dir / "package.ini", encoding="utf-8")
    assert stop_config["Package"]["Name"] == builder.STOP_APP_NAME
    assert stop_config["Package"]["Description"] == "Stop the origin-mcp Origin GUI bridge."

    stop_launch = (stop_app_dir / "launch.ogs").read_text(encoding="utf-8")
    assert "stop_bridge.vbs" in stop_launch
    assert "wscript.exe" in stop_launch
    assert "powershell.exe" not in stop_launch
    assert "run -pyf" not in stop_launch
    assert 'run.section("%@AOrigin MCP Bridge Stop\\launch.ogs", Stop)' in stop_launch
    assert "[Status]" not in launch

    starter = (app_dir / "start_bridge.py").read_text(encoding="utf-8")
    assert "origin_mcp_bridge_status()" in starter
    assert "start_origin_mcp_bridge(background=False)" in starter
    assert "Bridge is already running." in starter
    assert "background=True" not in starter

    stop_powershell = (stop_app_dir / "stop_bridge.ps1").read_text(encoding="utf-8")
    assert "ConvertFrom-Json" in stop_powershell
    assert "ConvertTo-Json -Compress" in stop_powershell
    assert '"method"' not in stop_powershell  # request is built as a PS hashtable
    assert "method = " in stop_powershell
    assert "release_origin = $true" in stop_powershell
    assert "close_origin = $false" in stop_powershell
    assert "Bridge stop requested." in stop_powershell

    stop_vbs = (stop_app_dir / "stop_bridge.vbs").read_text(encoding="utf-8")
    assert "WScript.Shell" in stop_vbs
    assert "stop_bridge.ps1" in stop_vbs
    assert "shell.Run cmd, 0, False" in stop_vbs

    # The package-root workaround is gone; mkOPX app:= packs from the Apps folder.
    assert not (builder.BUILD_ROOT / "package-root").exists()
    assert not hasattr(builder, "PACKAGE_APP_DIR")
    assert "SourcePath" not in config["Files"]
    assert "OPXFile" not in config["Files"]

    command_text = builder.COMMAND_PATH.read_text(encoding="utf-8")
    assert "Origin's Command Window" in command_text
    assert 'mkOPX app:="Origin MCP Bridge Start"' in command_text
    assert 'mkOPX app:="Origin MCP Bridge Stop"' in command_text
    assert "ini:=" not in command_text
    assert "package-root" not in command_text
    assert "make-origin-mcp-bridge-opx.ogs" not in command_text
    assert f"Expected OPX output:\n{builder.OPX_PATH}" in command_text
    assert str(builder.STOP_OPX_PATH) in command_text


def test_origin_apps_dir_resolution(monkeypatch) -> None:
    builder = load_builder_module()
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\tester\AppData\Local")
    dest = builder.origin_apps_dir()
    assert dest is not None
    assert dest.name == builder.START_APP_NAME
    assert dest.parent.name == "Apps"

    destinations = builder.origin_app_dirs()
    assert destinations is not None
    assert [path.name for path in destinations] == [builder.START_APP_NAME, builder.STOP_APP_NAME]

    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert builder.origin_apps_dir() is None
    assert builder.origin_app_dirs() is None
