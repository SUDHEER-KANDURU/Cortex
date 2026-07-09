"""Cortex FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cortex.config import get_settings
from cortex.health.presentation.router import router as health_router
from cortex.jobs.presentation.router import router as jobs_router
from cortex.artifacts.presentation.router import router as artifacts_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Cortex API",
        description="Engineering Reasoning Engine",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,@
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")

    from cortex.graph.presentation.router import router as graph_router
    app.include_router(graph_router, prefix="/api/v1")

    return app


app = create_app()