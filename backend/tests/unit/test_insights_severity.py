"""Tests for the context-aware severity model, role classification, and
issue grouping introduced to make HIGH/CRITICAL mean genuine engineering risk.

These tests lock in the behaviours that fixed the "noisy dashboard" problem:
  - severity ladder helpers
  - architectural role classification
  - fan-out on wiring roles is downgraded unless it's also a hub
  - generator/parser large files are downgraded (large procedural bodies)
  - blast-radius (dependents) and reinforcing signals escalate
  - grouping collapses reinforcing signals on one symbol into one concern
  - end-to-end calibration: LOW / MEDIUM / HIGH / CRITICAL
"""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType, RelationshipType
from cortex.insights.application.engine import InsightsEngine
from cortex.insights.application.grouping import group_into_concerns
from cortex.insights.domain.entities import (
    CodeIssue,
    IssueCategory,
    IssueSeverity,
)
from cortex.insights.domain.severity import (
    ArchitecturalRole,
    adjust_severity,
    classify_role,
    downgrade,
    escalate,
    max_severity,
    severity_rank,
)

_NOW = datetime.now(UTC)
_JOB = "sev-job"
engine = InsightsEngine()


def _node(nid, label, ntype, props):
    return GraphNode(id=nid, label=label, node_type=ntype, job_id=_JOB,
                     properties=props, created_at=_NOW)

def _edge(sid, tid, rel):
    return GraphEdge(id=f"{sid}-{tid}", source_id=sid, target_id=tid,
                     relationship=rel, job_id=_JOB, created_at=_NOW)


# ══════════════════════════════════════════════════════════════════════════════
# SEVERITY LADDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

class TestSeverityLadder:
    def test_rank_order(self):
        assert severity_rank(IssueSeverity.INFO) < severity_rank(IssueSeverity.LOW)
        assert severity_rank(IssueSeverity.LOW) < severity_rank(IssueSeverity.MEDIUM)
        assert severity_rank(IssueSeverity.MEDIUM) < severity_rank(IssueSeverity.HIGH)
        assert severity_rank(IssueSeverity.HIGH) < severity_rank(IssueSeverity.CRITICAL)

    def test_downgrade_escalate_clamped(self):
        assert downgrade(IssueSeverity.HIGH) == IssueSeverity.MEDIUM
        assert escalate(IssueSeverity.HIGH) == IssueSeverity.CRITICAL
        assert escalate(IssueSeverity.CRITICAL) == IssueSeverity.CRITICAL  # clamp
        assert downgrade(IssueSeverity.INFO) == IssueSeverity.INFO          # clamp

    def test_max_severity(self):
        assert max_severity(IssueSeverity.LOW, IssueSeverity.HIGH) == IssueSeverity.HIGH
        assert max_severity(IssueSeverity.CRITICAL, IssueSeverity.MEDIUM) == IssueSeverity.CRITICAL


# ══════════════════════════════════════════════════════════════════════════════
# ROLE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestRoleClassification:
    def test_entry_point(self):
        assert classify_role("src/cortex/main.py") == ArchitecturalRole.ENTRY_POINT

    def test_router_by_name(self):
        role = classify_role("src/cortex/auth/presentation/router.py")
        assert role == ArchitecturalRole.ROUTER

    def test_router_by_endpoints(self):
        role = classify_role("src/cortex/foo/handlers.py", endpoint_count=3)
        assert role == ArchitecturalRole.ROUTER

    def test_orchestrator(self):
        assert classify_role(
            "src/cortex/pipeline/application/orchestrator.py"
        ) == ArchitecturalRole.ORCHESTRATOR
        assert classify_role(
            "src/cortex/pipeline/infrastructure/stages.py"
        ) == ArchitecturalRole.ORCHESTRATOR

    def test_parser(self):
        role = classify_role("src/cortex/pipeline/infrastructure/ast_parser.py")
        assert role == ArchitecturalRole.PARSER

    def test_generator(self):
        role = classify_role("src/cortex/pipeline/infrastructure/diagram_generator.py")
        assert role == ArchitecturalRole.GENERATOR

    def test_repository(self):
        role = classify_role("src/cortex/graph/infrastructure/sqlite_repository.py")
        assert role == ArchitecturalRole.REPOSITORY

    def test_ordinary_default(self):
        role = classify_role("src/cortex/chat/infrastructure/context_retriever.py")
        assert role == ArchitecturalRole.ORDINARY


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXT-AWARE SEVERITY DECISIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestAdjustSeverity:
    def test_fanout_on_router_downgraded(self):
        """A router composing many collaborators is normal wiring, not HIGH."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ROUTER,
            signal="fanout", magnitude_ratio=1.1, dependents=2, fan_in_hub=False,
        )
        assert d.severity == IssueSeverity.MEDIUM
        assert d.factors, "Downgrade must record a reason"

    def test_fanout_on_router_kept_when_hub(self):
        """If the router is ALSO a dependency hub, the risk is real — keep HIGH."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ROUTER,
            signal="fanout", magnitude_ratio=1.1, dependents=30, fan_in_hub=True,
        )
        assert d.severity == IssueSeverity.HIGH

    def test_extreme_fanout_on_router_still_downgraded(self):
        """Even a very high import count on a router is expected shape, not HIGH."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ROUTER,
            signal="fanout", magnitude_ratio=3.8, dependents=1, fan_in_hub=False,
        )
        assert d.severity == IssueSeverity.MEDIUM

    def test_fanout_on_ordinary_module_kept(self):
        """An ordinary module with high fan-out IS a real coupling smell."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ORDINARY,
            signal="fanout", magnitude_ratio=1.5, dependents=1, fan_in_hub=False,
        )
        assert d.severity == IssueSeverity.HIGH

    def test_generator_large_file_downgraded(self):
        """A generator's large procedural file is expected, not top-severity."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.GENERATOR,
            signal="oversized_file", magnitude_ratio=1.3,
        )
        assert d.severity == IssueSeverity.MEDIUM

    def test_ordinary_large_file_kept(self):
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ORDINARY,
            signal="oversized_file", magnitude_ratio=1.3,
        )
        assert d.severity == IssueSeverity.HIGH

    def test_blast_radius_escalates_complexity(self):
        """Complex code that many files depend on is a wider risk."""
        d = adjust_severity(
            base=IssueSeverity.HIGH, role=ArchitecturalRole.ORDINARY,
            signal="god_class", magnitude_ratio=1.2, dependents=19,
        )
        assert d.severity == IssueSeverity.CRITICAL

    def test_reinforcing_signals_escalate(self):
        """Several complexity signals firing together reinforce into a bigger concern."""
        d = adjust_severity(
            base=IssueSeverity.MEDIUM, role=ArchitecturalRole.ORDINARY,
            signal="large_function", magnitude_ratio=1.0, reinforcing_signals=3,
        )
        assert severity_rank(d.severity) >= severity_rank(IssueSeverity.HIGH)


# ══════════════════════════════════════════════════════════════════════════════
# GROUPING
# ══════════════════════════════════════════════════════════════════════════════

class TestGrouping:
    def _issue(self, title, sev, signal, symbol="gen", file="m.py",
               cat=IssueCategory.COMPLEXITY):
        return CodeIssue(category=cat, severity=sev, title=title,
                         description="d", recommendation="r",
                         file_path=file, affected_symbol=symbol, signal=signal)

    def test_reinforcing_signals_collapse_to_one_concern(self):
        issues = [
            self._issue("High cyclomatic complexity", IssueSeverity.HIGH, "cyclomatic"),
            self._issue("Deep nesting", IssueSeverity.HIGH, "nesting"),
            self._issue("God function", IssueSeverity.HIGH, "god_function"),
        ]
        concerns = group_into_concerns(issues)
        assert len(concerns) == 1, "Three signals on one symbol must be ONE concern"
        c = concerns[0]
        assert c.signal_count == 3
        assert c.severity == IssueSeverity.HIGH
        assert "doing too much" in c.title.lower()

    def test_unrelated_problems_stay_separate(self):
        issues = [
            self._issue("High cyclomatic complexity", IssueSeverity.HIGH, "cyclomatic",
                        symbol="fn_a", file="a.py"),
            self._issue("Circular dependency", IssueSeverity.HIGH, "circular_dep",
                        symbol="b.py", file="b.py", cat=IssueCategory.ARCHITECTURE),
        ]
        concerns = group_into_concerns(issues)
        assert len(concerns) == 2, "Different symbols/categories must not merge"

    def test_concern_severity_is_max_of_signals(self):
        issues = [
            self._issue("Large function", IssueSeverity.MEDIUM, "large_function"),
            self._issue("Critical cyclomatic complexity", IssueSeverity.CRITICAL, "cyclomatic"),
        ]
        concerns = group_into_concerns(issues)
        assert len(concerns) == 1
        assert concerns[0].severity == IssueSeverity.CRITICAL

    def test_signals_preserved_as_evidence(self):
        issues = [
            self._issue("High cyclomatic complexity", IssueSeverity.HIGH, "cyclomatic"),
            self._issue("God function", IssueSeverity.HIGH, "god_function"),
        ]
        concerns = group_into_concerns(issues)
        assert len(concerns[0].signals) == 2, "Individual signals must remain as evidence"


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END CALIBRATION (LOW / MEDIUM / HIGH / CRITICAL)
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEndCalibration:
    """Deterministic benchmark: known inputs must land on the right severity."""

    def _file(self, nid, path, lines, lang="python", classes=0, endpoints=0):
        return _node(nid, path.split("/")[-1], NodeType.FILE, {
            "path": path, "lines": lines, "language": lang,
            "classes": classes, "functions": 0, "endpoints": endpoints,
        })

    def _fn(self, nid, name, file_path, lines=10, cc=1, params=0, nesting=0, calls=0):
        return _node(nid, name, NodeType.FUNCTION, {
            "file": file_path, "line": 1, "lines": lines,
            "cyclomatic": cc, "param_count": params, "nesting_depth": nesting,
            "call_count": calls, "is_method": False, "has_docstring": True,
        })

    def _severities_for(self, symbol, nodes, edges):
        report = engine.compute(_JOB, "https://github.com/x/r", nodes, edges)
        return [i.severity for i in report.issues if i.affected_symbol == symbol]

    def test_low_simple_function_no_issue(self):
        repo = _node("repo", "r", NodeType.REPOSITORY, {})
        f = self._file("f", "src/util/helpers.py", 40)
        fn = self._fn("fn", "small", "src/util/helpers.py", lines=8, cc=2)
        edges = [_edge("f", "fn", RelationshipType.CONTAINS)]
        sevs = self._severities_for("small", [repo, f, fn], edges)
        assert sevs == [], f"Simple function should raise no issue, got {sevs}"

    def test_medium_moderate_complexity(self):
        repo = _node("repo", "r", NodeType.REPOSITORY, {})
        f = self._file("f", "src/util/helpers.py", 120)
        fn = self._fn("fn", "moderate", "src/util/helpers.py", lines=30, cc=7)
        edges = [_edge("f", "fn", RelationshipType.CONTAINS)]
        sevs = self._severities_for("moderate", [repo, f, fn], edges)
        assert IssueSeverity.MEDIUM in sevs
        assert IssueSeverity.HIGH not in sevs
        assert IssueSeverity.CRITICAL not in sevs

    def test_high_clearly_complex_function(self):
        repo = _node("repo", "r", NodeType.REPOSITORY, {})
        f = self._file("f", "src/util/helpers.py", 300)
        fn = self._fn("fn", "problematic", "src/util/helpers.py",
                      lines=90, cc=12, params=3, nesting=3, calls=15)
        edges = [_edge("f", "fn", RelationshipType.CONTAINS)]
        sevs = self._severities_for("problematic", [repo, f, fn], edges)
        assert IssueSeverity.HIGH in sevs or IssueSeverity.CRITICAL in sevs

    def test_critical_extreme_complexity(self):
        repo = _node("repo", "r", NodeType.REPOSITORY, {})
        f = self._file("f", "src/util/helpers.py", 400)
        fn = self._fn("fn", "monster", "src/util/helpers.py",
                      lines=240, cc=40, params=4, nesting=5, calls=100)
        edges = [_edge("f", "fn", RelationshipType.CONTAINS)]
        sevs = self._severities_for("monster", [repo, f, fn], edges)
        assert IssueSeverity.CRITICAL in sevs, f"Extreme CC must be CRITICAL, got {sevs}"

    def test_low_method_large_class_is_not_god_class(self):
        """A big file with few methods is a 'large class', never a 'god class'."""
        repo = _node("repo", "r", NodeType.REPOSITORY, {})
        f = self._file("f", "src/pipeline/infrastructure/diagram_generator.py", 620, classes=1)
        cls = _node("c", "DiagramGenerator", NodeType.CLASS, {
            "file": "src/pipeline/infrastructure/diagram_generator.py",
            "line": 1, "lines": 600, "methods": 3, "is_abstract": False,
        })
        edges = [_edge("f", "c", RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f, cls], edges)
        god = [i for i in report.issues
               if i.affected_symbol == "DiagramGenerator" and "god class" in i.title.lower()]
        assert not god, "3-method class must not be a god class"
