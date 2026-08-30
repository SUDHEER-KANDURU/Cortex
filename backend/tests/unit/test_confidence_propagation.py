"""Confidence propagation tests (Task 15 — Req 6.2, Req 6.3).

Covers:
  1. Each health dimension in an engineering health report carries a
     deterministic confidence score in 0..1 (Req 6.2).
  2. A low-confidence CortexAnswer surfaces a caveat (Req 6.3).
  3. A low-coverage situation surfaces a caveat (Req 6.3).
  4. A high-confidence / high-coverage answer does NOT show a spurious
     caveat (Req 6.3).

These exercise both seams:
  - the insights layer (per-dimension confidence), and
  - the reasoning producers + scoped explanation (caveat surfacing).
"""

from __future__ import annotations

from datetime import datetime, timezone

from cortex.graph.domain.entities import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from cortex.insights.application.engine import InsightsEngine
from cortex.pipeline.domain.entities import Coverage, CoverageGap
from cortex.reasoning.application.producers import (
    LOW_CONFIDENCE_THRESHOLD,
    LOW_FILE_COVERAGE_THRESHOLD,
    ArchitectureOverviewProducer,
    build_coverage_note,
)
from cortex.reasoning.domain.entities import (
    ArchitectureStyle,
    ModuleIntelligence,
    RepositoryUnderstanding,
)

_NOW = datetime.now(timezone.utc)
_JOB = "test-confidence-001"


# ── Graph helpers (mirror test_insights_engine conventions) ───────────────────


def _node(id: str, label: str, ntype: NodeType, props: dict) -> GraphNode:
    return GraphNode(
        id=id, label=label, node_type=ntype, job_id=_JOB,
        properties=props, created_at=_NOW,
    )


def _edge(sid: str, tid: str, rel: RelationshipType) -> GraphEdge:
    return GraphEdge(
        id=f"{sid}-{tid}", source_id=sid, target_id=tid,
        relationship=rel, job_id=_JOB, created_at=_NOW,
    )


def _file(id: str, path: str, lines: int = 60) -> GraphNode:
    return _node(id, path, NodeType.FILE, {
        "path": path, "lines": lines, "language": "python",
    })


def _fn(id: str, label: str, file_path: str, lines: int = 12,
        params: int = 2, has_doc: bool = True) -> GraphNode:
    return _node(id, label, NodeType.FUNCTION, {
        "file": file_path, "line": 1, "lines": lines,
        "param_count": params, "is_method": False,
        "has_docstring": has_doc, "cyclomatic": 3,
    })


def _small_graph() -> tuple[list[GraphNode], list[GraphEdge]]:
    """A tiny but well-formed Python repo graph the engine can score."""
    f1 = _file("f1", "src/app/service.py", lines=80)
    f2 = _file("f2", "src/app/models.py", lines=60)
    fn1 = _fn("fn1", "handle_request", "src/app/service.py")
    fn2 = _fn("fn2", "load_model", "src/app/models.py")
    nodes = [f1, f2, fn1, fn2]
    edges = [
        _edge("f1", "fn1", RelationshipType.CONTAINS),
        _edge("f2", "fn2", RelationshipType.CONTAINS),
        _edge("f1", "f2", RelationshipType.IMPORTS),
    ]
    return nodes, edges


# ── Understanding helpers ─────────────────────────────────────────────────────


def _healthy_understanding() -> RepositoryUnderstanding:
    """A well-analyzed repo whose overview producer earns high confidence."""
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/app",
        repo_name="app",
        purpose="A service.",
        headline="A modular Python service.",
        architecture_style=ArchitectureStyle.MODULAR,
        architecture_description="Modular architecture.",
        languages=["python"],
        frameworks=["fastapi"],
        total_files=4,
        total_lines=400,
        total_modules=4,
        total_classes=8,
        total_functions=30,
        total_endpoints=2,
        top_dependencies=["fastapi"],
    )
    # As many modules as files → _confidence_from_counts is maxed (0.95).
    u.modules = [
        ModuleIntelligence(
            name=f"mod{i}", path=f"src/mod{i}", node_id=f"mod-{i}",
            file_count=1, class_count=2, function_count=8, total_lines=100,
            architecture_role="core", layer="application",
        )
        for i in range(4)
    ]
    return u


def _thin_understanding() -> RepositoryUnderstanding:
    """A barely-analyzed repo: files exist and one module, but little else.

    ``_confidence_from_counts(total_files=10, present=1)`` → ~0.36, below the
    low-confidence threshold, so the overview producer must surface a caveat —
    yet ``total_modules`` is non-zero so the historic structural short-circuit
    does not fire, isolating the *confidence* signal.
    """
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/thin",
        repo_name="thin",
        architecture_style=ArchitectureStyle.MODULAR,
        languages=["python"],
        total_files=10,
        total_lines=1000,
        total_modules=1,
    )
    u.modules = [
        ModuleIntelligence(
            name="only", path="src/only", node_id="mod-only",
            file_count=1, class_count=1, function_count=1, total_lines=50,
        )
    ]
    return u


# ══════════════════════════════════════════════════════════════════════════════
# 1. Each health dimension carries a deterministic confidence score (Req 6.2)
# ══════════════════════════════════════════════════════════════════════════════


class TestHealthDimensionConfidence:
    def test_every_dimension_has_confidence_in_range(self):
        nodes, edges = _small_graph()
        report = InsightsEngine().compute(
            _JOB, "https://github.com/example/app", nodes, edges
        )

        assert report.dimensions, "expected the engine to produce dimensions"
        for dim in report.dimensions:
            assert 0.0 <= dim.confidence <= 1.0, (
                f"dimension {dim.name!r} confidence {dim.confidence} out of range"
            )
        # Overall confidence is also attached and in range (Req 6.2).
        assert 0.0 <= report.overall_confidence <= 1.0

    def test_dimension_confidence_is_deterministic(self):
        nodes, edges = _small_graph()
        engine = InsightsEngine()
        r1 = engine.compute(_JOB, "https://github.com/example/app", nodes, edges)
        r2 = engine.compute(_JOB, "https://github.com/example/app", nodes, edges)

        c1 = {d.name: d.confidence for d in r1.dimensions}
        c2 = {d.name: d.confidence for d in r2.dimensions}
        assert c1 == c2, "per-dimension confidence must be deterministic"
        assert r1.overall_confidence == r2.overall_confidence


# ══════════════════════════════════════════════════════════════════════════════
# 2. A low-confidence answer surfaces a caveat (Req 6.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestLowConfidenceCaveat:
    def test_low_confidence_answer_has_coverage_note(self):
        u = _thin_understanding()
        answer = ArchitectureOverviewProducer(u).produce()

        assert answer.confidence < LOW_CONFIDENCE_THRESHOLD, (
            "fixture must produce a low-confidence answer to exercise the caveat"
        )
        assert answer.coverage_note is not None
        assert "confidence is low" in answer.coverage_note.lower()

    def test_build_coverage_note_fires_on_low_confidence_only(self):
        # A repo with adequate structure (so the structural short-circuit does
        # not fire) but a low answer confidence must still get a caveat.
        u = _healthy_understanding()
        note = build_coverage_note(u, confidence=0.2, coverage=None)
        assert note is not None
        assert "provisional" in note.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 3. A low-coverage situation surfaces a caveat (Req 6.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestLowCoverageCaveat:
    def test_low_file_coverage_surfaces_caveat(self):
        u = _healthy_understanding()  # high confidence, adequate structure
        # 4 of 10 files analyzed → 40% file coverage, below the threshold.
        coverage = Coverage(
            total_files=10,
            analyzed_files=4,
            resolved_references=20,
            unresolved_references=1,
            gaps=(CoverageGap("a.py", "SyntaxError"),),
        )
        assert coverage.file_coverage_ratio() < LOW_FILE_COVERAGE_THRESHOLD

        answer = ArchitectureOverviewProducer(u, coverage=coverage).produce()
        assert answer.coverage_note is not None
        assert "40%" in answer.coverage_note
        assert "files were analyzed" in answer.coverage_note

    def test_low_reference_coverage_surfaces_caveat(self):
        u = _healthy_understanding()
        # Files fully analyzed, but only 3/10 references resolved → 30%.
        coverage = Coverage(
            total_files=10,
            analyzed_files=10,
            resolved_references=3,
            unresolved_references=7,
        )
        note = build_coverage_note(u, confidence=0.95, coverage=coverage)
        assert note is not None
        assert "references were resolved" in note


# ══════════════════════════════════════════════════════════════════════════════
# 4. A high-confidence / high-coverage answer shows NO spurious caveat (Req 6.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestNoSpuriousCaveat:
    def test_high_confidence_high_coverage_has_no_caveat(self):
        u = _healthy_understanding()
        coverage = Coverage(
            total_files=4,
            analyzed_files=4,
            resolved_references=40,
            unresolved_references=0,
        )
        answer = ArchitectureOverviewProducer(u, coverage=coverage).produce()

        assert answer.confidence >= LOW_CONFIDENCE_THRESHOLD
        assert answer.coverage_note is None, (
            f"unexpected caveat on a well-grounded answer: {answer.coverage_note!r}"
        )

    def test_build_coverage_note_returns_none_when_all_signals_healthy(self):
        u = _healthy_understanding()
        coverage = Coverage(
            total_files=4, analyzed_files=4,
            resolved_references=40, unresolved_references=0,
        )
        assert build_coverage_note(u, confidence=0.95, coverage=coverage) is None
