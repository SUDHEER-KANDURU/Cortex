"""Repository Memory API router — persistent, cross-job knowledge about
repositories: summaries, durable facts, and keyword search."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cortex.insights.application.engine import InsightsEngine
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
from cortex.jobs.infrastructure.pg_repository import PostgresJobRepository
from cortex.memory.application.summarizer import RepositoryMemorySummarizer
from cortex.memory.infrastructure.dependencies import memory_repository
from cortex.config import get_settings
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/memory", tags=["memory"])

_settings = get_settings()
_graph_repo = SQLiteGraphRepository(_settings.database_url)
_job_repo = PostgresJobRepository(_settings.database_url)
_engine = InsightsEngine()
_summarizer = RepositoryMemorySummarizer()


class RepositorySummaryResponse(BaseModel):
    repo_url: str
    repo_name: str
    last_job_id: str
    analysis_count: int
    overall_score: int | None
    overall_grade: str | None
    dominant_language: str | None
    total_files: int
    total_classes: int
    total_functions: int
    headline: str


class RepositoryFactResponse(BaseModel):
    id: str
    job_id: str
    category: str
    text: str
    source_symbol: str | None
    source_file: str | None


class RememberResponse(BaseModel):
    summary: RepositorySummaryResponse
    facts_recorded: int


@router.post(
    "/remember/{job_id}",
    response_model=RememberResponse,
    summary="Extract and store durable facts from a completed job",
    description=(
        "Computes engineering insights for a completed job (same as "
        "GET /insights/{job_id}) and extracts durable, searchable facts "
        "into repository memory. Refreshes the repo's summary — repeat "
        "analyses of the same repo_url accumulate history instead of "
        "starting over each time."
    ),
)
async def remember_job(job_id: str) -> RememberResponse:
    job = await _job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status.value != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status: {job.status.value}). "
                   "Can only remember completed jobs.",
        )

    nodes = await _graph_repo.get_nodes_by_job(job_id)
    edges = await _graph_repo.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail="No graph data found for this job.",
        )

    try:
        report = _engine.compute(
            job_id=job_id,
            repo_url=job.repo_url,
            nodes=nodes,
            edges=edges,
        )
    except Exception as e:
        logger.error("memory_insights_computation_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Insights computation failed: {e}")

    existing = await memory_repository.get_summary_by_repo_url(job.repo_url)
    summary, facts = _summarizer.summarize(report, existing)

    await memory_repository.save_summary(summary)
    await memory_repository.add_facts(facts)

    logger.info(
        "repository_remembered",
        repo_url=job.repo_url,
        job_id=job_id,
        analysis_count=summary.analysis_count,
        facts_recorded=len(facts),
    )

    return RememberResponse(
        summary=RepositorySummaryResponse(**summary.__dict__),
        facts_recorded=len(facts),
    )


@router.get(
    "/repositories",
    response_model=list[RepositorySummaryResponse],
    summary="List all repositories with stored memory",
)
async def list_repositories(limit: int = Query(50, ge=1, le=200)) -> list[RepositorySummaryResponse]:
    summaries = await memory_repository.list_summaries(limit=limit)
    return [RepositorySummaryResponse(**s.__dict__) for s in summaries]


@router.get(
    "/repositories/summary",
    response_model=RepositorySummaryResponse,
    summary="Get the stored summary for a repository by URL",
)
async def get_repository_summary(repo_url: str = Query(...)) -> RepositorySummaryResponse:
    summary = await memory_repository.get_summary_by_repo_url(repo_url)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No memory found for this repository. Analyze it first, "
                   "then call POST /memory/remember/{job_id}.",
        )
    return RepositorySummaryResponse(**summary.__dict__)


@router.get(
    "/repositories/facts",
    response_model=list[RepositoryFactResponse],
    summary="Get every stored fact for a repository",
)
async def get_repository_facts(repo_url: str = Query(...)) -> list[RepositoryFactResponse]:
    facts = await memory_repository.get_facts_for_repo(repo_url)
    return [
        RepositoryFactResponse(
            id=f.id,
            job_id=f.job_id,
            category=f.category,
            text=f.text,
            source_symbol=f.source_symbol,
            source_file=f.source_file,
        )
        for f in facts
    ]


@router.get(
    "/search",
    response_model=list[RepositoryFactResponse],
    summary="Keyword search over stored repository facts",
    description=(
        "Searches durable facts across all remembered repositories, or "
        "scoped to one repo_url. Matches on fact text, affected symbol, "
        "and source file — e.g. 'god class UserManager' or 'circular "
        "dependency'."
    ),
)
async def search_facts(
    q: str = Query(..., min_length=2, description="Search query"),
    repo_url: str | None = Query(None, description="Optionally scope to one repo"),
    limit: int = Query(10, ge=1, le=50),
) -> list[RepositoryFactResponse]:
    keywords = [kw.strip().lower() for kw in q.split() if len(kw.strip()) > 2]
    if not keywords:
        raise HTTPException(status_code=400, detail="Query too short — use at least one word over 2 characters.")

    results = await memory_repository.search_facts(keywords, repo_url=repo_url, limit=limit)
    return [
        RepositoryFactResponse(
            id=f.id,
            job_id=f.job_id,
            category=f.category,
            text=f.text,
            source_symbol=f.source_symbol,
            source_file=f.source_file,
        )
        for f in results
    ]