"""Shared job repository singleton.

Single source of truth for the job repository instance.
The jobs router, ChatService, and any other module that needs to look up
jobs should import from here — not construct their own PostgresJobRepository
and engine. Same pattern as artifacts/chat/memory infrastructure/dependencies.py.

To switch storage backends, change the import below — no other file needs
to change.
"""

from cortex.jobs.infrastructure.pg_repository import PostgresJobRepository
from cortex.config import get_settings

# Single shared instance for the lifetime of the process.
job_repository = PostgresJobRepository(get_settings().database_url)
