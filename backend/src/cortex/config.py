"""Application settings via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
