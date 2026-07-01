"""Abstract repository and service interfaces for the jobs domain.
Nothing in this file knows about databases, HTTP, or frameworks."""

from abc import ABC, abstractmethod
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType


class AbstractJobRepository(ABC):
    """Defines every storage operation the jobs domain needs.
    The infrastructure layer implements this against PostgreSQL."""

    @abstractmethod
    async def save(self, job: Job) -> Job:
        """Persist a new job. Returns the saved job with all fields populated."""
        ...

    @abstractmethod
    async def get_by_id(self, job_id: str) -> Job | None:
        """Return a job by ID. Returns None if not found — never raises."""
        ...

    @abstractmethod
    async def get_all(self) -> list[Job]:
        """Return every job, newest first."""
        ...

    @abstractmethod
    async def get_by_status(self, status: JobStatus) -> list[Job]:
        """Return all jobs with a given status.
        Used by the worker to find pending jobs to process."""
        ...

    @abstractmethod
    async def get_by_repo_url(self, repo_url: str) -> list[Job]:
        """Return all jobs for a given repo URL.
        Used to show history for a specific repository."""
        ...

    @abstractmethod
    async def get_by_artifact_type(
        self, artifact_type: ArtifactType
    ) -> list[Job]:
        """Return all jobs of a specific artifact type."""
        ...

    @abstractmethod
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: str | None = None,
    ) -> Job:
        """Update a job's status and optionally record an error message.
        Returns the updated job. Raises NotFoundError if job doesn't exist."""
        ...

    @abstractmethod
    async def delete(self, job_id: str) -> None:
        """Hard delete a job and all its associated artifacts.
        Raises NotFoundError if job doesn't exist."""
        ...

    @abstractmethod
    async def count_by_status(self) -> dict[JobStatus, int]:
        """Return a count of jobs grouped by status.
        Used for the health dashboard and analytics."""
        ...


class AbstractJobService(ABC):
    """Defines the business operations the application layer exposes.
    The use_cases.py implements this. The router calls this — never
    the repository directly."""

    @abstractmethod
    async def submit(
        self,
        repo_url: str,
        artifact_type: ArtifactType,
        options: dict[str, str] | None = None,
    ) -> Job:
        """Validate the request, create a Job entity, persist it,
        and dispatch it to the Celery worker queue."""
        ...

    @abstractmethod
    async def get(self, job_id: str) -> Job:
        """Return a job by ID. Raises NotFoundError if not found."""
        ...

    @abstractmethod
    async def list_all(self) -> list[Job]:
        """Return all jobs."""
        ...

    @abstractmethod
    async def list_by_status(self, status: JobStatus) -> list[Job]:
        """Return jobs filtered by status."""
        ...

    @abstractmethod
    async def cancel(self, job_id: str) -> Job:
        """Cancel a pending or running job.
        Raises NotFoundError if not found.
        Raises ValidationError if job is already completed or failed."""
        ...

    @abstractmethod
    async def retry(self, job_id: str) -> Job:
        """Retry a failed job by creating a new job with the same parameters.
        Raises NotFoundError if original job not found.
        Raises ValidationError if job is not in failed state."""
        ...