"""Navigate API router — full-depth code exploration endpoints.

Endpoints:
  GET  /api/v1/navigate/{job_id}/{node_id}           — Full navigation context
  GET  /api/v1/navigate/{job_id}/{node_id}/impact     — Impact analysis
  POST /api/v1/navigate/{job_id}/{node_id}/explain    — AI explanation
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from cortex.chat.infrastructure.nim_client import NIMClient
from cortex.config import get_settings
from cortex.navigate.models import (
    ConnectedNode,
    NavigateExplainRequest,
    NavigateExplainResponse,
    NavigateResponse,
)
from cortex.navigate.service import NavigateService

logger = structlog.get_logger()

router = APIRouter(prefix="/navigate", tags=["navigate"])

_service = NavigateService()


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
    summary="AI explanation of an entity",
    description=(
        "Uses NIM to explain how this entity fits into the system, "
        "grounded in the navigation evidence (relationships, source, metrics)."
    ),
)
async def explain_entity(
    job_id: str, node_id: str, request: NavigateExplainRequest
) -> NavigateExplainResponse:
    """Get an AI explanation of this entity, grounded in graph evidence."""
    settings = get_settings()
    if not settings.nim_api_key:
        raise HTTPException(
            status_code=503,
            detail="NIM API key not configured. AI explanation unavailable.",
        )

    # First get the full navigation context
    nav_context = await _service.get_navigation_context(job_id, node_id)
    if not nav_context:
        raise HTTPException(status_code=404, detail="Node not found")

    # Build the evidence summary for the AI
    evidence_parts: list[str] = []

    # Definition
    evidence_parts.append(
        f"Entity: {nav_context.node_type} '{nav_context.label}' "
        f"at {nav_context.source.file_path}:{nav_context.source.line_start}"
    )

    # Callers
    if nav_context.callers:
        callers_str = ", ".join(f"{c.label} ({c.node_type})" for c in nav_context.callers[:5])
        evidence_parts.append(f"Called by: {callers_str}")

    # Callees
    if nav_context.callees:
        callees_str = ", ".join(f"{c.label} ({c.node_type})" for c in nav_context.callees[:5])
        evidence_parts.append(f"Calls: {callees_str}")

    # Dependencies
    if nav_context.dependencies:
        deps_str = ", ".join(f"{d.label} ({d.node_type})" for d in nav_context.dependencies[:5])
        evidence_parts.append(f"Depends on: {deps_str}")

    # Dependents
    if nav_context.dependents:
        deps_str = ", ".join(f"{d.label} ({d.node_type})" for d in nav_context.dependents[:5])
        evidence_parts.append(f"Depended on by: {deps_str}")

    # Tests
    if nav_context.tests:
        tests_str = ", ".join(t.label for t in nav_context.tests[:5])
        evidence_parts.append(f"Tested by: {tests_str}")

    # Insights
    ins = nav_context.insights
    if ins.complexity > 0:
        evidence_parts.append(f"Complexity: {ins.complexity}")
    if ins.risk_factors:
        evidence_parts.append(f"Risks: {'; '.join(ins.risk_factors)}")
    if ins.issues:
        issues_str = "; ".join(f"{i.title} ({i.severity})" for i in ins.issues[:3])
        evidence_parts.append(f"Issues: {issues_str}")

    # Breadcrumb (architectural position)
    if nav_context.breadcrumb:
        path_str = " > ".join(f"{b.label}" for b in nav_context.breadcrumb)
        evidence_parts.append(f"Architectural path: {path_str}")

    evidence_text = "\n".join(f"- {p}" for p in evidence_parts)

    # Build the prompt
    user_question = request.question or "Explain how this entity fits into the system architecture."

    system_msg = (
        "You are Cortex, an AI Engineering Copilot. You are explaining a specific "
        "code entity to a developer who wants to understand how it fits into the system.\n\n"
        "Rules:\n"
        "- Only reference facts from the evidence provided below\n"
        "- Never invent relationships or file paths\n"
        "- Be concise but thorough\n"
        "- Show architectural context\n"
        "- Highlight risks and important connections\n"
        "- If evidence is limited, say so clearly\n"
    )

    user_msg = (
        f"## Evidence from Knowledge Graph\n\n{evidence_text}\n\n"
        f"## Question\n\n{user_question}"
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    # Call NIM (non-streaming for this endpoint)
    nim = NIMClient(settings.nim_api_key)
    response_chunks: list[str] = []

    async for chunk in nim.stream(messages, temperature=0.4, max_tokens=800):
        response_chunks.append(chunk)

    explanation = "".join(response_chunks)

    return NavigateExplainResponse(
        explanation=explanation,
        evidence_used=evidence_parts,
        confidence=min(len(evidence_parts) / 8.0, 1.0),  # more evidence = higher confidence
    )
