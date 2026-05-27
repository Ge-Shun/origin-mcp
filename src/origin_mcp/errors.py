class OriginMcpError(RuntimeError):
    """Base exception for expected origin-mcp failures."""


class OriginDependencyError(OriginMcpError):
    """Raised when Origin automation dependencies are unavailable."""


class OriginOperationError(OriginMcpError):
    """Raised when Origin rejects or cannot complete an operation."""


class OriginBridgeError(OriginMcpError):
    """Raised when the Origin GUI bridge cannot complete a request."""

    def __init__(self, message: str, error_code: str = "origin_bridge_failed") -> None:
        super().__init__(message)
        self.error_code = error_code
