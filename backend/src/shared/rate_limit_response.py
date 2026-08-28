"""HTTP 429 response builder for rate-limited requests."""

import math

from fastapi import Response
from fastapi.responses import JSONResponse
from shared.rate_limiter import RateLimitResult


def rate_limit_response(result: RateLimitResult) -> JSONResponse:
    """Build a structured 429 response from a RateLimitResult."""
    retry_after = max(1, math.ceil(result.retry_after))
    return JSONResponse(
        status_code=429,
        content={
            "error": result.error_type,
            "message": result.message,
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
        },
    )


def add_rate_limit_headers(
    response: Response,
    remaining: int,
    window_seconds: int,
) -> None:
    """Add informational rate-limit headers to a successful response."""
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(window_seconds)
