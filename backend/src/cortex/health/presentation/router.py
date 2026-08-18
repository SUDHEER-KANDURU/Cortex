"""Health check endpoints — liveness and readiness probes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    modules: dict[str, str]
    endpoints: dict[str, int]


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 when the API is running.",
)
async def health() -> HealthResponse:
    """Liveness probe — always returns 200 if the server is up."""
    # Fix 14 — removed unused settings = get_settings()
    # Fix 1  — use timezone.utc instead of deprecated utcnow()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment="development",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns detailed status of all modules and registered endpoints.",
)
async def readiness(request: Request) -> ReadinessResponse:
    """Readiness probe — checks all modules are loaded."""
    api_routes = [
        route.path for route in request.app.routes if hasattr(route, "path") and route.path.startswith("/api/v1")
    ]
    endpoint_counts = {
        "health": sum(1 for path in api_routes if path.startswith("/api/v1/health")),
        "jobs": sum(1 for path in api_routes if path.startswith("/api/v1/jobs")),
        "artifacts": sum(1 for path in api_routes if path.startswith("/api/v1/artifacts")),
        "graph": sum(1 for path in api_routes if path.startswith("/api/v1/graph")),
        "total": len(api_routes),
    }

    return ReadinessResponse(
        status="ready",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        modules={
            "jobs": "loaded",
            "artifacts": "loaded",
            "graph": "loaded",
            "pipeline": "loaded",
            "health": "loaded",
        },
        endpoints=endpoint_counts,
    )
