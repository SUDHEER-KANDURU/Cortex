"""Pydantic models for the Jobs API.
Request bodies, response shapes, and query filter models."""

from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator
from cortex.jobs.domain.entities import JobStatus, ArtifactType


class JobCreateRequest(BaseModel):
    repo_url: HttpUrl
    artifact_type: ArtifactType
    options: dict[str, str] | None = None

    @field_validator("repo_url")
    @classmethod
    def must_be_github(cls, v: HttpUrl) -> HttpUrl:
        """Reject non-GitHub URLs at the model level."""
        if "github.com" not in str(v):
            raise ValueError("repo_url must be a GitHub repository URL")
        return v


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    repo_url: str
    artifact_type: ArtifactType
    error_message: str | None = None
    options: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime
    is_terminal: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_job(cls, job: "Job") -> "JobResponse":  # type: ignore[name-defined]
        """Build a response from a Job domain entity."""
        return cls(
            id=job.id,
            status=job.status,
            repo_url=job.repo_url,
            artifact_type=job.artifact_type,
            error_message=job.error_message,
            options=job.options,
            created_at=job.created_at,
            updated_at=job.updated_at,
            is_terminal=job.is_terminal(),
        )


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int

    @classmethod
    def from_jobs(cls, jobs: list) -> "JobListResponse":
        return cls(
            jobs=[JobResponse.from_job(j) for j in jobs],
            total=len(jobs),
        )


class JobCancelResponse(BaseModel):
    id: str
    status: JobStatus
    message: str = "Job cancelled successfully"


class JobStatusFilter(BaseModel):
    status: JobStatus | None = None
    artifact_type: ArtifactType | None = None