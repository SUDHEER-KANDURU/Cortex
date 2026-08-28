"""Module Breakdown Generator — evidence-backed architectural analysis.

This is NOT a file/folder lister. It produces engineering intelligence:
  - Purpose inference from contained symbols and imports
  - Dependency analysis (fan-in, fan-out, instability metric)
  - Architectural layer detection (domain, application, infrastructure, presentation)
  - Coupling assessment with evidence
  - Risk identification with metrics
  - Inter-module communication patterns

Every claim is backed by evidence from the knowledge graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


# ─── Layer detection patterns ─────────────────────────────────────────────────

_LAYER_PATTERNS: dict[str, list[str]] = {
    "domain": ["domain", "entities", "models", "core", "value_objects"],
    "application": ["application", "use_cases", "services", "usecases", "interactors"],
    "infrastructure": [
        "infrastructure", "persistence", "repository", "repositories",
        "adapters", "db", "database", "clients", "external",
    ],
    "presentation": [
        "presentation", "api", "routes", "routers", "controllers",
        "views", "handlers", "endpoints", "rest", "graphql",
    ],
    "testing": ["tests", "test", "spec", "specs", "fixtures", "__tests__"],
    "configuration": ["config", "settings", "env", "configuration"],
    "shared": ["shared", "common", "utils", "utilities", "helpers", "lib"],
}

_RESPONSIBILITY_SIGNALS: dict[str, list[str]] = {
    "Data Access": ["repository", "dao", "store", "persistence", "query"],
    "Business Logic": ["service", "use_case", "manager", "handler", "processor"],
    "API Layer": ["router", "controller", "endpoint", "view", "handler"],
    "Data Model": ["entity", "model", "schema", "dto", "dataclass"],
    "External Integration": ["client", "adapter", "gateway", "connector", "api"],
    "Event Handling": ["event", "listener", "subscriber", "publisher", "emitter"],
    "Authentication": ["auth", "security", "permission", "token", "session"],
    "Orchestration": ["orchestrator", "pipeline", "workflow", "saga", "coordinator"],
}


@dataclass
class ModuleAnalysis:
    """Complete analysis of a single module with evidence."""
    path: str
    name: str
    # Metrics
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    method_count: int = 0
    endpoint_count: int = 0
    test_count: int = 0
    line_count: int = 0
    # Dependency metrics
    fan_out: int = 0  # modules this depends on
    fan_in: int = 0   # modules that depend on this
    instability: float = 0.0  # fan_out / (fan_in + fan_out), 0=stable, 1=unstable
    # Architectural classification
    detected_layer: str = "unknown"
    detected_responsibilities: list[str] = field(default_factory=list)
    # Dependencies
    depends_on: list[str] = field(default_factory=list)
    depended_on_by: list[str] = field(default_factory=list)
    # Key symbols
    public_classes: list[str] = field(default_factory=list)
    public_interfaces: list[str] = field(default_factory=list)
    key_functions: list[str] = field(default_factory=list)
    # Complexity
    total_complexity: int = 0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    max_complexity_symbol: str = ""
    # Documentation
    documentation_ratio: float = 0.0
    # Risks
    risks: list[str] = field(default_factory=list)


@dataclass
class ModuleBreakdownResult:
    """Full module breakdown analysis for a repository."""
    repo_name: str
    total_modules: int
    total_files: int
    total_classes: int
    total_functions: int
    modules: list[ModuleAnalysis] = field(default_factory=list)
    # Cross-cutting concerns
    circular_dependencies: list[tuple[str, str]] = field(default_factory=list)
    most_coupled_module: str = ""
    most_unstable_module: str = ""
    most_stable_module: str = ""


class ModuleBreakdownGenerator:
    """Generates evidence-backed module breakdown from the knowledge graph.

    Intelligence pipeline:
      COLLECT → RELATE → MEASURE → DETECT → RANK → EXPLAIN
    """

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate full module breakdown as Markdown."""
        analysis = self.analyze(graph, repo_name)
        return self._render_markdown(analysis)

    def analyze(self, graph: GraphBuildResult, repo_name: str) -> ModuleBreakdownResult:
        """Perform the full module analysis pipeline."""
        modules = graph.nodes_by_type(NodeType.MODULE)
        files = graph.nodes_by_type(NodeType.FILE)
        all_classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
        )]
        all_functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT, NodeType.TEST
        )]

        result = ModuleBreakdownResult(
            repo_name=repo_name,
            total_modules=len(modules),
            total_files=len(files),
            total_classes=len(all_classes),
            total_functions=len(all_functions),
        )

        if not modules:
            return result

        # Build module → contained nodes index
        module_contents = self._index_module_contents(graph, modules)

        # Build inter-module dependency map
        module_deps = self._compute_module_dependencies(graph, modules)

        # Analyze each module
        for module_node in modules:
            analysis = self._analyze_module(
                module_node, module_contents, module_deps, graph
            )
            result.modules.append(analysis)

        # Sort by importance (fan_in descending — most depended-on first)
        result.modules.sort(key=lambda m: m.fan_in, reverse=True)

        # Detect circular dependencies. Pass a module-id → readable-path map so
        # the result holds human-readable module paths (e.g. "src/cortex/chat")
        # rather than internal node IDs like "f402bc3b_module_27a7d71c3594".
        module_label_by_id = {
            m.id: str(m.properties.get("path", m.label)).rstrip("/") or m.label
            for m in modules
        }
        result.circular_dependencies = self._detect_circular_deps(
            module_deps, module_label_by_id
        )

        # Identify extremes
        if result.modules:
            by_coupling = sorted(result.modules, key=lambda m: m.fan_in + m.fan_out, reverse=True)
            result.most_coupled_module = by_coupling[0].name if by_coupling else ""

            unstable = [m for m in result.modules if m.instability > 0]
            if unstable:
                result.most_unstable_module = max(unstable, key=lambda m: m.instability).name

            stable = [m for m in result.modules if m.fan_in > 0]
            if stable:
                result.most_stable_module = min(stable, key=lambda m: m.instability).name

        return result

    def _index_module_contents(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> dict[str, list[GraphNode]]:
        """Build a mapping of module_id → list of contained nodes (recursive)."""
        # Build CONTAINS edge index
        contains_from: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains_from[edge.source_id].append(edge.target_id)

        result: dict[str, list[GraphNode]] = {}
        for module in modules:
            contained: list[GraphNode] = []
            self._collect_descendants(module.id, contains_from, graph.node_by_id, contained)
            result[module.id] = contained
        return result

    def _collect_descendants(
        self,
        node_id: str,
        contains_from: dict[str, list[str]],
        node_by_id: dict[str, GraphNode],
        result: list[GraphNode],
    ) -> None:
        """Recursively collect all descendants of a node via CONTAINS edges."""
        for child_id in contains_from.get(node_id, []):
            child = node_by_id.get(child_id)
            if child:
                result.append(child)
                self._collect_descendants(child_id, contains_from, node_by_id, result)

    def _compute_module_dependencies(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> dict[str, set[str]]:
        """Compute which modules depend on which other modules via IMPORTS edges.

        Returns: {module_id: set of module_ids it depends on}
        """
        # Map each file/node to its parent module
        node_to_module: dict[str, str] = {}
        contains_from: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains_from[edge.source_id].append(edge.target_id)

        module_ids = {m.id for m in modules}

        def assign_module(mod_id: str) -> None:
            for child_id in contains_from.get(mod_id, []):
                node_to_module[child_id] = mod_id
                # Recurse for nested containment (files within modules)
                assign_module(child_id)

        for module in modules:
            assign_module(module.id)

        # Now find cross-module IMPORTS
        deps: dict[str, set[str]] = {m.id: set() for m in modules}
        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                src_module = node_to_module.get(edge.source_id)
                tgt_module = node_to_module.get(edge.target_id)
                if src_module and tgt_module and src_module != tgt_module:
                    if src_module in deps:
                        deps[src_module].add(tgt_module)

        return deps

    def _analyze_module(
        self,
        module_node: GraphNode,
        module_contents: dict[str, list[GraphNode]],
        module_deps: dict[str, set[str]],
        graph: GraphBuildResult,
    ) -> ModuleAnalysis:
        """Analyze a single module with full evidence."""
        contents = module_contents.get(module_node.id, [])
        module_path = module_node.properties.get("path", module_node.label)
        module_name = str(module_path).rstrip("/").split("/")[-1]

        analysis = ModuleAnalysis(
            path=str(module_path),
            name=module_name,
        )

        # Count by type
        for node in contents:
            if node.node_type == NodeType.FILE:
                analysis.file_count += 1
                analysis.line_count += int(node.properties.get("lines", 0) or 0)
            elif node.node_type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM):
                analysis.class_count += 1
                if node.node_type == NodeType.INTERFACE:
                    analysis.public_interfaces.append(node.label)
                else:
                    analysis.public_classes.append(node.label)
            elif node.node_type in (NodeType.FUNCTION, NodeType.METHOD):
                analysis.function_count += 1
            elif node.node_type == NodeType.ENDPOINT:
                analysis.endpoint_count += 1
                analysis.key_functions.append(
                    node.properties.get("route_info", node.label) or node.label
                )
            elif node.node_type == NodeType.TEST:
                analysis.test_count += 1

        # Method count (from class properties)
        for node in contents:
            if node.node_type in (NodeType.CLASS, NodeType.INTERFACE):
                analysis.method_count += int(node.properties.get("methods", 0) or 0)

        # Complexity metrics
        complexities = []
        for node in contents:
            cc = int(node.properties.get("cyclomatic", 0) or 0)
            if cc > 0:
                complexities.append((cc, node.label))

        if complexities:
            analysis.total_complexity = sum(c for c, _ in complexities)
            analysis.avg_complexity = round(analysis.total_complexity / len(complexities), 2)
            max_cc, max_name = max(complexities, key=lambda x: x[0])
            analysis.max_complexity = max_cc
            analysis.max_complexity_symbol = max_name

        # Documentation ratio
        doc_counts = [node for node in contents if node.properties.get("has_docstring")]
        documentable = [n for n in contents if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.FUNCTION,
            NodeType.METHOD, NodeType.ENDPOINT
        )]
        if documentable:
            analysis.documentation_ratio = round(len(doc_counts) / len(documentable), 2)

        # Dependency metrics
        my_deps = module_deps.get(module_node.id, set())
        analysis.fan_out = len(my_deps)

        # Fan-in: how many modules depend on THIS module
        fan_in_count = sum(
            1 for deps in module_deps.values()
            if module_node.id in deps
        )
        analysis.fan_in = fan_in_count

        # Instability metric (Robert C. Martin)
        total_coupling = analysis.fan_in + analysis.fan_out
        analysis.instability = round(
            analysis.fan_out / total_coupling if total_coupling > 0 else 0.5,
            2,
        )

        # Resolve dependency names
        for dep_id in my_deps:
            dep_node = graph.node_by_id.get(dep_id)
            if dep_node:
                dep_path = dep_node.properties.get("path", dep_node.label)
                dep_name = str(dep_path).rstrip("/").split("/")[-1]
                analysis.depends_on.append(dep_name)

        # Find who depends on this module
        for other_id, other_deps in module_deps.items():
            if module_node.id in other_deps:
                other_node = graph.node_by_id.get(other_id)
                if other_node:
                    other_path = other_node.properties.get("path", other_node.label)
                    other_name = str(other_path).rstrip("/").split("/")[-1]
                    analysis.depended_on_by.append(other_name)

        # Detect architectural layer
        analysis.detected_layer = self._detect_layer(str(module_path), contents)

        # Detect responsibilities
        analysis.detected_responsibilities = self._detect_responsibilities(
            str(module_path), contents
        )

        # Identify risks
        analysis.risks = self._identify_risks(analysis)

        return analysis

    def _detect_layer(self, module_path: str, contents: list[GraphNode]) -> str:
        """Detect which architectural layer this module belongs to."""
        path_lower = module_path.lower()

        # Direct path matching
        for layer, patterns in _LAYER_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return layer

        # Heuristic from contents: if mostly endpoints → presentation
        endpoint_count = sum(1 for n in contents if n.node_type == NodeType.ENDPOINT)
        test_count = sum(1 for n in contents if n.node_type == NodeType.TEST)
        interface_count = sum(1 for n in contents if n.node_type == NodeType.INTERFACE)

        if endpoint_count > 2:
            return "presentation"
        if test_count > 2:
            return "testing"
        if interface_count > 1:
            return "domain"

        return "unknown"

    def _detect_responsibilities(
        self, module_path: str, contents: list[GraphNode]
    ) -> list[str]:
        """Detect what responsibilities this module has from its symbol names."""
        responsibilities: set[str] = set()
        path_lower = module_path.lower()

        # Check path
        for responsibility, signals in _RESPONSIBILITY_SIGNALS.items():
            for signal in signals:
                if signal in path_lower:
                    responsibilities.add(responsibility)
                    break

        # Check contained symbol names
        symbol_names = " ".join(n.label.lower() for n in contents)
        for responsibility, signals in _RESPONSIBILITY_SIGNALS.items():
            for signal in signals:
                if signal in symbol_names:
                    responsibilities.add(responsibility)
                    break

        return sorted(responsibilities)[:4]  # Cap at 4

    def _identify_risks(self, analysis: ModuleAnalysis) -> list[str]:
        """Identify engineering risks for this module with evidence."""
        risks = []

        if analysis.max_complexity > 15:
            risks.append(
                f"High complexity: `{analysis.max_complexity_symbol}` has "
                f"cyclomatic complexity {analysis.max_complexity} (threshold: 15)"
            )

        if analysis.instability > 0.8 and analysis.fan_in > 0:
            risks.append(
                f"Highly unstable: instability={analysis.instability:.2f} "
                f"(depends on {analysis.fan_out} modules, depended on by {analysis.fan_in})"
            )

        if analysis.fan_out > 5:
            risks.append(
                f"High coupling: depends on {analysis.fan_out} other modules "
                f"({', '.join(analysis.depends_on[:5])})"
            )

        if analysis.documentation_ratio < 0.3 and analysis.function_count > 5:
            risks.append(
                f"Poor documentation: only {analysis.documentation_ratio:.0%} of "
                f"symbols are documented"
            )

        if analysis.line_count > 2000:
            risks.append(
                f"Large module: {analysis.line_count} lines across "
                f"{analysis.file_count} files — consider splitting"
            )

        if analysis.class_count > 10:
            risks.append(
                f"Many classes ({analysis.class_count}) — may indicate "
                f"multiple responsibilities"
            )

        return risks

    def _detect_circular_deps(
        self,
        module_deps: dict[str, set[str]],
        module_label_by_id: dict[str, str] | None = None,
    ) -> list[tuple[str, str]]:
        """Detect pairs of modules with circular dependencies.

        `module_deps` is keyed by internal module node IDs. When
        `module_label_by_id` is supplied, each pair is translated to the
        module's readable path/name so the rendered report is human-friendly;
        otherwise the raw IDs are returned (kept for backward compatibility).
        """
        circular: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for src, targets in module_deps.items():
            for tgt in targets:
                if tgt in module_deps and src in module_deps[tgt]:
                    pair = tuple(sorted([src, tgt]))
                    if pair not in seen:
                        seen.add(pair)
                        if module_label_by_id is not None:
                            circular.append((
                                module_label_by_id.get(src, src),
                                module_label_by_id.get(tgt, tgt),
                            ))
                        else:
                            circular.append((src, tgt))

        return circular

    def _render_markdown(self, analysis: ModuleBreakdownResult) -> str:
        """Render the full analysis as structured Markdown."""
        lines: list[str] = []

        lines.append(f"# Module Breakdown — {analysis.repo_name}")
        lines.append("")
        lines.append(
            "> **What is a module?** A module is a self-contained section of the codebase "
            "that handles one area of responsibility (like \"user accounts\" or \"payments\"). "
            "Well-organized modules make software easier to understand, test, and change. "
            "This breakdown shows you how the project is organized and where potential "
            "problems exist."
        )
        lines.append("")

        # ── Executive Summary ────────────────────────────────────────────────
        lines.append("## At a Glance")
        lines.append("")
        lines.append(f"This project is organized into **{analysis.total_modules} modules** "
                     f"containing {analysis.total_files} files.")
        lines.append("")
        lines.append(f"| What | Count | Why it matters |")
        lines.append(f"|------|-------|---------------|")
        lines.append(f"| Modules | {analysis.total_modules} | Separate areas of responsibility |")
        lines.append(f"| Source Files | {analysis.total_files} | Individual code files |")
        lines.append(f"| Classes / Interfaces | {analysis.total_classes} | Blueprints for objects and contracts |")
        lines.append(f"| Functions / Methods | {analysis.total_functions} | Individual units of behavior |")
        if analysis.most_coupled_module:
            lines.append(f"| Most Connected | `{analysis.most_coupled_module}` | Has the most dependencies (risky to change) |")
        if analysis.most_stable_module:
            lines.append(f"| Most Stable | `{analysis.most_stable_module}` | Many things depend on it, rarely changes |")
        if analysis.most_unstable_module:
            lines.append(f"| Most Volatile | `{analysis.most_unstable_module}` | Depends on many others, likely to change often |")
        lines.append("")

        # ── Circular Dependencies Warning ────────────────────────────────────
        if analysis.circular_dependencies:
            lines.append("## ⚠ Circular Dependencies Detected")
            lines.append("")
            lines.append(
                "**What does this mean?** These modules depend on each other in a loop — "
                "Module A needs Module B, but Module B also needs Module A. This is like "
                "two people who can't start work until the other person finishes first. "
                "It makes the code harder to test, change, and understand."
            )
            lines.append("")
            lines.append("**Affected pairs** (each depends on the other):")
            lines.append("")
            for src, tgt in analysis.circular_dependencies[:5]:
                lines.append(f"- `{src}` &harr; `{tgt}`")
            lines.append("")
            lines.append(
                "> Circular dependencies make modules harder to test in isolation "
                "and can cause import-order bugs."
            )
            lines.append("")

        # ── Module Details ───────────────────────────────────────────────────
        lines.append("## Module Details")
        lines.append("")

        for mod in analysis.modules:
            lines.append(f"### `{mod.path}/`")
            lines.append("")

            # Layer badge
            layer_badge = f"**Layer:** {mod.detected_layer.title()}"
            if mod.detected_responsibilities:
                layer_badge += f" · **Responsibilities:** {', '.join(mod.detected_responsibilities)}"
            lines.append(layer_badge)
            lines.append("")

            # Metrics table
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Files | {mod.file_count} |")
            lines.append(f"| Lines | {mod.line_count:,} |")
            if mod.class_count:
                lines.append(f"| Classes | {mod.class_count} |")
            if mod.endpoint_count:
                lines.append(f"| Endpoints | {mod.endpoint_count} |")
            if mod.test_count:
                lines.append(f"| Tests | {mod.test_count} |")
            lines.append(f"| Avg Complexity | {mod.avg_complexity} |")
            lines.append(f"| Documentation | {mod.documentation_ratio:.0%} |")
            lines.append(f"| Instability | {mod.instability:.2f} |")
            lines.append("")

            # Dependencies
            if mod.depends_on:
                lines.append(f"**Depends on:** {', '.join(f'`{d}`' for d in mod.depends_on[:8])}")
                lines.append("")
            if mod.depended_on_by:
                lines.append(f"**Depended on by:** {', '.join(f'`{d}`' for d in mod.depended_on_by[:8])}")
                lines.append("")

            # Key symbols
            if mod.public_interfaces:
                lines.append(f"**Interfaces:** {', '.join(f'`{c}`' for c in mod.public_interfaces[:6])}")
                lines.append("")
            if mod.public_classes:
                lines.append(f"**Classes:** {', '.join(f'`{c}`' for c in mod.public_classes[:8])}")
                lines.append("")
            if mod.key_functions:
                lines.append(f"**Endpoints:** {', '.join(f'`{e}`' for e in mod.key_functions[:6])}")
                lines.append("")

            # Risks
            if mod.risks:
                lines.append("**Risks:**")
                for risk in mod.risks:
                    lines.append(f"- {risk}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # ── Dependency Matrix (compact) ──────────────────────────────────────
        if len(analysis.modules) > 1 and len(analysis.modules) <= 12:
            lines.append("## Dependency Overview")
            lines.append("")
            lines.append("```")
            lines.append("Module Dependencies (→ depends on):")
            for mod in analysis.modules:
                if mod.depends_on:
                    lines.append(f"  {mod.name} → {', '.join(mod.depends_on[:5])}")
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
