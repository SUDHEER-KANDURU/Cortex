"""Insights API router — engineering health and code quality metrics."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from cortex.insights.application.engine import InsightsEngine
from cortex.insights.presentation.models import InsightsReportResponse
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
from cortex.jobs.infrastructure.pg_repository import PostgresJobRepository
from cortex.config import get_settings
from shared.exceptions import NotFoundError
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/insights", tags=["insights"])

_settings = get_settings()
_graph_repo = SQLiteGraphRepository(_settings.database_url)
_job_repo = PostgresJobRepository(_settings.database_url)
_engine = InsightsEngine()


@router.get(
    "/{job_id}",
    response_model=InsightsReportResponse,
    summary="Get engineering health report for a job",
    description=(
        "Computes engineering health metrics from the knowledge graph "
        "built during analysis. Returns scores, dimensions, and issues. "
        "No re-analysis required — reads from stored graph data."
    ),
)
async def get_insights(job_id: str) -> InsightsReportResponse:
    # Verify job exists
    job = await _job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status.value != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status: {job.status.value}). "
                   "Insights are only available for completed jobs.",
        )

    nodes = await _graph_repo.get_nodes_by_job(job_id)
    edges = await _graph_repo.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail="No graph data found for this job. "
                   "The analysis may not have built a graph yet.",
        )

    try:
        report = _engine.compute(
            job_id=job_id,
            repo_url=job.repo_url,
            nodes=nodes,
            edges=edges,
        )
        return InsightsReportResponse.from_report(report)
    except Exception as e:
        logger.error("insights_computation_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Insights computation failed: {e}")


@router.get(
    "/{job_id}/export",
    response_class=PlainTextResponse,
    summary="Export engineering report as Markdown",
    description="Returns a full engineering health report in Markdown format, ready to share or save.",
)
async def export_insights_markdown(job_id: str) -> str:
    job = await _job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status.value != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status: {job.status.value}).",
        )

    nodes = await _graph_repo.get_nodes_by_job(job_id)
    edges = await _graph_repo.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data found for this job.")

    try:
        report = _engine.compute(
            job_id=job_id,
            repo_url=job.repo_url,
            nodes=nodes,
            edges=edges,
        )
        return _engine.to_markdown_report(report)
    except Exception as e:
        logger.error("insights_export_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
