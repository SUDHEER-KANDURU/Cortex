"""Navigate API router — full-depth code exploration endpoints.

Endpoints:
  GET  /api/v1/navigate/{job_id}/{node_id}           — Full navigation context
  GET  /api/v1/navigate/{job_id}/{node_id}/impact     — Impact analysis
  POST /api/v1/navigate/{job_id}/{node_id}/explain    — AI explanation
  POST /api/v1/navigate/{job_id}/explain              — Scoped explanation (file + line range)
"""

from __future__ import annotations

import structlog
from cortex.chat.infrastructure.nim_client import NIMClient
from cortex.config import get_settings
from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.navigate.models import (
    AnswerSectionResponse,
    ClaimResponse,
    ConnectedNode,
    CortexAnswerResponse,
    EvidenceResponse,
    ExplanationSectionResponse,
    NavigateExplainRequest,
    NavigateExplainResponse,
    NavigateResponse,
    NextActionResponse,
    ScopedExplainRequest,
)
from cortex.navigate.service import NavigateService
from cortex.reasoning.application.explainer import CortexExplainer
from cortex.reasoning.application.scoped_explanation import ScopedExplanationProducer
from cortex.reasoning.domain.answer import CortexAnswer
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger()

router = APIRouter(prefix="/navigate", tags=["navigate"])

_service = NavigateService()
_explainer = CortexExplainer()


def _serialize_answer(answer: CortexAnswer) -> CortexAnswerResponse:
    """Map a domain `CortexAnswer` onto its Pydantic response model."""
    return CortexAnswerResponse(
        intent=answer.intent,
        title=answer.title,
        summary=answer.summary,
        sections=[
            AnswerSectionResponse(
                heading=section.heading,
                claims=[
                    ClaimResponse(
                        text=claim.text,
                        epistemic=claim.epistemic.value,
                        evidence=[
                            EvidenceResponse(
                                file_path=ev.file_path,
                                line_start=ev.line_start,
                                line_end=ev.line_end,
                                node_id=ev.node_id,
                            )
                            for ev in claim.evidence
                        ],
                    )
                    for claim in section.claims
                ],
            )
            for section in answer.sections
        ],
        confidence=answer.confidence,
        coverage_note=answer.coverage_note,
        next_actions=[
            NextActionResponse(
                label=na.label,
                kind=na.kind.value,
                target=na.target,
                line_start=na.line_start,
                line_end=na.line_end,
            )
            for na in answer.next_actions
        ],
    )


@router.get(
    "/{job_id}/{node_id}",
    response_model=NavigateResponse,
    summary="Full navigation context for an entity",
    description=(
        "Returns comprehensive navigation data: definition, callers, callees, "
        "dependencies, dependents, related tests, issues, insights, breadcrumb, "
        "and call paths. This is the primary Navigate endpoint."
    ),
)
async def get_navigate(job_id: str, node_id: str) -> NavigateResponse:
    """Get full navigation context for a graph entity."""
    result = await _service.get_navigation_context(job_id, node_id)
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@router.get(
    "/{job_id}/{node_id}/impact",
    response_model=list[ConnectedNode],
    summary="Impact analysis",
    description=(
        "Compute what might be affected if this entity changes. "
        "Traverses dependents transitively via BFS."
    ),
)
async def get_impact(job_id: str, node_id: str) -> list[ConnectedNode]:
    """Get impact analysis — what breaks if this changes."""
    result = await _service.get_impact_analysis(job_id, node_id)
    return result


@router.post(
    "/{job_id}/{node_id}/explain",
    response_model=NavigateExplainResponse,
    summary="Explain this entity (Cortex's own analysis)",
    description=(
        "Cortex explains what this file/class/function is, what it does, how it "
        "works, who uses it, what it uses, how it fits into the architecture, its "
        "risks, and what to read next — derived deterministically from the "
        "knowledge graph (AST + metrics + relationships). If a NIM key is "
        "configured, NIM refines the wording only; Cortex's facts are authoritative. "
        "Works fully without NIM."
    ),
)
async def explain_entity(
    job_id: str, node_id: str, request: NavigateExplainRequest
) -> NavigateExplainResponse:
    """Explain an entity. Cortex is the author; NIM (if present) only refines."""
    # ── Load the job's graph and build Cortex's own explanation FIRST ─────────
    nodes = await graph_repository.get_nodes_by_job(job_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")
    edges = await graph_repository.get_edges_by_job(job_id)

    explanation = _explainer.explain_node(node_id, nodes, edges)
    if explanation is None:
        raise HTTPException(status_code=404, detail="Node not found")

    # Cortex's deterministic explanation is the source of truth.
    draft_md = explanation.to_markdown()
    source = "cortex"

    # ── Optional NIM refinement of WORDING ONLY (facts stay Cortex's) ─────────
    settings = get_settings()
    if settings.nim_api_key:
        evidence_text = "\n".join(f"- {e}" for e in explanation.evidence)
        refined = await NIMClient(settings.nim_api_key).refine(draft_md, evidence_text)
        if refined and refined != draft_md:
            draft_md = refined
            source = "cortex+nim"

    return NavigateExplainResponse(
        explanation=draft_md,
        sections=[
            ExplanationSectionResponse(
                key=s.key, heading=s.heading, body=s.body, evidence=s.evidence
            )
            for s in explanation.sections
        ],
        headline=explanation.headline,
        architectural_role=explanation.architectural_role,
        read_next=explanation.read_next,
        evidence_used=explanation.evidence,
        confidence=explanation.confidence,
        source=source,
    )


@router.post(
    "/{job_id}/explain",
    response_model=CortexAnswerResponse,
    summary="Scoped explanation of a file + line range",
    description=(
        "Resolves a file and line range to the graph node(s) whose span overlaps "
        "those lines (picking the most specific inner symbol, or falling back to "
        "whole-file scope when nothing inner matches), then returns a scoped "
        "explanation as a CortexAnswer. The answer includes the selected code's "
        "callers, callees, and inferred role where available. Grounded "
        "deterministically in the knowledge graph — no NIM required."
    ),
)
async def explain_scope(
    job_id: str, request: ScopedExplainRequest
) -> CortexAnswerResponse:
    """Explain a file + line range (Req 7.3, Req 7.4)."""
    nodes = await graph_repository.get_nodes_by_job(job_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="No graph data for this job")
    edges = await graph_repository.get_edges_by_job(job_id)

    producer = ScopedExplanationProducer(nodes=nodes, edges=edges)
    answer = producer.produce(
        file_path=request.file_path,
        line_start=request.line_start,
        line_end=request.line_end,
        question=request.question,
    )
    return _serialize_answer(answer)
