"""Jobs API router — uses JobService via FastAPI dependency injection."""

from fastapi import APIRouter, HTTPException, Query, Depends
from cortex.jobs.domain.entities import JobStatus, ArtifactType
from cortex.jobs.application.use_cases import JobService
from cortex.jobs.infrastructure.repository import InMemoryJobRepository
from cortex.jobs.presentation.models import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    JobCancelResponse,
)
from shared.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Single shared repository instance for the lifetime of the process
# Replaced with PostgreSQL repository in Week 4 — only this line changes
_repository = InMemoryJobRepository()


def get_job_service() -> JobService:
    """FastAPI dependency — returns JobService with the shared repository.
    When we switch to PostgreSQL, only _repository changes here.
    The router, service, and all tests stay exactly the same."""
    return JobService(_repository)


@router.post(
    "",
    response_model=JobResponse,
    status_code=201,
    summary="Submit a new analysis job",
    description=(
        "Creates a new job and queues it for processing. "
        "Returns immediately with status=pending."
    ),
)
async def create_job(
    request: JobCreateRequest,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.submit(
            repo_url=str(request.repo_url),
            artifact_type=request.artifact_type,
            options=request.options,
        )
        return JobResponse.from_job(job)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "",
    response_model=JobListResponse,
    summary="List all jobs",
    description=(
        "Returns all jobs ordered by created_at descending. "
        "Optionally filter by status or artifact_type."
    ),
)
async def list_jobs(
    status: JobStatus | None = Query(default=None),
    artifact_type: ArtifactType | None = Query(default=None),
    service: JobService = Depends(get_job_service),
) -> JobListResponse:
    if status:
        jobs = await service.list_by_status(status)
    else:
        jobs = await service.list_all()

    if artifact_type:
        jobs = [j for j in jobs if j.artifact_type == artifact_type]

    return JobListResponse.from_jobs(jobs)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a job by ID",
    description=(
        "Returns a single job by UUID. "
        "Poll this every 3 seconds to track job progress."
    ),
)
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.get(job_id)
        return JobResponse.from_job(job)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.delete(
    "/{job_id}",
    response_model=JobCancelResponse,
    summary="Cancel a job",
    description=(
        "Cancels a pending or running job. "
        "Returns 409 if the job is already completed or failed."
    ),
)
async def cancel_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobCancelResponse:
    try:
        job = await service.cancel(job_id)
        return JobCancelResponse(id=job.id, status=job.status)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    status_code=201,
    summary="Retry a failed job",
    description=(
        "Creates a new job with the same parameters as a failed job. "
        "Returns 409 if the original job is not in failed state."
    ),
)
async def retry_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.retry(job_id)
        return JobResponse.from_job(job)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/{job_id}/complete",
    response_model=JobResponse,
    summary="Mark a job as completed",
    description=(
        "Called internally by the Celery worker when processing succeeds. "
        "Not intended for direct client use."
    ),
)
async def complete_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.mark_completed(job_id)
        return JobResponse.from_job(job)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/{job_id}/fail",
    response_model=JobResponse,
    summary="Mark a job as failed",
    description=(
        "Called internally by the Celery worker when processing fails. "
        "Requires an error message explaining the failure."
    ),
)
async def fail_job(
    job_id: str,
    error: str = Query(..., description="Error message describing the failure"),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.mark_failed(job_id, error)
        return JobResponse.from_job(job)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get(
    "/repo/{repo_url:path}",
    response_model=JobListResponse,
    summary="Get all jobs for a repository",
    description="Returns all jobs ever submitted for a specific GitHub URL.",
)
async def get_jobs_by_repo(
    repo_url: str,
    service: JobService = Depends(get_job_service),
) -> JobListResponse:
    jobs = await service.list_by_repo(repo_url)
    return JobListResponse.from_jobs(jobs)


@router.get(
    "/stats/summary",
    response_model=dict,
    summary="Job counts by status",
    description="Returns total job counts grouped by status. Used by the health dashboard.",
)
async def get_stats(
    service: JobService = Depends(get_job_service),
) -> dict:
    stats = await service.get_stats()
    return {status.value: count for status, count in stats.items()}