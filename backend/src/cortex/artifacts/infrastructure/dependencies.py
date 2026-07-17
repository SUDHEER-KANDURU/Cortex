"""Shared artifact repository singleton.

Both the artifacts API router and the pipeline stages import from here
so they operate on the same in-memory store.  When we switch to
PostgreSQL in Week 4, only this file changes.
"""

from cortex.artifacts.infrastructure.repository import (
    InMemoryArtifactRepository,
)

# Single shared instance for the lifetime of the process.
artifact_repository = InMemoryArtifactRepository()
