"""Shared repository-memory repository singleton.

Same pattern as chat/infrastructure/dependencies.py and
artifacts/infrastructure/dependencies.py — a single shared instance so
the router and summarizer operate on the same store.
"""

from cortex.memory.infrastructure.sqlite_repository import SQLiteMemoryRepository
from cortex.config import get_settings

memory_repository = SQLiteMemoryRepository(get_settings().database_url)