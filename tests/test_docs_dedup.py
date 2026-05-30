from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_tools_doc_does_not_duplicate_exhaustive_tool_catalogs() -> None:
    text = _read_doc("docs/tools.md")

    assert not re.findall(r"(?m)^-\s+`origin_[^`]+`", text)
    assert "## Worksheet Tools" not in text
    assert "## Plotting Tools" not in text
    assert "## Graph Editing Tools" not in text
    assert "## Analysis Tools" not in text


def test_bridge_doc_does_not_duplicate_bridge_tool_catalog() -> None:
    text = _read_doc("docs/origin-bridge.md")

    bridge_tool_bullets = re.findall(r"(?m)^-\s+`origin_bridge_[^`]+`", text)
    assert not bridge_tool_bullets
    assert '"collection": "mcp_tools"' in text


def test_mcp_config_doc_does_not_duplicate_install_or_runtime_troubleshooting() -> None:
    text = _read_doc("docs/mcp-config.md")

    assert "python -m venv" not in text
    assert "python -m pip install -e" not in text
    assert "originpro is missing" not in text


def test_bridge_doc_has_single_addon_launch_snippet() -> None:
    text = _read_doc("docs/origin-bridge.md")

    assert text.count("runpy.run_path") == 1
    assert '"path": "C:\\\\data\\\\run.csv"' not in text


def test_docs_do_not_duplicate_origin_doctor_field_explanations() -> None:
    docs = "\n".join(
        _read_doc(path)
        for path in (
            "README.md",
            "README.zh.md",
            "docs/mcp-config.md",
            "docs/origin-bridge.md",
            "docs/tools.md",
        )
    )

    forbidden = (
        "bridge configuration, status file",
        "status file, bridge ping result",
        "MCP-side bridge settings",
        "bridge ping results",
        "tool profile, and recommended fixes",
        "status 文件、bridge ping",
    )
    for phrase in forbidden:
        assert phrase not in docs


def test_setup_docs_do_not_prompt_origin_doctor_after_mcp_configuration() -> None:
    docs = "\n".join(
        _read_doc(path)
        for path in (
            "docs/mcp-config.md",
            "docs/agentic/origin-mcp-bootstrap.md",
            "docs/agentic/origin-mcp-bootstrap-codex.md",
            "docs/agentic/origin-mcp-bootstrap-claude.md",
        )
    )

    forbidden = (
        "Use the origin MCP server to run origin_doctor",
        '"ping_origin": true',
        "First ask the MCP client to call",
        "verified with `origin_doctor`",
    )
    for phrase in forbidden:
        assert phrase not in docs
