"""Jobs API router — uses JobService via FastAPI dependency injection."""
import structlog

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Header, Request
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
from cortex.auth.domain.entities import User
from cortex.auth.presentation.dependencies import get_current_user
from cortex.config import get_settings
from shared.exceptions import NotFoundError, ValidationError
from shared.identity import resolve_identity
from shared.rate_limit_response import rate_limit_response
from shared.rate_limiters import get_jobs_limiter, get_jobs_concurrency_limiter

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


async def _post_pipeline_intelligence(job: Job) -> None:
    """Run post-pipeline intelligence: memory persistence + FTS indexing +
    extended analysis (security, performance, testing).

    This is Cortex's own intelligence — it persists durable facts and
    indexes them for search. Fire-and-forget: failures here never fail the job.
    """
    from cortex.insights.application.engine import InsightsEngine
    from cortex.insights.application.security_analyzer import SecurityAnalyzer
    from cortex.insights.application.performance_analyzer import PerformanceAnalyzer
    from cortex.insights.application.testing_analyzer import TestingAnalyzer
    from cortex.memory.application.summarizer import RepositoryMemorySummarizer
    from cortex.memory.infrastructure.dependencies import memory_repository
    from cortex.graph.infrastructure.dependencies import graph_repository
    from cortex.search.fts_engine import FTSEngine

    # Step 1: Load graph data
    nodes = await graph_repository.get_nodes_by_job(job.id)
    edges = await graph_repository.get_edges_by_job(job.id)

    if not nodes:
        return

    # Step 2: Compute core insights
    engine = InsightsEngine()
    report = engine.compute(job_id=job.id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Step 3: Run extended analyzers (Cortex's own intelligence)
    from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
    graph_result = GraphBuildResult(
        nodes=nodes, edges=edges, job_id=job.id, repo_url=job.repo_url,
        node_by_id={n.id: n for n in nodes},
    )

    security_findings = SecurityAnalyzer().analyze(graph_result)
    performance_findings = PerformanceAnalyzer().analyze(graph_result)
    testing_report = TestingAnalyzer().analyze(graph_result)

    logger.info(
        "extended_analysis_complete",
        job_id=job.id,
        security_findings=len(security_findings),
        performance_findings=len(performance_findings),
        testing_findings=len(testing_report.findings),
    )

    # Step 4: Persist to memory
    summarizer = RepositoryMemorySummarizer()
    existing = await memory_repository.get_summary_by_repo_url(job.repo_url)
    summary, facts = summarizer.summarize(report, existing)

    await memory_repository.save_summary(summary)
    await memory_repository.add_facts(facts)

    # Step 5: Index for FTS5 search
    fts = FTSEngine()
    await fts.index_facts(repo_url=job.repo_url, job_id=job.id)
    await fts.index_nodes(job_id=job.id)

    # Step 6: Store file hashes for incremental analysis on next run
    from cortex.pipeline.infrastructure.incremental_analyzer import IncrementalAnalyzer
    incremental = IncrementalAnalyzer()
    # File contents are not available here (they're in PipelineContext, not persisted).
    # Hash storage is triggered from the pipeline stages instead. This is a no-op
    # placeholder — actual hash storage happens in GitHubFetchStage when file_contents
    # are available.

    logger.info(
        "post_pipeline_intelligence_complete",
        job_id=job.id,
        repo_url=job.repo_url,
        facts_count=len(facts),
    )


async def _run_pipeline_for_job(job: Job, service: JobService, identity_key: str) -> None:
    """Run the full analysis pipeline for a job.

    Called via FastAPI BackgroundTasks so it runs after the response is
    sent, within the same process lifetime as the HTTP request.

    Releases the concurrency slot when complete (success or failure).
    """
    concurrency = get_jobs_concurrency_limiter()
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
            await service.mark_failed(job.id, context.error or "Pipeline error")
            return

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

        # ── Post-pipeline intelligence: memory + search indexing ──────────
        try:
            await _post_pipeline_intelligence(job)
        except Exception as intel_err:
            logger.warning("post_pipeline_intelligence_failed", job_id=job.id, error=str(intel_err))

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
    finally:
        # Always release the concurrency slot regardless of outcome
        await concurrency.release(identity_key)


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
    http_request: Request,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> JobResponse:
    # ── Rate limit: job submission frequency ──────────────────────────────
    identity = resolve_identity(http_request)
    jobs_limiter = get_jobs_limiter()
    rate_result = await jobs_limiter.check(identity)
    if not rate_result.allowed:
        return rate_limit_response(rate_result)  # type: ignore[return-value]

    # ── Concurrent job limit: atomic acquire ──────────────────────────────
    concurrency = get_jobs_concurrency_limiter()
    acquired, current = await concurrency.acquire(identity)
    if not acquired:
        from fastapi.responses import JSONResponse
        return JSONResponse(  # type: ignore[return-value]
            status_code=429,
            content={
                "error": "concurrent_job_limit",
                "message": f"You already have {current} analyses running. "
                           f"Please wait for one to finish.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )

    # ── Duplicate detection: same repo_url with active (pending/running) job ─
    # Scoped to this user so one account's in-flight job never short-circuits
    # another account's submission.
    repo_url = str(request.repo_url).rstrip("/")
    try:
        existing_jobs = await service.list_by_repo(repo_url, user_id=user.id)
        active_job = next(
            (j for j in existing_jobs if j.status in (JobStatus.PENDING, JobStatus.RUNNING)),
            None,
        )
        if active_job:
            # Release the concurrency slot — we're not starting a new job
            await concurrency.release(identity)
            # Return the existing active job instead of creating a duplicate
            return JobResponse.from_job(active_job)
    except Exception:
        pass  # If listing fails, proceed with creation

    # ── Create and start job ──────────────────────────────────────────────
    try:
        job = await service.submit(
            repo_url=repo_url,
            artifact_type=request.artifact_type,
            options=request.options,
            user_id=user.id,
        )
    except ValidationError as e:
        await concurrency.release(identity)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        await concurrency.release(identity)
        raise

    background_tasks.add_task(_run_pipeline_for_job, job, service, identity)
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
    user: User = Depends(get_current_user),
) -> JobListResponse:
    if status:
        jobs = await service.list_by_status(status, user_id=user.id)
    else:
        jobs = await service.list_all(user_id=user.id)

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
    user: User = Depends(get_current_user),
) -> JobResponse:
    try:
        job = await service.get(job_id, owner_id=user.id)
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
    user: User = Depends(get_current_user),
) -> None:
    try:
        await service.delete(job_id, owner_id=user.id)
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
    user: User = Depends(get_current_user),
) -> JobCancelResponse:
    try:
        job = await service.cancel(job_id, owner_id=user.id)
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
    http_request: Request,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> JobResponse:
    # ── Rate limit + concurrency (same as create_job) ─────────────────────
    identity = resolve_identity(http_request)
    jobs_limiter = get_jobs_limiter()
    rate_result = await jobs_limiter.check(identity)
    if not rate_result.allowed:
        return rate_limit_response(rate_result)  # type: ignore[return-value]

    concurrency = get_jobs_concurrency_limiter()
    acquired, current = await concurrency.acquire(identity)
    if not acquired:
        from fastapi.responses import JSONResponse
        return JSONResponse(  # type: ignore[return-value]
            status_code=429,
            content={
                "error": "concurrent_job_limit",
                "message": f"You already have {current} analyses running. "
                           f"Please wait for one to finish.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )

    try:
        job = await service.retry(job_id, owner_id=user.id)
    except NotFoundError:
        await concurrency.release(identity)
        raise HTTPException(status_code=404, detail="Job not found")
    except ValidationError as e:
        await concurrency.release(identity)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        await concurrency.release(identity)
        raise

    background_tasks.add_task(_run_pipeline_for_job, job, service, identity)
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
    user: User = Depends(get_current_user),
) -> dict:
    stats = await service.get_stats(user_id=user.id)
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
    user: User = Depends(get_current_user),
) -> JobListResponse:
    jobs = await service.list_by_repo(repo_url, user_id=user.id)
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
    user: User = Depends(get_current_user),
) -> JobResponse:
    try:
        job = await service.get(job_id, owner_id=user.id)
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
