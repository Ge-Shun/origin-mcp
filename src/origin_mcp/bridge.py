from __future__ import annotations

import argparse
import os
import sys

from . import _bridge_dispatch, _bridge_protocol
from ._bridge_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    OriginBridgeHandler,
    OriginBridgeServer,
    OriginEmbeddedBridgeServer,
)
from ._bridge_tasks import (
    DEFAULT_MAX_TASKS,
    TERMINAL_TASK_STATUSES,
    BridgeTask,
    BridgeTaskManager,
)

ALLOWED_CLIENT_METHODS = _bridge_dispatch.ALLOWED_CLIENT_METHODS
TASKABLE_METHODS = _bridge_dispatch.TASKABLE_METHODS
_call_client_method = _bridge_dispatch.call_client_method
_call_origin_method = _bridge_dispatch.call_origin_method
_coerce_path_args = _bridge_dispatch.coerce_path_args

_error_code = _bridge_protocol.error_code
_json_safe = _bridge_protocol.json_safe
_public_result = _bridge_protocol.public_result
_restore_bridge_value = _bridge_protocol.restore_bridge_value
_serialize_bridge_value = _bridge_protocol.serialize_bridge_value

__all__ = [
    "ALLOWED_CLIENT_METHODS",
    "DEFAULT_HOST",
    "DEFAULT_MAX_TASKS",
    "DEFAULT_PORT",
    "TASKABLE_METHODS",
    "TERMINAL_TASK_STATUSES",
    "BridgeTask",
    "BridgeTaskManager",
    "OriginBridgeHandler",
    "OriginBridgeServer",
    "OriginEmbeddedBridgeServer",
    "_call_client_method",
    "_call_origin_method",
    "_coerce_path_args",
    "_error_code",
    "_json_safe",
    "_public_result",
    "_restore_bridge_value",
    "_serialize_bridge_value",
    "main",
    "serve",
]


def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token: str | None = None,
    max_tasks: int = DEFAULT_MAX_TASKS,
) -> None:
    with OriginBridgeServer((host, port), token=token, max_tasks=max_tasks) as server:
        # typeshed types ``server_address`` as a sockaddr that may have >2
        # fields; index instead of unpacking to stay type-clean for AF_INET.
        bound = server.server_address
        actual_host, actual_port = str(bound[0]), bound[1]
        print(
            f"origin-mcp-bridge listening on {actual_host}:{actual_port}",
            file=sys.stderr,
            flush=True,
        )
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the optional origin-mcp GUI bridge.")
    parser.add_argument("--host", default=os.environ.get("ORIGIN_MCP_BRIDGE_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ORIGIN_MCP_BRIDGE_PORT", DEFAULT_PORT)),
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("ORIGIN_MCP_BRIDGE_TOKEN"),
        help="Optional shared token required from MCP bridge clients.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=int(os.environ.get("ORIGIN_MCP_BRIDGE_MAX_TASKS", DEFAULT_MAX_TASKS)),
        help="Maximum number of bridge task records to retain.",
    )
    args = parser.parse_args()
    serve(host=args.host, port=args.port, token=args.token, max_tasks=args.max_tasks)


if __name__ == "__main__":
    main()
