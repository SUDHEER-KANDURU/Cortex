"""Shared chat repository singleton.

This is the single source of truth for the chat repository instance.
The chat router and ChatService import from here so they operate on
the same store. Same pattern as artifacts/infrastructure/dependencies.py.

To switch storage backends, change the import below — no other file
needs to change.
"""

from cortex.chat.infrastructure.pg_repository import PostgresChatRepository
from cortex.config import get_settings

# Single shared instance for the lifetime of the process.
chat_repository = PostgresChatRepository(get_settings().database_url)