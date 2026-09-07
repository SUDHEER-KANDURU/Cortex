"""Jobs application layer — all business logic lives here.
The router calls this. This calls the repository.
Nothing here knows about HTTP or databases directly."""

import uuid
from datetime import datetime, timezone
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.domain.interfaces import (
    AbstractJobRepository,
    AbstractJobService,
)
from shared.exceptions import NotFoundError, ValidationError
import structlog

logger = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobService(AbstractJobService):
    """Concrete implementation of AbstractJobService.
    Injected with a repository at construction time —
    never instantiates storage directly."""

    def __init__(self, repository: AbstractJobRepository) -> None:
        self._repo = repository

    def _is_stale_running(self, job: Job) -> bool:
        """True if a RUNNING job hasn't advanced for longer than the watchdog
        window — meaning its in-process background task almost certainly died
        and the job would otherwise stay 'running' forever."""
        if job.status != JobStatus.RUNNING:
            return False
        from cortex.config import get_settings
        timeout = get_settings().job_stale_running_seconds
        updated = job.updated_at
        if updated is None:
            return False
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = (_now() - updated).total_seconds()
        return age > timeout

    async def _reap_if_stale(self, job: Job) -> Job:
        """Auto-fail a single job if its RUNNING state has gone stale."""
        if not self._is_stale_running(job):
            return job
        try:
            updated = await self._repo.update_status(
                job_id=job.id,
                status=JobStatus.FAILED,
                error_message=(
                    "Analysis stopped unexpectedly (no progress within the "
                    "expected time). Please retry."
                ),
            )
            logger.warning("job_reaped_stale_running", job_id=job.id)
            return updated
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("job_reap_failed", job_id=job.id, error=str(e))
            return job

    async def _reap_stale_list(self, jobs: list[Job]) -> list[Job]:
        """Sweep a list of jobs, auto-failing any stale RUNNING ones."""
        result: list[Job] = []
        for job in jobs:
            result.append(await self._reap_if_stale(job))
        return result

    async def submit(
        self,
        repo_url: str,
        artifact_type: ArtifactType,
        options: dict[str, str] | None = None,
        user_id: str | None = None,
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
            user_id=user_id,
            status=JobStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )

        saved = await self._repo.save(job)

        logger.info(
            "job_submitted",
            job_id=saved.id,
            repo_url=repo_url,
            artifact_type=artifact_type.value,
        )

        return saved

    async def get(self, job_id: str, owner_id: str | None = None) -> Job:
        """Return a job by ID. Raises NotFoundError if missing.

        When owner_id is provided, a job owned by a different user is treated
        as not found — this prevents one account from reading another's job
        (and avoids leaking that the job id exists at all)."""
        job = await self._repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job not found: {job_id}")
        if owner_id is not None and job.user_id is not None and job.user_id != owner_id:
            raise NotFoundError(f"Job not found: {job_id}")
        # Watchdog: if this job has been "running" with no progress past the
        # timeout, its background task died — auto-fail it so the UI stops
        # polling a job that will never finish.
        return await self._reap_if_stale(job)

    async def list_all(self, user_id: str | None = None) -> list[Job]:
        """Return all jobs, newest first, optionally scoped to a user."""
        jobs = await self._repo.get_all(user_id=user_id)
        return await self._reap_stale_list(jobs)

    async def list_by_status(
        self, status: JobStatus, user_id: str | None = None
    ) -> list[Job]:
        """Return jobs filtered by status, optionally scoped to a user."""
        jobs = await self._repo.get_by_status(status, user_id=user_id)
        return await self._reap_stale_list(jobs)

    async def list_by_repo(
        self, repo_url: str, user_id: str | None = None
    ) -> list[Job]:
        """Return all jobs for a specific repository, optionally scoped to a user."""
        jobs = await self._repo.get_by_repo_url(repo_url, user_id=user_id)
        return await self._reap_stale_list(jobs)

    async def cancel(self, job_id: str, owner_id: str | None = None) -> Job:
        """Cancel a pending or running job."""
        job = await self.get(job_id, owner_id=owner_id)

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

    async def retry(self, job_id: str, owner_id: str | None = None) -> Job:
        """Retry a failed job by creating a new one with same params."""
        original = await self.get(job_id, owner_id=owner_id)

        if not original.can_retry():
            raise ValidationError(
                f"Cannot retry job with status '{original.status.value}'. "
                f"Only failed jobs can be retried."
            )

        return await self.submit(
            repo_url=original.repo_url,
            artifact_type=original.artifact_type,
            options=original.options,
            user_id=original.user_id,
        )

    async def mark_running(self, job_id: str) -> Job:
        """Called by the pipeline when it starts processing."""
        job = await self.get(job_id)

        if job.status == JobStatus.RUNNING:
            return job  # idempotent

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

    async def update_progress(self, job_id: str, stage: str, percent: int) -> None:
        """Record live pipeline progress. Best-effort — never raises so a
        progress write can't abort an in-flight analysis."""
        try:
            await self._repo.update_progress(job_id, stage, percent)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("job_progress_update_failed", job_id=job_id, error=str(e))

    async def mark_completed(self, job_id: str) -> Job:
        """Called by the pipeline when processing succeeds."""
        job = await self.get(job_id)

        if job.status == JobStatus.COMPLETED:
            return job  # idempotent

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
        """Called by the pipeline when processing fails."""
        job = await self.get(job_id)

        # Fix 13 — don't overwrite terminal non-failed states
        if job.status in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
            raise ValidationError(
                f"Cannot mark job as failed — current status: '{job.status.value}'"
            )

        updated = await self._repo.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_message=error,
        )

        logger.error("job_failed", job_id=job_id, error=error)
        return updated

    async def delete(self, job_id: str, owner_id: str | None = None) -> None:
        """Hard delete a job and all its artifacts from the database."""
        # Verify it exists AND belongs to the caller first so we raise a
        # clean NotFoundError and never delete another user's job.
        await self.get(job_id, owner_id=owner_id)
        await self._repo.delete(job_id)
        logger.info("job_deleted", job_id=job_id)

    async def get_stats(self, user_id: str | None = None) -> dict[JobStatus, int]:
        """Return job counts by status for the health dashboard."""
        return await self._repo.count_by_status(user_id=user_id)
