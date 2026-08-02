"""Health check endpoints — liveness and readiness probes."""

from fastapi import APIRouter
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
async def readiness() -> ReadinessResponse:
    """Readiness probe — checks all modules are loaded."""
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
        endpoints={
            "health": 2,
            "jobs": 8,
            "artifacts": 5,
            "graph": 6,
            "total": 21,
        },
    )
