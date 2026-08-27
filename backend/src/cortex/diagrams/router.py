"""Diagrams API router — layered architecture diagrams.

Provides three zoom levels for interactive architecture exploration:
  GET /api/v1/diagrams/{job_id}?level=system   (default)
  GET /api/v1/diagrams/{job_id}?level=module&module=chat
  GET /api/v1/diagrams/{job_id}?level=class&class=ChatService
"""

from fastapi import APIRouter, HTTPException, Query
from cortex.graph.application.use_cases import GraphService
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
from cortex.jobs.application.use_cases import JobService
from cortex.jobs.infrastructure.dependencies import job_repository
from cortex.config import get_settings
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.pipeline.infrastructure.layered_diagram_generator import (
    LayeredDiagramGenerator,
)
from shared.exceptions import NotFoundError

router = APIRouter(prefix="/diagrams", tags=["diagrams"])

_graph_repo = SQLiteGraphRepository(get_settings().database_url)


def _get_graph_service() -> GraphService:
    return GraphService(_graph_repo)


def _get_job_service() -> JobService:
    return JobService(job_repository)


@router.get(
    "/{job_id}",
    summary="Get layered architecture diagram",
    description=(
        "Returns structured diagram data at the requested zoom level. "
        "Level 1 (system) shows one node per module with aggregated edges. "
        "Level 2 (module) shows classes/files inside a specific module. "
        "Level 3 (class) shows methods, callers, and inheritance for a class."
    ),
)
async def get_diagram(
    job_id: str,
    level: str = Query(
        default="system",
        description="Zoom level: 'system', 'module', or 'class'",
        pattern="^(system|module|class)$",
    ),
    module: str | None = Query(
        default=None,
        description="Module name (required when level=module)",
    ),
    class_name: str | None = Query(
        default=None,
        alias="class",
        description="Class name (required when level=class)",
    ),
) -> dict:
    """Return diagram data for the given job at the specified zoom level."""

    # Validate params
    if level == "module" and not module:
        raise HTTPException(
            status_code=422,
            detail="Query param 'module' is required when level=module",
        )
    if level == "class" and not class_name:
        raise HTTPException(
            status_code=422,
            detail="Query param 'class' is required when level=class",
        )

    # Get the job to extract repo_name
    job_service = _get_job_service()
    try:
        job = await job_service.get(job_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

    repo_name = job.repo_url.rstrip("/").split("/")[-1]

    # Load graph from SQLite
    graph_service = _get_graph_service()
    nodes, edges = await graph_service.get_graph_for_job(job_id)

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail="No graph data found for this job. The job may still be processing.",
        )

    # Reconstruct GraphBuildResult
    graph_result = GraphBuildResult(
        nodes=nodes,
        edges=edges,
        job_id=job_id,
        repo_url=job.repo_url,
    )

    # Generate the diagram at the requested level
    generator = LayeredDiagramGenerator(graph_result)

    if level == "system":
        result = generator.generate_system_view(repo_name)
    elif level == "module":
        result = generator.generate_module_detail(module, repo_name)  # type: ignore[arg-type]
    elif level == "class":
        result = generator.generate_class_detail(class_name, repo_name)  # type: ignore[arg-type]
    else:
        raise HTTPException(status_code=422, detail=f"Unknown level: {level}")

    return result.to_dict()
