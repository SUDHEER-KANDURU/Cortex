"""Cortex domain exception hierarchy."""


class CortexError(Exception):
    """Base error for all Cortex exceptions."""


class NotFoundError(CortexError):
    """Raised when a requested resource does not exist."""


class ValidationError(CortexError):
    """Raised when input data fails domain validation."""


class InfrastructureError(CortexError):
    """Raised when a database or external service call fails."""
