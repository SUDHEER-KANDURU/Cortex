"""Abstract repository and service interfaces for the artifacts domain."""

from abc import ABC, abstractmethod
from cortex.artifacts.domain.entities import Artifact, ArtifactContentType


class AbstractArtifactRepository(ABC):

    @abstractmethod
    async def save(self, artifact: Artifact) -> Artifact:
        """Persist a new artifact and return it."""
        ...

    @abstractmethod
    async def get_by_id(self, artifact_id: str) -> Artifact | None:
        """Return an artifact by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def get_by_job_id(self, job_id: str) -> list[Artifact]:
        """Return all artifacts for a given job ID."""
        ...

    @abstractmethod
    async def get_by_content_type(
        self,
        content_type: ArtifactContentType,
    ) -> list[Artifact]:
        """Return all artifacts of a specific content type."""
        ...

    @abstractmethod
    async def delete_by_job_id(self, job_id: str) -> int:
        """Delete all artifacts for a job. Returns count deleted."""
        ...

    @abstractmethod
    async def delete(self, artifact_id: str) -> None:
        """Delete a single artifact by ID."""
        ...

    @abstractmethod
    async def count_by_job_id(self, job_id: str) -> int:
        """Return count of artifacts for a given job."""
        ...


class AbstractArtifactService(ABC):

    @abstractmethod
    async def create(
        self,
        job_id: str,
        artifact_type: str,
        content_type: ArtifactContentType,
        content_inline: str | None = None,
        storage_path: str | None = None,
    ) -> Artifact:
        """Create and persist a new artifact for a job."""
        ...

    @abstractmethod
    async def get(self, artifact_id: str) -> Artifact:
        """Return an artifact by ID. Raises NotFoundError if missing."""
        ...

    @abstractmethod
    async def list_for_job(self, job_id: str) -> list[Artifact]:
        """Return all artifacts for a given job."""
        ...

    @abstractmethod
    async def delete(self, artifact_id: str) -> None:
        """Delete a single artifact."""
        ...

    @abstractmethod
    async def delete_all_for_job(self, job_id: str) -> int:
        """Delete all artifacts for a job. Returns count deleted."""
        ...