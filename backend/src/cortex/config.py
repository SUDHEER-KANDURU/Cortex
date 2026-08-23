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
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
