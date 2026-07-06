"""In-memory job repository — used until PostgreSQL is wired in Week 4.
Implements AbstractJobRepository exactly. Zero database code."""

from datetime import datetime
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.domain.interfaces import AbstractJobRepository
from shared.exceptions import NotFoundError

# Module-level store so data persists across requests in the same process
_store: dict[str, Job] = {}


class InMemoryJobRepository(AbstractJobRepository):

    async def save(self, job: Job) -> Job:
        _store[job.id] = job
        return job

    async def get_by_id(self, job_id: str) -> Job | None:
        return _store.get(job_id)

    async def get_all(self) -> list[Job]:
        return sorted(
            _store.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )

    async def get_by_status(self, status: JobStatus) -> list[Job]:
        return [j for j in _store.values() if j.status == status]

    async def get_by_repo_url(self, repo_url: str) -> list[Job]:
        return [j for j in _store.values() if j.repo_url == repo_url]

    async def get_by_artifact_type(
        self, artifact_type: ArtifactType
    ) -> list[Job]:
        return [
            j for j in _store.values()
            if j.artifact_type == artifact_type
        ]

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: str | None = None,
    ) -> Job:
        job = _store.get(job_id)
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        job.status = status
        job.updated_at = datetime.utcnow()
        if error_message:
            job.error_message = error_message
        return job

    async def delete(self, job_id: str) -> None:
        if job_id not in _store:
            raise NotFoundError(f"Job not found: {job_id}")
        del _store[job_id]

    async def count_by_status(self) -> dict[JobStatus, int]:
        counts: dict[JobStatus, int] = {s: 0 for s in JobStatus}
        for job in _store.values():
            counts[job.status] += 1
        return counts