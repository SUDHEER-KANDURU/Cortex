"""Artifacts application layer — all business logic lives here."""

from cortex.artifacts.domain.entities import Artifact, ArtifactContentType
from cortex.artifacts.domain.interfaces import (
    AbstractArtifactRepository,
    AbstractArtifactService,
)
from shared.exceptions import NotFoundError, ValidationError
import structlog

logger = structlog.get_logger()


class ArtifactService(AbstractArtifactService):

    def __init__(self, repository: AbstractArtifactRepository) -> None:
        self._repo = repository

    async def create(
        self,
        job_id: str,
        artifact_type: str,
        content_type: ArtifactContentType,
        content_inline: str | None = None,
        storage_path: str | None = None,
    ) -> Artifact:
        """Create and persist a new artifact."""
        if not content_inline and not storage_path:
            raise ValidationError(
                "Artifact must have either content_inline or storage_path."
            )

        artifact = Artifact(
            job_id=job_id,
            artifact_type=artifact_type,
            content_type=content_type,
            content_inline=content_inline,
            storage_path=storage_path,
        )

        saved = await self._repo.save(artifact)

        logger.info(
            "artifact_created",
            artifact_id=saved.id,
            job_id=job_id,
            artifact_type=artifact_type,
            content_type=content_type.value,
        )

        return saved

    async def get(self, artifact_id: str) -> Artifact:
        """Return an artifact by ID. Raises NotFoundError if missing."""
        artifact = await self._repo.get_by_id(artifact_id)
        if not artifact:
            raise NotFoundError(f"Artifact not found: {artifact_id}")
        return artifact

    async def list_for_job(self, job_id: str) -> list[Artifact]:
        """Return all artifacts for a given job."""
        return await self._repo.get_by_job_id(job_id)

    async def delete(self, artifact_id: str) -> None:
        """Delete a single artifact."""
        await self.get(artifact_id)
        await self._repo.delete(artifact_id)
        logger.info("artifact_deleted", artifact_id=artifact_id)

    async def delete_all_for_job(self, job_id: str) -> int:
        """Delete all artifacts for a job. Returns count deleted."""
        count = await self._repo.delete_by_job_id(job_id)
        logger.info(
            "artifacts_deleted_for_job",
            job_id=job_id,
            count=count,
        )
        return count