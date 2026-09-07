"""Application settings via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env path ABSOLUTELY, anchored to this file's location, so it
# loads no matter what working directory the server is launched from.
# Layout: backend/src/cortex/config.py  →  backend/.env  is three parents up.
#   config.py → cortex/ → src/ → backend/
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absolute path — CWD-independent. Previously this was the relative
        # string ".env", which only loaded when the process happened to be
        # started from backend/. Launched from backend/src (the import root)
        # or the repo root, GITHUB_TOKEN silently stayed empty, so the GitHub
        # API ran unauthenticated at 60 req/hr and large repos stalled mid-fetch.
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SQLite — no Docker needed
    # File stored at backend/cortex.db
    database_url: str = "sqlite+aiosqlite:///./cortex.db"

    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cortexpass"
    github_token: str = ""
    nim_api_key: str = ""
    # Secret token required by internal-only endpoints (/complete, /fail).
    # Set INTERNAL_SECRET=<random-string> in .env.
    # If left empty those endpoints return 503 (disabled).
    internal_secret: str = ""
    # Authentication
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    # When True, the app is allowed to start with the insecure default
    # jwt_secret (developer convenience). MUST be False in production so a
    # forgeable signing key can never reach a deployed environment.
    allow_insecure_jwt_secret: bool = True
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    verification_token_expire_hours: int = 24
    password_reset_token_expire_hours: int = 1

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@cortex.dev"
    smtp_from_name: str = "Cortex"
    smtp_use_tls: bool = True
    # Frontend URL for building verification/reset links in emails
    frontend_url: str = "http://localhost:3000"

    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # ── Rate Limiting ────────────────────────────────────────────────────────
    # All limits are configurable via environment variables.
    # Rate limiting state is process-local and is not shared across multiple workers.

    # Global API: requests per minute per identity
    rate_limit_global_requests: int = 100
    rate_limit_global_window_seconds: int = 60

    # Job submission: requests per window per identity
    rate_limit_jobs_requests: int = 5
    rate_limit_jobs_window_seconds: int = 600  # 10 minutes

    # Concurrent running jobs per identity
    rate_limit_jobs_concurrent: int = 3

    # Chat messages per minute per identity
    rate_limit_chat_requests: int = 20
    rate_limit_chat_window_seconds: int = 60

    # Login attempts per window per IP
    rate_limit_login_requests: int = 5
    rate_limit_login_window_seconds: int = 900  # 15 minutes

    # Password reset per window per IP
    rate_limit_password_reset_requests: int = 3
    rate_limit_password_reset_window_seconds: int = 3600  # 1 hour

    # Email verification resend per window per IP
    rate_limit_verify_resend_requests: int = 3
    rate_limit_verify_resend_window_seconds: int = 900  # 15 minutes

    # ── Job watchdog ─────────────────────────────────────────────────────────
    # A job that has been RUNNING with NO status/progress update for longer
    # than this is considered orphaned — its in-process background task most
    # likely died — and is auto-failed when next read so the UI never polls a
    # "running" job forever.
    #
    # This measures time SINCE THE LAST update, not total runtime: the pipeline
    # writes progress as each stage starts (which bumps updated_at), and the
    # CPU-bound stages are offloaded to worker threads so the event loop keeps
    # serving those progress writes even during a heavy analysis. So a healthy
    # long-running analysis keeps resetting this clock; only a task that has
    # gone completely silent trips the watchdog. 5 minutes is well beyond any
    # single stage's expected quiet time while still failing dead jobs fast.
    job_stale_running_seconds: int = 300  # 5 minutes


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton.

    Wrapped in ``lru_cache`` so it is constructed once and so tests can reset
    it via ``get_settings.cache_clear()`` to pick up patched environment vars.
    """
    return Settings()
