"""Determinism and offline verification (Task 20).

Two focused properties that the whole spec rests on:

1. **Determinism (Req 11.1).** Cortex produces identical understanding and
   answers for identical repository inputs across runs. We run the real pipeline
   (parse → graph → understand → produce) twice on byte-identical input and
   assert *structurally-identical* output: understanding facts, the graph's
   node ``(type, label)`` sets, AND every producer's fully-serialized
   ``CortexAnswer`` (title, summary, section headings, and each claim's text +
   epistemic tag + evidence pointers). Volatile UUID node ids are deliberately
   excluded — identity is keyed by ``type + label`` — so the comparison tracks
   meaning, not incidental allocation order. This complements the per-language
   determinism checks in ``test_reference_repos.py`` with one dedicated,
   explicit whole-answer determinism test.

2. **Offline / no-ML (Req 9.4).** Cortex requires no ML model, training data, or
   external API for any feature. We generate EVERY answer type — the five
   repository producers (ArchitectureOverview, ModuleBreakdown, ApiSpec,
   LearningPath, InterviewPrep) plus the ScopedExplanation producer — purely
   from the deterministic layer with NIM DISABLED (no key configured) and assert
   each is a valid ``CortexAnswer`` via ``assert_valid_answer`` with no network
   dependency. We also drive the ``ChatService`` offline branch
   (``_use_nim=False``, graph + reasoner stubbed as in ``test_chat_answer_contract``)
   and assert it yields a rendered ``CortexAnswer`` from a producer without ever
   touching NIM.

Both tests run entirely on the in-process engine — no database, no HTTP, no NIM.
"""

from __future__ import annotations

import asyncio

import pytest
from cortex.chat.application.chat_service import ChatService
from cortex.chat.domain.entities import ChatSession
from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.reasoning.application.answer_serializer import render_answer_markdown
from cortex.reasoning.application.producers import (
    ApiSpecProducer,
    ArchitectureOverviewProducer,
    InterviewPrepProducer,
    LearningPathProducer,
    ModuleBreakdownProducer,
)
from cortex.reasoning.application.scoped_explanation import ScopedExplanationProducer
from cortex.reasoning.domain.answer import (
    CortexAnswer,
    Epistemic,
    assert_valid_answer,
)

# Reuse the real reference-repo fixtures and the real pipeline driver from the
# Task 19 suite rather than duplicating them. This keeps determinism/offline
# assertions anchored to the exact same inputs the regression suite snapshots.
from tests.integration.test_reference_repos import (
    PYTHON_REPO,
    REFERENCE_REPOS,
    AnalyzedRepo,
    _analyze,
    _param,
)

# The repository-level producers (Tasks 7-8) that every repo can emit.
_REPO_PRODUCERS = (
    ArchitectureOverviewProducer,
    ModuleBreakdownProducer,
    ApiSpecProducer,
    LearningPathProducer,
    InterviewPrepProducer,
)

_ALL_LANG_PARAMS = [_param(lang) for lang in REFERENCE_REPOS]


# ═══════════════════════════════════════════════════════════════════════════════
# Serialization helpers — turn a CortexAnswer into a stable, comparable value
# that ignores volatile node UUIDs but captures everything meaningful.
# ═══════════════════════════════════════════════════════════════════════════════


def _serialize_answer(answer: CortexAnswer) -> tuple:
    """A hashable, UUID-free serialization of everything meaningful in an answer.

    Captures title, summary, each section heading, and for every claim its text,
    epistemic tag, and evidence pointers keyed by ``file_path`` + line range
    (NOT ``node_id``, which is a volatile UUID). Two answers with this same value
    are structurally identical for determinism purposes (Req 11.1).
    """
    return (
        answer.intent,
        answer.title,
        answer.summary,
        answer.confidence,
        answer.coverage_note,
        tuple(
            (
                section.heading,
                tuple(
                    (
                        claim.text,
                        claim.epistemic.value,
                        tuple(
                            (ev.file_path, ev.line_start, ev.line_end)
                            for ev in claim.evidence
                        ),
                    )
                    for claim in section.claims
                ),
            )
            for section in answer.sections
        ),
        tuple((a.label, a.kind.value, a.target) for a in answer.next_actions),
    )


def _keyed_nodes(nodes: list[GraphNode]) -> set[tuple[str, str]]:
    """Node identity keyed by ``(type, label)`` — never the volatile UUID id."""
    return {(n.node_type.value, n.label) for n in nodes}


def _understanding_facts(u: object) -> tuple:
    return (
        tuple(sorted(u.languages)),
        u.total_files,
        u.total_classes,
        u.total_functions,
        u.total_modules,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Determinism across repeated runs (Req 11.1).
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_identical_inputs_yield_identical_outputs(lang: str) -> None:
    """Two runs over byte-identical input produce structurally-identical output.

    Asserts identity of (a) understanding facts, (b) graph node ``(type, label)``
    sets, and (c) every producer's fully-serialized ``CortexAnswer`` — title,
    summary, section headings, and each claim's text + epistemic tag + evidence.
    UUID node ids are excluded on purpose; identity is keyed by type + label.
    """
    repo = REFERENCE_REPOS[lang]

    first = _analyze(repo)
    second = _analyze(repo)

    # (a) Understanding facts are identical.
    assert _understanding_facts(first.understanding) == _understanding_facts(
        second.understanding
    ), f"{repo.name}: understanding facts differ across runs"

    # (b) Graph node (type, label) sets are identical (UUIDs excluded).
    assert _keyed_nodes(first.nodes) == _keyed_nodes(second.nodes), (
        f"{repo.name}: graph node type+label set differs across runs"
    )

    # (c) Every producer's serialized answer is identical across runs.
    for producer_cls in _REPO_PRODUCERS:
        ans_a = producer_cls(
            first.understanding, nodes=first.nodes, edges=first.edges
        ).produce()
        ans_b = producer_cls(
            second.understanding, nodes=second.nodes, edges=second.edges
        ).produce()
        assert _serialize_answer(ans_a) == _serialize_answer(ans_b), (
            f"{repo.name}/{ans_a.intent}: serialized answer differs across runs"
        )
        # The rendered markdown (what the user actually sees) is byte-identical.
        assert render_answer_markdown(ans_a) == render_answer_markdown(ans_b), (
            f"{repo.name}/{ans_a.intent}: rendered markdown differs across runs"
        )


def test_scoped_explanation_is_deterministic() -> None:
    """The ScopedExplanation producer is deterministic for identical input too."""
    analyzed = _analyze(PYTHON_REPO)
    ev_file = "app/service.py"

    a = ScopedExplanationProducer(
        nodes=analyzed.nodes, edges=analyzed.edges
    ).produce(ev_file, 1, 40, "what does this do?")
    b = ScopedExplanationProducer(
        nodes=analyzed.nodes, edges=analyzed.edges
    ).produce(ev_file, 1, 40, "what does this do?")

    assert _serialize_answer(a) == _serialize_answer(b)
    assert render_answer_markdown(a) == render_answer_markdown(b)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Offline: every answer type is produced with NIM disabled (Req 9.4).
# ═══════════════════════════════════════════════════════════════════════════════


def _assert_answer_offline_valid(answer: CortexAnswer, label: str) -> None:
    """Every offline-produced answer must be a valid, evidence-backed CortexAnswer."""
    assert isinstance(answer, CortexAnswer), f"{label}: not a CortexAnswer"
    # Contract gate — raises AnswerValidationError on any violation.
    assert_valid_answer(answer)
    claims = answer.iter_claims()
    assert claims, f"{label}: produced no claims"
    assert all(c.evidence for c in claims), f"{label}: a claim lacks evidence"
    assert all(
        c.epistemic in (Epistemic.FACT, Epistemic.INFERENCE, Epistemic.PREDICTION)
        for c in claims
    ), f"{label}: unexpected epistemic tag"
    assert 0.0 <= answer.confidence <= 1.0, f"{label}: confidence out of range"


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_all_answer_types_offline_with_nim_disabled(lang: str) -> None:
    """Generate ALL answer types with NIM disabled — no key, no network.

    The five repository producers plus the ScopedExplanation producer are all
    driven purely from the deterministic layer. No NIM key is configured and no
    NIM client is constructed anywhere in this path, so a valid answer here
    proves the feature works fully offline (Req 9.4).
    """
    repo = REFERENCE_REPOS[lang]
    analyzed = _analyze(repo)

    # ── The five repository-level answer types. ──────────────────────────────
    produced_intents: set[str] = set()
    for producer_cls in _REPO_PRODUCERS:
        answer = producer_cls(
            analyzed.understanding, nodes=analyzed.nodes, edges=analyzed.edges
        ).produce()
        _assert_answer_offline_valid(answer, f"{repo.name}/{producer_cls.__name__}")
        produced_intents.add(answer.intent)

    assert produced_intents == {
        "architecture_overview",
        "module_breakdown",
        "api_spec",
        "learning_path",
        "interview_prep",
    }, f"{repo.name}: missing an answer type offline: {produced_intents}"

    # ── The ScopedExplanation answer type (Code Navigator, Task 11). ──────────
    # Pick any known file in the repo and explain a broad line range; the
    # producer resolves to a symbol or falls back to file scope, always offline.
    a_file = repo.files[0][0]
    scoped = ScopedExplanationProducer(
        nodes=analyzed.nodes, edges=analyzed.edges
    ).produce(a_file, 1, 100, "explain this file")
    _assert_answer_offline_valid(scoped, f"{repo.name}/ScopedExplanationProducer")
    assert scoped.intent == "scoped_explanation"


def test_chat_offline_path_yields_grounded_cortex_answer(monkeypatch) -> None:
    """The ChatService offline branch (Task 9) yields a grounded CortexAnswer.

    With ``_use_nim=False`` the chat path must render a ``CortexAnswer`` produced
    by a deterministic producer and NEVER require NIM (Req 9.1, Req 9.4). We stub
    the graph repository and the reasoner exactly as ``test_chat_answer_contract``
    does so the test exercises ``_generate_answer``'s producer branch without a
    database or network.
    """
    svc = ChatService()
    svc._use_nim = False  # NIM disabled — the offline branch under test.

    job = "task20-offline-chat"

    # Real graph nodes so the reasoner-driven producer has something to work on.
    nodes = [
        GraphNode(
            id="ep1",
            label="getUser",
            node_type=NodeType.ENDPOINT,
            job_id=job,
            properties={
                "route_info": "/users/{id}",
                "http_method": "get",
                "file": "src/routes/user.ts",
                "line": 10,
            },
        ),
        GraphNode(id="m1", label="routes", node_type=NodeType.MODULE, job_id=job),
    ]

    async def fake_nodes(job_id):
        return nodes

    async def fake_edges(job_id):
        return []

    import cortex.graph.infrastructure.dependencies as deps

    monkeypatch.setattr(deps.graph_repository, "get_nodes_by_job", fake_nodes)
    monkeypatch.setattr(deps.graph_repository, "get_edges_by_job", fake_edges)

    # Avoid the entity-explainer path claiming the question so the producer
    # branch (the one under test) runs.
    monkeypatch.setattr(
        ChatService, "_try_entity_explanation", lambda self, q, n, e: None
    )

    async def run():
        return await svc._generate_answer(
            job, "what is the architecture?", "raw repository context"
        )

    cortex_answer, draft = asyncio.run(run())

    # A grounded CortexAnswer came back purely from the deterministic layer.
    assert isinstance(cortex_answer, CortexAnswer)
    assert_valid_answer(cortex_answer)
    assert cortex_answer.intent == "architecture_overview"
    # The streamed draft is exactly the rendered form of that same answer —
    # no NIM was involved.
    assert draft == render_answer_markdown(cortex_answer)


def test_chat_service_offline_never_requires_nim_key(monkeypatch) -> None:
    """End-to-end offline stream: no NIM key, a rendered CortexAnswer is streamed.

    Mirrors the streaming assertions in ``test_chat_answer_contract`` but pins the
    offline guarantee: with ``_use_nim=False`` the full ``stream_response`` path
    yields the producer's rendered ``CortexAnswer`` and calls no NIM client.
    """
    svc = ChatService()
    svc._use_nim = False

    answer = ArchitectureOverviewProducer(
        _build_offline_understanding()
    ).produce()
    expected = render_answer_markdown(answer)

    async def fake_generate(job_id, question, context):
        return answer, render_answer_markdown(answer)

    monkeypatch.setattr(svc, "_generate_answer", fake_generate)

    async def fake_resolve(job_id):
        return None

    monkeypatch.setattr(svc, "_resolve_repo_url", fake_resolve)

    async def add_message(session_id, msg):
        return None

    monkeypatch.setattr(svc._repo, "add_message", add_message)

    async def retrieve(job_id, msg, repo_url=None):
        return "raw context"

    monkeypatch.setattr(svc._retriever, "retrieve", retrieve)

    # Guard: the NIM client must never be invoked on the offline path.
    async def forbidden_stream(messages):
        raise AssertionError("NIM was called on the offline path")
        yield ""  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(svc._nim, "stream", forbidden_stream)

    session = ChatSession(id="task20-s1", job_id="task20-offline-stream")

    async def run():
        out = []
        async for chunk in svc.stream_response(session, "explain the architecture"):
            out.append(chunk)
        return "".join(out)

    result = asyncio.run(run())
    assert result.strip() == expected.strip()
    assert "Architecture Overview" in result


def _build_offline_understanding():
    """A minimal RepositoryUnderstanding for the offline streaming test."""
    from cortex.reasoning.domain.entities import (
        ArchitectureStyle,
        ModuleIntelligence,
        RepositoryUnderstanding,
    )

    u = RepositoryUnderstanding(
        job_id="task20-offline-stream",
        repo_url="https://github.com/example/offline-app",
        repo_name="offline-app",
        purpose="An offline-analysed service.",
        headline="A service analysed with no NIM.",
        architecture_style=ArchitectureStyle.MODULAR,
        architecture_description="Modular architecture.",
        languages=["python"],
        frameworks=[],
        total_files=5,
        total_lines=500,
        total_modules=1,
        total_classes=3,
        total_functions=10,
        total_endpoints=0,
        top_dependencies=[],
        start_here_file="app/main.py",
    )
    u.modules = [
        ModuleIntelligence(
            name="app",
            path="app",
            node_id="mod-app",
            file_count=5,
            class_count=3,
            function_count=10,
            total_lines=500,
            architecture_role="core",
        ),
    ]
    return u
