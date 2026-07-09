"""Celery task definitions — async job processing.
These are the entry points called by the Celery worker."""

from worker.celery_app import celery_app
import structlog

logger = structlog.get_logger()


@celery_app.task(
    name="cortex.analyze_repo",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def analyze_repo(self, job_id: str) -> dict:
    """Main Celery task — runs the full analysis pipeline for a job.
    Called by JobService.submit() after persisting the job.

    Stages (wired in Week 9 when Docker is running):
    1. Mark job as RUNNING
    2. GitHubFetchStage — fetch file tree and contents
    3. GraphBuildStage — parse files, build Neo4j graph
    4. ArtifactGenerateStage — generate and store artifacts
    5. Mark job as COMPLETED
    On any failure: mark job as FAILED with error message
    """
    import asyncio

    logger.info("celery_task_started", job_id=job_id)

    try:
        # Pipeline wired here in Week 9
        # from cortex.jobs.application.use_cases import JobService
        # from cortex.pipeline.application.orchestrator import PipelineOrchestrator
        # result = asyncio.run(orchestrator.run(job))
        logger.info("celery_task_completed", job_id=job_id)
        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(
            "celery_task_failed",
            job_id=job_id,
            error=str(e),
        )
        raise self.retry(exc=e)