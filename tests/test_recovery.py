from __future__ import annotations

import pytest

from origin_mcp.recovery import recovery_guidance


@pytest.mark.parametrize(
    ("error_code", "recoverable", "action_fragment"),
    [
        ("origin_bridge_unavailable", True, "Start App"),
        ("origin_bridge_timeout", True, "modal dialog"),
        ("origin_bridge_unauthorized", True, "handshake token"),
        ("invalid_request", True, "tool schema"),
        ("worksheet_not_found", True, "project objects"),
        ("path_not_allowed", True, "ORIGIN_MCP_ALLOWED_ROOTS"),
        ("result_too_large", True, "fewer rows"),
        ("confirmation_required", True, "confirm=true"),
        ("origin_dependency_unavailable", True, "embedded-Python dependency"),
        ("unsupported_analysis_type", True, "supported analysis type"),
        ("unsupported_origin_version", False, "Upgrade Origin"),
        ("xfunction_not_allowed", False, "origin_list_xfunctions"),
        ("graph_export_failed", True, "project state"),
        ("analysis_template_not_created", True, "project state"),
        ("unexpected_error", False, "server and bridge logs"),
    ],
)
def test_recovery_guidance_is_actionable(
    error_code: str,
    recoverable: bool,
    action_fragment: str,
) -> None:
    guidance = recovery_guidance(error_code)

    assert guidance.recoverable is recoverable
    assert guidance.next_actions
    assert action_fragment in " ".join(guidance.next_actions)


def test_unknown_error_code_gets_safe_diagnostic_fallback() -> None:
    guidance = recovery_guidance("future_error_code")

    assert guidance.recoverable is False
    assert any("doctor" in action for action in guidance.next_actions)
