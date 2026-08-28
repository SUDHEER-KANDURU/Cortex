"""Centralized identity resolution for rate limiting.

Resolves the strongest available identity in this order:
1. Authenticated user ID (from JWT)
2. Client IP address (from request.client.host)

Does NOT trust arbitrary X-Forwarded-For headers in the current
single-process deployment. When a reverse proxy is introduced,
this module should be updated to read from a configured trusted header.
"""

from fastapi import Request


def resolve_identity(request: Request) -> str:
    """Extract the rate-limiting identity key from a request.

    Priority:
    1. Authenticated user ID (set by auth middleware/dependency via request.state)
    2. Client IP address

    Returns a string key suitable for use as a rate limiter bucket key.
    """
    # Check if auth dependency has attached a user to request state
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to client IP
    return f"ip:{_get_client_ip(request)}"


def resolve_ip_identity(request: Request) -> str:
    """Extract IP-only identity (for auth endpoints where no user is known yet)."""
    return f"ip:{_get_client_ip(request)}"


def _get_client_ip(request: Request) -> str:
    """Get client IP from the request.

    In the current single-process local deployment, we use request.client.host
    directly. We do NOT trust X-Forwarded-For or similar headers because there
    is no configured reverse proxy.

    When a reverse proxy is added, update this to read the trusted header.
    """
    if request.client:
        return request.client.host
    return "unknown"
