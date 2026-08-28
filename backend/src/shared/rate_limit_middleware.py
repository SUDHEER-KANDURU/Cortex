"""Global rate-limit middleware for the Cortex API.

Applies the global rate limiter to all requests except health/readiness
endpoints and internal pipeline callbacks. Endpoint-specific limiters
(jobs, chat, auth) are applied separately and are stricter.

Rate limiting state is process-local and is not shared across multiple workers.
"""

import math

from shared.identity import resolve_identity
from shared.rate_limiters import get_global_limiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths excluded from global rate limiting
_EXCLUDED_PREFIXES = (
    "/api/v1/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global API rate-limit middleware.

    Checks the global rate limiter for every non-excluded request.
    Sets request.state.user_id if an Authorization header is present
    (decoded by identity resolution for downstream use).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
            return await call_next(request)

        # Ensure request.state has a user_id attribute for identity resolution
        if not hasattr(request.state, "user_id"):
            request.state.user_id = None

        # Try to extract user_id from Authorization header for identity keying
        # (Lightweight parse — full JWT validation happens in endpoint deps)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer ") and len(auth_header) > 20:
            try:
                from cortex.config import get_settings
                from jose import jwt as jose_jwt

                settings = get_settings()
                token = auth_header[7:]
                payload = jose_jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_exp": False},  # Don't fail here on expiry
                )
                user_id = payload.get("sub")
                if user_id and payload.get("type") == "access":
                    request.state.user_id = user_id
            except Exception:
                pass  # Token invalid — fall through to IP-based identity

        # Apply global rate limit
        identity = resolve_identity(request)
        limiter = get_global_limiter()
        result = await limiter.check(identity)

        if not result.allowed:
            retry_after = max(1, math.ceil(result.retry_after))
            return JSONResponse(
                status_code=429,
                content={
                    "error": result.error_type,
                    "message": result.message,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Add rate-limit info headers to successful responses
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
