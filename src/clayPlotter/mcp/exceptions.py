"""
Exceptions for the clayPlotter MCP server.
"""

class BaseError(Exception):
    """Base exception class for clayPlotter MCP server."""
    pass

class ConfigurationError(BaseError):
    """Exception raised for configuration errors."""
    pass

class ValidationError(BaseError):
    """Exception raised for validation errors."""
    pass

class MapGenerationError(BaseError):
    """Exception raised for map generation errors."""
    pass

class ResourceNotFoundError(BaseError):
    """Exception raised when a requested resource is not found."""
    pass