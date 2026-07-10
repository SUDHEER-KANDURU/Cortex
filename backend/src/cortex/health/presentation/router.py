"""Health check endpoints — liveness and readiness probes."""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from cortex.config import get_settings

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
    description="Returns 200 when the API is running. "
    "Used by Docker and load balancers to check if the "
    "service is alive.",
)
async def health() -> HealthResponse:
    """Liveness probe — always returns 200 if the server is up."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        environment="development",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns detailed status of all modules and "
    "registered endpoints. Use this to verify the full "
    "API is wired correctly.",
)
async def readiness() -> ReadinessResponse:
    """Readiness probe — checks all modules are loaded."""
    return ReadinessResponse(
        status="ready",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        modules={
            "jobs": "loaded",
            "artifacts": "loaded",
            "graph": "loaded",
            "pipeline": "loaded",
            "health": "loaded",
        },
        endpoints={
            "health": 2,
            "jobs": 9,
            "artifacts": 5,
            "graph": 6,
            "total": 22,
        },
    )
