"""Cortex FastAPI application factory."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cortex.config import get_settings
from cortex.health.presentation.router import router as health_router
from cortex.jobs.presentation.router import router as jobs_router
from cortex.artifacts.presentation.router import router as artifacts_router
from cortex.graph.presentation.router import router as graph_router
from cortex.insights.presentation.router import router as insights_router
from cortex.chat.presentation.router import router as chat_router
from cortex.memory.presentation.router import router as memory_router
from cortex.diagrams.router import router as diagrams_router
from cortex.search.router import router as search_router
from cortex.overview.router import router as overview_router
from cortex.auth.presentation.router import router as auth_router
from cortex.reasoning.presentation.router import router as reasoning_router
from cortex.navigate.router import router as navigate_router
from shared.correlation import CorrelationMiddleware
from shared.logging import configure_logging
from shared.rate_limit_middleware import RateLimitMiddleware

_startup_logger = structlog.get_logger()

#: The placeholder shipped in config defaults. Signing tokens with this key
#: lets anyone forge a valid JWT for any user, so the app must refuse to start
#: with it unless the operator has explicitly opted into insecure dev mode.
_INSECURE_JWT_SECRET = "change-me-in-production"


class InsecureConfigurationError(RuntimeError):
    """Raised at startup when the app is configured with an unsafe default that
    would create a critical security hole in a real deployment."""


def _enforce_secure_secrets(settings) -> None:  # type: ignore[type-arg]
    """Fail fast on configuration that is catastrophic in production.

    The default ``jwt_secret`` is a public placeholder. If it reaches a
    deployed environment, JWTs can be forged for any account (full takeover).
    We refuse to boot with it unless ``allow_insecure_jwt_secret`` is True
    (the developer-convenience default for local work).
    """
    if settings.jwt_secret == _INSECURE_JWT_SECRET:
        if settings.allow_insecure_jwt_secret:
            _startup_logger.warning(
                "config_insecure_jwt_secret",
                effect="Using the DEFAULT jwt_secret. Tokens can be forged. "
                       "This is allowed only because ALLOW_INSECURE_JWT_SECRET "
                       "is true. Set a strong JWT_SECRET and "
                       "ALLOW_INSECURE_JWT_SECRET=false before deploying.",
            )
        else:
            raise InsecureConfigurationError(
                "Refusing to start: jwt_secret is the built-in default "
                "'change-me-in-production'. Set a strong JWT_SECRET in the "
                "environment. (For local development only, set "
                "ALLOW_INSECURE_JWT_SECRET=true.)"
            )


def _warn_missing_secrets(settings) -> None:  # type: ignore[type-arg]
    """Emit structured warnings for configuration that will cause silent
    degradation at runtime. Called once at startup so the operator sees
    the problem immediately rather than discovering it mid-job.

    Missing github_token  → GitHub API limited to 60 req/hr (unauthenticated).
                            Large repos or rapid submissions will hit rate limits.
    Missing nim_api_key   → Chat falls back to the rule-based stub; no real AI.
    Missing internal_secret → /complete and /fail endpoints are disabled (503).
    """
    if not settings.github_token:
        _startup_logger.warning(
            "config_missing_github_token",
            effect="GitHub API running unauthenticated (60 req/hr limit). "
                   "Set GITHUB_TOKEN in backend/.env to raise limit to 5000 req/hr.",
        )
    if not settings.nim_api_key:
        _startup_logger.info(
            "config_missing_nim_api_key",
            effect="NIM API key not set. Cortex still produces its own deterministic, "
                   "evidence-grounded explanations and chat answers; NIM only refines "
                   "wording when a key is present. Set NIM_API_KEY in backend/.env to "
                   "enable optional AI refinement.",
        )
    if not settings.internal_secret:
        _startup_logger.warning(
            "config_missing_internal_secret",
            effect="INTERNAL_SECRET not set. "
                   "POST /jobs/{id}/complete and /fail endpoints are disabled (503). "
                   "Set INTERNAL_SECRET in backend/.env to enable them.",
        )


def _ensure_user_id_columns(connection) -> None:  # type: ignore[no-untyped-def]
    """Add the `user_id` column to `jobs` and `chat_sessions` on databases
    created before multi-user isolation existed.

    Runs synchronously inside `conn.run_sync`. Uses the SQLAlchemy inspector
    to check existing columns so it is safe to run on every startup and on a
    fresh DB alike. Only handles the additive column case (SQLite supports
    `ALTER TABLE ... ADD COLUMN`). Postgres accepts the same DDL.
    """
    from sqlalchemy import inspect as sa_inspect, text

    inspector = sa_inspect(connection)
    existing_tables = set(inspector.get_table_names())

    for table in ("jobs", "chat_sessions"):
        if table not in existing_tables:
            continue  # create_all already made it with user_id
        columns = {col["name"] for col in inspector.get_columns(table)}
        if "user_id" not in columns:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(36)")
            )
            _startup_logger.info("migration_added_user_id_column", table=table)

    # Additive migration for live job progress columns (P1-6) on pre-existing
    # databases. Safe to run on every startup — skips columns already present.
    if "jobs" in existing_tables:
        job_columns = {col["name"] for col in inspector.get_columns("jobs")}
        if "progress_stage" not in job_columns:
            connection.execute(
                text("ALTER TABLE jobs ADD COLUMN progress_stage VARCHAR(120)")
            )
            _startup_logger.info("migration_added_progress_stage_column", table="jobs")
        if "progress_percent" not in job_columns:
            connection.execute(
                text("ALTER TABLE jobs ADD COLUMN progress_percent INTEGER DEFAULT 0")
            )
            _startup_logger.info("migration_added_progress_percent_column", table="jobs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup, then reset orphaned jobs."""
    from cortex.schema.models import Base
    from cortex.db import get_engine
    from sqlalchemy import update as sa_update
    from cortex.schema.models import JobModel

    settings = get_settings()

    # Fail fast on catastrophic misconfiguration (e.g. default JWT secret)
    # BEFORE any tables are created or requests are served.
    _enforce_secure_secrets(settings)

    # Use the shared engine singleton — avoids a separate pool just for startup.
    engine = get_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration: create_all() never ALTERs existing tables,
        # so add the user_id ownership columns to pre-multi-user databases.
        # Idempotent — skips columns that already exist.
        await conn.run_sync(_ensure_user_id_columns)
        # Reset jobs stuck in running/pending from a previous process —
        # their background tasks died and will never complete.
        await conn.execute(
            sa_update(JobModel)
            .where(JobModel.status.in_(["running", "pending"]))
            .values(
                status="failed",
                error_message="Server restarted — job was lost. Please resubmit.",
                updated_at=datetime.now(timezone.utc),
            )
        )
    # No engine.dispose() here — the shared singleton must stay alive
    # for the lifetime of the process.

    # Create FTS5 virtual tables for search
    from cortex.search.fts_engine import FTSEngine
    fts = FTSEngine(settings.database_url)
    await fts.ensure_fts_tables()

    # Create incremental analysis table
    from cortex.pipeline.infrastructure.incremental_analyzer import IncrementalAnalyzer
    incremental = IncrementalAnalyzer(settings.database_url)
    await incremental.ensure_table()

    # Warn about any missing secrets/config that cause silent degradation.
    _warn_missing_secrets(settings)

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
    app.add_middleware(RateLimitMiddleware)
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
    app.include_router(insights_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(diagrams_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(overview_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(reasoning_router, prefix="/api/v1")
    app.include_router(navigate_router, prefix="/api/v1")

    return app


app = create_app()
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
