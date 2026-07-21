"""Artifact generator — produces high quality artifacts from graph data.
Each generator takes a GraphBuildResult and produces formatted content."""

from dataclasses import dataclass
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
import structlog


def _graph_debug_snapshot(graph: GraphBuildResult) -> dict[str, object]:
    """Return a serializable summary of a graph for pipeline tracing."""
    node_types: dict[str, int] = {}
    edge_types: dict[str, int] = {}
    for node in graph.nodes:
        node_types[node.node_type.value] = node_types.get(node.node_type.value, 0) + 1
    for edge in graph.edges:
        edge_types[edge.relationship.value] = edge_types.get(edge.relationship.value, 0) + 1

    return {
        "node_count": graph.node_count(),
        "edge_count": graph.edge_count(),
        "first_nodes": [
            {
                "id": node.id,
                "type": node.node_type.value,
                "label": node.label,
                "path": node.properties.get("path"),
            }
            for node in graph.nodes[:30]
        ],
        "first_edges": [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relationship": edge.relationship.value,
            }
            for edge in graph.edges[:30]
        ],
        "node_types": node_types,
        "edge_types": edge_types,
    }

logger = structlog.get_logger()


class MermaidGenerator:
    """Generates Mermaid architecture diagrams from the knowledge graph."""

    def generate(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Render the repository hierarchy from the existing graph."""
        snapshot = _graph_debug_snapshot(graph)
        print("[pipeline_debug][MermaidGenerator] input_graph", snapshot)

        lines = ["graph TD"]

        repo_nodes = graph.nodes_by_type(NodeType.REPOSITORY)
        modules = graph.nodes_by_type(NodeType.MODULE)
        files = graph.nodes_by_type(NodeType.FILE)
        classes = graph.nodes_by_type(NodeType.CLASS)

        # Style definitions
        lines.append(
            "  classDef repo fill:#7C3AED,stroke:#5B21B6,"
            "color:#fff,rx:8"
        )
        lines.append(
            "  classDef module fill:#1D4ED8,stroke:#1E40AF,"
            "color:#fff,rx:6"
        )
        lines.append(
            "  classDef file fill:#F59E0B,stroke:#D97706,"
            "color:#fff,rx:4"
        )
        lines.append(
            "  classDef cls fill:#065F46,stroke:#064E3B,"
            "color:#fff,rx:4"
        )

        node_ids: dict[str, str] = {}
        rendered_edges: set[tuple[str, str, str]] = set()
        render_order = [NodeType.REPOSITORY, NodeType.MODULE, NodeType.FILE, NodeType.CLASS]

        for node_type in render_order:
            for node in graph.nodes:
                if node.node_type != node_type:
                    continue
                safe_id = self._safe_id(node.id)
                node_ids[node.id] = safe_id

                if node_type == NodeType.REPOSITORY:
                    label = node.label or repo_name
                    lines.append(f'  {safe_id}["{label}"]:::repo')
                elif node_type == NodeType.MODULE:
                    path = str(node.properties.get("path") or node.label).rstrip("/")
                    label = f"{path}/" if path else node.label
                    lines.append(f'  {safe_id}["{label}"]:::module')
                elif node_type == NodeType.FILE:
                    lines.append(f'  {safe_id}["{node.label}"]:::file')
                elif node_type == NodeType.CLASS:
                    lines.append(f'  {safe_id}["{node.label}"]:::cls')

        for edge in graph.edges:
            if edge.relationship not in {RelationshipType.CONTAINS, RelationshipType.INHERITS}:
                continue

            source = next((n for n in graph.nodes if n.id == edge.source_id), None)
            target = next((n for n in graph.nodes if n.id == edge.target_id), None)
            if not source or not target:
                continue

            if source.node_type not in {NodeType.REPOSITORY, NodeType.MODULE, NodeType.FILE, NodeType.CLASS}:
                continue
            if target.node_type not in {NodeType.MODULE, NodeType.FILE, NodeType.CLASS}:
                continue

            edge_key = (source.id, target.id, edge.relationship.value)
            if edge_key in rendered_edges:
                continue
            rendered_edges.add(edge_key)

            src_id = node_ids.get(source.id, self._safe_id(source.id))
            tgt_id = node_ids.get(target.id, self._safe_id(target.id))
            if edge.relationship == RelationshipType.INHERITS:
                lines.append(f"  {src_id} -.->|extends| {tgt_id}")
            else:
                lines.append(f"  {src_id} --> {tgt_id}")

        output = "\n".join(lines)
        rendered_node_count = len(node_ids)
        rendered_edge_count = len(rendered_edges)
        print(
            "[pipeline_debug][MermaidGenerator] rendered_nodes",
            rendered_node_count,
        )
        print(
            "[pipeline_debug][MermaidGenerator] rendered_edges",
            rendered_edge_count,
        )
        return output

    def _safe_id(self, raw_id: str) -> str:
        """Convert a node ID to a Mermaid-safe identifier."""
        clean = (
            raw_id
            .replace("-", "_")
            .replace(".", "_")
            .replace("/", "_")
            .replace(" ", "_")
        )
        # Must start with a letter
        if clean and not clean[0].isalpha():
            clean = "n_" + clean
        return clean[:30]


class MarkdownReportGenerator:
    """Generates detailed markdown reports from the knowledge graph."""

    def generate_module_breakdown(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        modules = graph.nodes_by_type(NodeType.MODULE)
        files = graph.nodes_by_type(NodeType.FILE)
        classes = graph.nodes_by_type(NodeType.CLASS)
        functions = graph.nodes_by_type(NodeType.FUNCTION)

        lines = [
            f"# Module Breakdown — {repo_name}",
            "",
            "## Overview",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Modules | {len(modules)} |",
            f"| Files | {len(files)} |",
            f"| Classes | {len(classes)} |",
            f"| Functions | {len(functions)} |",
            f"| Graph nodes | {graph.node_count()} |",
            f"| Graph edges | {graph.edge_count()} |",
            "",
        ]

        lines.append("## Module Details")
        lines.append("")

        for module in modules:
            module_label = module.label.rstrip("/")
            lines.append(f"### `{module.label}`")
            lines.append("")

            module_files = [
                f for f in files
                if str(f.properties.get("path", "")).startswith(
                    module_label
                )
            ]
            module_classes = [
                c for c in classes
                if str(c.properties.get("file", "")).startswith(
                    module_label
                )
            ]

            lines.append(
                f"**{len(module_files)} files** · "
                f"**{len(module_classes)} classes**"
            )
            lines.append("")

            if module_classes:
                lines.append("**Classes:**")
                for cls in module_classes:
                    methods = cls.properties.get("methods", 0)
                    bases = cls.properties.get("base_classes", "")
                    base_str = f" extends `{bases}`" if bases else ""
                    lines.append(
                        f"- `{cls.label}`{base_str} "
                        f"— {methods} methods"
                    )
                lines.append("")

        return "\n".join(lines)

    def generate_learning_path(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        modules = graph.nodes_by_type(NodeType.MODULE)
        classes = graph.nodes_by_type(NodeType.CLASS)
        abstract_classes = [
            c for c in classes
            if str(c.properties.get("is_abstract", False)) == "True"
        ]

        lines = [
            f"# Learning Path — {repo_name}",
            "",
            "A structured path to understand this codebase "
            "from first principles.",
            "",
            "---",
            "",
            "## Phase 1 — Understand the Structure (Day 1)",
            "",
            "Before reading any code, understand what each module does.",
            "",
        ]

        for i, module in enumerate(modules, 1):
            lines.append(
                f"{i}. **`{module.label}`** — "
                "read the README or __init__.py first"
            )

        lines += [
            "",
            "## Phase 2 — Read the Domain Layer (Day 2-3)",
            "",
            "The domain layer contains the core business objects. "
            "Start here — nothing depends on frameworks.",
            "",
        ]

        domain_classes = [
            c for c in classes
            if "domain" in str(c.properties.get("file", ""))
        ]
        for cls in domain_classes:
            file_path = cls.properties.get("file", "")
            lines.append(f"- **`{cls.label}`** — `{file_path}`")

        lines += [
            "",
            "## Phase 3 — Application Layer (Day 4-5)",
            "",
            "The application layer contains use cases and services. "
            "This is where business logic lives.",
            "",
        ]

        app_classes = [
            c for c in classes
            if "application" in str(c.properties.get("file", ""))
            or "use_case" in str(c.properties.get("file", ""))
        ]
        for cls in app_classes:
            file_path = cls.properties.get("file", "")
            lines.append(f"- **`{cls.label}`** — `{file_path}`")

        lines += [
            "",
            "## Phase 4 — Infrastructure (Day 6-7)",
            "",
            "The infrastructure layer connects to databases, "
            "APIs, and external services.",
            "",
        ]

        infra_classes = [
            c for c in classes
            if "infrastructure" in str(c.properties.get("file", ""))
        ]
        for cls in infra_classes:
            file_path = cls.properties.get("file", "")
            lines.append(f"- **`{cls.label}`** — `{file_path}`")

        if abstract_classes:
            lines += [
                "",
                "## Key Abstractions to Understand",
                "",
                "These abstract classes define the system's contracts. "
                "Understanding them unlocks the whole codebase.",
                "",
            ]
            for cls in abstract_classes:
                lines.append(f"- **`{cls.label}`**")

        return "\n".join(lines)

    def generate_interview_questions(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        modules = graph.nodes_by_type(NodeType.MODULE)
        classes = graph.nodes_by_type(NodeType.CLASS)
        abstract_classes = [
            c for c in classes
            if str(c.properties.get("is_abstract", False)) == "True"
        ]

        module_names = [m.label for m in modules]
        module_list = ", ".join(f"`{m}`" for m in module_names[:4])

        lines = [
            f"# Interview Preparation — {repo_name}",
            "",
            "10 technical questions about this specific codebase. "
            "Answer using actual class and method names — "
            "not generic descriptions.",
            "",
            "---",
            "",
        ]

        questions = [
            (
                "Architecture Overview",
                f"Walk me through the high-level architecture of "
                f"`{repo_name}`. What are the main modules "
                f"({module_list}) and what does each one do?",
            ),
            (
                "Clean Architecture",
                "Explain the four-layer architecture used in this "
                "codebase: domain, application, infrastructure, "
                "and presentation. Why is the domain layer isolated "
                "from everything else?",
            ),
            (
                "Abstract Classes",
                f"This codebase has {len(abstract_classes)} abstract "
                "classes. Name them, explain what each one contracts, "
                "and explain why they exist instead of concrete classes.",
            ),
            (
                "Dependency Injection",
                "How are dependencies injected in this project? "
                "Give a specific example tracing from the router "
                "through the service to the repository.",
            ),
            (
                "Data Flow",
                "Trace the complete flow of a POST request from "
                "the moment it hits the API endpoint to when the "
                "response is returned. Name every class involved.",
            ),
            (
                "Error Handling",
                "Describe the exception hierarchy in this codebase. "
                "Where are exceptions raised, where are they caught, "
                "and how do they map to HTTP status codes?",
            ),
            (
                "Repository Pattern",
                "Why does this codebase use the repository pattern? "
                "What would need to change to swap the in-memory "
                "store for a PostgreSQL database?",
            ),
            (
                "Testing Strategy",
                "How would you unit test the service layer? "
                "What would you mock, what would you assert, "
                "and why is the architecture easy to test?",
            ),
            (
                "Design Decisions",
                f"What is the most important architectural decision "
                f"in `{repo_name}` and what tradeoffs does it involve?",
            ),
            (
                "Scaling",
                f"This system currently uses in-memory storage. "
                f"Walk me through the changes needed to make it "
                f"production-ready with PostgreSQL, Redis caching, "
                f"and async Celery workers.",
            ),
        ]

        for i, (category, question) in enumerate(questions, 1):
            lines += [
                f"## Q{i}: {category}",
                "",
                question,
                "",
                "> **Tip:** Use specific class names from the "
                "codebase in your answer.",
                "",
            ]

        return "\n".join(lines)

    def generate_api_spec(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        functions = graph.nodes_by_type(NodeType.FUNCTION)
        router_fns = [
            f for f in functions
            if "router" in str(f.properties.get("file", ""))
            or "controller" in str(
                f.properties.get("file", "")
            ).lower()
        ]

        lines = [
            f"# API Specification — {repo_name}",
            "",
            "Auto-generated from router and controller files.",
            "",
        ]

        if not router_fns:
            lines.append(
                "_No router files detected in this repository._"
            )
            return "\n".join(lines)

        lines += [
            "## Endpoints",
            "",
            "| Endpoint | Parameters | File |",
            "|----------|------------|------|",
        ]

        for fn in router_fns:
            params = fn.properties.get("parameters", "—")
            file_path = str(
                fn.properties.get("file", "")
            ).split("/")[-1]
            lines.append(
                f"| `{fn.label}` | `{params}` | `{file_path}` |"
            )

        return "\n".join(lines)