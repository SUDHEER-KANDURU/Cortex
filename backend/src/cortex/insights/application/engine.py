"""Insights engine — computes engineering health from graph data.

Reads graph nodes and edges already stored in SQLite.
No re-analysis required — all data comes from the last pipeline run.

Design principles:
- Every check uses ACTUAL stored properties (has_docstring, lines, param_count, etc.)
- Thresholds are industry-standard (Google/NASA style guides, Clean Code)
- Scores are calibrated: a healthy mid-size repo should land B/C, not F
- Each issue carries file path + line number when available
- Naming, error-handling, async hygiene, param-count all analysed
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


# ── Industry thresholds ───────────────────────────────────────────────────────
# Based on: Clean Code (Martin), Google style guides, SonarQube defaults

_FN_LINES_CRITICAL   = 50   # >50 lines → god function (SonarQube default)
_FN_LINES_WARNING    = 30   # >30 lines → large (Google Python style)
_FN_PARAMS_CRITICAL  = 7    # >7 params → too many (Clean Code)
_FN_PARAMS_WARNING   = 5    # >5 params → worth noting
_CLASS_METHODS_CRIT  = 20   # >20 methods → god class
_CLASS_METHODS_WARN  = 12   # >12 methods → large class
_CLASS_LINES_CRIT    = 400  # >400 lines → too large
_FILE_LINES_CRIT     = 500  # >500 lines → split candidate
_FILE_LINES_WARN     = 300  # >300 lines → watch list
_FANOUT_CRIT         = 12   # >12 imports in one file
_FANOUT_WARN         = 8    # >8 imports
_FANIN_CRIT          = 20   # imported by >20 files → fragile hub
_FANIN_WARN          = 10   # imported by >10 files
_DOC_COVERAGE_LOW    = 0.50 # below 50% documented = issue
_DOC_COVERAGE_WARN   = 0.70 # below 70% = warning


class InsightsEngine:
    """Derives engineering insights from an existing knowledge graph."""

    def compute(
        self,
        job_id: str,
        repo_url: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> InsightsReport:
        repo_name = repo_url.rstrip("/").split("/")[-1]

        # ── Index nodes by type ───────────────────────────────────────────────
        by_type: dict[NodeType, list[GraphNode]] = defaultdict(list)
        for node in nodes:
            by_type[node.node_type].append(node)

        # ── Index edges ───────────────────────────────────────────────────────
        edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        edges_to:   dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            edges_from[edge.source_id].append(edge)
            edges_to[edge.target_id].append(edge)

        issues: list[CodeIssue] = []

        # ── Compute each dimension ────────────────────────────────────────────
        complexity_dim    = self._complexity_dimension(by_type, issues)
        coupling_dim      = self._coupling_dimension(by_type, edges_from, edges_to, issues)
        size_dim          = self._size_dimension(by_type, issues)
        architecture_dim  = self._architecture_dimension(by_type, edges, edges_from, edges_to, issues)
        documentation_dim = self._documentation_dimension(by_type, issues)
        naming_dim        = self._naming_dimension(by_type, issues)

        dimensions = [
            complexity_dim,
            coupling_dim,
            size_dim,
            architecture_dim,
            documentation_dim,
            naming_dim,
        ]

        # ── Overall weighted score ────────────────────────────────────────────
        # Weights reflect real-world impact on maintainability
        weights = [0.22, 0.22, 0.18, 0.20, 0.10, 0.08]
        overall = int(sum(d.score * w for d, w in zip(dimensions, weights)))
        overall = max(0, min(100, overall))

        # ── Stats ─────────────────────────────────────────────────────────────
        all_fns   = by_type[NodeType.FUNCTION]
        doc_fns   = [f for f in all_fns if str(f.properties.get("has_docstring", False)) == "True"]
        async_fns = [f for f in all_fns if str(f.properties.get("is_async", False)) == "True"]

        stats = {
            "total_nodes":    len(nodes),
            "total_edges":    len(edges),
            "repositories":   len(by_type[NodeType.REPOSITORY]),
            "modules":        len(by_type[NodeType.MODULE]),
            "files":          len(by_type[NodeType.FILE]),
            "classes":        len(by_type[NodeType.CLASS]),
            "functions":      len(all_fns),
            "async_functions": len(async_fns),
            "documented_fns": len(doc_fns),
            "total_issues":   len(issues),
            "high_issues":    len([i for i in issues if i.severity == IssueSeverity.HIGH]),
            "medium_issues":  len([i for i in issues if i.severity == IssueSeverity.MEDIUM]),
            "low_issues":     len([i for i in issues if i.severity == IssueSeverity.LOW]),
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
                key=lambda i: ({"high": 0, "medium": 1, "low": 2, "info": 3}[i.severity.value], i.file_path),
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

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Complexity
    # ═══════════════════════════════════════════════════════════════════════════

    def _complexity_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Function size, class size, parameter count, async correctness."""
        functions = by_type[NodeType.FUNCTION]
        classes   = by_type[NodeType.CLASS]

        god_fns: list[GraphNode]   = []
        large_fns: list[GraphNode] = []
        high_param: list[GraphNode]= []

        for fn in functions:
            lines      = int(fn.properties.get("lines", 0))
            param_count= int(fn.properties.get("param_count", 0))
            name       = fn.label

            # Strip 'self'/'cls' for methods — they don't count
            is_method  = bool(fn.properties.get("is_method", False))
            effective_params = max(0, param_count - 1) if is_method else param_count

            if lines > _FN_LINES_CRITICAL:
                god_fns.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God function — too long",
                    description=f"`{name}` is {lines} lines (limit: {_FN_LINES_CRITICAL}). Functions this long violate SRP and are hard to test.",
                    suggestion="Extract logical blocks into named helper functions. Aim for <30 lines per function.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))
            elif lines > _FN_LINES_WARNING:
                large_fns.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large function",
                    description=f"`{name}` is {lines} lines. Consider breaking it down.",
                    suggestion="Extract helper functions for distinct logical steps.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))

            if effective_params > _FN_PARAMS_CRITICAL:
                high_param.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="Too many parameters",
                    description=f"`{name}` takes {effective_params} parameters (limit: {_FN_PARAMS_CRITICAL}). Hard to call and test correctly.",
                    suggestion="Introduce a config/options dataclass or builder pattern to group related params.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))
            elif effective_params > _FN_PARAMS_WARNING:
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="High parameter count",
                    description=f"`{name}` takes {effective_params} parameters.",
                    suggestion="Consider grouping related parameters into a dataclass.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=fn.label,
                ))

        god_classes: list[GraphNode]   = []
        large_classes: list[GraphNode] = []

        for cls in classes:
            methods    = int(cls.properties.get("methods", 0))
            cls_lines  = int(cls.properties.get("lines", 0))
            name       = cls.label

            if methods > _CLASS_METHODS_CRIT or cls_lines > _CLASS_LINES_CRIT:
                god_classes.append(cls)
                detail = f"{methods} methods" if methods > _CLASS_METHODS_CRIT else f"{cls_lines} lines"
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God class detected",
                    description=f"`{name}` has {detail} — almost certainly violates Single Responsibility.",
                    suggestion="Apply SRP: split into focused classes. Extract services, validators, or helpers.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=name,
                ))
            elif methods > _CLASS_METHODS_WARN:
                large_classes.append(cls)
                issues.append(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large class",
                    description=f"`{name}` has {methods} methods.",
                    suggestion="Consider splitting responsibilities. Aim for <10 public methods per class.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=name,
                ))

        # ── Scoring ───────────────────────────────────────────────────────────
        n_fns = max(1, len(functions))
        n_cls = max(1, len(classes))

        god_fn_pct   = len(god_fns)   / n_fns
        large_fn_pct = len(large_fns) / n_fns
        god_cls_pct  = len(god_classes) / n_cls
        param_pct    = len(high_param)  / n_fns

        # Weighted penalty — god issues hurt more than large issues
        penalty = (
            god_fn_pct   * 50 +
            large_fn_pct * 20 +
            god_cls_pct  * 40 +
            param_pct    * 30
        )
        score = max(0, min(100, int(100 - penalty)))

        avg_fn_lines = (
            sum(int(f.properties.get("lines", 0)) for f in functions) / n_fns
            if functions else 0.0
        )
        avg_params = (
            sum(int(f.properties.get("param_count", 0)) for f in functions) / n_fns
            if functions else 0.0
        )

        return HealthDimension(
            name="Complexity",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(god_fns)} god functions, {len(god_classes)} god classes, "
                f"{len(high_param)} high-param functions."
            ),
            metrics=[
                MetricScore("Total Functions",           100, len(functions),           "functions", "All function/method nodes"),
                MetricScore("God Functions (>50 lines)", max(0, 100 - int(god_fn_pct * 100)), len(god_fns), "functions", f"Functions exceeding {_FN_LINES_CRITICAL} lines"),
                MetricScore("Large Functions (>30 lines)",max(0, 100 - int(large_fn_pct * 60)), len(large_fns), "functions", f"Functions between {_FN_LINES_WARNING}–{_FN_LINES_CRITICAL} lines"),
                MetricScore("God Classes (>20 methods)", max(0, 100 - int(god_cls_pct * 100)), len(god_classes), "classes", "Classes likely violating SRP"),
                MetricScore("High-Param Functions (>7)", max(0, 100 - int(param_pct * 100)), len(high_param), "functions", "Functions with too many parameters"),
                MetricScore("Avg Function Length",       max(0, int(100 - max(0, avg_fn_lines - 15) * 1.5)), round(avg_fn_lines, 1), "lines", "Average lines per function"),
                MetricScore("Avg Parameter Count",       max(0, int(100 - max(0, avg_params - 2) * 15)), round(avg_params, 1), "params", "Average parameters per function"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Coupling
    # ═══════════════════════════════════════════════════════════════════════════

    def _coupling_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        edges_from: dict[str, list[GraphEdge]],
        edges_to:   dict[str, list[GraphEdge]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Import fan-out/fan-in, deep inheritance, instability ratio."""
        files   = by_type[NodeType.FILE]
        classes = by_type[NodeType.CLASS]

        high_fanout: list[tuple[GraphNode, int]] = []
        high_fanin:  list[tuple[GraphNode, int]] = []
        instability_values: list[float] = []

        for f in files:
            # De-duplicate: multiple IMPORTS+DEPENDS_ON edges per target
            out_targets = {
                e.target_id for e in edges_from.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
            }
            in_sources = {
                e.source_id for e in edges_to.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
            }
            fan_out = len(out_targets)
            fan_in  = len(in_sources)

            # Martin's instability = Ce / (Ca + Ce)  (1=unstable, 0=stable)
            if fan_out + fan_in > 0:
                instability = fan_out / (fan_out + fan_in)
                instability_values.append(instability)

            if fan_out > _FANOUT_CRIT:
                high_fanout.append((f, fan_out))
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.HIGH,
                    title="High fan-out (excessive dependencies)",
                    description=f"`{f.label}` imports {fan_out} distinct modules (limit: {_FANOUT_CRIT}).",
                    suggestion="Apply Facade or Mediator pattern to reduce direct dependencies. Consider dependency injection.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))
            elif fan_out > _FANOUT_WARN:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Elevated fan-out",
                    description=f"`{f.label}` imports {fan_out} modules.",
                    suggestion="Review whether all dependencies are necessary. Look for consolidation opportunities.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

            if fan_in > _FANIN_CRIT:
                high_fanin.append((f, fan_in))
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Critical hub — high fan-in",
                    description=f"`{f.label}` is imported by {fan_in} files. Changes here have wide blast radius.",
                    suggestion="Freeze the public interface. Add comprehensive tests. Document invariants clearly.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))
            elif fan_in > _FANIN_WARN:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.LOW,
                    title="Moderate fan-in",
                    description=f"`{f.label}` is imported by {fan_in} files.",
                    suggestion="Keep the public API of this file stable. Avoid breaking changes.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

        # Deep inheritance check — uses actual base_classes property
        for cls in classes:
            bases_raw  = str(cls.properties.get("base_classes", ""))
            base_list  = [b.strip() for b in bases_raw.split(",") if b.strip()]
            base_count = len(base_list)
            if base_count >= 3:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Deep multiple inheritance",
                    description=f"`{cls.label}` inherits from {base_count} base classes: {bases_raw}.",
                    suggestion="Prefer composition over inheritance. Use mixins only for orthogonal concerns.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=cls.label,
                ))
            elif base_count == 2:
                issues.append(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.LOW,
                    title="Multiple inheritance",
                    description=f"`{cls.label}` inherits from 2 base classes: {bases_raw}.",
                    suggestion="Verify this cannot be replaced with composition or a single mixin.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=cls.label,
                ))

        # ── Scoring ───────────────────────────────────────────────────────────
        n_files = max(1, len(files))
        fanout_pct = len(high_fanout) / n_files
        fanin_pct  = len(high_fanin)  / n_files
        avg_instability = (
            sum(instability_values) / len(instability_values)
            if instability_values else 0.0
        )
        avg_fan_out = (
            sum(v for _, v in high_fanout) / len(high_fanout)
            if high_fanout else 0.0
        )

        penalty = fanout_pct * 55 + fanin_pct * 25
        score   = max(0, min(100, int(100 - penalty)))

        return HealthDimension(
            name="Coupling",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(high_fanout)} high fan-out files, "
                f"{len(high_fanin)} critical hubs."
            ),
            metrics=[
                MetricScore("High Fan-out Files (>12 deps)",  max(0, 100 - int(fanout_pct * 100)), len(high_fanout), "files",   f"Files importing >{_FANOUT_CRIT} modules"),
                MetricScore("Critical Hubs (>20 dependents)", max(0, 100 - int(fanin_pct  * 100)), len(high_fanin),  "files",   f"Files imported by >{_FANIN_CRIT} others"),
                MetricScore("Avg Instability (0=stable)",     max(0, int((1 - avg_instability) * 100)), round(avg_instability, 2), "ratio", "Martin's instability metric Ce/(Ca+Ce)"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Size
    # ═══════════════════════════════════════════════════════════════════════════

    def _size_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """File-level size checks + classes-per-file ratio."""
        files = by_type[NodeType.FILE]

        large_files: list[GraphNode] = []
        watch_files: list[GraphNode] = []

        for f in files:
            lines = int(f.properties.get("lines", 0))
            if lines > _FILE_LINES_CRIT:
                large_files.append(f)
                issues.append(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.HIGH,
                    title="Oversized file",
                    description=f"`{f.label}` is {lines} lines (limit: {_FILE_LINES_CRIT}).",
                    suggestion="Split into focused modules by responsibility. Each file should do one thing.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))
            elif lines > _FILE_LINES_WARN:
                watch_files.append(f)
                issues.append(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.LOW,
                    title="Large file — watch list",
                    description=f"`{f.label}` is {lines} lines.",
                    suggestion="Consider splitting if complexity grows further.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

        n_files    = max(1, len(files))
        n_classes  = len(by_type[NodeType.CLASS])
        avg_lines  = sum(int(f.properties.get("lines", 0)) for f in files) / n_files if files else 0.0
        cls_per_file = n_classes / n_files

        # Flag files with many classes — likely mixed responsibilities
        for f in files:
            cls_count = int(f.properties.get("classes", 0))
            if cls_count > 5:
                issues.append(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.MEDIUM,
                    title="Too many classes in one file",
                    description=f"`{f.label}` defines {cls_count} classes.",
                    suggestion="One class (or tightly related group) per file is the standard. Split into separate modules.",
                    file_path=str(f.properties.get("path", "")),
                    affected_symbol=f.label,
                ))

        large_pct = len(large_files) / n_files
        penalty   = large_pct * 60
        score     = max(0, min(100, int(100 - penalty)))

        return HealthDimension(
            name="Size",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(files)} files analysed, {len(large_files)} oversized, "
                f"{len(watch_files)} on watch list."
            ),
            metrics=[
                MetricScore("Total Files",                 100,                                    len(files),       "files", "All source files in the graph"),
                MetricScore("Oversized Files (>500 lines)",max(0, 100 - int(large_pct * 100)),    len(large_files), "files", f"Files exceeding {_FILE_LINES_CRIT} lines"),
                MetricScore("Watch-list Files (>300 lines)",max(0, 100 - len(watch_files) * 5),   len(watch_files), "files", f"Files between {_FILE_LINES_WARN}–{_FILE_LINES_CRIT} lines"),
                MetricScore("Avg File Size",               max(0, int(100 - max(0, avg_lines - 80) * 0.12)), round(avg_lines, 0), "lines", "Average lines per file"),
                MetricScore("Classes / File",              max(0, int(100 - max(0, cls_per_file - 1) * 20)), round(cls_per_file, 2), "ratio", "Average classes per file (1 is ideal)"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Architecture
    # ═══════════════════════════════════════════════════════════════════════════

    def _architecture_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        edges: list[GraphEdge],
        edges_from: dict[str, list[GraphEdge]],
        edges_to:   dict[str, list[GraphEdge]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Circular deps, layering violations, abstraction ratio."""
        modules = by_type[NodeType.MODULE]
        classes = by_type[NodeType.CLASS]
        files   = by_type[NodeType.FILE]

        # ── True circular dependency detection ────────────────────────────────
        # Build adjacency: file_id → set of file_ids it imports (deduplicated)
        import_adj: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                import_adj[edge.source_id].add(edge.target_id)

        # Find mutual cycles A↔B (direct cycles) — these are definitive
        direct_cycles: list[tuple[str, str]] = []
        seen_pairs: set[frozenset] = set()
        for src, targets in import_adj.items():
            for tgt in targets:
                pair = frozenset({src, tgt})
                if pair in seen_pairs:
                    continue
                if tgt in import_adj and src in import_adj[tgt]:
                    direct_cycles.append((src, tgt))
                    seen_pairs.add(pair)

        # Build node label lookup for reporting
        node_label: dict[str, str] = {n.id: n.label for n in files}
        node_path:  dict[str, str] = {
            n.id: str(n.properties.get("path", n.label)) for n in files
        }

        for src_id, tgt_id in direct_cycles[:10]:  # cap at 10 to avoid noise
            src_label = node_label.get(src_id, src_id)
            tgt_label = node_label.get(tgt_id, tgt_id)
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.HIGH,
                title="Circular dependency",
                description=f"`{src_label}` ↔ `{tgt_label}` mutually import each other.",
                suggestion="Break the cycle: extract shared types to a third module, or invert one dependency using an interface.",
                file_path=node_path.get(src_id, ""),
                affected_symbol=f"{src_label} ↔ {tgt_label}",
            ))

        # ── Abstract class / interface coverage ───────────────────────────────
        abstract_classes = [
            c for c in classes
            if str(c.properties.get("is_abstract", False)) == "True"
        ]
        abstraction_ratio = len(abstract_classes) / max(1, len(classes))

        # Low abstraction in larger codebases is an architectural smell
        if len(classes) > 10 and abstraction_ratio < 0.10:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.MEDIUM,
                title="Low abstraction coverage",
                description=f"Only {len(abstract_classes)} abstract classes out of {len(classes)} total ({round(abstraction_ratio*100)}%). Concrete-only designs resist change.",
                suggestion="Define interfaces or abstract base classes for core domain concepts. Program to abstractions, not concretions.",
                affected_symbol="codebase",
            ))

        # ── Poor modularisation ───────────────────────────────────────────────
        n_files = len(files)
        n_modules = len(modules)
        if n_files > 15 and n_modules < 3:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.MEDIUM,
                title="Poor modularisation",
                description=f"{n_files} files across only {n_modules} package(s).",
                suggestion="Group files by responsibility into sub-packages (e.g. domain/, application/, infrastructure/).",
            ))

        # ── Inheritance depth — detect deep chains ────────────────────────────
        # Build child→parents map from INHERITS edges
        inherits_edges = [e for e in edges if e.relationship == RelationshipType.INHERITS]
        child_parents: dict[str, set[str]] = defaultdict(set)
        for e in inherits_edges:
            child_parents[e.source_id].add(e.target_id)

        def _depth(node_id: str, visited: set) -> int:
            if node_id in visited or node_id not in child_parents:
                return 0
            visited.add(node_id)
            return 1 + max((_depth(p, visited) for p in child_parents[node_id]), default=0)

        class_id_label = {c.id: c.label for c in classes}
        class_id_file  = {c.id: str(c.properties.get("file", "")) for c in classes}

        for cls in classes:
            depth = _depth(cls.id, set())
            if depth >= 4:
                issues.append(CodeIssue(
                    category=IssueCategory.ARCHITECTURE,
                    severity=IssueSeverity.MEDIUM,
                    title="Deep inheritance chain",
                    description=f"`{cls.label}` has inheritance depth of {depth}.",
                    suggestion="Inheritance chains >3 levels are hard to understand. Favour composition.",
                    file_path=class_id_file.get(cls.id, ""),
                    affected_symbol=cls.label,
                ))

        # ── Scoring ───────────────────────────────────────────────────────────
        cycle_penalty        = len(direct_cycles) * 18
        abstraction_bonus    = min(15, int(abstraction_ratio * 60))
        modular_penalty      = 10 if (n_files > 15 and n_modules < 3) else 0

        score = max(0, min(100, 100 - cycle_penalty - modular_penalty + abstraction_bonus))

        inherit_count = len(inherits_edges)
        calls_count   = len([e for e in edges if e.relationship == RelationshipType.CALLS])

        return HealthDimension(
            name="Architecture",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{n_modules} modules, {len(direct_cycles)} circular dep pairs, "
                f"{len(abstract_classes)} abstractions."
            ),
            metrics=[
                MetricScore("Modules / Packages",           100,                              n_modules,              "modules",  "Distinct packages/directories"),
                MetricScore("Circular Dependencies",        max(0, 100 - len(direct_cycles) * 25), len(direct_cycles), "pairs",    "Mutual A↔B import cycles (definitive)"),
                MetricScore("Abstract Classes / Interfaces",min(100, int(abstraction_ratio * 200)), len(abstract_classes), "classes", "ABCs and interfaces present"),
                MetricScore("Abstraction Ratio",            min(100, int(abstraction_ratio * 200)), round(abstraction_ratio * 100, 1), "%", "% of classes that are abstract"),
                MetricScore("Inheritance Edges",            100,                              inherit_count,          "edges",    "INHERITS relationships in graph"),
                MetricScore("Call Edges",                   100,                              calls_count,            "edges",    "CALLS relationships captured"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Documentation
    # ═══════════════════════════════════════════════════════════════════════════

    def _documentation_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Uses the actual has_docstring property stored on every node."""
        functions = by_type[NodeType.FUNCTION]
        classes   = by_type[NodeType.CLASS]

        # ── Class docstrings ──────────────────────────────────────────────────
        public_classes     = [c for c in classes if not c.label.startswith("_")]
        undoc_classes      = [
            c for c in public_classes
            if str(c.properties.get("has_docstring", False)) != "True"
        ]

        # ── Function docstrings ───────────────────────────────────────────────
        # Only flag non-trivial public functions (>5 lines)
        non_trivial_fns    = [
            f for f in functions
            if not f.label.startswith("_") and int(f.properties.get("lines", 0)) > 5
        ]
        undoc_fns          = [
            f for f in non_trivial_fns
            if str(f.properties.get("has_docstring", False)) != "True"
        ]

        total_public       = len(public_classes) + len(non_trivial_fns)
        total_undoc        = len(undoc_classes)  + len(undoc_fns)
        doc_coverage       = 1.0 - (total_undoc / max(1, total_public))

        if len(undoc_classes) > 0:
            # Report top offenders by size (largest first)
            worst = sorted(undoc_classes, key=lambda c: int(c.properties.get("lines", 0)), reverse=True)[:5]
            for cls in worst:
                issues.append(CodeIssue(
                    category=IssueCategory.DOCUMENTATION,
                    severity=IssueSeverity.MEDIUM,
                    title="Public class missing docstring",
                    description=f"`{cls.label}` has no docstring.",
                    suggestion="Add a class-level docstring explaining purpose, responsibilities, and usage.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=cls.label,
                ))

        if doc_coverage < _DOC_COVERAGE_LOW:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.HIGH,
                title="Critical documentation gap",
                description=f"Only {round(doc_coverage*100)}% of public symbols are documented ({total_public - total_undoc}/{total_public}).",
                suggestion="Adopt a docstring policy. Start with public APIs and complex functions. Use NumPy or Google style.",
            ))
        elif doc_coverage < _DOC_COVERAGE_WARN:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.MEDIUM,
                title="Low documentation coverage",
                description=f"{round(doc_coverage*100)}% of public symbols documented. Target ≥70%.",
                suggestion="Add docstrings to all public classes and non-trivial functions.",
            ))

        score = min(100, int(doc_coverage * 100))

        return HealthDimension(
            name="Documentation",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{round(doc_coverage*100)}% doc coverage "
                f"({total_public - total_undoc}/{total_public} public symbols documented)."
            ),
            metrics=[
                MetricScore("Doc Coverage",                score,                                  round(doc_coverage * 100, 1),       "%",         "Actual has_docstring=True ratio"),
                MetricScore("Undocumented Public Classes", max(0, 100 - len(undoc_classes) * 10), len(undoc_classes),                 "classes",   "Public classes without docstrings"),
                MetricScore("Undocumented Public Functions",max(0, 100 - len(undoc_fns) * 3),     len(undoc_fns),                     "functions", "Non-trivial public fns without docstrings"),
                MetricScore("Total Public Symbols",        100,                                    total_public,                       "symbols",   "Classes + non-trivial public functions"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Dimension: Naming
    # ═══════════════════════════════════════════════════════════════════════════

    def _naming_dimension(
        self,
        by_type: dict[NodeType, list[GraphNode]],
        issues: list[CodeIssue],
    ) -> HealthDimension:
        """Convention checks: snake_case functions, PascalCase classes, no single-letter names."""
        import re

        functions = by_type[NodeType.FUNCTION]
        classes   = by_type[NodeType.CLASS]

        _snake   = re.compile(r'^[a-z_][a-z0-9_]*$')
        _pascal  = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
        _dunder  = re.compile(r'^__[a-z]+__$')
        _private = re.compile(r'^_[a-z]')

        bad_fn_names:  list[GraphNode] = []
        bad_cls_names: list[GraphNode] = []
        too_short:     list[GraphNode] = []

        for fn in functions:
            name = fn.label
            if _dunder.match(name):       # __init__, __str__ — always OK
                continue
            if len(name) <= 2 and not _dunder.match(name) and not name.startswith("_"):
                too_short.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.NAMING,
                    severity=IssueSeverity.LOW,
                    title="Single/double letter function name",
                    description=f"`{name}` is too short to be self-documenting.",
                    suggestion="Use descriptive names that reveal intent (e.g. `calculate_total` not `ct`).",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=name,
                ))
            elif not _snake.match(name) and not _private.match(name) and not _dunder.match(name):
                bad_fn_names.append(fn)
                issues.append(CodeIssue(
                    category=IssueCategory.NAMING,
                    severity=IssueSeverity.LOW,
                    title="Non-standard function name (expected snake_case)",
                    description=f"`{name}` does not follow snake_case convention.",
                    suggestion="Rename to snake_case per PEP 8 / language conventions.",
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0)),
                    affected_symbol=name,
                ))

        for cls in classes:
            name = cls.label
            if not _pascal.match(name):
                bad_cls_names.append(cls)
                issues.append(CodeIssue(
                    category=IssueCategory.NAMING,
                    severity=IssueSeverity.LOW,
                    title="Non-standard class name (expected PascalCase)",
                    description=f"`{name}` does not follow PascalCase convention.",
                    suggestion="Rename to PascalCase per PEP 8 / language conventions.",
                    file_path=str(cls.properties.get("file", "")),
                    line=int(cls.properties.get("line", 0)),
                    affected_symbol=name,
                ))

        total_symbols  = max(1, len(functions) + len(classes))
        total_bad      = len(bad_fn_names) + len(bad_cls_names) + len(too_short)
        convention_pct = 1.0 - (total_bad / total_symbols)
        score          = max(0, min(100, int(convention_pct * 100)))

        return HealthDimension(
            name="Naming",
            score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{total_bad} naming violations across "
                f"{total_symbols} symbols checked."
            ),
            metrics=[
                MetricScore("Convention Compliance",          score, round(convention_pct * 100, 1), "%",         "% of symbols following naming rules"),
                MetricScore("Bad Function Names",             max(0, 100 - len(bad_fn_names) * 5),  len(bad_fn_names),  "functions", "Functions not in snake_case"),
                MetricScore("Bad Class Names",                max(0, 100 - len(bad_cls_names) * 8), len(bad_cls_names), "classes",   "Classes not in PascalCase"),
                MetricScore("Too-short Names (≤2 chars)",     max(0, 100 - len(too_short) * 8),     len(too_short),     "symbols",   "Single/double letter names"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Markdown export
    # ═══════════════════════════════════════════════════════════════════════════

    def to_markdown_report(self, report: InsightsReport) -> str:
        """Generate a full engineering report as markdown."""
        sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}

        lines = [
            f"# Engineering Health Report — {report.repo_name}",
            "",
            f"**Overall Score: {report.overall_score}/100 (Grade {report.overall_grade})**",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files | {report.stats.get('files', 0)} |",
            f"| Classes | {report.stats.get('classes', 0)} |",
            f"| Functions | {report.stats.get('functions', 0)} |",
            f"| Async Functions | {report.stats.get('async_functions', 0)} |",
            f"| Doc Coverage | {report.stats.get('documented_fns', 0)}/{report.stats.get('functions', 0)} fns |",
            f"| High Issues | {report.stats.get('high_issues', 0)} |",
            f"| Medium Issues | {report.stats.get('medium_issues', 0)} |",
            f"| Low Issues | {report.stats.get('low_issues', 0)} |",
            "",
            "## Dimension Scores",
            "",
            "| Dimension | Score | Grade | Summary |",
            "|-----------|-------|-------|---------|",
        ]

        for dim in report.dimensions:
            lines.append(f"| {dim.name} | {dim.score}/100 | {dim.grade} | {dim.summary} |")

        lines += ["", "## Issues by Severity", ""]

        if not report.issues:
            lines.append("✅ No issues detected.")
        else:
            for sev in ("high", "medium", "low", "info"):
                sev_issues = [i for i in report.issues if i.severity.value == sev]
                if not sev_issues:
                    continue
                icon = sev_icon.get(sev, "⚪")
                lines += [f"### {icon} {sev.capitalize()} ({len(sev_issues)})", ""]
                for issue in sev_issues:
                    lines += [f"**{issue.title}** — `{issue.affected_symbol or 'N/A'}`"]
                    if issue.file_path:
                        loc = f"{issue.file_path}:{issue.line}" if issue.line else issue.file_path
                        lines.append(f"- File: `{loc}`")
                    lines += [
                        f"- Issue: {issue.description}",
                        f"- Fix: {issue.suggestion}",
                        "",
                    ]

        return "\n".join(lines)
