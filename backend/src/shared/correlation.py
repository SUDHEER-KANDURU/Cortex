"""Middleware to attach a correlation_id to every request."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach X-Correlation-ID header to every request and response."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Correlation-ID"] = correlation_id
        structlog.contextvars.clear_contextvars()
        return response
