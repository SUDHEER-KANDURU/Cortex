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
        lines = ["graph TD"]
    
        lines.append("  classDef repo fill:#7C3AED,stroke:#5B21B6,color:#fff")
        lines.append("  classDef module fill:#1D4ED8,stroke:#1E40AF,color:#fff")
        lines.append("  classDef cls fill:#065F46,stroke:#064E3B,color:#fff")

        repo_nodes = graph.nodes_by_type(NodeType.REPOSITORY)
        all_modules = graph.nodes_by_type(NodeType.MODULE)
        classes = graph.nodes_by_type(NodeType.CLASS)

        # Skip generic container modules
        skip_labels = {"main/", "test/", "src/", "java/"}
        good_modules = [
            m for m in all_modules
            if m.label not in skip_labels
        ][:8]

        if not good_modules:
            good_modules = all_modules[:8]

        # Repo node
        repo_id = "REPO"
        if repo_nodes:
            lines.append(f'  {repo_id}["{repo_nodes[0].label}"]:::repo')
        else:
            lines.append(f'  {repo_id}["{repo_name}"]:::repo')

        # One unique ID per module — never reuse
        module_id_map: dict[str, str] = {}
        for i, module in enumerate(good_modules):
            mid = f"MOD{i}"
            module_id_map[module.id] = mid
            path = str(module.properties.get("path", ""))
            parts = [p for p in path.split("/") if p]
            label = parts[-1] if parts else module.label.rstrip("/")
            lines.append(f'  {mid}["{label}/"]:::module')
            # One arrow from repo to this module
            lines.append(f"  {repo_id} --> {mid}")

        # Classes — connect to best matching module
        important_classes = sorted(
            classes,
            key=lambda c: int(str(c.properties.get("methods", 0))),
            reverse=True,
        )[:10]

        for i, cls in enumerate(important_classes):
            cid = f"CLS{i}"
            file_path = str(cls.properties.get("file", ""))
            lines.append(f'  {cid}["{cls.label}"]:::cls')

            best_mid = None
            best_len = 0
            for module in good_modules:
                mpath = str(module.properties.get("path", ""))
                if file_path.startswith(mpath) and len(mpath) > best_len:
                    best_mid = module_id_map[module.id]
                    best_len = len(mpath)

            if best_mid:
                lines.append(f"  {best_mid} --> {cid}")
            else:
                lines.append(f"  {repo_id} --> {cid}")

        return "\n".join(lines)

    def _safe_id(self, raw_id: str) -> str:
        """Convert a node ID to a Mermaid-safe identifier."""
        clean = (
            raw_id
            .replace("-", "_")
            .replace(".", "_")
            .replace("/", "_")
            .replace(" ", "_")
        )
        if clean and not clean[0].isalpha():
            clean = "n_" + clean
        return clean[:24]


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

    def generate_database_schema(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Fix 6 — generate a database schema report from class/model nodes."""
        classes = graph.nodes_by_type(NodeType.CLASS)
        model_classes = [
            c for c in classes
            if any(
                keyword in str(c.properties.get("file", "")).lower()
                for keyword in ("model", "schema", "entity", "table", "orm")
            )
            or any(
                keyword in c.label.lower()
                for keyword in ("model", "entity", "schema", "record")
            )
        ]

        lines = [
            f"# Database Schema — {repo_name}",
            "",
            "Auto-generated from ORM model and entity files.",
            "",
        ]

        if not model_classes:
            # Fall back to all classes if no model-specific ones found
            model_classes = classes[:20]
            lines.append(
                "> _No dedicated model files detected — showing all classes._\n"
            )

        lines += [
            "## Tables / Entities",
            "",
        ]

        for cls in model_classes:
            file_path = str(cls.properties.get("file", "unknown"))
            methods = cls.properties.get("methods", 0)
            bases = cls.properties.get("base_classes", "")
            base_str = f" extends `{bases}`" if bases else ""
            lines += [
                f"### `{cls.label}`{base_str}",
                "",
                f"- **File:** `{file_path}`",
                f"- **Methods:** {methods}",
                "",
            ]

        lines += [
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total entities | {len(model_classes)} |",
            f"| Total graph nodes | {graph.node_count()} |",
            f"| Total graph edges | {graph.edge_count()} |",
        ]

        return "\n".join(lines)
