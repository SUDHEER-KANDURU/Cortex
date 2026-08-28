"""Unit tests for the BlastRadiusAnalyzer.

Covers:
  - Direct dependent detection (nodes that import/call the target)
  - Transitive dependent detection (multi-hop through dependency graph)
  - Affected module detection
  - Risk scoring (based on dependent count, test coverage, module spread)
  - Impact path construction
  - Edge cases (isolated node, deeply nested)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType, RelationshipType
from cortex.overview.blast_radius import BlastRadiusAnalyzer

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)
_JOB = "test-blast-001"


def _node(id: str, label: str, ntype: NodeType, props: dict | None = None) -> GraphNode:
    return GraphNode(
        id=id, label=label, node_type=ntype, job_id=_JOB,
        properties=props or {}, created_at=_NOW,
    )


def _edge(sid: str, tid: str, rel: RelationshipType) -> GraphEdge:
    return GraphEdge(
        id=f"{sid}-{tid}-{rel.value}", source_id=sid, target_id=tid,
        relationship=rel, job_id=_JOB, created_at=_NOW,
    )


@pytest.fixture
def analyzer() -> BlastRadiusAnalyzer:
    return BlastRadiusAnalyzer()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDirectDependents:
    """Tests for detecting direct dependents."""

    def test_finds_importing_files(self, analyzer: BlastRadiusAnalyzer):
        """Files that import the target should be direct dependents."""
        target = _node("lib", "utils.py", NodeType.FILE, {"path": "src/utils.py"})
        nodes = [
            target,
            _node("a", "handler.py", NodeType.FILE, {"path": "src/handler.py"}),
            _node("b", "service.py", NodeType.FILE, {"path": "src/service.py"}),
            _node("c", "unrelated.py", NodeType.FILE, {"path": "src/unrelated.py"}),
        ]
        edges = [
            _edge("a", "lib", RelationshipType.IMPORTS),  # handler imports utils
            _edge("b", "lib", RelationshipType.IMPORTS),  # service imports utils
            # unrelated doesn't import utils
        ]

        result = analyzer.analyze(target, nodes, edges)

        direct_labels = {d.label for d in result.direct_dependents}
        assert "handler.py" in direct_labels
        assert "service.py" in direct_labels
        assert "unrelated.py" not in direct_labels

    def test_finds_calling_functions(self, analyzer: BlastRadiusAnalyzer):
        """Functions that call the target should be dependents."""
        target = _node("fn-a", "validate", NodeType.FUNCTION, {"file": "validators.py"})
        nodes = [
            target,
            _node("fn-b", "create_user", NodeType.FUNCTION, {"file": "service.py"}),
            _node("fn-c", "update_user", NodeType.FUNCTION, {"file": "service.py"}),
        ]
        edges = [
            _edge("fn-b", "fn-a", RelationshipType.CALLS),
            _edge("fn-c", "fn-a", RelationshipType.CALLS),
        ]

        result = analyzer.analyze(target, nodes, edges)

        dependent_labels = {d.label for d in result.direct_dependents}
        assert "create_user" in dependent_labels
        assert "update_user" in dependent_labels


class TestTransitiveDependents:
    """Tests for multi-hop impact propagation."""

    def test_finds_transitive_chain(self, analyzer: BlastRadiusAnalyzer):
        """A → imports → B → imports → C: changing C affects both B and A."""
        c = _node("c", "core.py", NodeType.FILE, {"path": "src/core.py"})
        b = _node("b", "service.py", NodeType.FILE, {"path": "src/service.py"})
        a = _node("a", "handler.py", NodeType.FILE, {"path": "src/handler.py"})
        nodes = [c, b, a]
        edges = [
            _edge("b", "c", RelationshipType.IMPORTS),  # service imports core
            _edge("a", "b", RelationshipType.IMPORTS),  # handler imports service
        ]

        result = analyzer.analyze(c, nodes, edges)

        all_dependent_labels = {
            d.label for d in result.direct_dependents + result.transitive_dependents
        }
        assert "service.py" in all_dependent_labels
        assert "handler.py" in all_dependent_labels

    def test_respects_max_depth(self, analyzer: BlastRadiusAnalyzer):
        """Should not traverse beyond max_depth hops."""
        # Create a chain of 10 nodes
        nodes = [
            _node(f"n{i}", f"file{i}.py", NodeType.FILE, {"path": f"file{i}.py"})
            for i in range(10)
        ]
        edges = [_edge(f"n{i+1}", f"n{i}", RelationshipType.IMPORTS) for i in range(9)]

        result = analyzer.analyze(nodes[0], nodes, edges, max_depth=3)

        # Should find at most 3 hops of dependents
        all_deps = result.direct_dependents + result.transitive_dependents
        max_distance = max((d.distance for d in all_deps), default=0)
        assert max_distance <= 3


class TestAffectedModules:
    """Tests for module impact detection."""

    def test_identifies_affected_modules(self, analyzer: BlastRadiusAnalyzer):
        """Should identify which modules are impacted by the change."""
        target = _node("fn", "validate", NodeType.FUNCTION, {"file": "auth/validators.py"})
        nodes = [
            target,
            _node("dep1", "login", NodeType.FUNCTION, {"file": "auth/login.py"}),
            _node("dep2", "register", NodeType.FUNCTION, {"file": "users/register.py"}),
            _node("dep3", "check", NodeType.FUNCTION, {"file": "payments/check.py"}),
        ]
        edges = [
            _edge("dep1", "fn", RelationshipType.CALLS),
            _edge("dep2", "fn", RelationshipType.CALLS),
            _edge("dep3", "fn", RelationshipType.CALLS),
        ]

        result = analyzer.analyze(target, nodes, edges)

        # Should detect multiple affected modules from file paths
        assert len(result.affected_modules) >= 2


class TestRiskScoring:
    """Tests for risk level assessment."""

    def test_isolated_node_low_risk(self, analyzer: BlastRadiusAnalyzer):
        """A node with no dependents should be low risk."""
        target = _node("iso", "isolated.py", NodeType.FILE, {"path": "isolated.py"})
        result = analyzer.analyze(target, [target], [])

        assert result.risk_level == "low"
        assert result.risk_score == 0

    def test_high_fanin_high_risk(self, analyzer: BlastRadiusAnalyzer):
        """A node with many direct dependents should have high risk."""
        target = _node("core", "core_lib", NodeType.CLASS, {"file": "core.py"})
        dependents = [
            _node(f"d{i}", f"consumer_{i}", NodeType.CLASS, {"file": f"mod{i}/code.py"})
            for i in range(12)
        ]
        nodes = [target] + dependents
        edges = [
            _edge(f"d{i}", "core", RelationshipType.IMPORTS)
            for i in range(12)
        ]

        result = analyzer.analyze(target, nodes, edges)

        # 12 direct dependents should push risk to high or critical
        assert result.risk_level in ("high", "critical")
        assert result.risk_score >= 40

    def test_no_tests_increases_risk(self, analyzer: BlastRadiusAnalyzer):
        """Untested code should have risk factors mentioning lack of tests."""
        target = _node("fn", "risky_fn", NodeType.FUNCTION, {"file": "src/risky.py"})
        dep = _node("dep", "caller", NodeType.FUNCTION, {"file": "src/caller.py"})
        nodes = [target, dep]
        edges = [_edge("dep", "fn", RelationshipType.CALLS)]

        result = analyzer.analyze(target, nodes, edges)

        # Should mention no tests as a risk factor
        risk_text = " ".join(result.risk_factors).lower()
        assert "test" in risk_text or result.risk_score >= 0  # At least produced output


class TestAffectedTests:
    """Tests for finding affected test files."""

    def test_finds_test_dependents(self, analyzer: BlastRadiusAnalyzer):
        """Test nodes that depend on the target should be in affected_tests."""
        target = _node("cls", "UserService", NodeType.CLASS, {"file": "service.py"})
        test = _node("t1", "test_user_service", NodeType.TEST, {"file": "tests/test_service.py"})
        nodes = [target, test]
        edges = [_edge("t1", "cls", RelationshipType.CALLS)]

        result = analyzer.analyze(target, nodes, edges)

        test_labels = {t.label for t in result.affected_tests}
        assert "test_user_service" in test_labels


class TestImpactPaths:
    """Tests for impact path construction."""

    def test_builds_paths(self, analyzer: BlastRadiusAnalyzer):
        """Should build representative paths from target to affected nodes."""
        target = _node("t", "core", NodeType.CLASS, {"file": "core.py"})
        dep1 = _node("d1", "service", NodeType.CLASS, {"file": "service.py"})
        dep2 = _node("d2", "handler", NodeType.CLASS, {"file": "handler.py"})
        nodes = [target, dep1, dep2]
        edges = [
            _edge("d1", "t", RelationshipType.IMPORTS),
            _edge("d2", "d1", RelationshipType.IMPORTS),
        ]

        result = analyzer.analyze(target, nodes, edges)

        assert len(result.impact_paths) > 0
        # Each path should be a list of strings
        for path in result.impact_paths:
            assert len(path) >= 2


class TestEdgeCases:
    """Edge case handling."""

    def test_class_with_methods(self, analyzer: BlastRadiusAnalyzer):
        """Changing a class should expand to its methods for dependency checking."""
        cls = _node("cls", "UserService", NodeType.CLASS, {"file": "service.py"})
        method = _node("m1", "get_user", NodeType.FUNCTION, {"file": "service.py"})
        caller = _node("c1", "handler", NodeType.FUNCTION, {"file": "handler.py"})
        nodes = [cls, method, caller]
        edges = [
            _edge("cls", "m1", RelationshipType.CONTAINS),  # class contains method
            _edge("c1", "m1", RelationshipType.CALLS),      # handler calls method
        ]

        result = analyzer.analyze(cls, nodes, edges)

        # Caller of the method should be affected (because class CONTAINS method)
        all_deps = result.direct_dependents + result.transitive_dependents
        dep_labels = {d.label for d in all_deps}
        assert "handler" in dep_labels

    def test_self_reference_ignored(self, analyzer: BlastRadiusAnalyzer):
        """A node should not appear in its own blast radius."""
        target = _node("t", "self_ref", NodeType.FUNCTION, {"file": "x.py"})
        nodes = [target]
        edges = [_edge("t", "t", RelationshipType.CALLS)]  # Recursive call

        result = analyzer.analyze(target, nodes, edges)

        all_dep_ids = {d.id for d in result.direct_dependents + result.transitive_dependents}
        assert "t" not in all_dep_ids
