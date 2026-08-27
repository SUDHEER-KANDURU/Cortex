"""Code Quality Generator — objective, evidence-backed quality analysis.

Combines AST-level detection (from VibeDetector) with graph-level analysis
to produce a comprehensive code quality report. Every finding includes:
  - Objective signal (metric, not opinion)
  - Evidence (file, line, symbol, measured value)
  - Severity (critical, high, medium, low)
  - Category (complexity, naming, documentation, architecture, coupling, testing)
  - Recommendation (specific, actionable fix)

NIM/AI is NOT used for detection — only for optional natural-language
explanation of deterministic findings (future enhancement).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.pipeline.infrastructure.vibe_detector import VibeReport


@dataclass
class QualityFinding:
    """A single code quality finding with full evidence."""
    category: str  # complexity, naming, documentation, architecture, coupling, testing, size
    severity: str  # critical, high, medium, low
    title: str
    description: str
    # Evidence
    file_path: str = ""
    line: int = 0
    symbol: str = ""
    metric_name: str = ""
    metric_value: str = ""
    threshold: str = ""
    # Fix
    recommendation: str = ""


@dataclass
class QualityCategory:
    """Assessment of one quality dimension."""
    name: str
    score: int = 100  # 0-100
    grade: str = "A"
    finding_count: int = 0
    summary: str = ""


@dataclass
class CodeQualityResult:
    """Full code quality analysis."""
    repo_name: str
    overall_score: int = 100
    overall_grade: str = "A"
    total_findings: int = 0
    files_analyzed: int = 0
    # Category scores
    categories: list[QualityCategory] = field(default_factory=list)
    # All findings sorted by severity
    findings: list[QualityFinding] = field(default_factory=list)


class CodeQualityGenerator:
    """Generates evidence-backed code quality analysis.

    Detection pipeline:
      1. Graph-level analysis (complexity, coupling, documentation from node properties)
      2. AST-level patterns (from existing VibeReport if available)
      3. Architectural analysis (layer violations, dependency direction)
      4. Scoring and grading per category
    """

    def generate(
        self,
        graph: GraphBuildResult,
        repo_name: str,
        vibe_report: VibeReport | None = None,
    ) -> str:
        """Generate code quality report as Markdown."""
        result = self.analyze(graph, repo_name, vibe_report)
        return self._render_markdown(result)

    def analyze(
        self,
        graph: GraphBuildResult,
        repo_name: str,
        vibe_report: VibeReport | None = None,
    ) -> CodeQualityResult:
        """Run full code quality analysis."""
        result = CodeQualityResult(repo_name=repo_name)

        files = graph.nodes_by_type(NodeType.FILE)
        functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT
        )]
        classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
        )]
        modules = graph.nodes_by_type(NodeType.MODULE)

        result.files_analyzed = len(files)
        all_findings: list[QualityFinding] = []

        # 1. Complexity findings
        complexity_findings = self._check_complexity(functions, files)
        all_findings.extend(complexity_findings)

        # 2. Size findings
        size_findings = self._check_size(functions, classes, files)
        all_findings.extend(size_findings)

        # 3. Documentation findings
        doc_findings = self._check_documentation(functions, classes)
        all_findings.extend(doc_findings)

        # 4. Coupling findings
        coupling_findings = self._check_coupling(graph, modules)
        all_findings.extend(coupling_findings)

        # 5. Architecture findings
        arch_findings = self._check_architecture(graph, modules)
        all_findings.extend(arch_findings)

        # 6. Incorporate VibeReport findings (if available)
        if vibe_report:
            vibe_findings = self._convert_vibe_findings(vibe_report)
            all_findings.extend(vibe_findings)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 4))

        result.findings = all_findings
        result.total_findings = len(all_findings)

        # Compute category scores
        result.categories = self._compute_category_scores(all_findings)

        # Overall score
        if result.categories:
            result.overall_score = round(
                sum(c.score for c in result.categories) / len(result.categories)
            )
        result.overall_grade = self._grade(result.overall_score)

        return result

    def _check_complexity(
        self, functions: list[GraphNode], files: list[GraphNode]
    ) -> list[QualityFinding]:
        """Detect complexity issues from graph metrics."""
        findings: list[QualityFinding] = []

        for fn in functions:
            cc = int(fn.properties.get("cyclomatic", 0) or 0)
            nesting = int(fn.properties.get("nesting_depth", 0) or 0)
            file_path = str(fn.properties.get("file", ""))

            if cc >= 20:
                findings.append(QualityFinding(
                    category="complexity",
                    severity="critical",
                    title=f"Extremely high complexity: `{fn.label}`",
                    description=f"Cyclomatic complexity of {cc} indicates too many execution paths to test reliably.",
                    file_path=file_path,
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    metric_name="cyclomatic_complexity",
                    metric_value=str(cc),
                    threshold="< 20",
                    recommendation="Split into multiple functions. Extract each major branch into a named helper.",
                ))
            elif cc >= 10:
                findings.append(QualityFinding(
                    category="complexity",
                    severity="high",
                    title=f"High complexity: `{fn.label}`",
                    description=f"Cyclomatic complexity of {cc} makes this function hard to test and maintain.",
                    file_path=file_path,
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    metric_name="cyclomatic_complexity",
                    metric_value=str(cc),
                    threshold="< 10",
                    recommendation="Use guard clauses, extract methods, or apply strategy pattern.",
                ))

            if nesting >= 4:
                findings.append(QualityFinding(
                    category="complexity",
                    severity="medium",
                    title=f"Deep nesting: `{fn.label}`",
                    description=f"Nesting depth of {nesting} makes logic flow hard to follow.",
                    file_path=file_path,
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    metric_name="nesting_depth",
                    metric_value=str(nesting),
                    threshold="< 4",
                    recommendation="Use early returns/guard clauses to flatten the nesting.",
                ))

        return findings[:15]  # Cap per category

    def _check_size(
        self, functions: list[GraphNode], classes: list[GraphNode], files: list[GraphNode]
    ) -> list[QualityFinding]:
        """Detect size-related issues."""
        findings: list[QualityFinding] = []

        # Long functions
        for fn in functions:
            lines = int(fn.properties.get("lines", 0) or 0)
            if lines >= 100:
                findings.append(QualityFinding(
                    category="size",
                    severity="high",
                    title=f"Very long function: `{fn.label}` ({lines} lines)",
                    description="Functions over 100 lines are hard to understand and test.",
                    file_path=str(fn.properties.get("file", "")),
                    symbol=fn.label,
                    metric_name="line_count",
                    metric_value=str(lines),
                    threshold="< 50",
                    recommendation="Extract logical sections into helper functions with descriptive names.",
                ))
            elif lines >= 50:
                findings.append(QualityFinding(
                    category="size",
                    severity="medium",
                    title=f"Long function: `{fn.label}` ({lines} lines)",
                    description="Consider splitting for better readability.",
                    file_path=str(fn.properties.get("file", "")),
                    symbol=fn.label,
                    metric_name="line_count",
                    metric_value=str(lines),
                    threshold="< 50",
                    recommendation="Look for logical groupings that can be extracted.",
                ))

        # God classes
        for cls in classes:
            methods = int(cls.properties.get("methods", 0) or 0)
            cls_lines = int(cls.properties.get("lines", 0) or 0)
            if methods >= 15 or cls_lines >= 500:
                findings.append(QualityFinding(
                    category="size",
                    severity="high",
                    title=f"God class: `{cls.label}` ({methods} methods, {cls_lines} lines)",
                    description="Too many responsibilities in one class.",
                    file_path=str(cls.properties.get("file", "")),
                    symbol=cls.label,
                    metric_name="method_count",
                    metric_value=str(methods),
                    threshold="< 15",
                    recommendation="Group methods by cohesion, extract into focused classes.",
                ))

        # Long parameter lists
        for fn in functions:
            params = int(fn.properties.get("param_count", 0) or 0)
            if params >= 6:
                findings.append(QualityFinding(
                    category="size",
                    severity="medium",
                    title=f"Too many parameters: `{fn.label}` ({params} params)",
                    description="Functions with many parameters are hard to call correctly.",
                    file_path=str(fn.properties.get("file", "")),
                    symbol=fn.label,
                    metric_name="parameter_count",
                    metric_value=str(params),
                    threshold="< 5",
                    recommendation="Group related parameters into a dataclass/config object.",
                ))

        return findings[:15]

    def _check_documentation(
        self, functions: list[GraphNode], classes: list[GraphNode]
    ) -> list[QualityFinding]:
        """Detect documentation gaps."""
        findings: list[QualityFinding] = []

        # Public classes without docstrings
        undocumented_classes = [
            c for c in classes
            if not c.properties.get("has_docstring")
            and not c.label.startswith("_")
            and c.node_type != NodeType.ENUM
        ]

        if len(undocumented_classes) > 3:
            sample = undocumented_classes[:5]
            findings.append(QualityFinding(
                category="documentation",
                severity="medium",
                title=f"{len(undocumented_classes)} classes without documentation",
                description="Public classes should explain their purpose and usage.",
                symbol=", ".join(c.label for c in sample),
                metric_name="undocumented_classes",
                metric_value=str(len(undocumented_classes)),
                recommendation="Add docstrings explaining purpose, usage patterns, and key methods.",
            ))

        # Complex functions without docstrings
        complex_undocumented = [
            fn for fn in functions
            if int(fn.properties.get("cyclomatic", 0) or 0) >= 5
            and not fn.properties.get("has_docstring")
        ]

        if complex_undocumented:
            sample = complex_undocumented[:3]
            findings.append(QualityFinding(
                category="documentation",
                severity="medium",
                title=f"{len(complex_undocumented)} complex functions without docs",
                description="Complex functions especially need documentation explaining the logic.",
                symbol=", ".join(fn.label for fn in sample),
                metric_name="complex_undocumented",
                metric_value=str(len(complex_undocumented)),
                recommendation="Document the WHY — complex code with no explanation is a maintenance hazard.",
            ))

        return findings

    def _check_coupling(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> list[QualityFinding]:
        """Detect coupling issues from dependency analysis."""
        findings: list[QualityFinding] = []

        # Build module dependency map
        contains_children: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains_children[edge.source_id].append(edge.target_id)

        node_to_module: dict[str, str] = {}
        module_ids = {m.id for m in modules}

        def assign(mod_id: str) -> None:
            for child_id in contains_children.get(mod_id, []):
                node_to_module[child_id] = mod_id
                assign(child_id)

        for m in modules:
            assign(m.id)

        # Count cross-module dependencies
        module_fan_out: dict[str, set[str]] = defaultdict(set)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                src_mod = node_to_module.get(edge.source_id)
                tgt_mod = node_to_module.get(edge.target_id)
                if src_mod and tgt_mod and src_mod != tgt_mod:
                    module_fan_out[src_mod].add(tgt_mod)

        # Detect circular dependencies
        for src_id, targets in module_fan_out.items():
            for tgt_id in targets:
                if src_id in module_fan_out.get(tgt_id, set()):
                    src_node = graph.node_by_id.get(src_id)
                    tgt_node = graph.node_by_id.get(tgt_id)
                    if src_node and tgt_node:
                        src_name = str(src_node.properties.get("path", src_node.label)).split("/")[-1]
                        tgt_name = str(tgt_node.properties.get("path", tgt_node.label)).split("/")[-1]
                        findings.append(QualityFinding(
                            category="coupling",
                            severity="high",
                            title=f"Circular dependency: `{src_name}` ↔ `{tgt_name}`",
                            description="Bidirectional dependencies prevent independent testing and deployment.",
                            metric_name="circular_dependency",
                            metric_value="true",
                            recommendation="Introduce an interface in one module and invert the dependency.",
                        ))
                        break  # One finding per pair

        # High fan-out
        for mod_id, targets in module_fan_out.items():
            if len(targets) >= 5:
                mod_node = graph.node_by_id.get(mod_id)
                if mod_node:
                    name = str(mod_node.properties.get("path", mod_node.label)).split("/")[-1]
                    findings.append(QualityFinding(
                        category="coupling",
                        severity="medium",
                        title=f"High fan-out: `{name}` depends on {len(targets)} modules",
                        description="High fan-out means changes in many modules can break this one.",
                        symbol=name,
                        metric_name="fan_out",
                        metric_value=str(len(targets)),
                        threshold="< 5",
                        recommendation="Consider a facade or mediator to reduce direct dependencies.",
                    ))

        return findings[:8]

    def _check_architecture(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> list[QualityFinding]:
        """Detect architectural issues."""
        findings: list[QualityFinding] = []

        # Check for test files without corresponding source
        files = graph.nodes_by_type(NodeType.FILE)
        test_files = [f for f in files if f.properties.get("is_test_file")]
        source_files = [f for f in files if not f.properties.get("is_test_file")]

        if source_files and not test_files:
            findings.append(QualityFinding(
                category="testing",
                severity="high",
                title="No test files detected",
                description=f"{len(source_files)} source files with zero test coverage.",
                metric_name="test_file_count",
                metric_value="0",
                recommendation="Add tests for the highest-complexity modules first.",
            ))
        elif source_files and test_files and len(test_files) < len(source_files) * 0.2:
            findings.append(QualityFinding(
                category="testing",
                severity="medium",
                title=f"Low test coverage: {len(test_files)} test files for {len(source_files)} source files",
                description="Test-to-source ratio is below 0.2.",
                metric_name="test_ratio",
                metric_value=f"{len(test_files)}/{len(source_files)}",
                threshold=">= 0.3",
                recommendation="Prioritize testing for domain and application layers.",
            ))

        return findings

    def _convert_vibe_findings(self, vibe_report: VibeReport) -> list[QualityFinding]:
        """Convert existing VibeReport flags to QualityFinding format."""
        findings: list[QualityFinding] = []
        _category_map = {
            "no_error_handling": "architecture",
            "duplicate_logic": "size",
            "god_function": "complexity",
            "inconsistent_naming": "naming",
            "unused_imports": "size",
            "missing_docstrings": "documentation",
            "hardcoded_values": "architecture",
            "deep_nesting": "complexity",
            "long_parameter_list": "size",
            "copy_paste_blocks": "size",
        }

        for flag in vibe_report.flags[:10]:
            category = _category_map.get(flag.pattern.value, "architecture")
            findings.append(QualityFinding(
                category=category,
                severity=flag.severity,
                title=flag.pattern.value.replace("_", " ").title(),
                description=flag.message,
                file_path=flag.file_path,
                line=flag.line,
                recommendation=flag.fix,
            ))

        return findings

    def _compute_category_scores(
        self, findings: list[QualityFinding]
    ) -> list[QualityCategory]:
        """Compute scores per category based on findings."""
        category_names = ["complexity", "size", "documentation", "coupling", "architecture", "testing"]
        categories: list[QualityCategory] = []

        severity_penalty = {"critical": 20, "high": 12, "medium": 5, "low": 2}

        for cat_name in category_names:
            cat_findings = [f for f in findings if f.category == cat_name]
            penalty = sum(severity_penalty.get(f.severity, 0) for f in cat_findings)
            score = max(0, 100 - penalty)
            categories.append(QualityCategory(
                name=cat_name.title(),
                score=score,
                grade=self._grade(score),
                finding_count=len(cat_findings),
                summary=f"{len(cat_findings)} issues found" if cat_findings else "No issues",
            ))

        return categories

    def _grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 65:
            return "C"
        if score >= 50:
            return "D"
        return "F"

    def _render_markdown(self, result: CodeQualityResult) -> str:
        """Render code quality report as Markdown."""
        lines: list[str] = []

        lines.append(f"# Code Quality Report — {result.repo_name}")
        lines.append("")
        lines.append(
            "> **What is code quality?** Code quality measures how easy the code is to "
            "understand, change, and maintain. High-quality code has fewer bugs, is easier "
            "for new team members to learn, and costs less to modify over time. "
            "This report grades the code like a school report card — A is excellent, F needs work."
        )
        lines.append("")

        # ── Overall Score ────────────────────────────────────────────────────
        grade_meaning = {
            "A": "Excellent — clean, well-organized code",
            "B": "Good — mostly clean with minor issues",
            "C": "Acceptable — some areas need attention",
            "D": "Below average — significant issues found",
            "F": "Poor — major problems that affect reliability",
        }
        lines.append(f"## Overall Grade: {result.overall_grade} ({result.overall_score}/100)")
        lines.append("")
        lines.append(f"*{grade_meaning.get(result.overall_grade, '')}*")
        lines.append("")
        lines.append(f"Cortex found **{result.total_findings} issues** across {result.files_analyzed} files.")
        lines.append("")

        # Category scores with explanations
        lines.append("### Scores by Category")
        lines.append("")
        lines.append("| Category | Score | Grade | What it measures |")
        lines.append("|----------|-------|-------|-----------------|")
        _cat_explanations = {
            "Complexity": "How tangled and hard-to-follow the logic is",
            "Size": "Whether functions/classes are too large to understand",
            "Documentation": "Whether the code explains itself with comments",
            "Coupling": "How tangled the dependencies between modules are",
            "Architecture": "Whether the code is organized in a sensible structure",
            "Testing": "Whether automated tests exist to catch bugs",
        }
        for cat in result.categories:
            explanation = _cat_explanations.get(cat.name, "")
            lines.append(f"| {cat.name} | {cat.score}/100 | {cat.grade} | {explanation} |")
        lines.append("")

        if not result.findings:
            lines.append("✅ **No issues found!** This codebase is clean and well-maintained.")
            return "\n".join(lines)

        # ── Findings by severity ─────────────────────────────────────────────
        critical = [f for f in result.findings if f.severity == "critical"]
        high = [f for f in result.findings if f.severity == "high"]
        medium = [f for f in result.findings if f.severity == "medium"]
        low = [f for f in result.findings if f.severity == "low"]

        if critical:
            lines.append("## 🔴 Critical Issues")
            lines.append("")
            for f in critical:
                self._render_finding(lines, f)

        if high:
            lines.append("## 🟠 High Severity")
            lines.append("")
            for f in high[:8]:
                self._render_finding(lines, f)

        if medium:
            lines.append("## 🟡 Medium Severity")
            lines.append("")
            for f in medium[:8]:
                self._render_finding(lines, f)

        if low:
            lines.append("## 🟢 Low Severity")
            lines.append("")
            for f in low[:5]:
                self._render_finding(lines, f)

        return "\n".join(lines)

    def _render_finding(self, lines: list[str], f: QualityFinding) -> None:
        """Render a single finding."""
        lines.append(f"### {f.title}")
        lines.append("")
        lines.append(f"{f.description}")
        lines.append("")

        # Evidence
        evidence_parts: list[str] = []
        if f.file_path:
            evidence_parts.append(f"**File:** `{f.file_path.split('/')[-1]}`")
        if f.symbol:
            evidence_parts.append(f"**Symbol:** `{f.symbol}`")
        if f.metric_name:
            evidence_parts.append(f"**{f.metric_name}:** `{f.metric_value}`")
        if f.threshold:
            evidence_parts.append(f"**Threshold:** {f.threshold}")

        if evidence_parts:
            lines.append(" · ".join(evidence_parts))
            lines.append("")

        if f.recommendation:
            lines.append(f"> **Fix:** {f.recommendation}")
            lines.append("")
