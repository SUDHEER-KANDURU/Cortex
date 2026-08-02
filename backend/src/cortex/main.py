"""Cortex FastAPI application factory."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cortex.config import get_settings
from cortex.health.presentation.router import router as health_router
from cortex.jobs.presentation.router import router as jobs_router
from cortex.artifacts.presentation.router import router as artifacts_router
from cortex.graph.presentation.router import router as graph_router
from shared.correlation import CorrelationMiddleware
from shared.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup, then reset orphaned jobs."""
    from cortex.schema.models import Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import update as sa_update
    from cortex.schema.models import JobModel

    settings = get_settings()

    connect_args = {}
    if "sqlite" in settings.database_url:
        connect_args = {"check_same_thread": False}

    engine = create_async_engine(settings.database_url, connect_args=connect_args)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Reset jobs stuck in running/pending from a previous process —
        # their background tasks died and will never complete.
        await conn.execute(
            sa_update(JobModel)
            .where(JobModel.status.in_(["running", "pending"]))
            .values(
                status="failed",
                error_message="Server restarted — job was lost. Please resubmit.",
                updated_at=datetime.now(timezone.utc),  # Fix 1
            )
        )
    await engine.dispose()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Cortex API",
        description="Engineering Reasoning Engine — Understand Code. Learn Engineering.",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")

    return app


app = create_app()
