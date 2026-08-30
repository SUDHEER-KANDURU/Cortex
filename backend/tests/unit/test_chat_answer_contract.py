"""Tests for chat's migration to the unified answer contract (Task 9).

Covers:
  - Req 4.5: intent → Answer Producer selection replaces the old `_format_*`
    formatters.
  - Req 9.1: with no NIM key, chat produces a rendered `CortexAnswer` purely
    from deterministic analysis.
  - Req 9.2: NIM only rewords; facts/evidence/epistemic tags come from the
    original `CortexAnswer`, not from NIM.
  - Req 9.3: when NIM refinement fails/returns unusable output, chat falls back
    to the original rendered `CortexAnswer` unchanged.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from cortex.chat.application.chat_service import ChatService
from cortex.chat.domain.entities import ChatSession
from cortex.chat.infrastructure.context_retriever import QueryIntent
from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.reasoning.application.answer_serializer import render_answer_markdown
from cortex.reasoning.application.producers import (
    ApiSpecProducer,
    ArchitectureOverviewProducer,
    InterviewPrepProducer,
    LearningPathProducer,
    ModuleBreakdownProducer,
)
from cortex.reasoning.domain.answer import (
    AnswerSection,
    Claim,
    CortexAnswer,
    Epistemic,
    Evidence,
    NextAction,
    NextActionKind,
)
from cortex.reasoning.domain.entities import (
    ArchitectureStyle,
    ModuleIntelligence,
    RepositoryUnderstanding,
)

_JOB = "chat-task9-001"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _understanding() -> RepositoryUnderstanding:
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/ts-app",
        repo_name="ts-app",
        purpose="A web API server.",
        headline="A TypeScript web service.",
        architecture_style=ArchitectureStyle.MODULAR,
        architecture_description="Modular architecture.",
        languages=["typescript"],
        frameworks=["express"],
        total_files=20,
        total_lines=2000,
        total_modules=2,
        total_classes=10,
        total_functions=40,
        total_endpoints=1,
        top_dependencies=["express"],
        start_here_file="src/index.ts",
    )
    u.modules = [
        ModuleIntelligence(
            name="routes",
            path="src/routes",
            node_id="mod-routes",
            key_classes=["UserController"],
            dependencies=["services"],
            file_count=3,
            class_count=2,
            function_count=8,
            total_lines=300,
            architecture_role="api",
        ),
        ModuleIntelligence(
            name="services",
            path="src/services",
            node_id="mod-services",
            file_count=2,
            class_count=1,
            function_count=6,
            total_lines=250,
            architecture_role="core",
        ),
    ]
    return u


def _endpoint_nodes() -> list[GraphNode]:
    return [
        GraphNode(
            id="ep1",
            label="getUser",
            node_type=NodeType.ENDPOINT,
            job_id=_JOB,
            properties={
                "route_info": "/users/{id}",
                "http_method": "get",
                "file": "src/routes/user.ts",
                "line": 10,
            },
        )
    ]


def _service_no_nim() -> ChatService:
    """A ChatService whose NIM is disabled (offline path)."""
    svc = ChatService()
    svc._use_nim = False
    return svc


# ── Req 4.5: intent → producer selection ─────────────────────────────────────


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (QueryIntent.ARCHITECTURE, ArchitectureOverviewProducer),
        (QueryIntent.METRICS, ArchitectureOverviewProducer),
        (QueryIntent.EXPLANATION, ArchitectureOverviewProducer),
        (QueryIntent.GENERAL, ArchitectureOverviewProducer),
        (QueryIntent.ENTRY_POINT, ApiSpecProducer),
        (QueryIntent.DATA_FLOW, ApiSpecProducer),
        (QueryIntent.LEARNING, LearningPathProducer),
        (QueryIntent.COMPLEXITY, InterviewPrepProducer),
        (QueryIntent.DEBUGGING, InterviewPrepProducer),
        (QueryIntent.NAVIGATION, ModuleBreakdownProducer),
        (QueryIntent.DEPENDENCY, ModuleBreakdownProducer),
    ],
)
def test_intent_maps_to_expected_producer(intent, expected) -> None:
    svc = _service_no_nim()
    producer = svc._select_producer(intent, _understanding(), [], [])
    assert isinstance(producer, expected)


def test_api_spec_producer_receives_endpoint_nodes() -> None:
    """ApiSpecProducer must be handed the graph nodes so it can read endpoints."""
    svc = _service_no_nim()
    nodes = _endpoint_nodes()
    producer = svc._select_producer(
        QueryIntent.DATA_FLOW, _understanding(), nodes, []
    )
    answer = producer.produce()
    text = render_answer_markdown(answer)
    # The endpoint (a FACT) came from the graph node we passed in.
    assert "/users/{id}" in text


# ── Serializer renders a CortexAnswer with tags + evidence ───────────────────


def test_render_answer_markdown_includes_tags_and_evidence() -> None:
    answer = CortexAnswer(
        intent="demo",
        title="Demo Answer",
        summary="A short summary.",
        sections=[
            AnswerSection(
                heading="Overview",
                claims=[
                    Claim(
                        text="There are 3 files.",
                        epistemic=Epistemic.FACT,
                        evidence=[Evidence(file_path="src/app.ts", line_start=1)],
                    ),
                    Claim(
                        text="It looks layered.",
                        epistemic=Epistemic.INFERENCE,
                        evidence=[Evidence(file_path="repo")],
                    ),
                ],
            )
        ],
        confidence=0.7,
        coverage_note="Thin analysis.",
        next_actions=[
            NextAction(label="Open app.ts", kind=NextActionKind.OPEN_FILE, target="src/app.ts")
        ],
    )
    text = render_answer_markdown(answer)
    assert "## Demo Answer" in text
    assert "A short summary." in text
    assert "### Overview" in text
    assert "[Fact]" in text
    assert "[Inference]" in text
    assert "src/app.ts:1" in text
    assert "Coverage: Thin analysis." in text
    assert "Open app.ts" in text


# ── Req 9.1: offline path produces a rendered CortexAnswer ───────────────────


def test_offline_generate_answer_returns_rendered_cortex_answer(monkeypatch) -> None:
    svc = _service_no_nim()

    async def fake_nodes(job_id):
        return _endpoint_nodes() + [
            GraphNode(id="m1", label="routes", node_type=NodeType.MODULE, job_id=_JOB)
        ]

    async def fake_edges(job_id):
        return []

    import cortex.graph.infrastructure.dependencies as deps

    monkeypatch.setattr(deps.graph_repository, "get_nodes_by_job", fake_nodes)
    monkeypatch.setattr(deps.graph_repository, "get_edges_by_job", fake_edges)

    # Force a deterministic understanding so the test doesn't depend on the
    # full reasoner pipeline; the point is that a producer emits the answer.
    from cortex.reasoning.application import reasoner as reasoner_mod

    monkeypatch.setattr(
        reasoner_mod.CortexReasoner,
        "understand",
        lambda self, **kwargs: _understanding(),
    )
    # Avoid the entity-explainer path claiming the question.
    monkeypatch.setattr(
        ChatService, "_try_entity_explanation", lambda self, q, n, e: None
    )

    async def run():
        return await svc._generate_answer(
            _JOB, "what is the architecture?", "raw context"
        )

    cortex_answer, draft = asyncio.run(run())
    assert isinstance(cortex_answer, CortexAnswer)
    assert cortex_answer.intent == "architecture_overview"
    # The draft is the rendered form of the same answer.
    assert draft == render_answer_markdown(cortex_answer)
    assert "Architecture Overview" in draft


# ── Req 9.2 / 9.3: NIM failure falls back to the original answer ─────────────


def _seed_stream(svc: ChatService, monkeypatch) -> CortexAnswer:
    """Patch graph + reasoner so stream_response builds a known CortexAnswer."""
    answer = ArchitectureOverviewProducer(_understanding()).produce()

    async def fake_generate(job_id, question, context):
        return answer, render_answer_markdown(answer)

    monkeypatch.setattr(svc, "_generate_answer", fake_generate)

    async def fake_resolve(job_id):
        return None

    monkeypatch.setattr(svc, "_resolve_repo_url", fake_resolve)

    # In-memory repo stub — persistence must still work.
    async def add_message(session_id, msg):
        return None

    monkeypatch.setattr(svc._repo, "add_message", add_message)

    async def retrieve(job_id, msg, repo_url=None):
        return "raw context"

    monkeypatch.setattr(svc._retriever, "retrieve", retrieve)
    return answer


async def _collect(gen: AsyncGenerator[str, None]) -> str:
    out = []
    async for chunk in gen:
        out.append(chunk)
    return "".join(out)


def test_nim_failure_falls_back_to_original_answer(monkeypatch) -> None:
    svc = ChatService()
    svc._use_nim = True
    answer = _seed_stream(svc, monkeypatch)
    expected = render_answer_markdown(answer)

    async def failing_stream(messages):
        yield "Sorry — I couldn't connect to the AI service. All available models are unavailable."

    monkeypatch.setattr(svc._nim, "stream", failing_stream)

    session = ChatSession(id="s1", job_id=_JOB)

    async def run():
        return await _collect(svc.stream_response(session, "explain the architecture"))

    result = asyncio.run(run())
    # On NIM failure we stream the ORIGINAL rendered CortexAnswer unchanged.
    assert result.strip() == expected.strip()
    # Facts/evidence are those authored by the producer, not by NIM.
    assert "Architecture Overview" in result


def test_nim_reword_keeps_original_facts(monkeypatch) -> None:
    """NIM may reword, but the authoritative facts/evidence live in the original
    CortexAnswer — the draft handed to NIM carries them, and on any unusable
    output we return that original unchanged."""
    svc = ChatService()
    svc._use_nim = True
    answer = _seed_stream(svc, monkeypatch)

    captured = {}

    async def empty_stream(messages):
        # NIM returns unusable (empty) output → must fall back to original.
        captured["messages"] = messages
        if False:
            yield ""  # make this an async generator
        return

    monkeypatch.setattr(svc._nim, "stream", empty_stream)

    session = ChatSession(id="s2", job_id=_JOB)

    async def run():
        return await _collect(svc.stream_response(session, "explain the architecture"))

    result = asyncio.run(run())
    # Unusable NIM output → original rendered answer is returned unchanged.
    assert result.strip() == render_answer_markdown(answer).strip()
    # The draft handed to NIM contained the producer's facts (evidence pointers),
    # proving NIM was only asked to reword pre-authored facts.
    draft_msg = captured["messages"][-1]["content"]
    assert "DRAFT ANSWER" in draft_msg
    assert "evidence:" in draft_msg
