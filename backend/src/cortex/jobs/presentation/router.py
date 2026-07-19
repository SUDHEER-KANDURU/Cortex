"""Jobs API router — uses JobService via FastAPI dependency injection."""
import asyncio
from cortex.artifacts.application.use_cases import ArtifactService
from cortex.artifacts.domain.entities import ArtifactContentType

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

def _get_artifact_service() -> ArtifactService:
    from cortex.artifacts.presentation.router import (
        get_shared_artifact_repository,
    )
    return ArtifactService(get_shared_artifact_repository())


@router.post(
    "",
    response_model=JobResponse,
    status_code=201,
    summary="Submit a new analysis job",
    description="Creates a job and immediately starts the full "
    "analysis pipeline in the background.",
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
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    async def run_pipeline() -> None:
        try:
            from cortex.pipeline.application.orchestrator import (
                build_default_pipeline,
            )
            await service.mark_running(job.id)
            pipeline = build_default_pipeline()
            context = await pipeline.run(job)

            if context.artifact_content:
                content_type = getattr(
                    context,
                    "_artifact_content_type",
                    ArtifactContentType.MARKDOWN,
                )
                await _get_artifact_service().create(
                    job_id=job.id,
                    artifact_type=job.artifact_type.value,
                    content_type=content_type,
                    content_inline=context.artifact_content,
                )

            await service.mark_completed(job.id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await service.mark_failed(job.id, str(e))

    asyncio.create_task(run_pipeline())
    return JobResponse.from_job(job)

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


@router.post(
    "/{job_id}/analyze",
    response_model=JobResponse,
    summary="Run the full analysis pipeline for a job",
    description="Fetches the repo, parses code, builds graph, "
    "generates artifacts. Updates job status automatically.",
)
async def analyze_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.get(job_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.can_cancel():
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in status '{job.status.value}'",
        )

    try:
        from cortex.pipeline.application.orchestrator import (
            build_default_pipeline,
        )
        await service.mark_running(job_id)

        pipeline = build_default_pipeline()
        context = await pipeline.run(job)

        await service.mark_completed(job_id)

        updated_job = await service.get(job_id)
        return JobResponse.from_job(updated_job)

    except Exception as e:
        await service.mark_failed(job_id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {str(e)}"
        )