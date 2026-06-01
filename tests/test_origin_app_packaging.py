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
    app_dir = builder.build_app(force=True)

    assert not builder.OPX_PATH.exists()
    assert (app_dir / "addon.py").is_file()
    assert (app_dir / "toggle_bridge.py").is_file()
    assert (app_dir / "src" / "origin_mcp" / "bridge.py").is_file()
    assert (app_dir / "launch.ogs").is_file()
    assert (app_dir / "AppIcon.png").is_file()

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(app_dir / "package.ini", encoding="utf-8")

    assert config["Package"]["Name"] == builder.APP_NAME
    assert config["Package"]["Version"] == "0.1.2"
    assert config["Package"]["Description"] == "Toggle the origin-mcp Origin GUI bridge."
    assert config["App"]["LaunchScript"] == "launch.ogs"
    assert config["AppEnable"]["Always"] == "1"

    launch = (app_dir / "launch.ogs").read_text(encoding="utf-8")
    assert "run -pyf" in launch
    assert "toggle_bridge.py" in launch
    assert "run.section(\"%@AOrigin MCP Bridge\\launch.ogs\", Toggle)" in launch
    assert "[Status]" not in launch
    assert "[Start]" not in launch
    assert "[Stop]" not in launch

    toggler = (app_dir / "toggle_bridge.py").read_text(encoding="utf-8")
    assert "origin_mcp_bridge_status()" in toggler
    assert "request_stop_origin_mcp_bridge()" in toggler
    assert "start_origin_mcp_bridge(background=False)" in toggler
    assert "Bridge stop requested." in toggler
    assert 'request_bridge("shutdown"' not in toggler
    assert "background=True" not in toggler
    assert "except Exception" not in toggler

    # The package-root workaround is gone; mkOPX app:= packs from the Apps folder.
    assert not (builder.BUILD_ROOT / "package-root").exists()
    assert not hasattr(builder, "PACKAGE_APP_DIR")
    assert "SourcePath" not in config["Files"]
    assert "OPXFile" not in config["Files"]

    command_text = builder.COMMAND_PATH.read_text(encoding="utf-8")
    assert "Origin's Command Window" in command_text
    assert 'mkOPX app:="Origin MCP Bridge"' in command_text
    assert "ini:=" not in command_text
    assert "package-root" not in command_text
    assert "make-origin-mcp-bridge-opx.ogs" not in command_text
    assert f"Expected OPX output:\n{builder.OPX_PATH}" in command_text


def test_origin_apps_dir_resolution(monkeypatch) -> None:
    builder = load_builder_module()
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\tester\AppData\Local")
    dest = builder.origin_apps_dir()
    assert dest is not None
    assert dest.name == builder.APP_NAME
    assert dest.parent.name == "Apps"

    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert builder.origin_apps_dir() is None
