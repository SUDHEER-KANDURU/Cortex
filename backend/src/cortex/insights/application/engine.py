"""Insights engine — computes engineering health from graph data.

Reads graph nodes and edges already stored in SQLite.
No re-analysis required — all data comes from the last pipeline run.
"""

from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING

import structlog

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.insights.domain.entities import (
    CodeIssue,
    HealthDimension,
    InsightsReport,
    IssueSeverity,
    IssueCategory,
    MetricScore,
)

if TYPE_CHECKING:
    from cortex.graph.domain.entities import GraphNode, GraphEdge

logger = structlog.get_logger()


class InsightsEngine:
    """Derives engineering insights from an existing knowledge graph.

    All methods are pure computations over lists of nodes/edges —
    no database calls, no HTTP, no side effects.
    """

    def compute(
        self,
        job_id: str,
        repo_url: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> InsightsReport:
        repo_name = repo_url.rstrip("/").split("/")[-1]

        # Index nodes by type for fast lookups
        by_type: dict[NodeType, list[GraphNode]] = defaultdict(list)
        for node in nodes:
            by_type[node.node_type].append(node)

        # Index edges by source for fast lookups
        edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            edges_from[edge.source_id].append(edge)
            edges_to[edge.target_id].append(edge)

        issues: list[CodeIssue] = []

        # Compute each dimension
        complexity_dim = self._complexity_dimension(by_type, issues)
        coupling_dim = self._coupling_dimension(by_type, edges_from, edges_to, issues)
        size_dim = self._size_dimension(by_type, issues)
        architecture_dim = self._architecture_dimension(by_type, edges, issues)
        documentation_dim = self._documentation_dimension(by_type, issues)

        dimensions = [
            complexity_dim,
            coupling_dim,
            size_dim,
            architecture_dim,
            documentation_dim,
        ]

        # Overall score = weighted average
        weights = [0.25, 0.25, 0.20, 0.20, 0.10]
        overall = int(sum(d.score * w for d, w in zip(dimensions, weights)))

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "repositories": len(by_type[NodeType.REPOSITORY]),
            "modules": len(by_type[NodeType.MODULE]),
            "files": len(by_type[NodeType.FILE]),
            "classes": len(by_type[NodeType.CLASS]),
            "functions": len(by_type[NodeType.FUNCTION]),
            "total_issues": len(issues),
            "high_issues": len([i for i in issues if i.severity == IssueSeverity.HIGH]),
            "medium_issues": len([i for i in issues if i.severity == IssueSeverity.MEDIUM]),
            "low_issues": len([i for i in issues if i.severity == IssueSeverity.LOW]),
        }

        report = InsightsReport(
            job_id=job_id,
            repo_url=repo_url,
            repo_name=repo_name,
            overall_score=overall,
            overall_grade=HealthDimension.grade_from_score(overall),
            dimensions=dimensions,
            issues=sorted(
                issues,
                key=lambda i: {"high": 0, "medium": 1, "low": 2, "info": 3}[i.severity.value],
            ),
            stats=stats,
        )

        logger.info(
            "insights_computed",
            job_id=job_id,
            overall_score=overall,
            total_issues=len(issues),
        )

        return report

    # ── Dimensions ───────────────────────────────────────────────────────────

    def _complexity_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Measure function size and class method count."""
        functions = by_type[NodeType.FUNCTION]
        classes = by_type[NodeType.CLASS]

        god_functions = []
        large_functions = []
        for fn in functions:
            lines = int(fn.properties.get("lines", 0))
            if lines > 60:
                god_functions.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God function detected",
                    description=f"`{fn.label}` is {lines} lines long.",
                    suggestion="Split into smaller single-purpose functions (aim for <30 lines).",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))
            elif lines > 35:
                large_functions.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large function",
                    description=f"`{fn.label}` is {lines} lines.",
                    suggestion="Consider extracting helper functions.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))

        god_classes = []
        for cls in classes:
            methods = int(cls.properties.get("methods", 0))
            if methods > 20:
                god_classes.append(cls)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God class detected",
                    description=f"`{cls.label}` has {methods} methods — likely doing too much.",
                    suggestion="Apply Single Responsibility Principle. Split into focused classes.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=cls.label,
                ))
            elif methods > 12:
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large class",
                    description=f"`{cls.label}` has {methods} methods.",
                    suggestion="Consider splitting responsibilities across multiple classes.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=cls.label,
                ))

        # Score: deduct for god functions and classes
        penalty = len(god_functions) * 8 + len(god_classes) * 10 + len(large_functions) * 3
        score = max(0, min(100, 100 - penalty))

        avg_fn_lines = 0.0
        if functions:
            avg_fn_lines = sum(
                int(f.properties.get("lines", 0)) for f in functions
            ) / len(functions)

        return HealthDimension(
            name="Complexity",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(god_functions)} god functions, {len(god_classes)} god classes detected.",
            metrics=[
                MetricScore("Total Functions", 100, len(functions), "functions", "All function/method nodes in the graph"),
                MetricScore("God Functions (>60 lines)", max(0, 100 - len(god_functions) * 15), len(god_functions), "functions", "Functions with >60 lines"),
                MetricScore("God Classes (>20 methods)", max(0, 100 - len(god_classes) * 20), len(god_classes), "classes", "Classes with >20 methods"),
                MetricScore("Average Function Size", max(0, int(100 - max(0, avg_fn_lines - 15) * 2)), round(avg_fn_lines, 1), "lines", "Average lines per function"),
            ],
        )

    def _coupling_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        edges_from: dict[str, list[GraphEdge]],
        edges_to: dict[str, list[GraphEdge]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Measure import coupling and dependency fan-out."""
        files = by_type[NodeType.FILE]

        high_fanout = []
        high_fanin = []

        for f in files:
            out_edges = [
                e for e in edges_from.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
            ]
            in_edges = [
                e for e in edges_to.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
            ]

            if len(out_edges) > 10:
                high_fanout.append((f, len(out_edges)))
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.HIGH,
                    title="High fan-out (too many dependencies)",
                    description=f"`{f.label}` imports {len(out_edges)} other modules.",
                    suggestion="Reduce direct dependencies. Consider a facade or mediator pattern.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))
            elif len(out_edges) > 6:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Moderate fan-out",
                    description=f"`{f.label}` imports {len(out_edges)} modules.",
                    suggestion="Review whether all dependencies are necessary.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

            if len(in_edges) > 15:
                high_fanin.append((f, len(in_edges)))
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="High fan-in (too many dependents)",
                    description=f"`{f.label}` is imported by {len(in_edges)} files — changes here ripple widely.",
                    suggestion="This file is a critical dependency. Document it thoroughly and keep its interface stable.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

        # Detect deep inheritance chains
        classes = by_type[NodeType.CLASS]
        for cls in classes:
            bases = str(cls.properties.get("base_classes", ""))
            base_count = len([b for b in bases.split(",") if b.strip()]) if bases else 0
            if base_count >= 3:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Deep inheritance",
                    description=f"`{cls.label}` inherits from {base_count} base classes.",
                    suggestion="Prefer composition over inheritance. Deep hierarchies are hard to understand.",
                    file_path=str(cls.properties.get("file", "")),
                    affected_symbol=cls.label,
                ))

        penalty = len(high_fanout) * 10 + len(high_fanin) * 5
        score = max(0, min(100, 100 - penalty))

        avg_deps = 0.0
        if files:
            avg_deps = sum(
                len([e for e in edges_from.get(f.id, [])
                     if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)])
                for f in files
            ) / len(files)

        return HealthDimension(
            name="Coupling",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(high_fanout)} high fan-out files detected.",
            metrics=[
                MetricScore("High Fan-out Files", max(0, 100 - len(high_fanout) * 15), len(high_fanout), "files", "Files importing >10 modules"),
                MetricScore("High Fan-in Files", max(0, 100 - len(high_fanin) * 8), len(high_fanin), "files", "Files imported by >15 others"),
                MetricScore("Avg Dependencies/File", max(0, int(100 - max(0, avg_deps - 3) * 8)), round(avg_deps, 1), "imports", "Average import count per file"),
            ],
        )

    def _size_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Measure file sizes and overall codebase scale."""
        files = by_type[NodeType.FILE]

        large_files = []
        for f in files:
            lines = int(f.properties.get("lines", 0))
            if lines > 500:
                large_files.append(f)
                issues.append(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.HIGH,
                    title="Large file",
                    description=f"`{f.label}` is {lines} lines long.",
                    suggestion="Split into multiple focused modules. Large files are hard to navigate and test.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))
            elif lines > 300:
                issues.append(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.LOW,
                    title="Moderately large file",
                    description=f"`{f.label}` is {lines} lines.",
                    suggestion="Consider splitting if it grows further.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

        avg_lines = 0.0
        if files:
            avg_lines = sum(int(f.properties.get("lines", 0)) for f in files) / len(files)

        penalty = len(large_files) * 12
        score = max(0, min(100, 100 - penalty))

        return HealthDimension(
            name="Size",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(files)} files, {len(large_files)} oversized.",
            metrics=[
                MetricScore("Total Files", 100, len(files), "files", "All source files in the graph"),
                MetricScore("Large Files (>500 lines)", max(0, 100 - len(large_files) * 20), len(large_files), "files", "Files with >500 lines"),
                MetricScore("Average File Size", max(0, int(100 - max(0, avg_lines - 100) * 0.15)), round(avg_lines, 0), "lines", "Average lines per file"),
                MetricScore("Classes / File Ratio", 100, round(len(by_type[NodeType.CLASS]) / max(1, len(files)), 2), "ratio", "Average classes per file"),
            ],
        )

    def _architecture_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        edges: list[GraphEdge],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Measure architectural quality — module structure, layering."""
        modules = by_type[NodeType.MODULE]
        classes = by_type[NodeType.CLASS]
        files = by_type[NodeType.FILE]

        # Detect circular dependency candidates using edge set
        import_edges = [
            e for e in edges
            if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
        ]
        # Build set of (source, target) pairs
        edge_set = {(e.source_id, e.target_id) for e in import_edges}
        circular_count = sum(
            1 for (src, tgt) in edge_set if (tgt, src) in edge_set
        )

        if circular_count > 0:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.HIGH,
                title="Circular dependencies detected",
                description=f"{circular_count} mutual import pairs found.",
                suggestion="Break cycles by extracting shared interfaces or inverting dependencies.",
                affected_symbol="multiple files",
            ))

        # Check if there are abstract classes (good sign of proper interfaces)
        abstract_classes = [
            c for c in classes
            if str(c.properties.get("is_abstract", "False")) == "True"
        ]

        # Low module count relative to files = poor modularization
        if len(files) > 10 and len(modules) < 2:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.MEDIUM,
                title="Poor modularization",
                description=f"{len(files)} files spread across only {len(modules)} modules.",
                suggestion="Organize files into meaningful packages/directories by responsibility.",
            ))

        penalty = circular_count * 15
        score = max(0, min(100, 100 - penalty))
        # Bonus for having abstractions
        if abstract_classes:
            score = min(100, score + min(10, len(abstract_classes) * 2))

        return HealthDimension(
            name="Architecture",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(modules)} modules, {circular_count} circular dependency pairs.",
            metrics=[
                MetricScore("Modules", 100, len(modules), "modules", "Distinct packages/directories"),
                MetricScore("Abstract Classes", min(100, len(abstract_classes) * 25), len(abstract_classes), "classes", "Interfaces and abstract base classes"),
                MetricScore("Circular Dependencies", max(0, 100 - circular_count * 20), circular_count, "pairs", "Mutual import cycles"),
                MetricScore("INHERITS edges", 100, len([e for e in edges if e.relationship == RelationshipType.INHERITS]), "edges", "Inheritance relationships in graph"),
            ],
        )

    def _documentation_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Estimate documentation coverage from class/function nodes."""
        classes = by_type[NodeType.CLASS]
        functions = by_type[NodeType.FUNCTION]

        # Heuristic: functions with 0 lines in properties are likely
        # placeholders or very short — flag large ones with no docstring proxy
        undocumented = []
        for fn in functions:
            lines = int(fn.properties.get("lines", 0))
            is_method = bool(fn.properties.get("is_method", False))
            # Only flag non-trivial public top-level functions
            if lines > 15 and not fn.label.startswith("_") and not is_method:
                undocumented.append(fn)

        if len(undocumented) > 5:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.LOW,
                title="Low documentation coverage",
                description=f"{len(undocumented)} public functions with >15 lines may lack docstrings.",
                suggestion="Add docstrings to all public functions explaining purpose, params, and return values.",
            ))

        doc_ratio = max(0.0, 1.0 - (len(undocumented) / max(1, len(functions))))
        score = int(doc_ratio * 100)

        return HealthDimension(
            name="Documentation",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(undocumented)} potentially undocumented public functions.",
            metrics=[
                MetricScore("Estimated Doc Coverage", score, round(doc_ratio * 100, 1), "%", "Proportion of functions likely documented"),
                MetricScore("Total Public Functions", 100, len([f for f in functions if not f.label.startswith("_")]), "functions", "Public functions in graph"),
            ],
        )

    def to_markdown_report(self, report: InsightsReport) -> str:
        """Generate a full engineering report as markdown."""
        lines = [
            f"# Engineering Health Report — {report.repo_name}",
            "",
            f"**Overall Score: {report.overall_score}/100 ({report.overall_grade})**",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Nodes | {report.stats.get('total_nodes', 0)} |",
            f"| Files | {report.stats.get('files', 0)} |",
            f"| Classes | {report.stats.get('classes', 0)} |",
            f"| Functions | {report.stats.get('functions', 0)} |",
            f"| Total Issues | {report.stats.get('total_issues', 0)} |",
            f"| High Severity | {report.stats.get('high_issues', 0)} |",
            f"| Medium Severity | {report.stats.get('medium_issues', 0)} |",
            "",
            "## Dimension Scores",
            "",
            "| Dimension | Score | Grade | Summary |",
            "|-----------|-------|-------|---------|",
        ]

        for dim in report.dimensions:
            lines.append(f"| {dim.name} | {dim.score}/100 | {dim.grade} | {dim.summary} |")

        lines += ["", "## Issues", ""]

        if not report.issues:
            lines.append("✅ No issues detected.")
        else:
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}
            for issue in report.issues[:30]:
                icon = sev_icon.get(issue.severity.value, "⚪")
                lines += [
                    f"### {icon} {issue.title}",
                    "",
                    f"**Category:** {issue.category.value.title()}",
                ]
                if issue.file_path:
                    lines.append(f"**File:** `{issue.file_path}`")
                if issue.affected_symbol:
                    lines.append(f"**Symbol:** `{issue.affected_symbol}`")
                lines += [
                    "",
                    f"**Issue:** {issue.description}",
                    "",
                    f"**Suggestion:** {issue.suggestion}",
                    "",
                ]

        return "\n".join(lines)
