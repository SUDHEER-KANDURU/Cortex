"""Shared SQLAlchemy async engine singleton.

All repositories in this process should use this engine instead of
creating their own — a single connection pool to the same SQLite file
is both cheaper and avoids SQLITE_BUSY contention under concurrent
writes.

Usage (in any repository __init__):
    from cortex.db import get_engine
    self._engine = get_engine(database_url)

Because get_engine is @lru_cache on the URL string, the same URL always
returns the same engine object regardless of how many repositories call
it. Repositories still own their async_sessionmaker — they just share
the underlying pool.
"""

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from cortex.config import get_settings


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> AsyncEngine:
    """Return a cached AsyncEngine for the given database URL.

    SQLite requires check_same_thread=False for async use.
    All other settings (echo, pool_size, etc.) can be tuned here
    without touching every individual repository.
    """
    connect_args: dict = {}
    if "sqlite" in database_url:
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
    )


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session using the shared engine."""
    settings = get_settings()
    engine = get_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    async with async_session() as session:
        yield session
