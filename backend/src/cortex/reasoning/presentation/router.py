"""Reasoning API router — the flagship intelligence endpoints.

These endpoints expose the unified Cortex reasoning layer:
  - Explain This Repository (structured 10-section explanation)
  - Learning Path (repository-specific onboarding)
  - Root-Cause Analysis (stacktrace → evidence-backed diagnosis)
  - Issue → Fix Intelligence (selected issue → fix context)
  - Full Repository Understanding (the central intelligence output)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.jobs.infrastructure.dependencies import job_repository
from cortex.insights.application.engine import InsightsEngine
from cortex.reasoning.application.reasoner import CortexReasoner
from cortex.reasoning.application.learning_path import LearningPathGenerator
from cortex.reasoning.application.root_cause import RootCauseAnalyzer
from cortex.reasoning.application.fix_intelligence import FixIntelligenceEngine
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class EntryPointResponse(BaseModel):
    label: str
    node_id: str
    node_type: str
    file_path: str
    kind: str
    method: str = ""
    route: str = ""


class ModuleResponse(BaseModel):
    name: str
    path: str
    node_id: str
    purpose: str = ""
    architecture_role: str = ""
    layer: str = ""
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    total_lines: int = 0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    key_classes: list[str] = []
    key_functions: list[str] = []
    dependencies: list[str] = []
    dependents: list[str] = []
    coupling_score: float = 0.0
    risks: list[str] = []
    is_god_module: bool = False


class DataFlowStepResponse(BaseModel):
    symbol: str
    node_id: str
    node_type: str
    file_path: str
    role: str = ""


class DataFlowResponse(BaseModel):
    name: str
    entry_point: str
    steps: list[DataFlowStepResponse] = []


class ComplexityHotspotResponse(BaseModel):
    symbol: str
    file: str = ""
    cyclomatic: int = 0
    lines: int = 0
    node_id: str = ""


class RepositoryUnderstandingResponse(BaseModel):
    """Full Cortex understanding of a repository."""
    job_id: str
    repo_url: str
    repo_name: str
    # What
    purpose: str = ""
    headline: str = ""
    # Architecture
    architecture_style: str = ""
    architecture_description: str = ""
    architecture_evidence: list[str] = []
    # Languages & Frameworks
    languages: list[str] = []
    frameworks: list[str] = []
    # Structure
    total_files: int = 0
    total_lines: int = 0
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_endpoints: int = 0
    total_tests: int = 0
    # Entry Points
    entry_points: list[EntryPointResponse] = []
    # Modules
    modules: list[ModuleResponse] = []
    # Data Flows
    data_flows: list[DataFlowResponse] = []
    # Health
    overall_score: int = 0
    overall_grade: str = ""
    complexity_hotspots: list[ComplexityHotspotResponse] = []
    architectural_risks: list[str] = []
    # Starting point
    start_here: str = ""
    start_here_reason: str = ""
    start_here_file: str = ""
    # Dependencies
    top_dependencies: list[str] = []


class LearningStepResponse(BaseModel):
    order: int
    title: str
    what_to_read: list[str]
    why: str
    symbols: list[str] = []
    prerequisites: list[str] = []
    difficulty: str = "beginner"
    what_to_understand: str = ""
    module: str = ""
    estimated_minutes: int = 0


class LearningPathResponse(BaseModel):
    repo_name: str
    total_steps: int = 0
    estimated_hours: float = 0.0
    start_here: list[LearningStepResponse] = []
    foundations: list[LearningStepResponse] = []
    core_flow: list[LearningStepResponse] = []
    important_modules: list[LearningStepResponse] = []
    advanced_areas: list[LearningStepResponse] = []
    known_risks: list[LearningStepResponse] = []


class RootCauseRequest(BaseModel):
    error_input: str = Field(..., description="Stacktrace, error message, or exception to analyze")


class RootCauseEvidenceResponse(BaseModel):
    source: str
    description: str
    symbol: str = ""
    file_path: str = ""
    confidence: float = 0.0


class RootCauseResponse(BaseModel):
    error_input: str
    parsed_symbols: list[str] = []
    matched_nodes: list[dict] = []
    callers: list[dict] = []
    callees: list[dict] = []
    related_issues: list[dict] = []
    static_evidence: list[RootCauseEvidenceResponse] = []
    likely_cause: str = ""
    affected_path: list[str] = []
    suggested_investigation: list[str] = []
    evidence_context: str = ""


class FixRequest(BaseModel):
    issue_title: str = Field(..., description="Title of the issue to analyze")
    issue_file: str = Field("", description="File path of the issue (for disambiguation)")
    issue_symbol: str = Field("", description="Affected symbol name (for disambiguation)")


class FixIntelligenceResponse(BaseModel):
    issue_title: str
    issue_category: str
    issue_severity: str
    problem_description: str
    evidence: dict = {}
    affected_code: list[dict] = []
    blast_radius_summary: str = ""
    recommended_approach: str = ""
    implementation_steps: list[str] = []
    related_dependencies: list[str] = []
    related_tests: list[str] = []
    fix_template: str = ""
    estimated_complexity: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/{job_id}/understand",
    response_model=RepositoryUnderstandingResponse,
    summary="Full repository understanding",
    description=(
        "The central Cortex intelligence output — complete understanding of "
        "the repository including architecture, modules, flows, health, and risks."
    ),
)
async def get_understanding(job_id: str) -> RepositoryUnderstandingResponse:
    """Get the full Cortex understanding of a repository."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    reasoner = CortexReasoner()
    understanding = reasoner.understand(
        job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges
    )

    return RepositoryUnderstandingResponse(
        job_id=understanding.job_id,
        repo_url=understanding.repo_url,
        repo_name=understanding.repo_name,
        purpose=understanding.purpose,
        headline=understanding.headline,
        architecture_style=understanding.architecture_style.value,
        architecture_description=understanding.architecture_description,
        architecture_evidence=understanding.architecture_evidence,
        languages=understanding.languages,
        frameworks=understanding.frameworks,
        total_files=understanding.total_files,
        total_lines=understanding.total_lines,
        total_modules=understanding.total_modules,
        total_classes=understanding.total_classes,
        total_functions=understanding.total_functions,
        total_endpoints=understanding.total_endpoints,
        total_tests=understanding.total_tests,
        entry_points=[
            EntryPointResponse(
                label=ep.label, node_id=ep.node_id, node_type=ep.node_type,
                file_path=ep.file_path, kind=ep.kind, method=ep.method, route=ep.route,
            )
            for ep in understanding.entry_points[:20]
        ],
        modules=[
            ModuleResponse(
                name=m.name, path=m.path, node_id=m.node_id,
                purpose=m.purpose, architecture_role=m.architecture_role,
                layer=m.layer, file_count=m.file_count,
                class_count=m.class_count, function_count=m.function_count,
                total_lines=m.total_lines, avg_complexity=m.avg_complexity,
                max_complexity=m.max_complexity,
                key_classes=m.key_classes, key_functions=m.key_functions,
                dependencies=m.dependencies, dependents=m.dependents,
                coupling_score=m.coupling_score, risks=m.risks,
                is_god_module=m.is_god_module,
            )
            for m in understanding.modules
        ],
        data_flows=[
            DataFlowResponse(
                name=f.name, entry_point=f.entry_point,
                steps=[
                    DataFlowStepResponse(
                        symbol=s.symbol, node_id=s.node_id,
                        node_type=s.node_type, file_path=s.file_path, role=s.role,
                    )
                    for s in f.steps
                ],
            )
            for f in understanding.data_flows
        ],
        overall_score=understanding.overall_score,
        overall_grade=understanding.overall_grade,
        complexity_hotspots=[
            ComplexityHotspotResponse(**h) for h in understanding.complexity_hotspots
        ],
        architectural_risks=understanding.architectural_risks,
        start_here=understanding.start_here,
        start_here_reason=understanding.start_here_reason,
        start_here_file=understanding.start_here_file,
        top_dependencies=understanding.top_dependencies,
    )


@router.get(
    "/{job_id}/explain",
    summary="Explain This Repository",
    description=(
        "Flagship feature — generates a structured 10-section explanation "
        "of the repository grounded in evidence from the knowledge graph."
    ),
)
async def explain_repository(job_id: str) -> dict:
    """Generate a structured repository explanation.

    Sections:
    1. What it does
    2. How it starts
    3. Main execution flow
    4. Architecture
    5. Important modules
    6. Important classes/functions
    7. Data flow
    8. Major dependencies
    9. Engineering risks
    10. Where to begin
    """
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    reasoner = CortexReasoner()
    u = reasoner.understand(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Build the 10-section explanation
    explanation = {
        "repo_name": u.repo_name,
        "sections": [
            {
                "title": "What It Does",
                "content": u.purpose,
                "evidence": f"Detected from {u.total_files} files across {len(u.languages)} languages. "
                            f"Frameworks: {', '.join(u.frameworks) or 'none detected'}.",
            },
            {
                "title": "How It Starts",
                "content": (
                    f"Entry point: `{u.start_here}` in `{u.start_here_file}`"
                    if u.start_here else "No clear entry point detected."
                ),
                "evidence": u.start_here_reason,
                "entry_points": [
                    {"label": ep.label, "kind": ep.kind, "file": ep.file_path}
                    for ep in u.entry_points[:5]
                ],
            },
            {
                "title": "Main Execution Flow",
                "content": (
                    f"{len(u.data_flows)} execution flows traced from entry points."
                    if u.data_flows else "No clear execution flows detected."
                ),
                "flows": [
                    {
                        "name": f.name,
                        "path": [f"{s.symbol} ({s.role})" for s in f.steps],
                    }
                    for f in u.data_flows[:5]
                ],
            },
            {
                "title": "Architecture",
                "content": u.architecture_description,
                "style": u.architecture_style.value,
                "evidence": u.architecture_evidence,
            },
            {
                "title": "Important Modules",
                "content": f"{len(u.modules)} modules detected.",
                "modules": [
                    {
                        "name": m.name,
                        "role": m.architecture_role,
                        "files": m.file_count,
                        "dependencies": m.dependencies[:3],
                        "dependents": m.dependents[:3],
                    }
                    for m in u.modules[:10]
                ],
            },
            {
                "title": "Important Classes & Functions",
                "content": "Key symbols ranked by centrality and complexity.",
                "hotspots": u.complexity_hotspots[:5],
                "key_symbols": [
                    cls
                    for m in u.modules[:5]
                    for cls in m.key_classes[:2]
                ][:10],
            },
            {
                "title": "Data Flow",
                "content": (
                    f"Traced {len(u.data_flows)} request/data flows through the system."
                ),
                "flows": [
                    {"name": f.name, "steps": len(f.steps)}
                    for f in u.data_flows[:5]
                ],
            },
            {
                "title": "Major Dependencies",
                "content": f"Top {len(u.top_dependencies)} most-depended-on components.",
                "dependencies": u.top_dependencies[:10],
            },
            {
                "title": "Engineering Risks",
                "content": (
                    f"Health score: {u.overall_score}/100 (Grade {u.overall_grade}). "
                    f"{len(u.architectural_risks)} architectural risks detected."
                ),
                "risks": u.architectural_risks[:5],
                "score": u.overall_score,
                "grade": u.overall_grade,
            },
            {
                "title": "Where to Begin",
                "content": (
                    f"Start with `{u.start_here}` — {u.start_here_reason}"
                    if u.start_here
                    else "Start by browsing the module list to find the most relevant area."
                ),
                "start_file": u.start_here_file,
                "recommended_order": [m.name for m in u.modules[:5]],
            },
        ],
    }

    return explanation


@router.get(
    "/{job_id}/learning-path",
    response_model=LearningPathResponse,
    summary="Repository-specific learning path",
    description=(
        "Generates an onboarding path using graph topology: "
        "START HERE → FOUNDATIONS → CORE FLOW → MODULES → ADVANCED → RISKS"
    ),
)
async def get_learning_path(job_id: str) -> LearningPathResponse:
    """Get the repository-specific learning path."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    # Get understanding first (shared foundation)
    reasoner = CortexReasoner()
    understanding = reasoner.understand(
        job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges
    )

    # Generate learning path
    generator = LearningPathGenerator()
    path = generator.generate(understanding, nodes, edges)

    def _step_response(step: object) -> LearningStepResponse:
        return LearningStepResponse(
            order=step.order,
            title=step.title,
            what_to_read=step.what_to_read,
            why=step.why,
            symbols=step.symbols,
            prerequisites=step.prerequisites,
            difficulty=step.difficulty.value,
            what_to_understand=step.what_to_understand,
            module=step.module,
            estimated_minutes=step.estimated_minutes,
        )

    return LearningPathResponse(
        repo_name=path.repo_name,
        total_steps=path.total_steps,
        estimated_hours=path.estimated_hours,
        start_here=[_step_response(s) for s in path.start_here],
        foundations=[_step_response(s) for s in path.foundations],
        core_flow=[_step_response(s) for s in path.core_flow],
        important_modules=[_step_response(s) for s in path.important_modules],
        advanced_areas=[_step_response(s) for s in path.advanced_areas],
        known_risks=[_step_response(s) for s in path.known_risks],
    )


@router.post(
    "/{job_id}/root-cause",
    response_model=RootCauseResponse,
    summary="Root-cause analysis",
    description=(
        "Parse a stacktrace/error, match symbols to the knowledge graph, "
        "find callers/callees/dependencies, and build evidence for diagnosis."
    ),
)
async def analyze_root_cause(job_id: str, request: RootCauseRequest) -> RootCauseResponse:
    """Perform root-cause analysis on a stacktrace or error message."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    # Optionally compute insights for cross-referencing
    engine = InsightsEngine()
    report = engine.compute(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Run root-cause analysis
    analyzer = RootCauseAnalyzer()
    result = analyzer.analyze(
        error_input=request.error_input,
        nodes=nodes,
        edges=edges,
        insights_report=report,
    )

    return RootCauseResponse(
        error_input=result.error_input,
        parsed_symbols=result.parsed_symbols,
        matched_nodes=result.matched_nodes,
        callers=result.callers,
        callees=result.callees,
        related_issues=result.related_issues,
        static_evidence=[
            RootCauseEvidenceResponse(
                source=e.source, description=e.description,
                symbol=e.symbol, file_path=e.file_path, confidence=e.confidence,
            )
            for e in result.static_evidence
        ],
        likely_cause=result.likely_cause,
        affected_path=result.affected_path,
        suggested_investigation=result.suggested_investigation,
        evidence_context=result.evidence_context,
    )


@router.post(
    "/{job_id}/fix",
    response_model=FixIntelligenceResponse,
    summary="Issue → Fix intelligence",
    description=(
        "For a selected engineering issue, returns the full fix context: "
        "problem, evidence, impact, affected code, recommended approach, "
        "and implementation steps."
    ),
)
async def get_fix_intelligence(job_id: str, request: FixRequest) -> FixIntelligenceResponse:
    """Get fix intelligence for a specific issue."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    # Find the issue from insights
    engine = InsightsEngine()
    report = engine.compute(job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges)

    # Find matching issue
    target_issue = None
    for issue in report.issues:
        title_match = issue.title.lower() == request.issue_title.lower()
        file_match = not request.issue_file or issue.file_path == request.issue_file
        symbol_match = not request.issue_symbol or issue.affected_symbol == request.issue_symbol

        if title_match and file_match and symbol_match:
            target_issue = issue
            break

    # Fallback: partial title match
    if not target_issue:
        for issue in report.issues:
            if request.issue_title.lower() in issue.title.lower():
                target_issue = issue
                break

    if not target_issue:
        raise HTTPException(
            status_code=404,
            detail=f"Issue '{request.issue_title}' not found in insights report"
        )

    # Run fix intelligence
    fix_engine = FixIntelligenceEngine()
    fix = fix_engine.analyze(issue=target_issue, nodes=nodes, edges=edges)

    return FixIntelligenceResponse(
        issue_title=fix.issue_title,
        issue_category=fix.issue_category,
        issue_severity=fix.issue_severity,
        problem_description=fix.problem_description,
        evidence=fix.evidence,
        affected_code=fix.affected_code,
        blast_radius_summary=fix.blast_radius_summary,
        recommended_approach=fix.recommended_approach,
        implementation_steps=fix.implementation_steps,
        related_dependencies=fix.related_dependencies,
        related_tests=fix.related_tests,
        fix_template=fix.fix_template,
        estimated_complexity=fix.estimated_complexity,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Module Intelligence Endpoint
# ═══════════════════════════════════════════════════════════════════════════════


class ModuleDetailResponse(BaseModel):
    """Rich intelligence about a single module."""
    name: str
    path: str
    node_id: str
    purpose: str = ""
    responsibilities: list[str] = []
    architecture_role: str = ""
    layer: str = ""
    # Structure
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    total_lines: int = 0
    # Metrics
    avg_complexity: float = 0.0
    max_complexity: int = 0
    coupling_score: float = 0.0
    cohesion_score: float = 0.0
    # Key symbols
    public_symbols: list[str] = []
    key_classes: list[str] = []
    key_functions: list[str] = []
    # Relationships
    dependencies: list[str] = []
    dependents: list[str] = []
    # Health
    risks: list[str] = []
    is_god_module: bool = False
    has_circular_deps: bool = False
    # Important interactions (with other modules)
    interactions: list[dict] = []


class ModuleListResponse(BaseModel):
    """All modules with their intelligence."""
    repo_name: str
    total_modules: int
    architecture_style: str
    modules: list[ModuleDetailResponse]
    # Suspicious modules flagged
    god_modules: list[str] = []
    highly_coupled: list[str] = []
    boundary_violations: list[str] = []


@router.get(
    "/{job_id}/modules",
    response_model=ModuleListResponse,
    summary="Module intelligence — all modules with rich analysis",
    description=(
        "Infers modules from graph connectivity (not just directories). "
        "For each module: purpose, responsibilities, public surface, "
        "dependencies, dependents, key symbols, architecture role, risks."
    ),
)
async def get_modules(job_id: str) -> ModuleListResponse:
    """Get full module intelligence for the repository."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    reasoner = CortexReasoner()
    understanding = reasoner.understand(
        job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges
    )

    # Detect circular dependencies between modules
    circular_pairs = _detect_circular_dependencies(understanding.modules)

    # Build interaction map
    module_interactions = _build_module_interactions(understanding.modules, edges, nodes)

    modules_response = []
    for m in understanding.modules:
        has_circular = m.name in circular_pairs
        interactions = module_interactions.get(m.name, [])

        modules_response.append(ModuleDetailResponse(
            name=m.name,
            path=m.path,
            node_id=m.node_id,
            purpose=m.purpose,
            responsibilities=m.responsibilities,
            architecture_role=m.architecture_role,
            layer=m.layer,
            file_count=m.file_count,
            class_count=m.class_count,
            function_count=m.function_count,
            total_lines=m.total_lines,
            avg_complexity=m.avg_complexity,
            max_complexity=m.max_complexity,
            coupling_score=m.coupling_score,
            cohesion_score=m.cohesion_score,
            public_symbols=m.public_symbols,
            key_classes=m.key_classes,
            key_functions=m.key_functions,
            dependencies=m.dependencies,
            dependents=m.dependents,
            risks=m.risks,
            is_god_module=m.is_god_module,
            has_circular_deps=has_circular,
            interactions=interactions[:10],
        ))

    return ModuleListResponse(
        repo_name=understanding.repo_name,
        total_modules=len(modules_response),
        architecture_style=understanding.architecture_style.value,
        modules=modules_response,
        god_modules=[m.name for m in understanding.modules if m.is_god_module],
        highly_coupled=[
            m.name for m in understanding.modules if m.coupling_score > 0.6
        ],
        boundary_violations=[
            m.name for m in understanding.modules
            if m.has_circular_deps or m.name in circular_pairs
        ],
    )


@router.get(
    "/{job_id}/modules/{module_name}",
    response_model=ModuleDetailResponse,
    summary="Single module detail",
    description="Get rich intelligence for a specific module by name.",
)
async def get_module_detail(job_id: str, module_name: str) -> ModuleDetailResponse:
    """Get detailed intelligence for a specific module."""
    job = await job_repository.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    nodes = await graph_repository.get_nodes_by_job(job_id)
    edges = await graph_repository.get_edges_by_job(job_id)

    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")

    reasoner = CortexReasoner()
    understanding = reasoner.understand(
        job_id=job_id, repo_url=job.repo_url, nodes=nodes, edges=edges
    )

    # Find the requested module (case-insensitive)
    target = None
    for m in understanding.modules:
        if m.name.lower() == module_name.lower():
            target = m
            break

    if not target:
        # Try partial match
        for m in understanding.modules:
            if module_name.lower() in m.name.lower():
                target = m
                break

    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' not found. "
                   f"Available: {', '.join(m.name for m in understanding.modules[:10])}"
        )

    circular_pairs = _detect_circular_dependencies(understanding.modules)
    module_interactions = _build_module_interactions(understanding.modules, edges, nodes)

    return ModuleDetailResponse(
        name=target.name,
        path=target.path,
        node_id=target.node_id,
        purpose=target.purpose,
        responsibilities=target.responsibilities,
        architecture_role=target.architecture_role,
        layer=target.layer,
        file_count=target.file_count,
        class_count=target.class_count,
        function_count=target.function_count,
        total_lines=target.total_lines,
        avg_complexity=target.avg_complexity,
        max_complexity=target.max_complexity,
        coupling_score=target.coupling_score,
        cohesion_score=target.cohesion_score,
        public_symbols=target.public_symbols,
        key_classes=target.key_classes,
        key_functions=target.key_functions,
        dependencies=target.dependencies,
        dependents=target.dependents,
        risks=target.risks,
        is_god_module=target.is_god_module,
        has_circular_deps=target.name in circular_pairs,
        interactions=module_interactions.get(target.name, [])[:10],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _detect_circular_dependencies(modules: list) -> set[str]:
    """Detect modules that have circular dependencies with each other."""
    circular: set[str] = set()
    dep_map = {m.name: set(m.dependencies) for m in modules}

    for module in modules:
        for dep_name in module.dependencies:
            if dep_name in dep_map and module.name in dep_map[dep_name]:
                circular.add(module.name)
                circular.add(dep_name)

    return circular


def _build_module_interactions(
    modules: list, edges: list, nodes: list
) -> dict[str, list[dict]]:
    """Build a map of inter-module interactions."""
    from collections import defaultdict
    from cortex.graph.domain.entities import NodeType, RelationshipType

    interactions: dict[str, list[dict]] = defaultdict(list)

    for module in modules:
        for dep_name in module.dependencies[:5]:
            interactions[module.name].append({
                "target": dep_name,
                "direction": "depends_on",
                "description": f"{module.name} imports from {dep_name}",
            })
        for dep_name in module.dependents[:5]:
            interactions[module.name].append({
                "target": dep_name,
                "direction": "depended_by",
                "description": f"{dep_name} depends on {module.name}",
            })

    return dict(interactions)
