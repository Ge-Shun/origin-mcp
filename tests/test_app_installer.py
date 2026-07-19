from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from origin_mcp import __version__
from origin_mcp.app_installer import APP_NAMES, install_origin_apps
from origin_mcp.cli import main


def test_installer_creates_self_contained_origin_apps(tmp_path: Path) -> None:
    paths = install_origin_apps(destination=tmp_path)

    assert tuple(path.name for path in paths) == APP_NAMES
    start, stop = paths
    assert (start / "addon.py").is_file()
    assert (start / "src" / "origin_mcp" / "bridge.py").is_file()
    starter = (start / "start_bridge.py").read_text(encoding="utf-8")
    assert "background=False" in starter
    assert 'sys.modules.pop("origin_mcp_addon", None)' in starter
    assert (stop / "stop_bridge.ps1").is_file()
    assert (stop / "stop_bridge.vbs").is_file()
    stop_script = (stop / "stop_bridge.ps1").read_text(encoding="utf-8")
    assert "$env:ORIGIN_MCP_BRIDGE_HANDSHAKE" in stop_script
    assert "GetTempPath" in stop_script
    assert "[System.Guid]::NewGuid()" in stop_script
    assert 'id = "origin-mcp-stop-button-" +' in stop_script
    assert "generation = [string]$handshake.generation" in stop_script
    assets = Path(__file__).resolve().parents[1] / "docs" / "assets"
    assert (start / "AppIcon.png").read_bytes() == (
        assets / "origin-mcp-start-icon.png"
    ).read_bytes()
    assert (stop / "AppIcon.png").read_bytes() == (assets / "origin-mcp-stop-icon.png").read_bytes()

    config = configparser.ConfigParser()
    config.read(start / "package.ini", encoding="utf-8")
    assert config["Package"]["Version"] == __version__


def test_installer_requires_force_and_replaces_atomically(tmp_path: Path) -> None:
    start, _ = install_origin_apps(destination=tmp_path)
    marker = start / "obsolete.txt"
    marker.write_text("old", encoding="utf-8")

    with pytest.raises(FileExistsError):
        install_origin_apps(destination=tmp_path)

    paths = install_origin_apps(destination=tmp_path, force=True)
    assert not (paths[0] / marker.name).exists()
    assert not list(tmp_path.glob(".*.backup-*"))
    assert not list(tmp_path.glob(".origin-mcp-stage-*"))


def test_installer_cli_prints_registration_commands(tmp_path: Path, capsys) -> None:
    main(["install-origin-app", "--destination", str(tmp_path)])

    output = capsys.readouterr().out
    assert 'mkOPX app:="Origin MCP Bridge Start"' in output
    assert 'mkOPX app:="Origin MCP Bridge Stop"' in output
    assert "drag both OPX files" in output
