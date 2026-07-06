"""Jobs application layer — all business logic lives here.
The router calls this. This calls the repository.
Nothing here knows about HTTP or databases directly."""

import uuid
from datetime import datetime
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.domain.interfaces import (
    AbstractJobRepository,
    AbstractJobService,
)
from shared.exceptions import NotFoundError, ValidationError
import structlog

logger = structlog.get_logger()


class JobService(AbstractJobService):
    """Concrete implementation of AbstractJobService.
    Injected with a repository at construction time —
    never instantiates storage directly."""

    def __init__(self, repository: AbstractJobRepository) -> None:
        self._repo = repository

    async def submit(
        self,
        repo_url: str,
        artifact_type: ArtifactType,
        options: dict[str, str] | None = None,
    ) -> Job:
        """Validate, create, persist, and queue a new job."""
        if "github.com" not in repo_url:
            raise ValidationError(
                f"repo_url must be a GitHub URL, got: {repo_url}"
            )

        repo_url = repo_url.rstrip("/")

        job = Job(
            id=str(uuid.uuid4()),
            repo_url=repo_url,
            artifact_type=artifact_type,
            options=options,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        saved = await self._repo.save(job)

        logger.info(
            "job_submitted",
            job_id=saved.id,
            repo_url=repo_url,
            artifact_type=artifact_type.value,
        )

        # Celery dispatch added in Week 9
        # from worker.celery_app import celery_app
        # celery_app.send_task("analyze_repo", args=[saved.id])

        return saved

    async def get(self, job_id: str) -> Job:
        """Return a job by ID. Raises NotFoundError if missing."""
        job = await self._repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        return job

    async def list_all(self) -> list[Job]:
        """Return all jobs, newest first."""
        return await self._repo.get_all()

    async def list_by_status(self, status: JobStatus) -> list[Job]:
        """Return jobs filtered by status."""
        return await self._repo.get_by_status(status)

    async def list_by_repo(self, repo_url: str) -> list[Job]:
        """Return all jobs for a specific repository."""
        return await self._repo.get_by_repo_url(repo_url)

    async def cancel(self, job_id: str) -> Job:
        """Cancel a pending or running job."""
        job = await self.get(job_id)

        if not job.can_cancel():
            raise ValidationError(
                f"Cannot cancel job with status '{job.status.value}'. "
                f"Only pending or running jobs can be cancelled."
            )

        updated = await self._repo.update_status(
            job_id=job.id,
            status=JobStatus.CANCELLED,
        )

        logger.info("job_cancelled", job_id=job_id)
        return updated

    async def retry(self, job_id: str) -> Job:
        """Retry a failed job by creating a new one with same params."""
        original = await self.get(job_id)

        if not original.can_retry():
            raise ValidationError(
                f"Cannot retry job with status '{original.status.value}'. "
                f"Only failed jobs can be retried."
            )

        return await self.submit(
            repo_url=original.repo_url,
            artifact_type=original.artifact_type,
            options=original.options,
        )

    async def mark_running(self, job_id: str) -> Job:
        """Called by the Celery worker when it starts processing."""
        job = await self.get(job_id)

        if job.status != JobStatus.PENDING:
            raise ValidationError(
                f"Cannot mark job as running — current status: "
                f"'{job.status.value}'"
            )

        updated = await self._repo.update_status(
            job_id=job_id,
            status=JobStatus.RUNNING,
        )

        logger.info("job_running", job_id=job_id)
        return updated

    async def mark_completed(self, job_id: str) -> Job:
        """Called by the Celery worker when processing succeeds."""
        job = await self.get(job_id)

        if job.status != JobStatus.RUNNING:
            raise ValidationError(
                f"Cannot mark job as completed — current status: "
                f"'{job.status.value}'"
            )

        updated = await self._repo.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
        )

        logger.info("job_completed", job_id=job_id)
        return updated

    async def mark_failed(self, job_id: str, error: str) -> Job:
        """Called by the Celery worker when processing fails."""
        await self.get(job_id)

        updated = await self._repo.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_message=error,
        )

        logger.error("job_failed", job_id=job_id, error=error)
        return updated

    async def get_stats(self) -> dict[JobStatus, int]:
        """Return job counts by status for the health dashboard."""
        return await self._repo.count_by_status()