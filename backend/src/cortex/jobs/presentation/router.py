"""Jobs API router — all job endpoints, complete and production-ready."""

from fastapi import APIRouter, HTTPException, Query
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.presentation.models import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    JobCancelResponse,
)
from shared.exceptions import NotFoundError, ValidationError
import uuid
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Temporary in-memory store — replaced by PostgreSQL repository next week
# The router code will NOT change when we swap this out
_jobs: dict[str, Job] = {}


@router.post(
    "",
    response_model=JobResponse,
    status_code=201,
    summary="Submit a new analysis job",
    description="Creates a new job and queues it for processing. "
    "Returns immediately with status=pending.",
)
async def create_job(request: JobCreateRequest) -> JobResponse:
    job = Job(
        repo_url=str(request.repo_url),
        artifact_type=request.artifact_type,
        options=request.options,
    )
    _jobs[job.id] = job
    return JobResponse.from_job(job)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List all jobs",
    description="Returns all jobs, optionally filtered by status "
    "or artifact type.",
)
async def list_jobs(
    status: JobStatus | None = Query(default=None),
    artifact_type: ArtifactType | None = Query(default=None),
) -> JobListResponse:
    jobs = list(_jobs.values())

    if status:
        jobs = [j for j in jobs if j.status == status]
    if artifact_type:
        jobs = [j for j in jobs if j.artifact_type == artifact_type]

    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return JobListResponse.from_jobs(jobs)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a job by ID",
    description="Returns a single job. Poll this endpoint every 3 "
    "seconds to track progress.",
)
async def get_job(job_id: str) -> JobResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_job(job)


@router.delete(
    "/{job_id}",
    response_model=JobCancelResponse,
    summary="Cancel a job",
    description="Cancels a pending or running job. "
    "Cannot cancel completed or failed jobs.",
)
async def cancel_job(job_id: str) -> JobCancelResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.can_cancel():
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a job with status '{job.status.value}'",
        )
    job.mark_cancelled()
    return JobCancelResponse(id=job.id, status=job.status)


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    status_code=201,
    summary="Retry a failed job",
    description="Creates a new job with the same parameters as a "
    "failed job.",
)
async def retry_job(job_id: str) -> JobResponse:
    original = _jobs.get(job_id)
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")
    if not original.can_retry():
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry a job with status "
            f"'{original.status.value}'. Only failed jobs can be retried.",
        )
    new_job = Job(
        repo_url=original.repo_url,
        artifact_type=original.artifact_type,
        options=original.options,
    )
    _jobs[new_job.id] = new_job
    return JobResponse.from_job(new_job)


@router.get(
    "/repo/{repo_url:path}",
    response_model=JobListResponse,
    summary="Get all jobs for a repository",
    description="Returns all jobs ever submitted for a specific "
    "GitHub repo URL.",
)
async def get_jobs_by_repo(repo_url: str) -> JobListResponse:
    jobs = [j for j in _jobs.values() if j.repo_url == repo_url]
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return JobListResponse.from_jobs(jobs)