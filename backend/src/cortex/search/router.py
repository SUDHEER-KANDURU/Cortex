"""Search API router — full-text search over Cortex's knowledge base.

Exposes Cortex's own search intelligence (FTS5) to the frontend.
Searches across repository facts and graph nodes with BM25 ranking.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cortex.search.fts_engine import FTSEngine, SearchResult
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/search", tags=["search"])

_fts = FTSEngine()


class SearchResultResponse(BaseModel):
    """A single search result."""
    source: str  # "fact" or "node"
    text: str
    category: str = ""
    source_symbol: str = ""
    source_file: str = ""
    repo_url: str = ""
    job_id: str = ""
    relevance: float = 0.0
    node_id: str = ""


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    query: str
    total_results: int
    results: list[SearchResultResponse]


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search repository knowledge",
    description=(
        "Full-text search over repository facts and graph nodes using "
        "BM25 relevance ranking. Supports natural language queries, "
        "quoted phrases, and prefix matching."
    ),
)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    job_id: str | None = Query(None, description="Scope to a specific job"),
    repo_url: str | None = Query(None, description="Scope to a specific repository"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
) -> SearchResponse:
    """Search Cortex's knowledge base."""
    results = await _fts.search(
        query=q,
        job_id=job_id,
        repo_url=repo_url,
        limit=limit,
    )

    return SearchResponse(
        query=q,
        total_results=len(results),
        results=[
            SearchResultResponse(
                source=r.source,
                text=r.text,
                category=r.category,
                source_symbol=r.source_symbol,
                source_file=r.source_file,
                repo_url=r.repo_url,
                job_id=r.job_id,
                relevance=round(r.relevance, 4),
                node_id=r.node_id,
            )
            for r in results
        ],
    )
