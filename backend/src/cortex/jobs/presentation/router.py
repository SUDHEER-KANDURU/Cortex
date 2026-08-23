"""Jobs API router — uses JobService via FastAPI dependency injection."""
import structlog

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Header
from cortex.artifacts.domain.entities import ArtifactContentType
from cortex.artifacts.application.use_cases import ArtifactService
from cortex.artifacts.infrastructure.dependencies import artifact_repository
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.application.use_cases import JobService
from cortex.jobs.infrastructure.dependencies import job_repository
from cortex.jobs.presentation.models import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    JobCancelResponse,
)
from cortex.config import get_settings
from shared.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["jobs"])

_artifact_service = ArtifactService(artifact_repository)


def _require_internal(x_internal_token: str | None = Header(default=None)) -> None:
    """Guard for internal-only state-mutation endpoints (/complete, /fail).

    Callers must supply the header:  X-Internal-Token: <INTERNAL_SECRET>
    If INTERNAL_SECRET is not configured, the endpoints are disabled entirely.
    This prevents any external client from arbitrarily changing job state.
    """
    secret = get_settings().internal_secret
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Internal endpoints are disabled — INTERNAL_SECRET is not configured.",
        )
    if x_internal_token != secret:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing X-Internal-Token header.",
        )


def get_job_service() -> JobService:
    """FastAPI dependency — returns JobService with the shared repository."""
    return JobService(job_repository)


async def _run_pipeline_for_job(job: Job, service: JobService) -> None:
    """Run the full analysis pipeline for a job.

    Called via FastAPI BackgroundTasks so it runs after the response is
    sent, within the same process lifetime as the HTTP request.
    """
    try:
        from cortex.pipeline.application.orchestrator import build_default_pipeline

        await service.mark_running(job.id)
        pipeline = build_default_pipeline()
        context = await pipeline.run(job)

        if context.has_error():
            logger.error(
                "pipeline_context_error",
                job_id=job.id,
                error=context.error,
            )

        content = (
            context.artifact_content
            or "# No content generated\n\nThe pipeline completed but produced no output."
        )
        content_type = context.artifact_content_type or ArtifactContentType.MARKDOWN

        await _artifact_service.create(
            job_id=job.id,
            artifact_type=job.artifact_type.value,
            content_type=content_type,
            content_inline=content,
        )

        await service.mark_completed(job.id)

        logger.info(
            "pipeline_completed",
            job_id=job.id,
            content_length=len(content),
        )

    except Exception as e:
        import traceback
        logger.error("pipeline_failed", job_id=job.id, error=str(e))
        traceback.print_exc()
        try:
            await service.mark_failed(job.id, str(e))
        except Exception as mark_err:
            # mark_failed itself failed (e.g. DB unreachable).
            # Log it — do not swallow it silently. The job will be stuck in
            # 'running' and will be reset to 'failed' on next server restart
            # via the lifespan startup reset.
            logger.error(
                "mark_failed_error",
                job_id=job.id,
                original_error=str(e),
                mark_failed_error=str(mark_err),
            )


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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(_run_pipeline_for_job, job, service)
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
    status_code=204,
    summary="Hard delete a job",
    description=(
        "Permanently removes a job and all its artifacts from the database. "
        "This cannot be undone."
    ),
)
async def delete_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> None:
    try:
        await service.delete(job_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post(
    "/{job_id}/cancel",
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
        "Creates a new job with the same parameters as a failed job "
        "and immediately starts the pipeline. "
        "Returns 409 if the original job is not in failed state."
    ),
)
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    try:
        job = await service.retry(job_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))

    background_tasks.add_task(_run_pipeline_for_job, job, service)
    return JobResponse.from_job(job)


@router.post(
    "/{job_id}/complete",
    response_model=JobResponse,
    summary="Mark a job as completed",
    description="Called internally when processing succeeds. Requires X-Internal-Token header.",
    dependencies=[Depends(_require_internal)],
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
    description="Called internally when processing fails. Requires X-Internal-Token header.",
    dependencies=[Depends(_require_internal)],
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
    "/stats/summary",
    response_model=dict,
    summary="Job counts by status",
    description="Returns total job counts grouped by status.",
)
async def get_stats(
    service: JobService = Depends(get_job_service),
) -> dict:
    stats = await service.get_stats()
    return {status.value: count for status, count in stats.items()}


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


@router.post(
    "/{job_id}/analyze",
    response_model=JobResponse,
    summary="Run the full analysis pipeline for a job synchronously",
    description="Runs the pipeline inline and waits for completion. "
    "Used for testing. For production, use POST /jobs instead.",
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
        from cortex.pipeline.application.orchestrator import build_default_pipeline

        await service.mark_running(job_id)
        pipeline = build_default_pipeline()
        context = await pipeline.run(job)

        content = (
            context.artifact_content
            or "# No content generated\n\nThe pipeline completed but produced no output."
        )
        content_type = context.artifact_content_type or ArtifactContentType.MARKDOWN

        await _artifact_service.create(
            job_id=job.id,
            artifact_type=job.artifact_type.value,
            content_type=content_type,
            content_inline=content,
        )

        await service.mark_completed(job_id)
        return JobResponse.from_job(await service.get(job_id))

    except Exception as e:
        await service.mark_failed(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
