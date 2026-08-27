"""Architecture Diagram Generator — progressive disclosure architecture view.

This generates a MULTI-LEVEL architecture representation:
  Level 1 (System): Modules as nodes, aggregated cross-module dependencies
  Level 2 (Module): Classes within each module with relationships
  Level 3 (included): Existing Mermaid detail view for file-level graph

The diagram answers: "What are the major parts of this system and
how do they communicate?" — NOT "show me every file and import."

Design principles:
  - Progressive disclosure (overview → detail)
  - Cap visible nodes to prevent spaghetti
  - Layer-based grouping (Presentation → Application → Domain → Infrastructure)
  - Evidence in each section (metrics, coupling data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


# Layer classification patterns (reused from module breakdown)
_LAYER_KEYWORDS: dict[str, list[str]] = {
    "Presentation": ["presentation", "router", "controller", "handler", "api", "endpoint", "view"],
    "Application": ["application", "service", "use_case", "usecase", "interactor"],
    "Domain": ["domain", "entity", "model", "core", "entities"],
    "Infrastructure": ["infrastructure", "repository", "persistence", "db", "client", "adapter"],
    "Frontend": ["component", "page", "hook", "feature", "frontend"],
    "Shared": ["shared", "common", "utils", "config", "lib"],
    "Testing": ["test", "tests", "spec", "fixture"],
}


@dataclass
class ModuleDiagramNode:
    """A module represented as a node in the system architecture."""
    id: str
    name: str
    path: str
    layer: str
    file_count: int = 0
    class_count: int = 0
    endpoint_count: int = 0
    complexity: int = 0


@dataclass
class ModuleDiagramEdge:
    """An aggregated dependency between two modules."""
    source: str  # module name
    target: str  # module name
    weight: int = 1  # number of individual imports


class ArchitectureDiagramGenerator:
    """Generates multi-level architecture diagrams from the knowledge graph."""

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate the full architecture artifact as Markdown with Mermaid."""
        modules = graph.nodes_by_type(NodeType.MODULE)
        files = graph.nodes_by_type(NodeType.FILE)

        if not modules and not files:
            return f"# Architecture — {repo_name}\n\n_No code structure detected._"

        lines: list[str] = []
        lines.append(f"# Architecture — {repo_name}")
        lines.append("")

        # ── Level 1: System Overview ─────────────────────────────────────────
        lines.append("## System Architecture")
        lines.append("")
        lines.append(
            "High-level view showing modules and their dependencies. "
            "Arrow direction = depends on."
        )
        lines.append("")

        # Build module dependency model
        mod_nodes, mod_edges = self._build_module_graph(graph, modules)

        if mod_nodes:
            # Generate system-level Mermaid
            mermaid = self._render_system_mermaid(mod_nodes, mod_edges, repo_name)
            lines.append("```mermaid")
            lines.append(mermaid)
            lines.append("```")
            lines.append("")

            # Module summary table
            lines.append("### Module Summary")
            lines.append("")
            lines.append("| Module | Layer | Files | Classes | Endpoints | Complexity |")
            lines.append("|--------|-------|-------|---------|-----------|-----------|")
            for mod in sorted(mod_nodes, key=lambda m: m.layer):
                lines.append(
                    f"| `{mod.name}` | {mod.layer} | {mod.file_count} | "
                    f"{mod.class_count} | {mod.endpoint_count} | {mod.complexity} |"
                )
            lines.append("")

        # ── Level 2: Layer Architecture ──────────────────────────────────────
        lines.append("## Layer Architecture")
        lines.append("")
        lines.append(
            "How the system is organized into architectural layers. "
            "Dependencies should flow downward (Presentation → Application → Domain → Infrastructure)."
        )
        lines.append("")

        # Group modules by layer
        by_layer: dict[str, list[ModuleDiagramNode]] = defaultdict(list)
        for mod in mod_nodes:
            by_layer[mod.layer].append(mod)

        layer_order = ["Presentation", "Application", "Domain", "Infrastructure", "Frontend", "Shared", "Testing", "Other"]
        for layer in layer_order:
            layer_modules = by_layer.get(layer, [])
            if not layer_modules:
                continue
            mod_names = ", ".join(f"`{m.name}`" for m in layer_modules)
            lines.append(f"**{layer}:** {mod_names}")
            lines.append("")

        # Detect layer violations
        violations = self._detect_layer_violations(mod_nodes, mod_edges)
        if violations:
            lines.append("### ⚠ Layer Violations")
            lines.append("")
            for violation in violations[:5]:
                lines.append(f"- {violation}")
            lines.append("")

        # ── Level 3: Component Relationships ─────────────────────────────────
        lines.append("## Key Components")
        lines.append("")

        # Show the most important classes (highest in-degree)
        all_classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE
        )]
        if all_classes:
            # Compute in-degree for classes
            class_in_degree: dict[str, int] = defaultdict(int)
            for edge in graph.edges:
                if edge.relationship in (
                    RelationshipType.INHERITS, RelationshipType.IMPLEMENTS, RelationshipType.CALLS
                ):
                    class_in_degree[edge.target_id] += 1

            important_classes = sorted(
                all_classes,
                key=lambda c: class_in_degree.get(c.id, 0),
                reverse=True,
            )[:12]

            if important_classes:
                lines.append(
                    "Most-referenced classes/interfaces in the system "
                    "(highest in-degree = most depended upon):"
                )
                lines.append("")
                lines.append("| Component | Type | File | Referenced By |")
                lines.append("|-----------|------|------|--------------|")
                for cls in important_classes:
                    in_deg = class_in_degree.get(cls.id, 0)
                    if in_deg == 0:
                        continue
                    type_str = cls.node_type.value
                    file_name = str(cls.properties.get("file", "")).split("/")[-1]
                    lines.append(
                        f"| `{cls.label}` | {type_str} | `{file_name}` | {in_deg} |"
                    )
                lines.append("")

        # ── Detailed Mermaid (existing generator for file-level) ─────────────
        lines.append("## Detailed Dependency Graph")
        lines.append("")
        lines.append(
            "File-level dependency graph with layer grouping. "
            "For interactive exploration, use the Architecture Graph view."
        )
        lines.append("")

        # Use the existing MermaidGenerator for the detailed view
        from cortex.pipeline.infrastructure.artifact_generator import MermaidGenerator
        detailed_mermaid = MermaidGenerator().generate(graph, repo_name)
        lines.append("```mermaid")
        lines.append(detailed_mermaid)
        lines.append("```")

        return "\n".join(lines)

    def _build_module_graph(
        self, graph: GraphBuildResult, modules: list[GraphNode]
    ) -> tuple[list[ModuleDiagramNode], list[ModuleDiagramEdge]]:
        """Build the system-level module dependency graph."""
        # Index: node → parent module
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

        # Build module nodes with metrics
        mod_nodes: list[ModuleDiagramNode] = []
        for module in modules:
            # Skip very nested modules — only keep top-level and one level deep
            path = str(module.properties.get("path", module.label))
            depth = path.count("/")
            if depth > 2:
                continue

            # Count contained elements
            children = self._get_all_descendants(module.id, contains_children)
            file_count = sum(1 for c in children if graph.node_by_id.get(c, GraphNode(id="", label="", node_type=NodeType.FILE, job_id="")).node_type == NodeType.FILE)
            class_count = sum(1 for c in children if graph.node_by_id.get(c, GraphNode(id="", label="", node_type=NodeType.FILE, job_id="")).node_type in (NodeType.CLASS, NodeType.INTERFACE))
            endpoint_count = sum(1 for c in children if graph.node_by_id.get(c, GraphNode(id="", label="", node_type=NodeType.FILE, job_id="")).node_type == NodeType.ENDPOINT)

            # Compute total complexity
            complexity = 0
            for c_id in children:
                c_node = graph.node_by_id.get(c_id)
                if c_node:
                    complexity += int(c_node.properties.get("cyclomatic", 0) or 0)

            name = path.rstrip("/").split("/")[-1]
            layer = self._classify_layer(path)

            mod_nodes.append(ModuleDiagramNode(
                id=module.id,
                name=name,
                path=path,
                layer=layer,
                file_count=file_count,
                class_count=class_count,
                endpoint_count=endpoint_count,
                complexity=complexity,
            ))

        # Build module edges (aggregated IMPORTS between modules)
        mod_id_set = {m.id for m in mod_nodes}
        edge_counts: dict[tuple[str, str], int] = defaultdict(int)

        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                src_mod = node_to_module.get(edge.source_id)
                tgt_mod = node_to_module.get(edge.target_id)
                if src_mod and tgt_mod and src_mod != tgt_mod:
                    if src_mod in mod_id_set and tgt_mod in mod_id_set:
                        edge_counts[(src_mod, tgt_mod)] += 1

        mod_edges: list[ModuleDiagramEdge] = []
        mod_id_to_name = {m.id: m.name for m in mod_nodes}
        for (src_id, tgt_id), weight in edge_counts.items():
            src_name = mod_id_to_name.get(src_id)
            tgt_name = mod_id_to_name.get(tgt_id)
            if src_name and tgt_name:
                mod_edges.append(ModuleDiagramEdge(
                    source=src_name,
                    target=tgt_name,
                    weight=weight,
                ))

        return mod_nodes, mod_edges

    def _get_all_descendants(
        self, node_id: str, contains: dict[str, list[str]]
    ) -> list[str]:
        """Get all transitive descendants via CONTAINS."""
        result: list[str] = []
        queue = list(contains.get(node_id, []))
        visited = set()
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            result.append(current)
            queue.extend(contains.get(current, []))
        return result

    def _classify_layer(self, path: str) -> str:
        """Classify a module path into an architectural layer."""
        path_lower = path.lower()
        for layer, keywords in _LAYER_KEYWORDS.items():
            for kw in keywords:
                if kw in path_lower:
                    return layer
        return "Other"

    def _render_system_mermaid(
        self,
        mod_nodes: list[ModuleDiagramNode],
        mod_edges: list[ModuleDiagramEdge],
        repo_name: str,
    ) -> str:
        """Render system-level Mermaid diagram with layer subgraphs."""
        lines: list[str] = ["graph TB"]

        # Group modules by layer into subgraphs
        by_layer: dict[str, list[ModuleDiagramNode]] = defaultdict(list)
        for mod in mod_nodes:
            by_layer[mod.layer].append(mod)

        layer_order = ["Presentation", "Frontend", "Application", "Domain", "Infrastructure", "Shared", "Other"]

        for layer in layer_order:
            layer_mods = by_layer.get(layer, [])
            if not layer_mods:
                continue

            safe_layer = layer.replace(" ", "_")
            lines.append(f"    subgraph {safe_layer}[\"{layer}\"]")
            for mod in layer_mods:
                safe_name = self._safe_id(mod.name)
                # Show file count in node label
                label = f"{mod.name}"
                if mod.endpoint_count:
                    label += f" [{mod.endpoint_count} endpoints]"
                elif mod.class_count:
                    label += f" [{mod.class_count} classes]"
                lines.append(f"        {safe_name}[\"{label}\"]")
            lines.append("    end")

        # Add edges (cap at 20 to prevent visual overload)
        edges_added = 0
        # Sort by weight descending — show strongest dependencies first
        for edge in sorted(mod_edges, key=lambda e: e.weight, reverse=True):
            if edges_added >= 20:
                break
            src_id = self._safe_id(edge.source)
            tgt_id = self._safe_id(edge.target)
            if edge.weight >= 3:
                lines.append(f"    {src_id} ==>|{edge.weight}| {tgt_id}")
            else:
                lines.append(f"    {src_id} --> {tgt_id}")
            edges_added += 1

        return "\n".join(lines)

    def _detect_layer_violations(
        self, mod_nodes: list[ModuleDiagramNode], mod_edges: list[ModuleDiagramEdge]
    ) -> list[str]:
        """Detect dependencies that flow in the wrong direction."""
        violations: list[str] = []
        # Expected flow: Presentation → Application → Domain → Infrastructure
        # A violation is Domain → Presentation or Infrastructure → Application
        layer_rank = {
            "Presentation": 0, "Frontend": 0,
            "Application": 1,
            "Domain": 2,
            "Infrastructure": 3,
            "Shared": 4,  # Shared can be depended on by anyone
            "Testing": 5,
            "Other": 3,
        }

        mod_name_to_layer = {m.name: m.layer for m in mod_nodes}

        for edge in mod_edges:
            src_layer = mod_name_to_layer.get(edge.source, "Other")
            tgt_layer = mod_name_to_layer.get(edge.target, "Other")
            src_rank = layer_rank.get(src_layer, 3)
            tgt_rank = layer_rank.get(tgt_layer, 3)

            # Skip shared — it's fine for anything to depend on shared
            if tgt_layer == "Shared" or src_layer == "Shared":
                continue
            if tgt_layer == "Testing" or src_layer == "Testing":
                continue

            # Violation: deeper layer depends on shallower layer
            # (e.g., Domain depends on Presentation)
            if src_rank > tgt_rank and src_layer != "Other" and tgt_layer != "Other":
                violations.append(
                    f"`{edge.source}` ({src_layer}) depends on `{edge.target}` ({tgt_layer}) "
                    f"— dependency flows upward (should flow downward)"
                )

        return violations

    def _safe_id(self, name: str) -> str:
        """Create a Mermaid-safe node ID."""
        return name.replace("-", "_").replace(".", "_").replace("/", "_").replace(" ", "_")
