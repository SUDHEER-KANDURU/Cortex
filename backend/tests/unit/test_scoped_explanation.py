"""Tests for the Scoped Explanation backend (Task 11).

Covers Req 7.3 (a file + line range resolves to the graph node(s) at those lines
and returns a Scoped Explanation as a CortexAnswer) and Req 7.4 (the answer
includes the selected code's callers, callees, and inferred role where available).

Verified here:
  - line-range → node resolution: overlap + innermost (most-specific) selection,
  - whole-file fallback when the range matches no inner symbol,
  - the producer emits a valid CortexAnswer including callers / callees / role,
  - a file that is not in the graph yields a stated-gap answer,
  - the API route POST /api/v1/navigate/{job_id}/explain (via FastAPI TestClient).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from cortex.graph.domain.entities import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from cortex.main import create_app
from cortex.navigate import router as navigate_router
from cortex.reasoning.application.scoped_explanation import (
    ScopedExplanationProducer,
    resolve_scope_nodes,
)
from cortex.reasoning.domain.answer import Epistemic, validate_answer
from fastapi.testclient import TestClient

_JOB = "job-scoped-1"
_FILE = "src/auth/auth_service.py"


def _node(node_id: str, label: str, node_type: NodeType, **props) -> GraphNode:
    return GraphNode(
        id=node_id,
        label=label,
        node_type=node_type,
        job_id=_JOB,
        properties=props,
        created_at=datetime.now(UTC),
    )


def _edge(edge_id: str, source: str, target: str, rel: RelationshipType) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source_id=source,
        target_id=target,
        relationship=rel,
        job_id=_JOB,
        properties={},
        created_at=datetime.now(UTC),
    )


# A small auth service:
#   file (1..120) contains class AuthService (5..120) which contains
#   authenticate (20..55) and validate_token (57..80).
#   login (in the router file) CALLS authenticate; authenticate CALLS find_user.
def _nodes() -> list[GraphNode]:
    return [
        _node(
            "file-service", "auth_service.py", NodeType.FILE,
            path=_FILE, lines=120, language="python",
        ),
        _node(
            "cls-service", "AuthService", NodeType.CLASS,
            file=_FILE, line=5, lines=116, methods=2,
        ),
        _node(
            "meth-auth", "authenticate", NodeType.METHOD,
            file=_FILE, line=20, lines=36, cyclomatic=6,
        ),
        _node(
            "meth-validate", "validate_token", NodeType.METHOD,
            file=_FILE, line=57, lines=24, cyclomatic=3,
        ),
        # A symbol in another file that calls authenticate (a caller).
        _node(
            "fn-login", "login", NodeType.FUNCTION,
            file="src/auth/auth_router.py", line=15, lines=21,
        ),
        # A symbol authenticate calls (a callee).
        _node(
            "fn-find-user", "find_user", NodeType.FUNCTION,
            file="src/auth/user_repo.py", line=10, lines=20,
        ),
    ]


def _edges() -> list[GraphEdge]:
    return [
        _edge("e-contains-cls", "file-service", "cls-service", RelationshipType.CONTAINS),
        _edge("e-contains-auth", "cls-service", "meth-auth", RelationshipType.CONTAINS),
        _edge("e-contains-val", "cls-service", "meth-validate", RelationshipType.CONTAINS),
        _edge("e-login-calls-auth", "fn-login", "meth-auth", RelationshipType.CALLS),
        _edge("e-auth-calls-find", "meth-auth", "fn-find-user", RelationshipType.CALLS),
    ]


# ── resolution: overlap + innermost selection ─────────────────────────────────


def test_resolve_picks_innermost_symbol():
    """A selection inside a method resolves to that method, not its enclosing class/file."""
    matched = resolve_scope_nodes(_FILE, 30, 40, _nodes())
    assert [n.id for n in matched] == ["meth-auth"]


def test_resolve_overlap_at_boundary():
    """Overlap is inclusive at the span boundaries."""
    # authenticate spans 20..55; selecting just line 55 still overlaps it.
    matched = resolve_scope_nodes(_FILE, 55, 55, _nodes())
    assert [n.id for n in matched] == ["meth-auth"]
    # Line 56 is between the two methods → only the enclosing class overlaps.
    matched = resolve_scope_nodes(_FILE, 56, 56, _nodes())
    assert [n.id for n in matched] == ["cls-service"]


def test_resolve_multi_symbol_selection_prefers_smallest():
    """A selection spanning both methods resolves to the smallest overlapping symbols."""
    # 20..80 overlaps class (116 lines), authenticate (36) and validate (24).
    # validate_token is the single smallest span.
    matched = resolve_scope_nodes(_FILE, 20, 80, _nodes())
    assert [n.id for n in matched] == ["meth-validate"]


def test_resolve_whole_file_fallback():
    """A selection matching no inner symbol falls back to the whole file node."""
    # Lines 1..4 are above the class (imports/module code) → file scope.
    matched = resolve_scope_nodes(_FILE, 1, 4, _nodes())
    assert [n.id for n in matched] == ["file-service"]


def test_resolve_unknown_file_returns_empty():
    matched = resolve_scope_nodes("src/does/not/exist.py", 1, 10, _nodes())
    assert matched == []


def test_resolve_reversed_range_is_normalised():
    matched = resolve_scope_nodes(_FILE, 40, 30, _nodes())
    assert [n.id for n in matched] == ["meth-auth"]


# ── producer: valid CortexAnswer including callers / callees / role ───────────


def test_producer_emits_valid_answer_with_callers_callees_role():
    producer = ScopedExplanationProducer(nodes=_nodes(), edges=_edges())
    answer = producer.produce(_FILE, 30, 40, "What does this do?")

    # Contract holds (no validation errors).
    assert validate_answer(answer) == []
    assert answer.intent == "scoped_explanation"

    headings = [s.heading for s in answer.sections]
    assert "Selected code" in headings
    assert "Inferred role" in headings
    assert "Callers" in headings
    assert "Callees" in headings

    text = " ".join(c.text for c in answer.iter_claims())
    # Resolved to the method.
    assert "authenticate" in text
    # Caller (login) and callee (find_user) are surfaced from the graph.
    assert "login" in text
    assert "find_user" in text

    # Role section is an INFERENCE; selected-code/callers/callees are FACTs.
    role_claims = next(s for s in answer.sections if s.heading == "Inferred role").claims
    assert all(c.epistemic is Epistemic.INFERENCE for c in role_claims)
    selected = next(s for s in answer.sections if s.heading == "Selected code").claims
    assert all(c.epistemic is Epistemic.FACT for c in selected)

    # Every claim carries evidence (contract), and next actions locate the symbol.
    assert all(c.evidence for c in answer.iter_claims())
    assert any(a.kind.value == "open_file" for a in answer.next_actions)


def test_producer_whole_file_scope_answer():
    producer = ScopedExplanationProducer(nodes=_nodes(), edges=_edges())
    answer = producer.produce(_FILE, 1, 3)  # module-level lines → whole file
    assert validate_answer(answer) == []
    summary_and_claims = answer.summary + " " + " ".join(
        c.text for c in answer.iter_claims()
    )
    assert "file" in summary_and_claims.lower()
    # The file node has no callers/callees resolved, so those sections say so.
    text = " ".join(c.text for c in answer.iter_claims())
    assert "auth_service.py" in text


def test_producer_symbol_without_callers_states_gap():
    """validate_token has no callers → the Callers section states that plainly."""
    producer = ScopedExplanationProducer(nodes=_nodes(), edges=_edges())
    answer = producer.produce(_FILE, 60, 70)  # inside validate_token
    callers = next(s for s in answer.sections if s.heading == "Callers").claims
    assert "No callers" in callers[0].text
    assert validate_answer(answer) == []


def test_producer_unknown_file_gap_answer():
    producer = ScopedExplanationProducer(nodes=_nodes(), edges=_edges())
    answer = producer.produce("src/missing.py", 1, 5)
    assert validate_answer(answer) == []
    assert answer.sections[0].heading == "No matching code"
    assert "not present in the analysed graph" in answer.sections[0].claims[0].text


# ── API: POST /api/v1/navigate/{job_id}/explain ───────────────────────────────


@pytest.fixture()
def client(monkeypatch):
    """FastAPI TestClient with the navigate router's graph_repository stubbed."""

    async def _nodes_by_job(job_id: str):
        return _nodes() if job_id == _JOB else []

    async def _edges_by_job(job_id: str):
        return _edges()

    monkeypatch.setattr(
        navigate_router.graph_repository,
        "get_nodes_by_job",
        AsyncMock(side_effect=_nodes_by_job),
    )
    monkeypatch.setattr(
        navigate_router.graph_repository,
        "get_edges_by_job",
        AsyncMock(side_effect=_edges_by_job),
    )
    return TestClient(create_app())


def test_api_scoped_explain_ok(client):
    resp = client.post(
        f"/api/v1/navigate/{_JOB}/explain",
        json={
            "file_path": _FILE,
            "line_start": 30,
            "line_end": 40,
            "question": "Explain this method",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["intent"] == "scoped_explanation"
    headings = [s["heading"] for s in body["sections"]]
    assert {"Selected code", "Inferred role", "Callers", "Callees"} <= set(headings)

    # Epistemic tags are serialized as strings; role is inference, others fact.
    all_claims = [c for s in body["sections"] for c in s["claims"]]
    assert all(c["evidence"] for c in all_claims)
    assert any(c["epistemic"] == "inference" for c in all_claims)
    assert any(c["epistemic"] == "fact" for c in all_claims)


def test_api_scoped_explain_unknown_job_404(client):
    resp = client.post(
        "/api/v1/navigate/no-such-job/explain",
        json={"file_path": _FILE, "line_start": 1, "line_end": 5},
    )
    assert resp.status_code == 404
