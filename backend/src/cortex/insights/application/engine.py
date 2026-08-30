"""Insights engine — computes engineering health from graph data.

Design contract:
  - Every metric traces back to a stored graph property
  - Every issue carries evidence dict
  - Every dimension carries a confidence score
  - Test files never distort production metrics
  - Language rules are isolated — no Python rules applied to Java
  - Scores are normalised per-codebase, never raw issue counts
  - Thresholds are imported from thresholds.py, never scattered inline
  - Deterministic: same input → same output
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import TYPE_CHECKING

import structlog

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.insights.application.file_classifier import FileClassifier, FileCategory
from cortex.insights.application.grouping import group_into_concerns
from cortex.insights.application.language_rules import get_rules
from cortex.insights.domain import thresholds as T
from cortex.insights.domain.entities import (
    AnalysisCoverage,
    CodeIssue,
    HealthDimension,
    InsightsReport,
    IssueSeverity,
    IssueCategory,
    MetricScore,
)
from cortex.insights.domain.severity import (
    ArchitecturalRole,
    adjust_severity,
    classify_role,
)

if TYPE_CHECKING:
    from cortex.graph.domain.entities import GraphNode, GraphEdge

logger = structlog.get_logger()

_classifier = FileClassifier()


# ── Small helpers ─────────────────────────────────────────────────────────────

def _prop(node: "GraphNode", key: str, default=None):
    """Safe property accessor — never raises."""
    return node.properties.get(key, default)

def _int(node: "GraphNode", key: str) -> int:
    try:
        return int(_prop(node, key, 0) or 0)
    except (TypeError, ValueError):
        return 0

def _bool(node: "GraphNode", key: str) -> bool:
    v = _prop(node, key, False)
    if isinstance(v, bool): return v
    return str(v).lower() in ("true", "1", "yes")

def _str(node: "GraphNode", key: str) -> str:
    return str(_prop(node, key, "") or "")

def _percentile(values: list[float], p: float) -> float:
    if not values: return 0.0
    s = sorted(values)
    idx = (len(s) - 1) * p
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


# ── Context-aware severity plumbing ───────────────────────────────────────────

class _SeverityContext:
    """Per-analysis context used to make severity decisions context-aware.

    Built once at the start of compute() and shared (read-only) by every
    detector so a file's architectural role and blast-radius (fan-in) can
    influence how seriously a raw metric is treated.
    """

    def __init__(
        self,
        role_by_path: dict[str, ArchitecturalRole],
        fan_in_by_path: dict[str, int],
        hub_threshold: int,
    ) -> None:
        self.role_by_path = role_by_path
        self.fan_in_by_path = fan_in_by_path
        self.hub_threshold = hub_threshold

    def role(self, file_path: str) -> ArchitecturalRole:
        return self.role_by_path.get(file_path, ArchitecturalRole.ORDINARY)

    def fan_in(self, file_path: str) -> int:
        return self.fan_in_by_path.get(file_path, 0)

    def is_hub(self, file_path: str) -> bool:
        return self.fan_in(file_path) >= self.hub_threshold


# A neutral context (no role info) — used when a detector runs without one.
_NEUTRAL_CTX = _SeverityContext({}, {}, hub_threshold=int(T.FANIN_CRITICAL.value))


def _apply_context(
    issue: CodeIssue,
    ctx: _SeverityContext,
    *,
    signal: str,
    magnitude_ratio: float = 1.0,
    reinforcing_signals: int = 0,
) -> CodeIssue:
    """Adjust an issue's severity for architectural context, in place.

    Records the role, the signal key, and the human-readable factors that
    moved the severity onto the issue so the evidence trail stays honest.
    """
    role = ctx.role(issue.file_path)
    decision = adjust_severity(
        base=issue.severity,
        role=role,
        signal=signal,
        magnitude_ratio=magnitude_ratio,
        dependents=ctx.fan_in(issue.file_path),
        fan_in_hub=ctx.is_hub(issue.file_path),
        reinforcing_signals=reinforcing_signals,
    )
    issue.severity = decision.severity
    issue.architectural_role = role.value
    issue.signal = signal
    if decision.factors:
        issue.context_factors = decision.factors
    return issue


# ═══════════════════════════════════════════════════════════════════════════════
# InsightsEngine
# ═══════════════════════════════════════════════════════════════════════════════

class InsightsEngine:
    """Derives engineering insights from an existing knowledge graph.

    All methods are pure computations over lists of nodes/edges —
    no database calls, no HTTP, no side effects, no randomness.
    """

    def compute(
        self,
        job_id:   str,
        repo_url: str,
        nodes:    list["GraphNode"],
        edges:    list["GraphEdge"],
    ) -> InsightsReport:

        repo_name = repo_url.rstrip("/").split("/")[-1]

        # ── Index nodes by type ───────────────────────────────────────────────
        by_type: dict[NodeType, list["GraphNode"]] = defaultdict(list)
        for node in nodes:
            by_type[node.node_type].append(node)

        # ── Index edges ───────────────────────────────────────────────────────
        edges_from: dict[str, list["GraphEdge"]] = defaultdict(list)
        edges_to:   dict[str, list["GraphEdge"]] = defaultdict(list)
        for edge in edges:
            edges_from[edge.source_id].append(edge)
            edges_to[edge.target_id].append(edge)

        # ── Classify files ────────────────────────────────────────────────────
        file_nodes = by_type[NodeType.FILE]
        classified = {
            f.id: _classifier.classify(_str(f, "path") or f.label)
            for f in file_nodes
        }
        source_file_ids = {
            fid for fid, cf in classified.items()
            if cf.category == FileCategory.SOURCE
        }
        test_file_ids = {
            fid for fid, cf in classified.items()
            if cf.category == FileCategory.TEST
        }

        # Restrict analysis to source files
        source_files = [f for f in file_nodes if f.id in source_file_ids]
        test_files   = [f for f in file_nodes if f.id in test_file_ids]

        # Map class/function nodes back to their parent file
        # via CONTAINS edges: file → class → function
        fn_to_file:  dict[str, str] = {}   # function_node_id → file_node_id
        cls_to_file: dict[str, str] = {}   # class_node_id    → file_node_id

        # Build node-type index for O(1) lookup in edge traversal
        node_type_idx: dict[str, NodeType] = {n.id: n.node_type for n in nodes}

        for edge in edges:
            if edge.relationship != RelationshipType.CONTAINS:
                continue
            src, tgt = edge.source_id, edge.target_id
            src_type = node_type_idx.get(src)
            tgt_type = node_type_idx.get(tgt)
            if src_type == NodeType.FILE and tgt_type == NodeType.CLASS:
                cls_to_file[tgt] = src
            if src_type == NodeType.FILE and tgt_type == NodeType.FUNCTION:
                fn_to_file[tgt] = src
            if src_type == NodeType.CLASS and tgt_type == NodeType.FUNCTION:
                fn_to_file.setdefault(tgt, cls_to_file.get(src, ""))

        # Build a path→id map for source files so we can resolve by path
        source_file_path_to_id: dict[str, str] = {}
        for f in file_nodes:
            p = _str(f, "path") or f.label
            source_file_path_to_id[p] = f.id

        # Assign class/function node lists BEFORE the fallback resolution
        all_classes   = by_type[NodeType.CLASS]
        all_functions = by_type[NodeType.FUNCTION]

        # Fallback: for any function/class not mapped via edges,
        # use the "file" property stored by the graph builder
        for fn_node in all_functions:
            if fn_node.id not in fn_to_file:
                file_prop = _str(fn_node, "file")
                if file_prop in source_file_path_to_id:
                    fn_to_file[fn_node.id] = source_file_path_to_id[file_prop]
        for cls_node in all_classes:
            if cls_node.id not in cls_to_file:
                file_prop = _str(cls_node, "file")
                if file_prop in source_file_path_to_id:
                    cls_to_file[cls_node.id] = source_file_path_to_id[file_prop]

        # Filter classes and functions to source-file scope only
        src_classes   = [c for c in all_classes   if cls_to_file.get(c.id, "") in source_file_ids]
        src_functions = [f for f in all_functions if fn_to_file.get(f.id, "")  in source_file_ids]
        test_functions= [f for f in all_functions if fn_to_file.get(f.id, "")  in test_file_ids]

        # ── Detect dominant language ──────────────────────────────────────────
        lang_counts: dict[str, int] = defaultdict(int)
        for f in source_files:
            lang = _str(f, "language") or "unknown"
            lang_counts[lang] += 1
        dominant_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "unknown"

        # ── Build file_id → language and file_path → language indexes ─────────
        # Used by naming/documentation so rules are applied per-file, not per-repo
        file_id_to_lang: dict[str, str] = {
            f.id: (_str(f, "language") or "unknown")
            for f in source_files
        }
        # Also map by path (the "file" property on function/class nodes)
        file_path_to_lang: dict[str, str] = {}
        for f in source_files:
            path = _str(f, "path") or f.label
            lang = _str(f, "language") or "unknown"
            file_path_to_lang[path] = lang

        def node_lang(node: "GraphNode") -> str:
            """Return the language of the file containing this node."""
            file_id = fn_to_file.get(node.id) or cls_to_file.get(node.id, "")
            if file_id in file_id_to_lang:
                return file_id_to_lang[file_id]
            # Fallback: use "file" property path
            file_prop = _str(node, "file")
            if file_prop in file_path_to_lang:
                return file_path_to_lang[file_prop]
            return dominant_lang

        # ── Build coverage object ─────────────────────────────────────────────
        non_source = len(file_nodes) - len(source_files)
        coverage = AnalysisCoverage(
            total_files_in_repo=len(file_nodes),
            source_files=len(source_files),
            test_files=len(test_files),
            generated_files=sum(1 for cf in classified.values() if cf.category == FileCategory.GENERATED),
            vendor_files=sum(1 for cf in classified.values() if cf.category == FileCategory.VENDOR),
            config_files=sum(1 for cf in classified.values() if cf.category in (FileCategory.CONFIG, FileCategory.DOCS)),
            unsupported_files=sum(1 for cf in classified.values() if cf.category == FileCategory.UNKNOWN),
            analyzed_files=len(source_files),
            skipped_files=0,
            coverage_pct=1.0 if not source_files else 1.0,  # all fetched source files analysed
            languages_detected=list(lang_counts.keys()),
        )

        # ── Build context-aware severity context ──────────────────────────────
        # 1. Fan-in (afferent coupling) per source file — the blast radius that
        #    turns a complex/large unit into a genuinely higher risk.
        # 2. Architectural role per source file — routers/orchestrators/
        #    repositories legitimately have high fan-out; generators/parsers
        #    legitimately have large procedural bodies. Role lets severity
        #    reflect engineering reality instead of raw magnitude.
        fan_in_by_path: dict[str, int] = {}
        role_by_path: dict[str, ArchitecturalRole] = {}
        for f in source_files:
            fpath = _str(f, "path") or f.label
            in_sources = {
                e.source_id for e in edges_to.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
                and e.source_id in source_file_ids
                and e.source_id != f.id
            }
            fan_in_by_path[fpath] = len(in_sources)
            role_by_path[fpath] = classify_role(
                fpath,
                endpoint_count=_int(f, "endpoints"),
            )
        ctx = _SeverityContext(
            role_by_path=role_by_path,
            fan_in_by_path=fan_in_by_path,
            hub_threshold=int(T.FANIN_CRITICAL.value),
        )

        # ── Compute dimensions ────────────────────────────────────────────────
        issues: list[CodeIssue] = []

        complexity_dim   = self._complexity(src_functions, src_classes, issues, dominant_lang, ctx)
        coupling_dim     = self._coupling(source_files, edges, edges_from, edges_to, issues, ctx)
        size_dim         = self._size(source_files, src_classes, issues, ctx)
        architecture_dim = self._architecture(source_files, src_classes, edges, edges_from, edges_to, issues)
        documentation_dim= self._documentation(src_functions, src_classes, issues, dominant_lang, node_lang)
        naming_dim       = self._naming(src_functions, src_classes, issues, dominant_lang, node_lang)

        dimensions = [
            complexity_dim, coupling_dim, size_dim,
            architecture_dim, documentation_dim, naming_dim,
        ]

        # ── Overall score — weighted, normalised ──────────────────────────────
        weights = [0.22, 0.22, 0.15, 0.20, 0.12, 0.09]
        raw_score = sum(d.score * w for d, w in zip(dimensions, weights))
        overall   = max(0, min(100, int(raw_score)))

        # Overall confidence = weighted average of dimension confidences
        overall_conf = sum(d.confidence * w for d, w in zip(dimensions, weights))
        overall_conf = round(min(1.0, max(0.0, overall_conf)), 3)

        # ── Stats dict ────────────────────────────────────────────────────────
        async_fns   = [f for f in src_functions if _bool(f, "is_async")]
        doc_fns     = [f for f in src_functions if _bool(f, "has_docstring")]
        doc_classes = [c for c in src_classes   if _bool(c, "has_docstring")]

        stats = {
            "total_nodes":        len(nodes),
            "total_edges":        len(edges),
            "repositories":       len(by_type[NodeType.REPOSITORY]),
            "modules":            len(by_type[NodeType.MODULE]),
            "files":              len(source_files),
            "test_files":         len(test_files),
            "classes":            len(src_classes),
            "functions":          len(src_functions),
            "async_functions":    len(async_fns),
            "documented_fns":     len(doc_fns),
            "documented_classes": len(doc_classes),
            "dominant_language":  dominant_lang,
            "total_issues":       len(issues),
            "critical_issues":    len([i for i in issues if i.severity == IssueSeverity.CRITICAL]),
            "high_issues":        len([i for i in issues if i.severity == IssueSeverity.HIGH]),
            "medium_issues":      len([i for i in issues if i.severity == IssueSeverity.MEDIUM]),
            "low_issues":         len([i for i in issues if i.severity == IssueSeverity.LOW]),
        }

        sorted_issues = sorted(
            issues,
            key=lambda i: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[i.severity.value],
                i.file_path,
            ),
        )

        # ── Group reinforcing signals into coherent engineering concerns ──────
        # A symbol that trips several detectors (CC + long function + god
        # function + oversized file) is ONE concern with multiple signals —
        # not four independent problems. Concerns lead the UX; the individual
        # issues remain available as supporting evidence.
        concerns = group_into_concerns(sorted_issues)

        report = InsightsReport(
            job_id=job_id,
            repo_url=repo_url,
            repo_name=repo_name,
            overall_score=overall,
            overall_grade=HealthDimension.grade_from_score(overall),
            overall_confidence=overall_conf,
            dimensions=dimensions,
            issues=sorted_issues,
            concerns=concerns,
            stats=stats,
            coverage=coverage,
        )

        logger.info(
            "insights_computed",
            job_id=job_id,
            overall_score=overall,
            overall_confidence=overall_conf,
            total_issues=len(issues),
            source_files=len(source_files),
            test_files=len(test_files),
            dominant_lang=dominant_lang,
        )
        return report

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLEXITY
    # ═══════════════════════════════════════════════════════════════════════════

    def _complexity(
        self,
        functions: list["GraphNode"],
        classes:   list["GraphNode"],
        issues:    list[CodeIssue],
        lang:      str,
        ctx:       "_SeverityContext" = _NEUTRAL_CTX,
    ) -> HealthDimension:
        """Multi-signal complexity analysis.

        Complexity is NOT just line count.
        God-function detection uses composite score (see thresholds.GOD_FUNCTION_WEIGHTS).
        """
        if not functions and not classes:
            return HealthDimension(
                name="Complexity", score=100,
                grade="A", summary="No functions or classes found.",
                confidence=0.1,
            )

        fn_line_values = [_int(f, "lines") for f in functions if _int(f, "lines") > 0]
        param_values   = [max(0, _int(f, "param_count") - (1 if _bool(f, "is_method") else 0)) for f in functions]

        # ── Per-function analysis ─────────────────────────────────────────────
        god_fns:    list["GraphNode"] = []
        large_fns:  list["GraphNode"] = []
        param_fns:  list["GraphNode"] = []

        # Percentile thresholds (repo-relative anomaly detection)
        p95_lines = _percentile(fn_line_values, T.FUNCTION_SIZE_TOP_PERCENTILE) if fn_line_values else 999

        for fn in functions:
            lines       = _int(fn, "lines")
            raw_params  = _int(fn, "param_count")
            is_method   = _bool(fn, "is_method")
            # strip self/cls — AST parser already does this but double-check
            eff_params  = max(0, raw_params)

            name     = fn.label
            filepath = _str(fn, "file")
            line_no  = _int(fn, "line")

            # ── God function composite score ──────────────────────────────────
            # Each signal contributes a 0–1 normalised score.
            # Weights and thresholds are defined in thresholds.py (fully documented).
            w = T.GOD_FUNCTION_WEIGHTS

            # cyclomatic — primary signal (McCabe, 1976)
            cyclomatic   = _int(fn, "cyclomatic")    # 0 for non-Python files
            has_cyclo    = cyclomatic > 0             # False for TS/Java (no AST cyclomatic)
            sig_lines    = min(1.0, max(0.0, (lines - T.FN_LINES_CRITICAL.value)
                                             / max(1, T.FN_LINES_CRITICAL.value)))
            sig_cyclo    = min(1.0, max(0.0, (cyclomatic - T.CYCLOMATIC_HIGH.value)
                                             / max(1, T.CYCLOMATIC_HIGH.value))) if has_cyclo else 0.0
            sig_params   = min(1.0, max(0.0, (eff_params - T.FN_PARAMS_CRITICAL.value)
                                             / max(1, T.FN_PARAMS_CRITICAL.value)))
            sig_nesting  = min(1.0, max(0.0, (_int(fn, "nesting_depth") - T.NESTING_HIGH.value)
                                             / max(1, T.NESTING_HIGH.value)))
            sig_calls    = min(1.0, max(0.0, (_int(fn, "call_count") - 8) / 10))

            # If cyclomatic is unavailable (non-Python), redistribute its weight to lines
            if not has_cyclo:
                effective_line_weight = w["lines"] + w["cyclomatic"]
                composite = (
                    sig_lines   * effective_line_weight +
                    sig_params  * w["param_count"] +
                    sig_nesting * w["nesting"] +
                    sig_calls   * w["calls"]
                )
            else:
                composite = (
                    sig_lines   * w["lines"] +
                    sig_cyclo   * w["cyclomatic"] +
                    sig_params  * w["param_count"] +
                    sig_nesting * w["nesting"] +
                    sig_calls   * w["calls"]
                )

            # Count reinforcing complexity signals on THIS function so a symbol
            # that trips several detectors is treated as one stronger concern.
            reinforcing = sum((
                has_cyclo and cyclomatic >= T.CYCLOMATIC_HIGH.value,
                _int(fn, "nesting_depth") >= T.NESTING_HIGH.value,
                lines > T.FN_LINES_HIGH.value,
                eff_params > T.FN_PARAMS_HIGH.value,
            ))

            # Also emit standalone cyclomatic complexity issues for Python
            if has_cyclo and cyclomatic >= T.CYCLOMATIC_CRITICAL.value:
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Critical cyclomatic complexity",
                    description=(
                        f"This function contains {cyclomatic} independent execution paths — "
                        f"meaning a complete test suite needs at least {cyclomatic} test cases "
                        f"just to cover every branch once. McCabe's research found that functions "
                        f"above 15 paths have statistically higher defect rates and are "
                        f"effectively impossible to fully test."
                    ),
                    recommendation=(
                        f"Break this function into smaller pieces, each handling one decision. "
                        f"Start by identifying the largest `if/elif` chain or loop and extracting "
                        f"it into a named helper. Aim for each piece to have complexity ≤ 5."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name,
                    evidence={"cyclomatic": cyclomatic, "threshold": int(T.CYCLOMATIC_CRITICAL.value), "lines": lines},
                    confidence=1.0,
                ), ctx, signal="cyclomatic",
                    magnitude_ratio=cyclomatic / T.CYCLOMATIC_CRITICAL.value,
                    reinforcing_signals=reinforcing))
            elif has_cyclo and cyclomatic >= T.CYCLOMATIC_HIGH.value:
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="High cyclomatic complexity",
                    description=(
                        f"This function has {cyclomatic} independent execution paths. "
                        f"Functions above 10 are harder to read, test, and safely modify — "
                        f"each new branch multiplies the number of states a reader must track "
                        f"simultaneously to understand what the function does."
                    ),
                    recommendation=(
                        "Replace nested conditionals with early returns to flatten the structure. "
                        "Extract each logical step into a clearly named helper function. "
                        "If several branches do similar things, consider a lookup table or strategy pattern."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name,
                    evidence={"cyclomatic": cyclomatic, "threshold": int(T.CYCLOMATIC_HIGH.value)},
                    confidence=1.0,
                ), ctx, signal="cyclomatic",
                    magnitude_ratio=cyclomatic / T.CYCLOMATIC_HIGH.value,
                    reinforcing_signals=reinforcing))
            elif has_cyclo and cyclomatic >= T.CYCLOMATIC_MEDIUM.value:
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Moderate cyclomatic complexity",
                    description=(
                        f"This function has {cyclomatic} independent decision points (if/else, "
                        f"loops, and boolean operators), which is above the recommended limit of 5. "
                        f"Each decision point doubles the number of paths a reader — and your test "
                        f"suite — must account for, so the function is still followable today but is "
                        f"one or two edits away from becoming genuinely hard to reason about. "
                        f"Catching it now is far cheaper than untangling it later."
                    ),
                    recommendation=(
                        "Review whether each condition is truly necessary at this level. "
                        "Consider extracting the body of any loop or `else` branch into a "
                        "separate function with a descriptive name."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name,
                    evidence={"cyclomatic": cyclomatic},
                    confidence=0.90,
                ), ctx, signal="cyclomatic",
                    magnitude_ratio=cyclomatic / T.CYCLOMATIC_MEDIUM.value,
                    reinforcing_signals=reinforcing))

            # Also flag nesting depth independently
            if _int(fn, "nesting_depth") >= T.NESTING_CRITICAL.value:
                nd = _int(fn, "nesting_depth")
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="Deep nesting",
                    description=(
                        f"This function reaches {nd} levels of indentation. "
                        f"Deep nesting forces readers to hold multiple conditions in their "
                        f"head at once just to understand what a single line does. "
                        f"Research consistently links nesting depth above 3 to higher bug rates."
                    ),
                    recommendation=(
                        "Invert conditions to return early instead of nesting deeper "
                        "(\"guard clauses\"). Extract the body of deeply nested blocks into "
                        "helper functions. If nesting comes from a loop inside a loop, "
                        "consider extracting the inner loop."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name,
                    evidence={"nesting_depth": nd, "threshold": int(T.NESTING_CRITICAL.value)},
                    confidence=0.95,
                ), ctx, signal="nesting",
                    magnitude_ratio=nd / T.NESTING_CRITICAL.value,
                    reinforcing_signals=reinforcing))

            # Repo-relative percentile outlier detection (only meaningful with ≥20 fns)
            is_percentile_outlier = (
                lines > 0
                and lines >= p95_lines
                and len(fn_line_values) >= 20
                and lines > T.FN_LINES_CRITICAL.value
            )

            evidence = {
                "lines":         lines,
                "cyclomatic":    cyclomatic if has_cyclo else "n/a (non-Python)",
                "param_count":   eff_params,
                "nesting_depth": _int(fn, "nesting_depth"),
                "call_count":    _int(fn, "call_count"),
                "composite_score": round(composite, 3),
            }

            # A percentile outlier is only a *god function* if the composite
            # index also confirms real complexity. Being merely long (top-5%
            # by line count) with low branching/params is a LARGE function,
            # not a god function — this prevents the false HIGH labels on
            # trivially-long-but-simple functions (e.g. sequential wiring code).
            is_god = composite >= T.GOD_FUNCTION_SCORE_THRESHOLD or (
                is_percentile_outlier and composite >= T.GOD_FUNCTION_SCORE_HIGH
            )

            if is_god:
                god_fns.append(fn)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God function — doing too much",
                    description=(
                        f"This function scores {composite:.2f} on a combined complexity index "
                        f"that weighs size ({lines} lines), branching, parameter count ({eff_params}), "
                        f"nesting depth, and the number of other functions it calls. "
                        f"A score above 0.55 means multiple independent warning signals fired "
                        f"at once — a strong indicator the function has grown beyond a single "
                        f"responsibility and will become progressively harder to change safely."
                    ),
                    recommendation=(
                        "Identify the distinct jobs this function does — give each one a name. "
                        "Extract each named job into its own function. The original function "
                        "should then read like a summary: calling helpers in sequence, "
                        "with no logic of its own beyond orchestration."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name, evidence=evidence,
                    confidence=min(1.0, 0.5 + composite * 0.5),
                ), ctx, signal="god_function",
                    magnitude_ratio=composite / T.GOD_FUNCTION_SCORE_THRESHOLD,
                    reinforcing_signals=reinforcing))
            elif composite >= T.GOD_FUNCTION_SCORE_HIGH or lines > T.FN_LINES_HIGH.value:
                large_fns.append(fn)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large function — approaching complexity limit",
                    description=(
                        f"At {lines} lines with {eff_params} parameters, this function is large "
                        f"enough that a new reader has to scroll to hold all of it in their head "
                        f"at once, which is where subtle bugs slip in. It hasn't crossed the "
                        f"god-function threshold yet, but it is clearly doing more than one small "
                        f"job, and every line added from here makes the next change riskier and "
                        f"the function harder to test in isolation."
                    ),
                    recommendation=(
                        "Look for steps that have a clear start and end — loops, validation "
                        "blocks, transformation logic — and extract each into a named helper. "
                        "Even moving 10–15 lines out can dramatically improve readability."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + lines,
                    affected_symbol=name, evidence=evidence,
                    confidence=0.8,
                ), ctx, signal="large_function", reinforcing_signals=reinforcing))

            if eff_params > T.FN_PARAMS_CRITICAL.value:
                param_fns.append(fn)
                if fn not in god_fns:  # don't double-report
                    issues.append(_apply_context(CodeIssue(
                        category=IssueCategory.COMPLEXITY,
                        severity=IssueSeverity.HIGH,
                        title="Too many parameters",
                        description=(
                            f"This function takes {eff_params} parameters. Functions with more "
                            f"than 5–7 parameters are hard to call correctly — callers must "
                            f"remember the order, meaning, and valid range of every argument. "
                            f"This also makes the function hard to mock in tests."
                        ),
                        recommendation=(
                            "Group related parameters into a dataclass or options object. "
                            "If several parameters always appear together, they likely belong "
                            "in a single config or context object. If the function does different "
                            "things based on which params are set, consider splitting it."
                        ),
                        file_path=filepath, line_start=line_no, line_end=line_no,
                        affected_symbol=name,
                        evidence={"param_count": eff_params, "threshold": int(T.FN_PARAMS_CRITICAL.value)},
                        confidence=0.95,
                    ), ctx, signal="too_many_params",
                        magnitude_ratio=eff_params / T.FN_PARAMS_CRITICAL.value,
                        reinforcing_signals=reinforcing))

        # ── Per-class analysis ────────────────────────────────────────────────
        god_classes:   list["GraphNode"] = []
        large_classes: list["GraphNode"] = []
        cls_line_vals = [_int(c, "lines") for c in classes if _int(c, "lines") > 0]
        p95_cls = _percentile(cls_line_vals, T.CLASS_SIZE_TOP_PERCENTILE) if cls_line_vals else 9999

        for cls in classes:
            methods   = _int(cls, "methods")
            cls_lines = _int(cls, "lines")
            name      = cls.label
            filepath  = _str(cls, "file")
            line_no   = _int(cls, "line")

            evidence = {
                "methods":     methods,
                "lines":       cls_lines,
                "is_abstract": _bool(cls, "is_abstract"),
            }

            is_outlier = (
                cls_lines > 0
                and cls_lines >= p95_cls
                and len(cls_line_vals) >= 10
                and cls_lines > T.CLASS_LINES_CRITICAL.value
            )

            # A "god class" is defined by responsibility concentration — many
            # methods — NOT by raw line count alone. A large class with FEW
            # methods (e.g. a generator/parser holding a couple of very long
            # procedures, or a big dataclass) is a *large class*, a different
            # and lesser concern. Requiring method evidence eliminates the
            # false "god class" labels on low-method large files.
            many_methods   = methods > T.CLASS_METHODS_CRITICAL.value
            large_and_broad = (
                (cls_lines > T.CLASS_LINES_CRITICAL.value or is_outlier)
                and methods >= T.CLASS_METHODS_HIGH.value
            )

            if many_methods or large_and_broad:
                god_classes.append(cls)
                detail = []
                if methods > T.CLASS_METHODS_HIGH.value: detail.append(f"{methods} methods")
                if cls_lines > T.CLASS_LINES_CRITICAL.value: detail.append(f"{cls_lines} lines")
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="God class — too many responsibilities",
                    description=(
                        f"This class has {', '.join(detail) if detail else 'an unusually large surface area'}. "
                        f"With {methods} methods it almost certainly handles more than one concern — "
                        f"meaning a change to one responsibility risks breaking another, "
                        f"and the class is difficult to test in isolation. "
                        f"This is the most common symptom of the Single Responsibility Principle being violated."
                    ),
                    recommendation=(
                        "List every distinct verb this class does (validate, persist, notify, transform...). "
                        "Each distinct verb is a candidate for its own class. "
                        "Extract services, validators, and data-mappers first — "
                        "they tend to be the easiest to pull out without breaking things."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + cls_lines,
                    affected_symbol=name, evidence=evidence,
                    confidence=0.85,
                ), ctx, signal="god_class",
                    magnitude_ratio=max(
                        methods / T.CLASS_METHODS_CRITICAL.value,
                        cls_lines / T.CLASS_LINES_CRITICAL.value,
                    )))
            elif (cls_lines > T.CLASS_LINES_CRITICAL.value or is_outlier):
                # Big by line count but NOT method-heavy: a large implementation
                # class, not a god class. Reported as a real (MEDIUM) concern
                # with honest framing — the risk is navigability/size, not a
                # tangle of responsibilities.
                large_classes.append(cls)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large class — heavy implementation",
                    description=(
                        f"This class spans {cls_lines} lines across {methods} method(s). "
                        f"The size comes from long method bodies rather than a large number of "
                        f"responsibilities, so it is not a classic 'god class' — but a file this "
                        f"long is still hard to navigate and review, and long methods inside it "
                        f"are the more likely place for hidden complexity."
                    ),
                    recommendation=(
                        "Rather than splitting the class, look inside its longest methods and "
                        "extract cohesive steps into named helpers. If distinct phases emerge "
                        "(parse, transform, emit), those phases can become collaborator classes."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + cls_lines,
                    affected_symbol=name, evidence=evidence,
                    confidence=0.75,
                ), ctx, signal="large_class"))
            elif methods > T.CLASS_METHODS_HIGH.value:
                large_classes.append(cls)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Large class — starting to accumulate responsibilities",
                    description=(
                        f"This class exposes {methods} public methods. While not yet at god-class "
                        f"level, a class with this many methods is usually starting to do more than "
                        f"one thing, which means unrelated features now share the same state and "
                        f"can interfere with each other. Every method added from here increases the "
                        f"chance that a change made for one reason quietly breaks another, and it "
                        f"makes the class progressively harder to test and reuse."
                    ),
                    recommendation=(
                        "Review the method list and group the methods by which data or concept "
                        "they actually operate on. If two groups emerge that never call each "
                        "other's methods or touch the same fields, they are almost certainly two "
                        "separate responsibilities — extract the smaller group into its own class "
                        "and have this class delegate to it."
                    ),
                    file_path=filepath, line_start=line_no, line_end=line_no + cls_lines,
                    affected_symbol=name, evidence=evidence,
                    confidence=0.75,
                ), ctx, signal="large_class"))

        # ── Scoring ───────────────────────────────────────────────────────────
        n_fns   = max(1, len(functions))
        n_cls   = max(1, len(classes))
        god_fn_pct   = len(god_fns)   / n_fns
        large_fn_pct = len(large_fns) / n_fns
        god_cls_pct  = len(god_classes)/ n_cls
        param_pct    = len(param_fns)  / n_fns

        penalty = god_fn_pct*50 + large_fn_pct*15 + god_cls_pct*35 + param_pct*20
        score   = max(0, min(100, int(100 - penalty)))

        avg_lines  = statistics.mean(fn_line_values)  if fn_line_values  else 0.0
        avg_params = statistics.mean(param_values)    if param_values    else 0.0
        med_lines  = statistics.median(fn_line_values)if fn_line_values  else 0.0

        # Cyclomatic stats (only for functions that have real data)
        cyclo_values = [_int(f, "cyclomatic") for f in functions if _int(f, "cyclomatic") > 0]
        avg_cyclo  = statistics.mean(cyclo_values)   if cyclo_values else 0.0
        max_cyclo  = max(cyclo_values)               if cyclo_values else 0
        high_cyclo = [f for f in functions if _int(f, "cyclomatic") >= T.CYCLOMATIC_HIGH.value]
        has_cyclo_data = len(cyclo_values) > 0

        # Confidence: proportional to how many functions had line data + cyclomatic data
        fn_with_data   = sum(1 for f in functions if _int(f, "lines") > 0)
        fn_with_cyclo  = len(cyclo_values)
        base_conf      = round(fn_with_data / n_fns, 3) if functions else 0.1
        # Full confidence only when we have cyclomatic data for Python files
        cyclo_boost    = round(fn_with_cyclo / n_fns, 3) if functions and has_cyclo_data else 0.0
        confidence     = min(1.0, round((base_conf + cyclo_boost) / (2 if has_cyclo_data else 1), 3))

        cyclo_summary = (
            f" Avg cyclomatic: {round(avg_cyclo,1)}, max: {max_cyclo}."
            if has_cyclo_data else " (cyclomatic: Python only)"
        )

        return HealthDimension(
            name="Complexity", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(god_fns)} god functions, {len(god_classes)} god classes; "
                f"median function: {round(med_lines,0)} lines.{cyclo_summary}"
            ),
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.COMPLEXITY]),
            metrics=[
                MetricScore("Functions Analysed",        100, n_fns,              "functions", "Source functions/methods analysed", denominator=n_fns, confidence=base_conf),
                MetricScore("God Functions",              max(0,100-int(god_fn_pct*100)),    len(god_fns),     "functions", f"Composite score >= {T.GOD_FUNCTION_SCORE_THRESHOLD}", denominator=n_fns),
                MetricScore("Large Functions",            max(0,100-int(large_fn_pct*60)),   len(large_fns),   "functions", f">{int(T.FN_LINES_HIGH.value)} lines but below god threshold", denominator=n_fns),
                MetricScore("God Classes",                max(0,100-int(god_cls_pct*100)),   len(god_classes), "classes",   f">{int(T.CLASS_METHODS_CRITICAL.value)} methods or >{int(T.CLASS_LINES_CRITICAL.value)} lines", denominator=n_cls),
                MetricScore("High-Param Functions",       max(0,100-int(param_pct*100)),     len(param_fns),   "functions", f">{int(T.FN_PARAMS_CRITICAL.value)} params", denominator=n_fns),
                MetricScore("High Cyclomatic (>=10)",     max(0,100-len(high_cyclo)*5),      len(high_cyclo),  "functions", "McCabe cyclomatic complexity >= 10 (Python only)", confidence=round(fn_with_cyclo/max(1,n_fns),3)),
                MetricScore("Avg Cyclomatic Complexity",  max(0,int(100-max(0,avg_cyclo-3)*6)), round(avg_cyclo,1), "CC", "Mean McCabe cyclomatic complexity (Python only)", confidence=round(fn_with_cyclo/max(1,n_fns),3)),
                MetricScore("Max Cyclomatic Complexity",  max(0,100-max(0,max_cyclo-5)*5),   max_cyclo,        "CC", "Highest cyclomatic complexity in codebase"),
                MetricScore("Median Function Length",     max(0,int(100-max(0,med_lines-15)*1.5)), round(med_lines,1), "lines", "Median lines per function"),
                MetricScore("Avg Function Length",        max(0,int(100-max(0,avg_lines-15)*1.5)), round(avg_lines,1), "lines", "Mean lines per function"),
                MetricScore("Avg Parameter Count",        max(0,int(100-max(0,avg_params-2)*15)),  round(avg_params,1), "params", "Mean parameters per function"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # COUPLING
    # ═══════════════════════════════════════════════════════════════════════════

    def _coupling(
        self,
        source_files: list["GraphNode"],
        edges:        list["GraphEdge"],
        edges_from:   dict[str, list["GraphEdge"]],
        edges_to:     dict[str, list["GraphEdge"]],
        issues:       list[CodeIssue],
        ctx:          "_SeverityContext" = _NEUTRAL_CTX,
    ) -> HealthDimension:
        """Martin's coupling metrics — Ca, Ce, instability.

        Deduplicates IMPORTS+DEPENDS_ON edges (both are emitted per import).
        Only counts INTERNAL dependencies (cross-file within the repo).
        """
        if not source_files:
            return HealthDimension(
                name="Coupling", score=100, grade="A",
                summary="No source files found.", confidence=0.0,
            )

        source_ids = {f.id for f in source_files}
        file_by_id = {f.id: f for f in source_files}

        high_fanout: list[tuple["GraphNode", int]] = []
        high_fanin:  list[tuple["GraphNode", int]] = []
        instability_vals: list[float] = []

        for f in source_files:
            # Deduplicate: use a set of target_ids
            out_targets = {
                e.target_id for e in edges_from.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
                and e.target_id in source_ids   # internal only
                and e.target_id != f.id
            }
            in_sources = {
                e.source_id for e in edges_to.get(f.id, [])
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
                and e.source_id in source_ids
                and e.source_id != f.id
            }
            ce = len(out_targets)
            ca = len(in_sources)

            if ce + ca > 0:
                instability_vals.append(ce / (ce + ca))

            label    = f.label
            filepath = _str(f, "path") or label

            if ce > T.FANOUT_CRITICAL.value:
                high_fanout.append((f, ce))
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.HIGH,
                    title="High efferent coupling — too many outgoing dependencies",
                    description=(
                        f"This file directly imports {ce} other internal modules. "
                        f"High fan-out means this file is tightly coupled to many parts of "
                        f"the codebase — changes anywhere in those {ce} modules may require "
                        f"changes here too, and this file cannot be understood or tested "
                        f"without understanding all of its dependencies."
                    ),
                    recommendation=(
                        "Introduce a Facade or service layer that consolidates related "
                        "imports behind a single interface. Use dependency injection to "
                        "receive collaborators rather than importing them directly — "
                        "this makes the dependencies explicit and easy to swap in tests."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"efferent_coupling": ce, "threshold": int(T.FANOUT_CRITICAL.value),
                              "afferent_coupling": ca},
                    confidence=0.90,
                ), ctx, signal="fanout",
                    magnitude_ratio=ce / T.FANOUT_CRITICAL.value))
            elif ce > T.FANOUT_HIGH.value:
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Elevated efferent coupling",
                    description=(
                        f"This file imports from {ce} other internal modules, which is above the "
                        f"recommended limit. The more modules a file depends on directly, the more "
                        f"reasons it has to change, and the harder it is to understand in isolation "
                        f"because you must load all {ce} of those modules into your head first. "
                        f"It also makes the file slow to test, since every dependency has to be "
                        f"set up or mocked before a single assertion can run."
                    ),
                    recommendation=(
                        "Review each import and ask whether it is truly needed at this level. "
                        "If several imports serve a single purpose, wrap them behind one helper "
                        "module so this file sees one dependency instead of many. Prefer receiving "
                        "collaborators as arguments (dependency injection) over importing them "
                        "directly — that keeps the coupling explicit and easy to swap in tests."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"efferent_coupling": ce},
                    confidence=0.75,
                ), ctx, signal="fanout",
                    magnitude_ratio=ce / T.FANOUT_CRITICAL.value))

            if ca > T.FANIN_CRITICAL.value:
                high_fanin.append((f, ca))
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.COUPLING,
                    severity=IssueSeverity.MEDIUM,
                    title="Critical dependency hub — wide blast radius",
                    description=(
                        f"This file is imported by {ca} other files across the codebase. "
                        f"That makes it a critical hub: any breaking change to its public "
                        f"interface — a renamed function, a changed return type, a removed "
                        f"constant — will require fixes in up to {ca} other places simultaneously."
                    ),
                    recommendation=(
                        "Treat this file's public interface as frozen. "
                        "Add comprehensive tests before touching it. "
                        "Document exactly what it exports and the contract each export guarantees. "
                        "If it has grown to serve too many consumers, consider splitting it "
                        "so unrelated consumers can be decoupled."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"afferent_coupling": ca, "threshold": int(T.FANIN_CRITICAL.value)},
                    confidence=0.85,
                ), ctx, signal="fanin_hub",
                    magnitude_ratio=ca / T.FANIN_CRITICAL.value))

        n_files = max(1, len(source_files))
        fanout_pct = len(high_fanout) / n_files
        fanin_pct  = len(high_fanin)  / n_files
        avg_instability = statistics.mean(instability_vals) if instability_vals else 0.0

        penalty = fanout_pct * 55 + fanin_pct * 25
        score   = max(0, min(100, int(100 - penalty)))

        avg_ce = statistics.mean([v for _, v in high_fanout]) if high_fanout else 0.0
        # Confidence: proportion of source files that have import edge data
        files_with_edges = sum(
            1 for f in source_files
            if edges_from.get(f.id) or edges_to.get(f.id)
        )
        confidence = round(files_with_edges / max(1, n_files), 3)

        return HealthDimension(
            name="Coupling", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(high_fanout)} high-fanout files, "
                f"{len(high_fanin)} dependency hubs; "
                f"avg instability {round(avg_instability,2)}."
            ),
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.COUPLING]),
            metrics=[
                MetricScore("High Fan-out Files",   max(0,100-int(fanout_pct*100)), len(high_fanout), "files",  f">{int(T.FANOUT_CRITICAL.value)} internal imports", denominator=n_files),
                MetricScore("Dependency Hubs",      max(0,100-int(fanin_pct*100)),  len(high_fanin),  "files",  f">{int(T.FANIN_CRITICAL.value)} dependents", denominator=n_files),
                MetricScore("Avg Instability",      max(0,int((1-avg_instability)*100)), round(avg_instability,3), "ratio", "Martin Ce/(Ca+Ce): 0=stable, 1=unstable"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # SIZE
    # ═══════════════════════════════════════════════════════════════════════════

    def _size(
        self,
        source_files: list["GraphNode"],
        src_classes:  list["GraphNode"],
        issues:       list[CodeIssue],
        ctx:          "_SeverityContext" = _NEUTRAL_CTX,
    ) -> HealthDimension:
        """File-level size. Generated/vendor files already excluded."""
        if not source_files:
            return HealthDimension(name="Size", score=100, grade="A",
                                   summary="No source files.", confidence=0.0)

        large_files: list["GraphNode"] = []
        watch_files: list["GraphNode"] = []
        multicls_files: list["GraphNode"] = []

        for f in source_files:
            lines     = _int(f, "lines")
            cls_count = _int(f, "classes")
            label     = f.label
            filepath  = _str(f, "path") or label

            if lines > T.FILE_LINES_CRITICAL.value:
                large_files.append(f)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.HIGH,
                    title="Oversized source file",
                    description=(
                        f"This file is {lines} lines long. Files this large are difficult to "
                        f"navigate, tend to accumulate unrelated responsibilities over time, "
                        f"and produce larger, harder-to-review pull requests. "
                        f"SonarQube's default quality gate flags files above 500 lines."
                    ),
                    recommendation=(
                        "Look for natural seams in the file — groups of functions that only "
                        "call each other, or distinct data types defined together. "
                        "Each seam is a candidate for its own module. "
                        "Split by responsibility, not by file size alone."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"lines": lines, "threshold": int(T.FILE_LINES_CRITICAL.value)},
                    confidence=0.90,
                ), ctx, signal="oversized_file",
                    magnitude_ratio=lines / T.FILE_LINES_CRITICAL.value))
            elif lines > T.FILE_LINES_HIGH.value:
                watch_files.append(f)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.LOW,
                    title="Large file — approaching split threshold",
                    description=(
                        f"At {lines} lines this file is not yet critical, but it is already large "
                        f"enough to slow down navigation and to hide unrelated pieces of logic "
                        f"behind one filename. Files that keep growing tend to quietly collect "
                        f"multiple responsibilities, which makes them harder to review and more "
                        f"likely to cause merge conflicts as more people touch them."
                    ),
                    recommendation=(
                        "No urgent action is needed, but treat the next addition as a decision "
                        "point: before adding another class or a second major group of helpers "
                        "here, split those into their own file instead. Keeping one clear "
                        "responsibility per file now avoids a painful reorganisation later."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"lines": lines},
                    confidence=0.80,
                ), ctx, signal="large_file",
                    magnitude_ratio=lines / T.FILE_LINES_HIGH.value))

            if cls_count > T.CLASSES_PER_FILE_CRITICAL.value:
                multicls_files.append(f)
                issues.append(_apply_context(CodeIssue(
                    category=IssueCategory.SIZE,
                    severity=IssueSeverity.MEDIUM,
                    title="Multiple classes in one file",
                    description=(
                        f"This file defines {cls_count} classes. All major style guides "
                        f"(Google, Airbnb, PEP 8) recommend one primary class per file. "
                        f"When multiple classes share a file, it becomes unclear which is "
                        f"the primary concern, and changes to one class can accidentally "
                        f"affect the others."
                    ),
                    recommendation=(
                        "Move each non-primary class to its own file. "
                        "Small helper classes used only by one other class can stay "
                        "as an exception, but anything with more than a few methods "
                        "deserves its own file."
                    ),
                    file_path=filepath, affected_symbol=label,
                    evidence={"class_count": cls_count},
                    confidence=0.85,
                ), ctx, signal="multiple_classes"))

        n_files     = max(1, len(source_files))
        large_pct   = len(large_files) / n_files
        all_lines   = [_int(f, "lines") for f in source_files if _int(f, "lines") > 0]
        avg_lines   = statistics.mean(all_lines)   if all_lines else 0.0
        med_lines   = statistics.median(all_lines) if all_lines else 0.0
        cls_per_file= len(src_classes) / n_files

        penalty = large_pct * 60
        score   = max(0, min(100, int(100 - penalty)))
        files_with_data = sum(1 for f in source_files if _int(f, "lines") > 0)
        confidence = round(files_with_data / n_files, 3)

        return HealthDimension(
            name="Size", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=f"{len(source_files)} source files; {len(large_files)} oversized; median {round(med_lines,0)} lines.",
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.SIZE]),
            metrics=[
                MetricScore("Source Files",          100, n_files,          "files",  "Production source files analysed"),
                MetricScore("Oversized Files",        max(0,100-int(large_pct*100)), len(large_files), "files", f">{int(T.FILE_LINES_CRITICAL.value)} lines", denominator=n_files),
                MetricScore("Watch-list Files",       max(0,100-len(watch_files)*5), len(watch_files), "files", f">{int(T.FILE_LINES_HIGH.value)} lines", denominator=n_files),
                MetricScore("Median File Size",       max(0,int(100-max(0,med_lines-80)*0.12)), round(med_lines,0), "lines", "Median LOC per source file"),
                MetricScore("Classes / File",         max(0,int(100-max(0,cls_per_file-1)*20)), round(cls_per_file,2), "ratio", "Avg classes per source file (1 = ideal)"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════════════

    def _architecture(
        self,
        source_files: list["GraphNode"],
        src_classes:  list["GraphNode"],
        edges:        list["GraphEdge"],
        edges_from:   dict[str, list["GraphEdge"]],
        edges_to:     dict[str, list["GraphEdge"]],
        issues:       list[CodeIssue],
    ) -> HealthDimension:
        """Architecture: Tarjan's SCC cycle detection, abstraction, modularisation."""
        source_ids = {f.id for f in source_files}

        # ── Build import adjacency (dedup, internal only) ─────────────────────
        adj: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.relationship not in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                continue
            if edge.source_id in source_ids and edge.target_id in source_ids:
                if edge.source_id != edge.target_id:
                    adj[edge.source_id].add(edge.target_id)

        node_label = {f.id: f.label for f in source_files}
        node_path  = {f.id: _str(f, "path") or f.label for f in source_files}

        # ── Tarjan's SCC — finds ALL cycles, not just A↔B pairs ──────────────
        # Iterative implementation to avoid Python recursion limit on large graphs.
        # Based on: https://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
        index_map:  dict[str, int]  = {}
        lowlink:    dict[str, int]  = {}
        on_stack:   dict[str, bool] = {}
        scc_stack:  list[str]       = []
        sccs:       list[list[str]] = []
        counter     = [0]

        def _strongconnect(root: str) -> None:
            """Iterative Tarjan's SCC using an explicit call-stack."""
            # Each frame: (node, iterator-over-neighbours, is_root_frame)
            call_stack: list[tuple[str, "Iterator", bool]] = []

            def _visit(v: str) -> None:
                index_map[v] = counter[0]
                lowlink[v]   = counter[0]
                counter[0]  += 1
                scc_stack.append(v)
                on_stack[v] = True
                call_stack.append((v, iter(adj.get(v, set())), True))

            _visit(root)

            while call_stack:
                v, nbrs, _ = call_stack[-1]
                advanced = False
                for w in nbrs:
                    if w not in index_map:
                        # Tree edge — recurse
                        _visit(w)
                        advanced = True
                        break
                    elif on_stack.get(w, False):
                        lowlink[v] = min(lowlink[v], index_map[w])
                # No more unvisited neighbours — pop this frame
                if not advanced:
                    call_stack.pop()
                    # Update parent's lowlink
                    if call_stack:
                        parent = call_stack[-1][0]
                        lowlink[parent] = min(lowlink[parent], lowlink[v])
                    # Check if v is SCC root
                    if lowlink[v] == index_map[v]:
                        scc: list[str] = []
                        while True:
                            w = scc_stack.pop()
                            on_stack[w] = False
                            scc.append(w)
                            if w == v:
                                break
                        if len(scc) > 1:
                            sccs.append(scc)

        for node_id in list(source_ids):
            if node_id not in index_map:
                _strongconnect(node_id)

        # Convert SCCs into issues — report the cycle path
        cycles: list[list[str]] = []
        for scc in sccs:
            # Build a representative path through the SCC
            scc_set = set(scc)
            path: list[str] = [scc[0]]
            visited_in_path: set[str] = {scc[0]}
            cur = scc[0]
            for _ in range(len(scc) - 1):
                next_nodes = [n for n in adj.get(cur, set()) if n in scc_set and n not in visited_in_path]
                if not next_nodes:
                    break
                nxt = next_nodes[0]
                path.append(nxt)
                visited_in_path.add(nxt)
                cur = nxt
            path.append(path[0])  # close the cycle

            path_labels = [node_label.get(n, n) for n in path]
            path_str = " -> ".join(path_labels)
            cycles.append(path)

            sev = IssueSeverity.HIGH if len(scc) <= 3 else IssueSeverity.CRITICAL
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=sev,
                title=f"Circular dependency — {len(scc)} files in a cycle",
                description=(
                    f"These {len(scc)} files import each other in a loop: {path_str}. "
                    f"Circular imports mean none of these files can be loaded, tested, "
                    f"or reused independently — they are permanently fused together. "
                    f"This also prevents any of them from being moved to a shared library "
                    f"without dragging the entire cycle along."
                ),
                recommendation=(
                    "Identify what the files in the cycle share — it's usually a type, "
                    "constant, or small interface. Extract that shared thing into a new "
                    "module that none of the cycle members import from each other. "
                    "Alternatively, apply the Dependency Inversion Principle: "
                    "define an abstract interface in the lower-level module and have "
                    "the higher-level module implement it."
                ),
                file_path=node_path.get(scc[0], ""),
                affected_symbol=path_str,
                evidence={
                    "cycle_path":   path_labels,
                    "cycle_length": len(scc),
                    "files_in_cycle": [node_path.get(n, n) for n in scc],
                },
                confidence=1.0,
            ))

        # ── Abstraction ratio ─────────────────────────────────────────────────
        abstract_cls   = [c for c in src_classes if _bool(c, "is_abstract")]
        abstraction_r  = len(abstract_cls) / max(1, len(src_classes))

        if len(src_classes) > 8 and abstraction_r < 0.10:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.MEDIUM,
                title="Low abstraction coverage",
                description=(
                    f"Only {round(abstraction_r*100)}% of classes ({len(abstract_cls)} out of "
                    f"{len(src_classes)}) are abstract. A codebase with few abstractions is "
                    f"hard to extend — adding a new implementation requires modifying existing "
                    f"callers rather than just plugging in a new class. It also makes testing "
                    f"harder because you cannot easily swap real implementations for fakes."
                ),
                recommendation=(
                    "Identify the core operations in your domain (store, notify, validate, render) "
                    "and define an abstract interface or protocol for each. "
                    "Concrete classes implement the interface; callers depend on the interface. "
                    "Start with the most-imported modules — those are the highest-value abstractions."
                ),
                affected_symbol="codebase",
                evidence={"abstract_classes": len(abstract_cls), "total_classes": len(src_classes)},
                confidence=0.75,
            ))

        # ── Modularisation ────────────────────────────────────────────────────
        n_files   = len(source_files)
        # Count distinct top-level directories as proxy for modules
        modules_set = set()
        for f in source_files:
            parts = (_str(f, "path") or f.label).split("/")
            if len(parts) > 1:
                modules_set.add(parts[0])
        n_modules = len(modules_set)

        if n_files > 15 and n_modules < 3:
            issues.append(CodeIssue(
                category=IssueCategory.ARCHITECTURE,
                severity=IssueSeverity.MEDIUM,
                title="Poor modularisation — flat file structure",
                description=(
                    f"This codebase has {n_files} source files spread across only "
                    f"{n_modules} top-level package{'s' if n_modules != 1 else ''}. "
                    f"A flat structure means every file is in the same namespace, "
                    f"making it hard to understand what belongs together, hard to "
                    f"enforce boundaries between concerns, and harder to onboard "
                    f"new contributors who need a mental map of the codebase."
                ),
                recommendation=(
                    "Group files by responsibility into sub-packages. "
                    "A clean split for most backends is domain/ (core types), "
                    "application/ (use cases), infrastructure/ (databases, APIs), "
                    "and presentation/ (routes, controllers). "
                    "Even just separating domain types from I/O code is a big improvement."
                ),
                evidence={"files": n_files, "modules": n_modules},
                confidence=0.70,
            ))

        # ── Inheritance depth ─────────────────────────────────────────────────
        inherits_edges = [e for e in edges if e.relationship == RelationshipType.INHERITS]
        child_parents: dict[str, set[str]] = defaultdict(set)
        for e in inherits_edges:
            child_parents[e.source_id].add(e.target_id)

        def _depth(nid: str, visited: set) -> int:
            if nid in visited or nid not in child_parents: return 0
            visited.add(nid)
            return 1 + max((_depth(p, visited) for p in child_parents[nid]), default=0)

        for cls in src_classes:
            d = _depth(cls.id, set())
            if d >= T.INHERIT_DEPTH_CRITICAL.value:
                issues.append(CodeIssue(
                    category=IssueCategory.ARCHITECTURE,
                    severity=IssueSeverity.MEDIUM,
                    title="Deep inheritance chain",
                    description=(
                        f"This class sits {d} levels deep in an inheritance hierarchy. "
                        f"Deep inheritance chains are fragile — a change to any ancestor "
                        f"class can silently break every class below it. "
                        f"They are also hard to understand: to know what this class does, "
                        f"a reader must trace through {d} parent classes first."
                    ),
                    recommendation=(
                        "Favour composition over inheritance. Instead of inheriting behaviour, "
                        "accept collaborators as constructor arguments. "
                        "If the hierarchy exists to share code, extract that shared code "
                        "into a standalone helper and call it from each class directly. "
                        "Inheritance chains deeper than 3 levels are almost always a design smell."
                    ),
                    file_path=_str(cls, "file"),
                    affected_symbol=cls.label,
                    evidence={"depth": d, "threshold": int(T.INHERIT_DEPTH_CRITICAL.value)},
                    confidence=0.85,
                ))

        # ── Scoring ───────────────────────────────────────────────────────────
        cycle_penalty    = len(cycles) * 18
        abstraction_bonus= min(12, int(abstraction_r * 50))
        mod_penalty      = 8 if (n_files > 15 and n_modules < 3) else 0

        score = max(0, min(100, 100 - cycle_penalty - mod_penalty + abstraction_bonus))
        # Confidence: proportion of source files that have at least one import/contains edge
        edge_count = len([e for e in edges if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)])
        files_with_any_edge = sum(
            1 for f in source_files
            if edges_from.get(f.id) or edges_to.get(f.id)
        )
        confidence = round(files_with_any_edge / max(1, len(source_files)), 3) if source_files else 0.0

        return HealthDimension(
            name="Architecture", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{len(cycles)} circular dep pairs, "
                f"{n_modules} modules, "
                f"{round(abstraction_r*100)}% abstraction."
            ),
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.ARCHITECTURE]),
            metrics=[
                MetricScore("Circular Dependencies", max(0,100-len(cycles)*25),      len(cycles),       "pairs",   "A↔B mutual import cycles (confirmed)"),
                MetricScore("Modules / Packages",    100,                             n_modules,         "modules", "Distinct top-level packages"),
                MetricScore("Abstract Classes",      min(100,int(abstraction_r*200)), len(abstract_cls), "classes", "ABCs / interfaces"),
                MetricScore("Abstraction Ratio",     min(100,int(abstraction_r*200)), round(abstraction_r*100,1), "%", "% of classes that are abstract"),
                MetricScore("Inheritance Edges",     100, len(inherits_edges), "edges", "INHERITS relationships"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # DOCUMENTATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _documentation(
        self,
        src_functions: list["GraphNode"],
        src_classes:   list["GraphNode"],
        issues:        list[CodeIssue],
        lang:          str,
        node_lang=None,
    ) -> HealthDimension:
        """Uses ACTUAL has_docstring boolean stored on every node.

        Per-symbol language-aware: only evaluates symbols whose language
        supports documentation (Python docstrings, JSDoc, JavaDoc).
        Does NOT punish TypeScript symbols for Python doc rules and vice versa.
        """
        get_lang = node_lang if callable(node_lang) else (lambda _: lang)

        def _sym_has_doc_support(node: "GraphNode") -> bool:
            return get_rules(get_lang(node)).has_doc_support()

        public_classes = [
            c for c in src_classes
            if not c.label.startswith("_") and _sym_has_doc_support(c)
        ]
        public_fns = [
            f for f in src_functions
            if not f.label.startswith("_")
            and _int(f, "lines") > 5
            and _sym_has_doc_support(f)
        ]

        undoc_cls = [c for c in public_classes if not _bool(c, "has_docstring")]
        undoc_fns = [f for f in public_fns     if not _bool(f, "has_docstring")]

        total_public = len(public_classes) + len(public_fns)
        total_undoc  = len(undoc_cls)      + len(undoc_fns)
        doc_coverage = 1.0 - (total_undoc / max(1, total_public))

        if total_public == 0:
            return HealthDimension(
                name="Documentation", score=100, grade="A",
                summary="No public symbols in supported languages found to evaluate.",
                confidence=0.1,
            )

        # Report worst offenders by size (largest first)
        if undoc_cls:
            worst_cls = sorted(undoc_cls, key=lambda c: -_int(c, "lines"))[:5]
            for cls in worst_cls:
                lines_c = _int(cls, "lines")
                issues.append(CodeIssue(
                    category=IssueCategory.DOCUMENTATION,
                    severity=IssueSeverity.MEDIUM,
                    title="Public class missing docstring",
                    description=(
                        f"This class ({lines_c} lines) has no docstring. "
                        f"Without a docstring, the only way to understand what this class "
                        f"does, what it owns, and how to use it safely is to read the entire "
                        f"implementation — there is no written contract."
                    ),
                    recommendation=(
                        "Add a class-level docstring covering: what this class represents, "
                        "what responsibilities it owns, and a one-line usage example. "
                        "This is the single highest-value documentation you can add — "
                        "it's read every time someone imports this class."
                    ),
                    file_path=_str(cls, "file"), line_start=_int(cls, "line"),
                    affected_symbol=cls.label,
                    evidence={"has_docstring": False, "lines": lines_c},
                    confidence=1.0,
                ))

        if doc_coverage < T.DOC_COVERAGE_CRITICAL.value:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.HIGH,
                title="Critical documentation gap",
                description=(
                    f"Only {round(doc_coverage*100)}% of public symbols have docstrings "
                    f"({total_public - total_undoc} of {total_public}). "
                    f"This means most of the public API has no written contract — "
                    f"callers cannot know what to pass, what is returned, or what errors "
                    f"to expect without reading the implementation. "
                    f"This significantly increases onboarding time and the risk of misuse."
                ),
                recommendation=(
                    "Set a team policy that every new public class and non-trivial function "
                    "gets a docstring before merging. "
                    "For existing code, start with the most-imported files — "
                    "they have the widest impact per docstring written."
                ),
                evidence={
                    "coverage_pct": round(doc_coverage * 100, 1),
                    "total_public": total_public,
                    "documented": total_public - total_undoc,
                },
                confidence=0.95,
            ))
        elif doc_coverage < T.DOC_COVERAGE_HIGH.value:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.MEDIUM,
                title="Low documentation coverage",
                description=(
                    f"{round(doc_coverage*100)}% of public symbols are documented. "
                    f"The remaining {total_undoc} undocumented symbols have no written "
                    f"contract, which forces readers to reverse-engineer intent from "
                    f"the implementation whenever they encounter them."
                ),
                recommendation=(
                    f"Target ≥{round(T.DOC_COVERAGE_HIGH.value*100)}% coverage. "
                    "Prioritise classes and functions that are imported by many other files — "
                    "a single docstring there saves every reader who uses that symbol."
                ),
                evidence={"coverage_pct": round(doc_coverage * 100, 1)},
                confidence=0.90,
            ))
        elif doc_coverage < T.DOC_COVERAGE_MEDIUM.value:
            issues.append(CodeIssue(
                category=IssueCategory.DOCUMENTATION,
                severity=IssueSeverity.LOW,
                title="Documentation below recommended threshold",
                description=(
                    f"{round(doc_coverage*100)}% of public symbols are documented. "
                    f"You're close to the recommended threshold — "
                    f"a small effort now would bring full coverage."
                ),
                recommendation=(
                    f"Aim for ≥{round(T.DOC_COVERAGE_MEDIUM.value*100)}%. "
                    "Run a quick pass over undocumented public functions and add a "
                    "single-sentence summary to each — even a brief description is "
                    "better than nothing."
                ),
                evidence={"coverage_pct": round(doc_coverage * 100, 1)},
                confidence=0.80,
            ))

        score = min(100, int(doc_coverage * 100))
        # Confidence: do we actually have nodes with docstring data?
        # has_docstring is stored as a bool (True/False), not None when missing
        # Use presence of "has_docstring" key in properties as the signal
        nodes_with_docstring_field = sum(
            1 for f in src_functions + src_classes
            if "has_docstring" in f.properties
        )
        total_nodes = max(1, len(src_functions) + len(src_classes))
        confidence  = round(nodes_with_docstring_field / total_nodes, 3)

        return HealthDimension(
            name="Documentation", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{round(doc_coverage*100,1)}% public API documented "
                f"({total_public-total_undoc}/{total_public} symbols). "
                f"Language: {lang}."
            ),
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.DOCUMENTATION]),
            metrics=[
                MetricScore("Doc Coverage",              score,                             round(doc_coverage*100,1), "%",        "has_docstring=True ratio on public symbols", denominator=total_public, confidence=confidence),
                MetricScore("Public Classes Documented",  max(0,100-len(undoc_cls)*10),     len(public_classes)-len(undoc_cls), "classes",   "Public classes with docstrings", denominator=max(1,len(public_classes))),
                MetricScore("Undocumented Public Classes",max(0,100-len(undoc_cls)*10),     len(undoc_cls),  "classes",   "Public classes missing docstrings"),
                MetricScore("Public Functions Documented",max(0,100-len(undoc_fns)*3),      len(public_fns)-len(undoc_fns), "functions", "Non-trivial public functions with docstrings", denominator=max(1,len(public_fns))),
                MetricScore("Total Public Symbols",       100, total_public, "symbols", "Classes + non-trivial public functions analysed"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # NAMING
    # ═══════════════════════════════════════════════════════════════════════════

    def _naming(
        self,
        src_functions: list["GraphNode"],
        src_classes:   list["GraphNode"],
        issues:        list[CodeIssue],
        lang:          str,
        node_lang=None,
    ) -> HealthDimension:
        """Per-symbol language-aware naming convention check.

        Each function/class is checked against the rules for ITS OWN file's
        language — not the repo-dominant language.
        Python snake_case methods are NOT flagged by TypeScript camelCase rules.
        Idiomatic short names (i, j, x, fn, id) are never flagged.
        """
        get_lang = node_lang if callable(node_lang) else (lambda _: lang)

        bad_fn:  list["GraphNode"] = []
        bad_cls: list["GraphNode"] = []
        supported_total = 0
        unsupported_total = 0

        for fn in src_functions:
            fn_lang  = get_lang(fn)
            fn_rules = get_rules(fn_lang)
            if not fn_rules.is_supported():
                unsupported_total += 1
                continue
            supported_total += 1
            name     = fn.label
            if fn_rules.is_idiomatic_short(name):
                continue
            sym_type = "method" if _bool(fn, "is_method") else "function"
            if not fn_rules.naming_ok(name, sym_type):
                bad_fn.append(fn)
                convention = fn_rules.description()
                expected   = "snake_case" if "snake" in convention.lower() else "camelCase"
                issues.append(CodeIssue(
                    category=IssueCategory.NAMING,
                    severity=IssueSeverity.LOW,
                    title="Non-standard function name",
                    description=(
                        f"The name `{name}` doesn't follow the {convention} convention "
                        f"expected for {fn_lang} {sym_type}s. "
                        f"Inconsistent naming breaks the visual rhythm readers rely on to "
                        f"scan code quickly — a name that doesn't match the pattern "
                        f"draws attention even when there's nothing special about it."
                    ),
                    recommendation=(
                        f"Rename to {expected} to match the rest of the codebase. "
                        f"Use your IDE's rename refactor so all call sites update automatically."
                    ),
                    file_path=_str(fn, "file"), line_start=_int(fn, "line"),
                    affected_symbol=name,
                    evidence={"name": name, "convention": convention, "language": fn_lang},
                    confidence=0.80,
                ))

        for cls in src_classes:
            cls_lang  = get_lang(cls)
            cls_rules = get_rules(cls_lang)
            if not cls_rules.is_supported():
                unsupported_total += 1
                continue
            supported_total += 1
            name = cls.label
            if not cls_rules.naming_ok(name, "class"):
                bad_cls.append(cls)
                convention = cls_rules.description()
                issues.append(CodeIssue(
                    category=IssueCategory.NAMING,
                    severity=IssueSeverity.LOW,
                    title="Non-standard class name",
                    description=(
                        f"The class name `{name}` doesn't follow the PascalCase convention "
                        f"expected by {convention}. "
                        f"Class names are used constantly across a codebase — in imports, "
                        f"type annotations, and instantiation. A non-standard name makes "
                        f"it unclear at a glance whether a symbol is a class, a function, "
                        f"or a constant."
                    ),
                    recommendation=(
                        "Rename to PascalCase using your IDE's rename refactor. "
                        "For example: `my_service` → `MyService`, `myService` → `MyService`. "
                        "All import sites will update automatically."
                    ),
                    file_path=_str(cls, "file"), line_start=_int(cls, "line"),
                    affected_symbol=name,
                    evidence={"name": name, "convention": convention, "language": cls_lang},
                    confidence=0.80,
                ))

        total     = max(1, supported_total)
        total_bad = len(bad_fn) + len(bad_cls)
        compliance= 1.0 - (total_bad / total)
        score     = max(0, min(100, int(compliance * 100)))

        # Confidence: proportion of symbols that were in a supported language
        all_syms = max(1, len(src_functions) + len(src_classes))
        confidence = round(supported_total / all_syms, 3)

        return HealthDimension(
            name="Naming", score=score,
            grade=HealthDimension.grade_from_score(score),
            summary=(
                f"{total_bad} naming violations in {supported_total} supported symbols. "
                f"{unsupported_total} symbols in unsupported languages skipped."
            ),
            confidence=confidence,
            issue_count=len([i for i in issues if i.category == IssueCategory.NAMING]),
            metrics=[
                MetricScore("Convention Compliance",  score,                      round(compliance*100,1), "%",         "% of supported symbols following their language's naming rules", denominator=total),
                MetricScore("Bad Function Names",      max(0,100-len(bad_fn)*5),  len(bad_fn),  "functions", "Functions not matching their language's convention"),
                MetricScore("Bad Class Names",         max(0,100-len(bad_cls)*8), len(bad_cls), "classes",   "Classes not matching their language's convention"),
                MetricScore("Unsupported Language Symbols", 100, unsupported_total, "symbols", "Symbols in languages with no naming rules (not penalised)"),
            ],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # MARKDOWN EXPORT
    # ═══════════════════════════════════════════════════════════════════════════

    def to_markdown_report(self, report: InsightsReport) -> str:
        sev_icon = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}
        lines = [
            f"# Engineering Health Report — {report.repo_name}",
            "",
            f"**Score: {report.overall_score}/100  Grade: {report.overall_grade}  Confidence: {round(report.overall_confidence*100)}%**",
            "",
            f"Analysis coverage: {round(report.coverage.coverage_pct*100,1)}%  "
            f"Source files: {report.coverage.source_files}  "
            f"Test files: {report.coverage.test_files}  "
            f"Generated excluded: {report.coverage.generated_files}",
            "",
            "## Dimension Scores",
            "",
            "| Dimension | Score | Grade | Confidence | Summary |",
            "|-----------|-------|-------|------------|---------|",
        ]
        for d in report.dimensions:
            lines.append(f"| {d.name} | {d.score}/100 | {d.grade} | {round(d.confidence*100)}% | {d.summary} |")

        lines += ["", "## Issues", ""]
        if not report.issues:
            lines.append("✅ No issues detected.")
        else:
            for sev in ("critical", "high", "medium", "low", "info"):
                sev_issues = [i for i in report.issues if i.severity.value == sev]
                if not sev_issues: continue
                icon = sev_icon.get(sev, "⚪")
                lines += [f"### {icon} {sev.capitalize()} ({len(sev_issues)})", ""]
                for issue in sev_issues:
                    lines += [f"**{issue.title}**"]
                    if issue.file_path:
                        loc = f"{issue.file_path}:{issue.line_start}" if issue.line_start else issue.file_path
                        lines.append(f"- File: `{loc}`")
                    if issue.affected_symbol:
                        lines.append(f"- Symbol: `{issue.affected_symbol}`")
                    lines.append(f"- {issue.description}")
                    if issue.evidence:
                        lines.append(f"- Evidence: {issue.evidence}")
                    lines += [f"- Fix: {issue.recommendation}", f"- Confidence: {round(issue.confidence*100)}%", ""]
        return "\n".join(lines)
