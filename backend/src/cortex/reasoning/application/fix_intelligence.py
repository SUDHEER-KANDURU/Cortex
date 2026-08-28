"""Issue → Fix Intelligence — when an engineering insight is selected,
provide the full context needed to understand and fix it.

Shows: Problem → Evidence → Impact → Affected Code → Recommended Direction
       → Related Dependencies → Implementation Approach

Deterministic fix templates for common issues. NIM explains the approach.
"""

from __future__ import annotations

from collections import defaultdict

import structlog

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.insights.domain.entities import CodeIssue, IssueCategory
from cortex.overview.blast_radius import BlastRadiusAnalyzer
from cortex.reasoning.domain.entities import FixIntelligence

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# Fix Templates — deterministic guidance for common issue categories
# ═══════════════════════════════════════════════════════════════════════════════

_FIX_TEMPLATES: dict[str, dict[str, str | list[str]]] = {
    "god_class": {
        "approach": (
            "Extract responsibilities into focused classes. Identify cohesive "
            "groups of methods that operate on the same subset of fields, and "
            "move each group into its own class."
        ),
        "steps": [
            "Identify method clusters — groups of methods that use the same fields",
            "Name each cluster as a responsibility (e.g., 'validation', 'persistence', 'notification')",
            "Create a new class for each responsibility",
            "Move methods and their required fields to the new class",
            "Replace direct access in the original class with delegation to the new classes",
            "Update callers to use the new classes directly where appropriate",
            "Verify tests still pass after each extraction",
        ],
        "complexity": "significant",
    },
    "god_function": {
        "approach": (
            "Break the function into smaller, single-purpose functions. "
            "Each extracted function should have a clear name describing what it does."
        ),
        "steps": [
            "Identify logical sections within the function (usually separated by comments or blank lines)",
            "Extract each section into a named helper function",
            "Reduce nesting by using early returns and guard clauses",
            "Consider using the Strategy or Template Method pattern if sections vary by type",
            "Keep the original function as a high-level orchestrator",
        ],
        "complexity": "moderate",
    },
    "high_coupling": {
        "approach": (
            "Reduce coupling by introducing interfaces or dependency injection. "
            "The goal is to depend on abstractions rather than concrete implementations."
        ),
        "steps": [
            "Identify the concrete dependencies being imported directly",
            "Create an interface (abstract class or Protocol) for each dependency",
            "Inject dependencies through constructor parameters instead of importing directly",
            "Create a composition root (factory or DI container) to wire implementations",
            "Use the interface in type hints instead of the concrete class",
        ],
        "complexity": "significant",
    },
    "circular_dependency": {
        "approach": (
            "Break the cycle by extracting shared abstractions into a third module "
            "that both sides depend on, or by using dependency inversion."
        ),
        "steps": [
            "Identify which specific symbols create the cycle",
            "Extract shared interfaces/types into a 'contracts' or 'ports' module",
            "Have both modules depend on the shared contracts instead of each other",
            "If one direction is weaker, consider inverting it with callbacks or events",
        ],
        "complexity": "moderate",
    },
    "deep_inheritance": {
        "approach": (
            "Flatten the hierarchy using composition over inheritance. "
            "Replace 'is-a' relationships with 'has-a' when the hierarchy is primarily for code reuse."
        ),
        "steps": [
            "Identify which levels of the hierarchy add real specialization vs just sharing code",
            "Extract shared behavior into composable mixins or strategy objects",
            "Replace intermediate abstract classes with composition",
            "Keep inheritance only where true polymorphism is needed",
        ],
        "complexity": "significant",
    },
    "missing_documentation": {
        "approach": (
            "Add documentation to public APIs. Focus on 'why' and 'how to use', "
            "not 'what' (which should be clear from the name)."
        ),
        "steps": [
            "Document the class/module purpose in a top-level docstring",
            "Document each public method with: what it does, parameters, return value, exceptions",
            "Add usage examples for complex APIs",
            "Skip documentation for obvious getters/setters and private helpers",
        ],
        "complexity": "trivial",
    },
    "high_complexity": {
        "approach": (
            "Reduce cyclomatic complexity by simplifying branching logic. "
            "Extract complex conditions into named predicates and use early returns."
        ),
        "steps": [
            "Replace nested if/else chains with guard clauses (early returns)",
            "Extract complex boolean expressions into well-named predicate functions",
            "Consider replacing type-checking conditionals with polymorphism",
            "Use lookup tables or dictionaries instead of long switch/match statements",
            "Break the function into smaller sub-functions if it handles multiple concerns",
        ],
        "complexity": "moderate",
    },
}


class FixIntelligenceEngine:
    """Provides fix context and guidance for a detected engineering issue.

    Pure computation — no IO. Takes an issue + graph data and returns
    structured fix intelligence.
    """

    def analyze(
        self,
        issue: CodeIssue,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> FixIntelligence:
        """Produce fix intelligence for a specific issue."""
        fix = FixIntelligence(
            issue_title=issue.title,
            issue_category=issue.category.value,
            issue_severity=issue.severity.value,
            problem_description=issue.description,
            evidence=issue.evidence,
        )

        node_map = {n.id: n for n in nodes}

        # Find the affected node(s)
        affected_nodes = self._find_affected_nodes(issue, nodes)
        fix.affected_code = [
            {
                "file": str(n.properties.get("file", "")),
                "symbol": n.label,
                "type": n.node_type.value,
                "lines": str(n.properties.get("lines", "")),
            }
            for n in affected_nodes
        ]

        # Compute blast radius summary for the primary affected node
        if affected_nodes:
            primary = affected_nodes[0]
            analyzer = BlastRadiusAnalyzer()
            blast = analyzer.analyze(primary, nodes, edges)
            fix.blast_radius_summary = (
                f"Risk: {blast.risk_level} · "
                f"{len(blast.direct_dependents)} direct dependents · "
                f"{len(blast.transitive_dependents)} transitive · "
                f"{len(blast.affected_tests)} tests affected"
            )

        # Find related dependencies
        if affected_nodes:
            primary_id = affected_nodes[0].id
            deps = set()
            for edge in edges:
                if edge.source_id == primary_id and edge.relationship in (
                    RelationshipType.IMPORTS, RelationshipType.CALLS, RelationshipType.INHERITS
                ):
                    tgt = node_map.get(edge.target_id)
                    if tgt:
                        deps.add(f"{tgt.label} ({tgt.node_type.value})")
            fix.related_dependencies = sorted(deps)[:10]

        # Find related tests
        if affected_nodes:
            primary_id = affected_nodes[0].id
            tests = set()
            for edge in edges:
                if edge.relationship == RelationshipType.TESTS:
                    if edge.target_id == primary_id or edge.source_id == primary_id:
                        test_node = node_map.get(edge.source_id) or node_map.get(edge.target_id)
                        if test_node and test_node.node_type == NodeType.TEST:
                            tests.add(test_node.label)
            fix.related_tests = sorted(tests)[:10]

        # Apply fix template
        template_key = self._determine_template_key(issue)
        if template_key and template_key in _FIX_TEMPLATES:
            template = _FIX_TEMPLATES[template_key]
            fix.recommended_approach = str(template["approach"])
            fix.implementation_steps = list(template["steps"])
            fix.fix_template = template_key
            fix.estimated_complexity = str(template["complexity"])
        else:
            # Generic recommendation
            fix.recommended_approach = issue.recommendation
            fix.estimated_complexity = self._estimate_complexity(issue, affected_nodes)

        return fix

    def _find_affected_nodes(
        self, issue: CodeIssue, nodes: list[GraphNode]
    ) -> list[GraphNode]:
        """Find graph nodes affected by this issue."""
        affected: list[GraphNode] = []

        for node in nodes:
            # Match by symbol name
            if issue.affected_symbol and issue.affected_symbol.lower() == node.label.lower():
                affected.append(node)
                continue

            # Match by file path
            node_file = str(node.properties.get("file", ""))
            if issue.file_path and issue.file_path == node_file:
                # If we also have a symbol match requirement, check label
                if not issue.affected_symbol or issue.affected_symbol.lower() in node.label.lower():
                    affected.append(node)

        # Prioritize exact symbol matches
        affected.sort(key=lambda n: (
            0 if n.label.lower() == (issue.affected_symbol or "").lower() else 1,
            0 if n.node_type in (NodeType.CLASS, NodeType.FUNCTION) else 1,
        ))

        return affected[:5]

    def _determine_template_key(self, issue: CodeIssue) -> str:
        """Determine which fix template applies to this issue."""
        title_lower = issue.title.lower()
        desc_lower = issue.description.lower()
        combined = title_lower + " " + desc_lower

        if "god class" in combined or "too many method" in combined:
            return "god_class"
        if "god function" in combined or "too complex" in combined or "god" in title_lower:
            return "god_function"
        if "cyclomatic" in combined or "complexity" in combined:
            return "high_complexity"
        if "coupling" in combined or "fan-out" in combined or "high efferent" in combined:
            return "high_coupling"
        if "circular" in combined:
            return "circular_dependency"
        if "inheritance" in combined or "deep hierarchy" in combined:
            return "deep_inheritance"
        if "documentation" in combined or "docstring" in combined or "undocumented" in combined:
            return "missing_documentation"

        return ""

    def _estimate_complexity(
        self, issue: CodeIssue, affected_nodes: list[GraphNode]
    ) -> str:
        """Estimate the complexity of fixing this issue."""
        if issue.severity.value == "critical":
            return "significant"
        if issue.severity.value == "high":
            return "moderate"

        # Check how much code is affected
        total_lines = sum(
            int(n.properties.get("lines", 0) or 0) for n in affected_nodes
        )
        if total_lines > 200:
            return "significant"
        if total_lines > 50:
            return "moderate"
        return "trivial"
