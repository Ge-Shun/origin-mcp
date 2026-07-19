"""Structured recovery guidance for stable origin-mcp error codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryGuidance:
    """Machine-readable guidance attached to a failed tool result."""

    recoverable: bool
    next_actions: tuple[str, ...]


_BRIDGE_GUIDANCE: dict[str, RecoveryGuidance] = {
    "origin_bridge_unavailable": RecoveryGuidance(
        True,
        (
            "Start Origin and click the Origin MCP Bridge Start App.",
            "Run `origin-mcp status`, then `origin-mcp doctor --ping-origin` to verify recovery.",
        ),
    ),
    "origin_bridge_timeout": RecoveryGuidance(
        True,
        (
            "Check Origin for a modal dialog or busy operation; close it or wait for it to finish.",
            "Run `origin-mcp doctor --ping-origin`; check for completion before retrying.",
        ),
    ),
    "origin_bridge_unauthorized": RecoveryGuidance(
        True,
        (
            "Stop and restart the Origin MCP Bridge Start App to refresh its handshake token.",
            "Match ORIGIN_MCP_BRIDGE_TOKEN to the active handshake, then run `origin-mcp doctor`.",
        ),
    ),
    "origin_bridge_generation_mismatch": RecoveryGuidance(
        True,
        (
            "Reload the active bridge handshake and reconnect the MCP client.",
            "Confirm only one Origin process listens on the configured bridge port.",
        ),
    ),
    "invalid_bridge_config": RecoveryGuidance(
        True,
        (
            "Correct the bridge host, port, timeout, or token configuration.",
            "Run `origin-mcp doctor` to compare the endpoint with the active status file.",
        ),
    ),
    "invalid_bridge_host": RecoveryGuidance(
        True,
        (
            "Set ORIGIN_MCP_BRIDGE_HOST to a valid local address, normally 127.0.0.1.",
            "Restart the bridge and run `origin-mcp doctor`.",
        ),
    ),
    "bridge_request_id_conflict": RecoveryGuidance(
        True,
        (
            "Retry the request with a new request ID.",
            "If conflicts continue, restart the MCP client so it resets its request sequence.",
        ),
    ),
    "bridge_task_capacity_reached": RecoveryGuidance(
        True,
        (
            "Wait for active bridge tasks to finish or cancel tasks that are no longer needed.",
            "List bridge tasks to confirm capacity is available before retrying.",
        ),
    ),
    "bridge_task_not_found": RecoveryGuidance(
        True,
        (
            "List bridge tasks and use a task ID that is still present.",
            "If it finished or expired, resubmit only when the operation is safe to repeat.",
        ),
    ),
}

_REQUEST_GUIDANCE: dict[str, RecoveryGuidance] = {
    "invalid_request": RecoveryGuidance(
        True,
        ("Correct parameters using the tool schema and validation message, then retry.",),
    ),
    "worksheet_block_shape_invalid": RecoveryGuidance(
        True,
        ("Make every row the same length and align it with the selected columns, then retry.",),
    ),
    "invalid_file_path": RecoveryGuidance(
        True,
        ("Use an existing file with an absolute or workspace-relative path, then retry.",),
    ),
    "unsupported_file_type": RecoveryGuidance(
        True,
        ("Convert the file to an accepted format or select a tool that supports its extension.",),
    ),
    "invalid_name": RecoveryGuidance(
        True,
        ("Choose a valid Origin object name using the error constraints, then retry.",),
    ),
    "path_not_allowed": RecoveryGuidance(
        True,
        (
            "Move the file under an allowed root or add its parent to ORIGIN_MCP_ALLOWED_ROOTS.",
            "Restart the MCP server after changing ORIGIN_MCP_ALLOWED_ROOTS, then retry.",
        ),
    ),
    "result_too_large": RecoveryGuidance(
        True,
        ("Request fewer rows, a smaller cell range, or a lower output_max_rows value.",),
    ),
    "confirmation_required": RecoveryGuidance(
        True,
        ("Review the destructive action, then use confirm=true only if the target is correct.",),
    ),
    "folder_not_empty": RecoveryGuidance(
        True,
        ("Inspect the folder; move/delete its contents or use recursive=true with confirmation.",),
    ),
    "object_already_exists": RecoveryGuidance(
        True,
        ("Choose a new object name or retry with overwrite=true when replacement is intended.",),
    ),
    "file_exists": RecoveryGuidance(
        True,
        ("Choose a new output path or retry with overwrite=true when replacement is intended.",),
    ),
    "empty_graph_created": RecoveryGuidance(
        True,
        (
            "Verify the selected columns contain data and their X/Y/Z roles match the plot type.",
            "Delete or reuse the empty graph, then retry with corrected data selections.",
        ),
    ),
}

_UNSUPPORTED_GUIDANCE: dict[str, RecoveryGuidance] = {
    "unsupported_origin_feature": RecoveryGuidance(
        False,
        (
            "Use a supported origin-mcp tool or workflow for this operation.",
            "If it needs Origin APIs, upgrade Origin and run `origin-mcp doctor --ping-origin`.",
        ),
    ),
    "unsupported_origin_version": RecoveryGuidance(
        False,
        ("Upgrade Origin or use the fallback workflow named in the error message.",),
    ),
    "origin_client_method_unavailable": RecoveryGuidance(
        False,
        (
            "Update the Origin bridge and origin-mcp package together so their methods match.",
            "Restart the bridge after updating, then run `origin-mcp doctor --ping-origin`.",
        ),
    ),
    "unsupported_bridge_method": RecoveryGuidance(
        False,
        ("Update the Origin bridge and origin-mcp package together, then restart the bridge.",),
    ),
    "unsupported_bridge_client_method": RecoveryGuidance(
        False,
        ("Update the Origin bridge and origin-mcp package together, then restart the bridge.",),
    ),
    "unsupported_bridge_task_method": RecoveryGuidance(
        False,
        ("Use one of the bridge task methods supported by the running bridge version.",),
    ),
    "xfunction_not_allowed": RecoveryGuidance(
        False,
        ("Choose an X-Function returned by origin_list_xfunctions or use a safer typed tool.",),
    ),
    "labtalk_unavailable": RecoveryGuidance(
        False,
        ("Use a typed tool, or update Origin/originpro to a version that exposes LabTalk.",),
    ),
    "graph_render_unavailable": RecoveryGuidance(
        False,
        ("Use origin_export_graph, or update Origin/originpro to enable in-memory rendering.",),
    ),
}

_DEPENDENCY_GUIDANCE = RecoveryGuidance(
    True,
    (
        "Run `origin-mcp doctor --ping-origin` and inspect the bridge status last_error field.",
        "Repair the missing Origin embedded-Python dependency, restart the bridge, and retry.",
    ),
)

_NOT_FOUND_GUIDANCE = RecoveryGuidance(
    True,
    (
        "Inspect the current Origin project objects and correct the referenced name or ID.",
        "Create or import the missing object before retrying the operation.",
    ),
)

_OPERATION_GUIDANCE = RecoveryGuidance(
    True,
    (
        "Inspect the live Origin session and bridge status last_error for the cause.",
        "Correct project state, then check for partial changes before retrying.",
    ),
)

_UNEXPECTED_GUIDANCE = RecoveryGuidance(
    False,
    (
        "Run `origin-mcp doctor --ping-origin` and inspect the MCP server and bridge logs.",
        "Retry only if safe; report the error code and log context if it persists.",
    ),
)


def recovery_guidance(error_code: str) -> RecoveryGuidance:
    """Return deterministic recovery guidance for any stable or future error code."""

    if error_code in _BRIDGE_GUIDANCE:
        return _BRIDGE_GUIDANCE[error_code]
    if error_code in _REQUEST_GUIDANCE:
        return _REQUEST_GUIDANCE[error_code]
    if error_code in _UNSUPPORTED_GUIDANCE:
        return _UNSUPPORTED_GUIDANCE[error_code]
    if error_code == "origin_dependency_unavailable":
        return _DEPENDENCY_GUIDANCE
    if error_code == "unsupported_analysis_type":
        return RecoveryGuidance(
            True,
            ("Choose a supported analysis type listed in the error message, then retry.",),
        )
    if error_code.endswith("_not_found") or error_code == "not_found":
        return _NOT_FOUND_GUIDANCE
    if error_code.startswith("unsupported_"):
        return RecoveryGuidance(
            False,
            ("Use a supported method or tool listed by the running origin-mcp version.",),
        )
    if error_code.endswith(("_failed", "_not_created")) or error_code in {
        "origin_bridge_failed",
        "origin_mcp_error",
    }:
        return _OPERATION_GUIDANCE
    return _UNEXPECTED_GUIDANCE
