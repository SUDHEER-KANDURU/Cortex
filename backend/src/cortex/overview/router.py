"""Overview API router — aggregated intelligence endpoints for the frontend.

These endpoints combine data from multiple Cortex modules into single
responses optimized for frontend consumption. Each endpoint represents
one "view" in the UI.

Endpoints:
  GET /api/v1/overview/{job_id}         — Repository overview (landing page)
  GET /api/v1/overview/{job_id}/health  — Health dashboard (dimension scores)
  GET /api/v1/overview/{job_id}/node/{node_id} — Code navigation (node detail)
  GET /api/v1/overview/{job_id}/analysis — Extended analysis (security, perf, testing)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.jobs.infrastructure.dependencies import job_repository
from cortex.insights.application.engine import InsightsEngine
from cortex.insights.application.security_analyzer import SecurityAnalyzer
from cortex.insights.application.performance_analyzer import PerformanceAnalyzer
from cortex.insights.application.testing_analyzer import TestingAnalyzer
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.graph.domain.entities import NodeType, RelationshipType
from shared.exceptions import NotFoundError
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/overview", tags=["overview"])


# ─── Response Models ──────────────────────────────────────────────────────────

class OverviewResponse(BaseModel):
    """Repository overview — the landing page data."""
    repo_name: str
    repo_url: str
    # Structure
    total_files: int
    total_lines: int
    total_modules: int
    total_classes: int
    total_functions: int
    total_endpoints: int
    total_tests: int
    languages: list[str]
    # Health
    overall_score: int
    overall_grade: str
    # Key stats
    avg_complexity: float
    max_complexity: int
    documentation_ratio: float
    test_ratio: float


class DimensionResponse(BaseModel):
    """A single health dimension."""
    name: str
    score: int
    grade: str
    summary: str
    issue_count: int


class HealthResponse(BaseModel):
    """Health dashboard data."""
    overall_score: int
    overall_grade: str
    dimensions: list[DimensionResponse]
    top_issues: list[dict]


class NodeDetailResponse(BaseModel):
    """Code navigation — detail for a single node."""
    id: str
    label: str
    node_type: str
    properties: dict
    # Connections
    callers: list[dict]  # nodes that call/import this
    callees: list[dict]  # nodes this calls/imports
    contained_by: str | None  # parent node label
    contains: list[dict]  # child nodes


class FindingResponse(BaseModel):
    """A single analysis finding."""
    title: str
    severity: str
    category: str
    description: str
    file_path: str = ""
    symbol: str = ""
    evidence: str = ""
    fix_template: str = ""


class ExtendedAnalysisResponse(BaseModel):
    """Extended analysis — security, performance, testing."""
    security_findings: list[FindingResponse]
    performance_findings: list[FindingResponse]
    testing_summary: dict
    testing_findings: list[FindingResponse]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=OverviewResponse,
    summary="Repository overview",
    description="Landing page data combining structure, health, and key statistics.",
)
async def get_overview(job_id: str) -> OverviewResponse:
    """Get the repository overview for a completed job."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    # Compute insights
    engine = InsightsEngine()
    report = engine.compute(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Count by type
    files = [n for n in nodes if n.node_type == NodeType.FILE]
    modules = [n for n in nodes if n.node_type == NodeType.MODULE]
    classes = [n for n in nodes if n.node_type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM)]
    functions = [n for n in nodes if n.node_type in (NodeType.FUNCTION, NodeType.METHOD)]
    endpoints = [n for n in nodes if n.node_type == NodeType.ENDPOINT]
    tests = [n for n in nodes if n.node_type == NodeType.TEST]

    total_lines = sum(int(f.properties.get("lines", 0) or 0) for f in files)

    # Languages
    from collections import defaultdict
    lang_counts: dict[str, int] = defaultdict(int)
    for f in files:
        lang = str(f.properties.get("language", ""))
        if lang and lang != "unknown":
            lang_counts[lang] += 1
    languages = sorted(lang_counts.keys(), key=lambda l: lang_counts[l], reverse=True)

    # Complexity
    complexities = [int(fn.properties.get("cyclomatic", 0) or 0) for fn in functions + endpoints + tests if int(fn.properties.get("cyclomatic", 0) or 0) > 0]
    avg_cc = round(sum(complexities) / max(len(complexities), 1), 2)
    max_cc = max(complexities, default=0)

    # Documentation
    documentable = functions + classes
    doc_count = sum(1 for n in documentable if n.properties.get("has_docstring"))
    doc_ratio = round(doc_count / max(len(documentable), 1), 2)

    # Test ratio
    test_files = [f for f in files if f.properties.get("is_test_file")]
    source_files = [f for f in files if not f.properties.get("is_test_file")]
    test_ratio = round(len(test_files) / max(len(source_files), 1), 2)

    repo_name = job.repo_url.rstrip("/").split("/")[-1]

    return OverviewResponse(
        repo_name=repo_name,
        repo_url=job.repo_url,
        total_files=len(files),
        total_lines=total_lines,
        total_modules=len(modules),
        total_classes=len(classes),
        total_functions=len(functions),
        total_endpoints=len(endpoints),
        total_tests=len(tests),
        languages=languages,
        overall_score=report.overall_score,
        overall_grade=report.overall_grade,
        avg_complexity=avg_cc,
        max_complexity=max_cc,
        documentation_ratio=doc_ratio,
        test_ratio=test_ratio,
    )


@router.get(
    "/{job_id}/health",
    response_model=HealthResponse,
    summary="Health dashboard",
    description="Per-dimension health scores with top issues.",
)
async def get_health(job_id: str) -> HealthResponse:
    """Get health dashboard data."""
    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data")

    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    engine = InsightsEngine()
    report = engine.compute(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    dimensions = [
        DimensionResponse(
            name=d.name,
            score=d.score,
            grade=d.grade,
            summary=d.summary,
            issue_count=d.issue_count,
        )
        for d in report.dimensions
    ]

    # Top issues (max 10)
    top_issues = [
        {
            "title": issue.title,
            "severity": issue.severity.value,
            "category": issue.category.value,
            "file_path": issue.file_path,
            "symbol": issue.affected_symbol,
            "recommendation": issue.recommendation,
        }
        for issue in report.high_issues()[:10]
    ]

    return HealthResponse(
        overall_score=report.overall_score,
        overall_grade=report.overall_grade,
        dimensions=dimensions,
        top_issues=top_issues,
    )


@router.get(
    "/{job_id}/node/{node_id}",
    response_model=NodeDetailResponse,
    summary="Code navigation — node detail",
    description="Get full detail for a graph node including its connections.",
)
async def get_node_detail(job_id: str, node_id: str) -> NodeDetailResponse:
    """Get detailed information about a specific graph node."""
    node = await graph_repository.get_node_by_id(node_id)
    if not node or node.job_id != job_id:
        raise HTTPException(status_code=404, detail="Node not found")

    edges = await graph_repository.get_edges_by_job(job_id)
    nodes = await graph_repository.get_nodes_by_job(job_id)
    node_map = {n.id: n for n in nodes}

    # Find connections
    callers: list[dict] = []
    callees: list[dict] = []
    contained_by: str | None = None
    contains: list[dict] = []

    for edge in edges:
        if edge.target_id == node_id:
            src = node_map.get(edge.source_id)
            if src:
                if edge.relationship == RelationshipType.CONTAINS:
                    contained_by = src.label
                else:
                    callers.append({
                        "id": src.id,
                        "label": src.label,
                        "type": src.node_type.value,
                        "relationship": edge.relationship.value,
                    })
        elif edge.source_id == node_id:
            tgt = node_map.get(edge.target_id)
            if tgt:
                if edge.relationship == RelationshipType.CONTAINS:
                    contains.append({
                        "id": tgt.id,
                        "label": tgt.label,
                        "type": tgt.node_type.value,
                    })
                else:
                    callees.append({
                        "id": tgt.id,
                        "label": tgt.label,
                        "type": tgt.node_type.value,
                        "relationship": edge.relationship.value,
                    })

    return NodeDetailResponse(
        id=node.id,
        label=node.label,
        node_type=node.node_type.value,
        properties=node.properties,
        callers=callers[:20],
        callees=callees[:20],
        contained_by=contained_by,
        contains=contains[:30],
    )


@router.get(
    "/{job_id}/analysis",
    response_model=ExtendedAnalysisResponse,
    summary="Extended analysis",
    description="Security, performance, and testing analysis findings.",
)
async def get_extended_analysis(job_id: str) -> ExtendedAnalysisResponse:
    """Get extended analysis (security, performance, testing) for a job."""
    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data")

    graph_result = GraphBuildResult(
        nodes=nodes, edges=edges, job_id=job_id,
        node_by_id={n.id: n for n in nodes},
    )

    # Run analyzers
    security = SecurityAnalyzer().analyze(graph_result)
    performance = PerformanceAnalyzer().analyze(graph_result)
    testing = TestingAnalyzer().analyze(graph_result)

    return ExtendedAnalysisResponse(
        security_findings=[
            FindingResponse(
                title=f.title, severity=f.severity, category=f.category,
                description=f.description, file_path=f.file_path,
                symbol=f.symbol, evidence=f.evidence, fix_template=f.fix_template,
            )
            for f in security
        ],
        performance_findings=[
            FindingResponse(
                title=f.title, severity=f.severity, category=f.category,
                description=f.description, file_path=f.file_path,
                symbol=f.symbol, evidence=f.evidence, fix_template=f.fix_template,
            )
            for f in performance
        ],
        testing_summary={
            "total_source_files": testing.total_source_files,
            "total_test_files": testing.total_test_files,
            "total_test_functions": testing.total_test_functions,
            "test_ratio": testing.test_ratio,
            "tested_modules": testing.tested_modules,
            "untested_modules": testing.untested_modules,
        },
        testing_findings=[
            FindingResponse(
                title=f.title, severity=f.severity, category=f.category,
                description=f.description, file_path=f.file_path,
                symbol=f.symbol, evidence=f.evidence, fix_template=f.fix_template,
            )
            for f in testing.findings
        ],
    )


# ─── Delta Intelligence Endpoint ─────────────────────────────────────────────

class ScoreChangeResponse(BaseModel):
    """A single score change between analyses."""
    metric: str
    previous: float
    current: float
    delta: float
    direction: str


class DeltaResponse(BaseModel):
    """Delta intelligence — what changed since last analysis."""
    repo_name: str
    is_first_analysis: bool
    analysis_count: int
    overall_change: ScoreChangeResponse | None = None
    dimension_changes: list[ScoreChangeResponse] = []
    structural_changes: list[str] = []
    improvements: list[str] = []
    degradations: list[str] = []


@router.get(
    "/{job_id}/delta",
    response_model=DeltaResponse,
    summary="Delta intelligence — what changed",
    description=(
        "Compares the current analysis against the previous one for the same "
        "repository. Shows score changes, structural differences, and "
        "improvements/degradations."
    ),
)
async def get_delta(job_id: str) -> DeltaResponse:
    """Get the delta report comparing this analysis to the previous one."""
    from cortex.memory.application.delta_analyzer import DeltaAnalyzer
    from cortex.memory.infrastructure.dependencies import memory_repository

    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data")

    # Compute current insights
    engine = InsightsEngine()
    report = engine.compute(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Get previous summary
    previous_summary = await memory_repository.get_summary_by_repo_url(job.repo_url)

    # Compute delta
    analyzer = DeltaAnalyzer()
    delta = analyzer.compute_delta(report, previous_summary)

    # Build response
    overall_change = None
    if delta.overall_score_change:
        sc = delta.overall_score_change
        overall_change = ScoreChangeResponse(
            metric=sc.metric,
            previous=float(sc.previous),
            current=float(sc.current),
            delta=float(sc.delta),
            direction=sc.direction,
        )

    return DeltaResponse(
        repo_name=delta.repo_name,
        is_first_analysis=delta.is_first_analysis,
        analysis_count=delta.analysis_count,
        overall_change=overall_change,
        dimension_changes=[
            ScoreChangeResponse(
                metric=dc.metric,
                previous=float(dc.previous),
                current=float(dc.current),
                delta=float(dc.delta),
                direction=dc.direction,
            )
            for dc in delta.dimension_changes
        ],
        structural_changes=delta.structural_changes,
        improvements=delta.improvements,
        degradations=delta.degradations,
    )
