"""Shared artifact repository singleton.

This is the single source of truth for the artifact repository instance.
Both the artifacts API router and pipeline stages import from here so they
operate on the same store.

To switch storage backends, change the import below — no other file needs
to change.
"""

from cortex.artifacts.infrastructure.pg_repository import (
    PostgresArtifactRepository,
)
from cortex.config import get_settings

# Single shared instance for the lifetime of the process.
artifact_repository = PostgresArtifactRepository(get_settings().database_url)
