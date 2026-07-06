"""In-memory artifact repository — used until PostgreSQL in Week 4."""

from cortex.artifacts.domain.entities import Artifact, ArtifactContentType
from cortex.artifacts.domain.interfaces import AbstractArtifactRepository
from shared.exceptions import NotFoundError

_store: dict[str, Artifact] = {}


class InMemoryArtifactRepository(AbstractArtifactRepository):

    async def save(self, artifact: Artifact) -> Artifact:
        _store[artifact.id] = artifact
        return artifact

    async def get_by_id(self, artifact_id: str) -> Artifact | None:
        return _store.get(artifact_id)

    async def get_by_job_id(self, job_id: str) -> list[Artifact]:
        return [
            a for a in _store.values() if a.job_id == job_id
        ]

    async def get_by_content_type(
        self,
        content_type: ArtifactContentType,
    ) -> list[Artifact]:
        return [
            a for a in _store.values()
            if a.content_type == content_type
        ]

    async def delete_by_job_id(self, job_id: str) -> int:
        to_delete = [
            k for k, v in _store.items() if v.job_id == job_id
        ]
        for key in to_delete:
            del _store[key]
        return len(to_delete)

    async def delete(self, artifact_id: str) -> None:
        if artifact_id not in _store:
            raise NotFoundError(f"Artifact not found: {artifact_id}")
        del _store[artifact_id]

    async def count_by_job_id(self, job_id: str) -> int:
        return sum(1 for a in _store.values() if a.job_id == job_id)