class OriginMcpError(RuntimeError):
    """Base exception for expected origin-mcp failures."""


class OriginDependencyError(OriginMcpError):
    """Raised when Origin automation dependencies are unavailable."""


class OriginOperationError(OriginMcpError):
    """Raised when Origin rejects or cannot complete an operation."""
