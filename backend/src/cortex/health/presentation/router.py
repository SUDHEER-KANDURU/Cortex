"""Health check endpoint — GET /api/v1/health."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — returns 200 when the API is running."""
    return HealthResponse(status="ok")
