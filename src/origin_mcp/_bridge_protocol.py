from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .errors import OriginMcpError
from .refs import GraphRef, WorksheetRef


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        json.dumps(value, allow_nan=False)
        return value
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [json_safe(item) for item in value]
        return str(value)


def restore_bridge_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__origin_mcp_type__") == "Path":
            return Path(str(value["value"]))
        return {key: restore_bridge_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [restore_bridge_value(item) for item in value]
    return value


def serialize_bridge_value(value: Any) -> Any:
    if isinstance(value, WorksheetRef):
        return {"__origin_mcp_type__": "WorksheetRef", "data": value.as_dict()}
    if isinstance(value, GraphRef):
        return {"__origin_mcp_type__": "GraphRef", "data": value.as_dict()}
    if isinstance(value, Path):
        return {"__origin_mcp_type__": "Path", "value": str(value)}
    if isinstance(value, dict):
        return {str(key): serialize_bridge_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_bridge_value(item) for item in value]
    return value


def public_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return json_safe(value)
    if isinstance(value, WorksheetRef):
        return {"worksheet": value.as_dict()}
    if isinstance(value, GraphRef):
        return {"graph": value.as_dict()}
    return {"result": json_safe(serialize_bridge_value(value))}


def error_code(exc: Exception) -> str:
    if isinstance(exc, OriginMcpError):
        return exc.error_code
    return "unexpected_error"
