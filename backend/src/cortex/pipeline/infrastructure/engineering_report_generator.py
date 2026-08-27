"""Engineering Report Generator — comprehensive evidence-backed analysis.

Produces a full engineering assessment with:
  - Executive summary with health score
  - Repository structure and statistics
  - Architecture assessment (layers, patterns)
  - Key modules ranked by importance
  - Dependency analysis with coupling metrics
  - Complexity hotspots with evidence
  - Quality risks with severity and recommendations
  - Documentation assessment
  - Testing assessment
  - Technical debt identification
  - Prioritized improvement recommendations

Every claim is backed by graph evidence. No filler prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class EngineeringReportResult:
    """Full engineering analysis data."""
    repo_name: str
    repo_url: str = ""
    # Structure
    total_files: int = 0
    total_lines: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_modules: int = 0
    total_endpoints: int = 0
    total_tests: int = 0
    languages: list[str] = field(default_factory=list)
    # Quality metrics
    avg_complexity: float = 0.0
    max_complexity: int = 0
    max_complexity_symbol: str = ""
    max_complexity_file: str = ""
    documentation_ratio: float = 0.0
    test_ratio: float = 0.0  # test files / source files
    # Architecture
    detected_layers: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)
    layer_violations: list[str] = field(default_factory=list)
    # Dependencies
    circular_deps: list[tuple[str, str]] = field(default_factory=list)
    most_coupled_modules: list[tuple[str, int]] = field(default_factory=list)  # (name, coupling)
    # Risks
    god_classes: list[tuple[str, int, str]] = field(default_factory=list)  # (name, methods, file)
    complex_functions: list[tuple[str, int, str]] = field(default_factory=list)  # (name, cc, file)
    large_files: list[tuple[str, int]] = field(default_factory=list)  # (path, lines)
    undocumented_public: int = 0
    # Recommendations
    recommendations: list[tuple[str, str, str]] = field(default_factory=list)  # (priority, title, detail)


class EngineeringReportGenerator:
    """Generates comprehensive engineering report from the knowledge graph."""

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate the full engineering report as Markdown."""
        result = self.analyze(graph, repo_name)
        return self._render_markdown(result)

    def analyze(self, graph: GraphBuildResult, repo_name: str) -> EngineeringReportResult:
        """Run full engineering analysis."""
        result = EngineeringReportResult(
            repo_name=repo_name,
            repo_url=graph.repo_url,
        )

        files = graph.nodes_by_type(NodeType.FILE)
        modules = graph.nodes_by_type(NodeType.MODULE)
        classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
        )]
        functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT, NodeType.TEST
        )]
        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)
        tests = graph.nodes_by_type(NodeType.TEST)

        # Structure
        result.total_files = len(files)
        result.total_modules = len(modules)
        result.total_classes = len(classes)
        result.total_functions = len(functions)
        result.total_endpoints = len(endpoints)
        result.total_tests = len(tests)
        result.total_lines = sum(int(f.properties.get("lines", 0) or 0) for f in files)

        # Languages
        lang_counts: dict[str, int] = defaultdict(int)
        for f in files:
            lang = str(f.properties.get("language", "unknown"))
            lang_counts[lang] += 1
        result.languages = sorted(lang_counts.keys(), key=lambda l: lang_counts[l], reverse=True)

        # Complexity
        complexities: list[tuple[int, str, str]] = []
        for fn in functions:
            cc = int(fn.properties.get("cyclomatic", 0) or 0)
            if cc > 0:
                complexities.append((cc, fn.label, str(fn.properties.get("file", ""))))

        if complexities:
            result.avg_complexity = round(sum(c for c, _, _ in complexities) / len(complexities), 2)
            max_cc, max_name, max_file = max(complexities, key=lambda x: x[0])
            result.max_complexity = max_cc
            result.max_complexity_symbol = max_name
            result.max_complexity_file = max_file

        # Documentation
        documentable = [n for n in functions + classes if n.node_type != NodeType.TEST]
        if documentable:
            documented = sum(1 for n in documentable if n.properties.get("has_docstring"))
            result.documentation_ratio = round(documented / len(documentable), 2)

        # Test ratio
        test_files = [f for f in files if f.properties.get("is_test_file")]
        source_files = [f for f in files if not f.properties.get("is_test_file")]
        if source_files:
            result.test_ratio = round(len(test_files) / len(source_files), 2)

        # Architecture detection
        result.detected_layers = self._detect_layers(modules)
        result.detected_patterns = self._detect_patterns(classes, functions, graph)

        # Dependencies
        module_deps = self._compute_module_deps(graph, modules)
        result.circular_deps = self._find_circular(module_deps, graph)
        result.most_coupled_modules = self._find_most_coupled(module_deps, graph)

        # Risks
        result.god_classes = [
            (c.label, int(c.properties.get("methods", 0) or 0), str(c.properties.get("file", "")))
            for c in classes
            if int(c.properties.get("methods", 0) or 0) >= 12
        ][:5]

        result.complex_functions = [
            (name, cc, file)
            for cc, name, file in sorted(complexities, reverse=True)[:5]
            if cc >= 10
        ]

        result.large_files = [
            (str(f.properties.get("path", f.label)), int(f.properties.get("lines", 0) or 0))
            for f in sorted(files, key=lambda f: int(f.properties.get("lines", 0) or 0), reverse=True)[:5]
            if int(f.properties.get("lines", 0) or 0) >= 300
        ]

        result.undocumented_public = len(documentable) - sum(
            1 for n in documentable if n.properties.get("has_docstring")
        )

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        return result

    def _detect_layers(self, modules: list[GraphNode]) -> list[str]:
        """Detect architectural layers from module paths."""
        layers: set[str] = set()
        _layer_map = {
            "domain": "Domain", "application": "Application",
            "infrastructure": "Infrastructure", "presentation": "Presentation",
            "api": "Presentation", "router": "Presentation",
            "service": "Application", "repository": "Infrastructure",
        }
        for m in modules:
            path = str(m.properties.get("path", m.label)).lower()
            for keyword, layer in _layer_map.items():
                if keyword in path:
                    layers.add(layer)
        return sorted(layers)

    def _detect_patterns(
        self, classes: list[GraphNode], functions: list[GraphNode], graph: GraphBuildResult
    ) -> list[str]:
        """Detect design patterns from naming and structure."""
        patterns: set[str] = set()

        class_names = " ".join(c.label.lower() for c in classes)
        fn_names = " ".join(f.label.lower() for f in functions)
        all_names = class_names + " " + fn_names

        if "repository" in all_names:
            patterns.add("Repository Pattern")
        if "factory" in all_names:
            patterns.add("Factory Pattern")
        if "observer" in all_names or "listener" in all_names or "subscriber" in all_names:
            patterns.add("Observer Pattern")
        if "singleton" in all_names:
            patterns.add("Singleton Pattern")
        if "strategy" in all_names:
            patterns.add("Strategy Pattern")
        if "middleware" in all_names:
            patterns.add("Middleware/Pipeline Pattern")
        if "decorator" in all_names:
            patterns.add("Decorator Pattern")
        if "adapter" in all_names:
            patterns.add("Adapter Pattern")
        if "facade" in all_names:
            patterns.add("Facade Pattern")

        # Check for DI pattern (interfaces with implementations)
        interfaces = [c for c in classes if c.node_type == NodeType.INTERFACE]
        if len(interfaces) >= 2:
            patterns.add("Dependency Injection")

        return sorted(patterns)

    def _compute_module_deps(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> dict[str, set[str]]:
        """Compute cross-module dependencies."""
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

        deps: dict[str, set[str]] = defaultdict(set)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                src_mod = node_to_module.get(edge.source_id)
                tgt_mod = node_to_module.get(edge.target_id)
                if src_mod and tgt_mod and src_mod != tgt_mod:
                    deps[src_mod].add(tgt_mod)

        return deps

    def _find_circular(
        self, deps: dict[str, set[str]], graph: GraphBuildResult
    ) -> list[tuple[str, str]]:
        """Find circular dependency pairs."""
        circular: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for src, targets in deps.items():
            for tgt in targets:
                if tgt in deps and src in deps[tgt]:
                    pair = tuple(sorted([src, tgt]))
                    if pair not in seen:
                        seen.add(pair)
                        src_node = graph.node_by_id.get(src)
                        tgt_node = graph.node_by_id.get(tgt)
                        if src_node and tgt_node:
                            src_name = str(src_node.properties.get("path", src_node.label)).split("/")[-1]
                            tgt_name = str(tgt_node.properties.get("path", tgt_node.label)).split("/")[-1]
                            circular.append((src_name, tgt_name))
        return circular[:5]

    def _find_most_coupled(
        self, deps: dict[str, set[str]], graph: GraphBuildResult
    ) -> list[tuple[str, int]]:
        """Find modules with highest total coupling (fan_in + fan_out)."""
        coupling: dict[str, int] = defaultdict(int)
        for src, targets in deps.items():
            coupling[src] += len(targets)  # fan_out
            for tgt in targets:
                coupling[tgt] += 1  # fan_in

        result: list[tuple[str, int]] = []
        for mod_id, score in sorted(coupling.items(), key=lambda x: x[1], reverse=True)[:5]:
            mod_node = graph.node_by_id.get(mod_id)
            if mod_node:
                name = str(mod_node.properties.get("path", mod_node.label)).split("/")[-1]
                result.append((name, score))
        return result

    def _generate_recommendations(self, result: EngineeringReportResult) -> list[tuple[str, str, str]]:
        """Generate prioritized recommendations from analysis."""
        recs: list[tuple[str, str, str]] = []

        if result.complex_functions:
            name, cc, file = result.complex_functions[0]
            recs.append((
                "HIGH",
                f"Refactor `{name}` (complexity: {cc})",
                f"Located in `{file.split('/')[-1]}`. Extract branches into named methods "
                f"or use strategy pattern to reduce cyclomatic complexity below 10.",
            ))

        if result.god_classes:
            name, methods, file = result.god_classes[0]
            recs.append((
                "HIGH",
                f"Split `{name}` ({methods} methods)",
                f"In `{file.split('/')[-1]}`. Group methods by cohesion, extract each "
                f"group into a focused class. Use composition to maintain the API.",
            ))

        if result.circular_deps:
            src, tgt = result.circular_deps[0]
            recs.append((
                "HIGH",
                f"Break circular dependency: `{src}` ↔ `{tgt}`",
                "Introduce an interface in the lower-level module and have the "
                "higher-level module depend on the abstraction instead.",
            ))

        if result.documentation_ratio < 0.4:
            recs.append((
                "MEDIUM",
                f"Improve documentation ({result.documentation_ratio:.0%} documented)",
                f"{result.undocumented_public} public symbols lack docstrings. "
                "Prioritize documenting interfaces and public API methods.",
            ))

        if result.test_ratio < 0.3 and result.total_files > 10:
            recs.append((
                "MEDIUM",
                f"Increase test coverage (ratio: {result.test_ratio:.2f})",
                "Add tests for the highest-complexity modules first. "
                "Focus on domain and application layers.",
            ))

        if result.large_files:
            path, lines = result.large_files[0]
            recs.append((
                "LOW",
                f"Split `{path.split('/')[-1]}` ({lines} lines)",
                "Large files are harder to navigate and review. "
                "Extract related functionality into separate modules.",
            ))

        if not result.detected_layers or len(result.detected_layers) < 2:
            recs.append((
                "MEDIUM",
                "Consider introducing architectural layers",
                "No clear layer separation detected. Separating domain, "
                "application, and infrastructure layers improves testability.",
            ))

        return recs

    def _render_markdown(self, r: EngineeringReportResult) -> str:
        """Render the full engineering report."""
        lines: list[str] = []

        lines.append(f"# Engineering Report — {r.repo_name}")
        lines.append("")

        # ── Executive Summary ────────────────────────────────────────────────
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"**{r.repo_name}** is a {'/'.join(r.languages[:2]) if r.languages else 'multi-language'} "
            f"project with {r.total_files} source files ({r.total_lines:,} lines) "
            f"organized into {r.total_modules} modules."
        )
        lines.append("")

        if r.detected_patterns:
            lines.append(f"**Design patterns detected:** {', '.join(r.detected_patterns)}")
            lines.append("")
        if r.detected_layers:
            lines.append(f"**Architecture:** {' → '.join(r.detected_layers)} layering")
            lines.append("")

        # Key metrics box
        lines.append("| Metric | Value | Assessment |")
        lines.append("|--------|-------|-----------|")
        # Complexity assessment
        cx_assess = "✓ Good" if r.avg_complexity < 5 else ("⚠ Moderate" if r.avg_complexity < 10 else "✗ High")
        lines.append(f"| Avg Complexity | {r.avg_complexity} | {cx_assess} |")
        # Documentation
        doc_assess = "✓ Good" if r.documentation_ratio >= 0.7 else ("⚠ Partial" if r.documentation_ratio >= 0.4 else "✗ Poor")
        lines.append(f"| Documentation | {r.documentation_ratio:.0%} | {doc_assess} |")
        # Testing
        test_assess = "✓ Good" if r.test_ratio >= 0.5 else ("⚠ Partial" if r.test_ratio >= 0.2 else "✗ Low")
        lines.append(f"| Test Ratio | {r.test_ratio:.2f} | {test_assess} |")
        # Coupling
        coupling_assess = "✓ Low" if not r.circular_deps else f"⚠ {len(r.circular_deps)} circular"
        lines.append(f"| Coupling | {len(r.most_coupled_modules)} hotspots | {coupling_assess} |")
        lines.append("")

        # ── Repository Structure ─────────────────────────────────────────────
        lines.append("## Repository Structure")
        lines.append("")
        lines.append("| | Count |")
        lines.append("|---|------|")
        lines.append(f"| Modules | {r.total_modules} |")
        lines.append(f"| Files | {r.total_files} |")
        lines.append(f"| Classes / Interfaces | {r.total_classes} |")
        lines.append(f"| Functions / Methods | {r.total_functions} |")
        lines.append(f"| API Endpoints | {r.total_endpoints} |")
        lines.append(f"| Test Functions | {r.total_tests} |")
        lines.append(f"| Total Lines | {r.total_lines:,} |")
        if r.languages:
            lines.append(f"| Languages | {', '.join(r.languages)} |")
        lines.append("")

        # ── Dependency Analysis ──────────────────────────────────────────────
        lines.append("## Dependency Analysis")
        lines.append("")

        if r.circular_deps:
            lines.append("### Circular Dependencies")
            lines.append("")
            for src, tgt in r.circular_deps:
                lines.append(f"- `{src}` ↔ `{tgt}`")
            lines.append("")
            lines.append("> Circular dependencies prevent independent testing and deployment.")
            lines.append("")

        if r.most_coupled_modules:
            lines.append("### Coupling Hotspots")
            lines.append("")
            lines.append("| Module | Coupling Score | Risk |")
            lines.append("|--------|---------------|------|")
            for name, score in r.most_coupled_modules:
                risk = "High" if score >= 6 else ("Medium" if score >= 3 else "Low")
                lines.append(f"| `{name}` | {score} | {risk} |")
            lines.append("")

        # ── Complexity Hotspots ──────────────────────────────────────────────
        if r.complex_functions:
            lines.append("## Complexity Hotspots")
            lines.append("")
            lines.append("Functions with cyclomatic complexity ≥ 10 (high bug risk):")
            lines.append("")
            lines.append("| Function | Complexity | File |")
            lines.append("|----------|-----------|------|")
            for name, cc, file in r.complex_functions:
                lines.append(f"| `{name}` | **{cc}** | `{file.split('/')[-1]}` |")
            lines.append("")

        # ── God Classes ──────────────────────────────────────────────────────
        if r.god_classes:
            lines.append("## Potential God Classes")
            lines.append("")
            lines.append("Classes with ≥12 methods (likely multiple responsibilities):")
            lines.append("")
            for name, methods, file in r.god_classes:
                lines.append(f"- **`{name}`** — {methods} methods in `{file.split('/')[-1]}`")
            lines.append("")

        # ── Large Files ──────────────────────────────────────────────────────
        if r.large_files:
            lines.append("## Large Files")
            lines.append("")
            for path, line_count in r.large_files:
                lines.append(f"- `{path.split('/')[-1]}` — {line_count} lines")
            lines.append("")

        # ── Recommendations ──────────────────────────────────────────────────
        if r.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for priority, title, detail in r.recommendations:
                badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "")
                lines.append(f"### {badge} [{priority}] {title}")
                lines.append("")
                lines.append(detail)
                lines.append("")

        return "\n".join(lines)
