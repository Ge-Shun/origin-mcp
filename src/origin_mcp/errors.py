from __future__ import annotations


class OriginMcpError(RuntimeError):
    """Base exception for expected origin-mcp failures.

    Subclasses carry a stable ``error_code`` string that the MCP layer surfaces
    to clients. Specific raise sites can override the default by passing
    ``error_code=`` explicitly; otherwise the subclass default is used.
    """

    DEFAULT_ERROR_CODE: str = "origin_mcp_error"

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code: str = error_code or self.DEFAULT_ERROR_CODE


class OriginDependencyError(OriginMcpError):
    """Raised when Origin automation dependencies are unavailable."""

    DEFAULT_ERROR_CODE = "origin_dependency_unavailable"


class OriginOperationError(OriginMcpError):
    """Raised when Origin rejects or cannot complete an operation."""

    DEFAULT_ERROR_CODE = "origin_operation_failed"


class OriginBridgeError(OriginMcpError):
    """Raised when the Origin GUI bridge cannot complete a request."""

    DEFAULT_ERROR_CODE = "origin_bridge_failed"

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message, error_code=error_code)
