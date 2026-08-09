"""Artifact generator — produces high quality artifacts from graph data.
Each generator takes a GraphBuildResult and produces formatted content."""

from dataclasses import dataclass
from cortex.graph.domain.entities import NodeType, RelationshipType, GraphNode
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


class GraphInterviewQuestionGenerator:
    """Generates interview questions derived directly from the knowledge graph.

    Instead of a fixed generic template, this walks the actual graph structure —
    god classes (highest method count), high fan-out/fan-in nodes, deep or
    multiple inheritance chains, and detected import cycles — and turns each
    real finding into a targeted question that names actual classes and files.
    """

    GOD_CLASS_METHOD_THRESHOLD = 8
    HIGH_FANOUT_THRESHOLD = 3

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        classes = graph.nodes_by_type(NodeType.CLASS)
        files = graph.nodes_by_type(NodeType.FILE)
        functions = graph.nodes_by_type(NodeType.FUNCTION)
        modules = graph.nodes_by_type(NodeType.MODULE)

        fan_out = self._count_fan_out(graph)
        fan_in = self._count_fan_in(graph)
        inheritance_depth = self._compute_inheritance_depth(graph, classes)
        cycles = self._find_import_cycles(graph, files)

        lines = [
            f"# Interview Preparation — {repo_name}",
            "",
            "Questions generated directly from this repository's knowledge graph — "
            "real class names, real coupling, real inheritance chains — not generic "
            "descriptions.",
            "",
            "---",
            "",
        ]

        q_num = 1

        # 1 — God classes (highest method count)
        god_classes = sorted(
            classes,
            key=lambda c: int(c.properties.get("methods", 0) or 0),
            reverse=True,
        )
        god_classes = [
            c for c in god_classes
            if int(c.properties.get("methods", 0) or 0) >= self.GOD_CLASS_METHOD_THRESHOLD
        ][:3]

        if god_classes:
            top = god_classes[0]
            methods = top.properties.get("methods", 0)
            file_path = top.properties.get("file", "unknown")
            others = ", ".join(
                f"`{c.label}` ({c.properties.get('methods', 0)} methods)"
                for c in god_classes[1:]
            )
            suffix = f", followed by {others}" if others else ""
            lines += self._question(
                q_num,
                "God Class",
                f"`{top.label}` in `{file_path}` has {methods} methods — the most of any "
                f"class in this codebase{suffix}. Walk through what responsibilities this "
                "class currently owns, and propose a concrete split (name the new classes "
                "and which methods move where).",
            )
        else:
            lines += self._question(
                q_num,
                "Class Design",
                f"No class in `{repo_name}` exceeds {self.GOD_CLASS_METHOD_THRESHOLD} "
                "methods — what design convention in this codebase seems to be keeping "
                "classes small?",
            )
        q_num += 1

        # 2 — High fan-out file
        file_fanout = sorted(
            ((f, fan_out.get(f.id, 0)) for f in files),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if file_fanout and file_fanout[0][1] >= self.HIGH_FANOUT_THRESHOLD:
            f_node, count = file_fanout[0]
            lines += self._question(
                q_num,
                "Coupling & Fan-Out",
                f"`{f_node.properties.get('path', f_node.label)}` imports from {count} "
                "other modules — the highest fan-out in the repo. Why might this file "
                "depend on so much, and what would you extract to reduce that number?",
            )
            q_num += 1

        # 3 — High fan-in node ("core" abstraction everyone depends on)
        node_fanin = sorted(
            (
                (n, fan_in.get(n.id, 0))
                for n in graph.nodes
                if n.node_type in (NodeType.CLASS, NodeType.FILE)
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if node_fanin and node_fanin[0][1] >= self.HIGH_FANOUT_THRESHOLD:
            n_node, count = node_fanin[0]
            kind = "class" if n_node.node_type == NodeType.CLASS else "file"
            lines += self._question(
                q_num,
                "Core Abstraction",
                f"`{n_node.label}` is depended on by {count} other nodes in the graph — "
                f"the most relied-upon {kind} in the codebase. What would break first if "
                "you changed its public interface, and how would you introduce that "
                "change safely?",
            )
            q_num += 1

        # 4 — Deep inheritance chain
        deep = sorted(inheritance_depth.items(), key=lambda kv: kv[1], reverse=True)
        if deep and deep[0][1] >= 2:
            cls_id, depth = deep[0]
            cls_node = next((c for c in classes if c.id == cls_id), None)
            if cls_node:
                lines += self._question(
                    q_num,
                    "Inheritance Depth",
                    f"`{cls_node.label}` sits {depth} levels deep in an inheritance chain "
                    f"(base: `{cls_node.properties.get('base_classes', '')}`). Trace the "
                    "full chain from this class to its root base — what does each level "
                    "add, and would composition work better than inheritance here?",
                )
                q_num += 1

        # 5 — Multiple inheritance
        multi_base = [
            c for c in classes
            if len([b for b in str(c.properties.get("base_classes", "")).split(",") if b.strip()]) > 1
        ]
        if multi_base:
            c = multi_base[0]
            lines += self._question(
                q_num,
                "Multiple Inheritance",
                f"`{c.label}` inherits from multiple base classes "
                f"(`{c.properties.get('base_classes', '')}`). Explain the method "
                "resolution order Python would use here, and any diamond-inheritance "
                "risk this creates.",
            )
            q_num += 1

        # 6 — Circular dependencies (or their absence)
        if cycles:
            cycle_str = " → ".join(f"`{c}`" for c in cycles[0])
            lines += self._question(
                q_num,
                "Circular Dependencies",
                f"There's an import cycle in this codebase: {cycle_str}. How did this "
                "likely happen, and what's your plan to break the cycle without a large "
                "rewrite?",
            )
        else:
            lines += self._question(
                q_num,
                "Dependency Direction",
                f"`{repo_name}` has no detected circular imports among its files. What "
                "convention (layering, dependency direction) is likely enforcing that, "
                "and where in the codebase is it most visible?",
            )
        q_num += 1

        # 7 — Largest file
        big_files = sorted(
            files,
            key=lambda f: int(f.properties.get("lines", 0) or 0),
            reverse=True,
        )
        if big_files:
            f_node = big_files[0]
            lines_count = f_node.properties.get("lines", 0)
            classes_in_file = f_node.properties.get("classes", 0)
            functions_in_file = f_node.properties.get("functions", 0)
            lines += self._question(
                q_num,
                "Largest File",
                f"`{f_node.properties.get('path', f_node.label)}` is the largest file in "
                f"the repo at {lines_count} lines ({classes_in_file} classes, "
                f"{functions_in_file} functions). Would you split this file? If so, "
                "along what boundary?",
            )
            q_num += 1

        # 8 — Testing strategy, tied to the riskiest node found so far
        risk_target = god_classes[0] if god_classes else (big_files[0] if big_files else None)
        if risk_target is not None:
            if risk_target.node_type == NodeType.CLASS:
                target_file = risk_target.properties.get("file", "")
                lines += self._question(
                    q_num,
                    "Testing Strategy",
                    f"How would you write unit tests for `{risk_target.label}` in "
                    f"`{target_file}`? Name what you'd mock, what you'd assert, and "
                    "where you'd start given its current size and dependencies.",
                )
            else:
                target_path = risk_target.properties.get("path", risk_target.label)
                lines += self._question(
                    q_num,
                    "Testing Strategy",
                    f"How would you write tests for `{target_path}`? Name what you'd "
                    "mock, what you'd assert, and where you'd start given its current "
                    "size and dependencies.",
                )
            q_num += 1

        # 9 — Function with the most parameters
        complex_fns = sorted(
            functions,
            key=lambda fn: len(
                [p for p in str(fn.properties.get("parameters", "")).split(",") if p.strip()]
            ),
            reverse=True,
        )
        if complex_fns:
            fn = complex_fns[0]
            param_count = len(
                [p for p in str(fn.properties.get("parameters", "")).split(",") if p.strip()]
            )
            if param_count >= 4:
                lines += self._question(
                    q_num,
                    "Function Signature Complexity",
                    f"`{fn.label}` in `{fn.properties.get('file', 'unknown')}` takes "
                    f"{param_count} parameters (`{fn.properties.get('parameters', '')}`). "
                    "What would you group into a parameter object or config class, and why?",
                )
                q_num += 1

        # 10 — Busiest module (most files)
        if modules:
            module_file_counts: dict[str, int] = {}
            for edge in graph.edges:
                if edge.relationship != RelationshipType.CONTAINS:
                    continue
                src = self._node_by_id(graph, edge.source_id)
                tgt = self._node_by_id(graph, edge.target_id)
                if src and tgt and src.node_type == NodeType.MODULE and tgt.node_type == NodeType.FILE:
                    module_file_counts[src.id] = module_file_counts.get(src.id, 0) + 1
            if module_file_counts:
                busiest_id = max(module_file_counts, key=module_file_counts.get)
                busiest = self._node_by_id(graph, busiest_id)
                if busiest:
                    lines += self._question(
                        q_num,
                        "Module Responsibility",
                        f"`{busiest.label}` contains {module_file_counts[busiest_id]} "
                        f"files — the most of any module in `{repo_name}`. What single "
                        "responsibility does this module own, and does every file in it "
                        "actually belong there?",
                    )
                    q_num += 1

        # Final — grounded system overview
        lines += self._question(
            q_num,
            "System Overview",
            f"This graph has {graph.node_count()} nodes and {graph.edge_count()} edges "
            f"across {len(modules)} modules, {len(files)} files, and {len(classes)} "
            f"classes. Give a two-minute walkthrough of `{repo_name}`'s architecture "
            "using only names that appear in this graph.",
        )

        return "\n".join(lines)

    def _question(self, number: int, category: str, question: str) -> list[str]:
        return [
            f"## Q{number}: {category}",
            "",
            question,
            "",
            "> **Tip:** Use the exact names above in your answer — they come directly "
            "from this repository's parsed structure.",
            "",
        ]

    def _count_fan_out(self, graph: GraphBuildResult) -> dict[str, int]:
        counts: dict[str, int] = {}
        for edge in graph.edges:
            if edge.relationship in (
                RelationshipType.IMPORTS,
                RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS,
            ):
                counts[edge.source_id] = counts.get(edge.source_id, 0) + 1
        return counts

    def _count_fan_in(self, graph: GraphBuildResult) -> dict[str, int]:
        counts: dict[str, int] = {}
        for edge in graph.edges:
            if edge.relationship in (
                RelationshipType.IMPORTS,
                RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS,
            ):
                counts[edge.target_id] = counts.get(edge.target_id, 0) + 1
        return counts

    def _compute_inheritance_depth(
        self,
        graph: GraphBuildResult,
        classes: list[GraphNode],
    ) -> dict[str, int]:
        """Depth = number of INHERITS hops from a class to its root base class."""
        child_to_base: dict[str, str] = {}
        for edge in graph.edges:
            if edge.relationship == RelationshipType.INHERITS:
                child_to_base[edge.source_id] = edge.target_id

        depths: dict[str, int] = {}
        for cls in classes:
            depth = 0
            current = cls.id
            visited = {current}
            while current in child_to_base:
                current = child_to_base[current]
                if current in visited:
                    break  # guard against malformed cycles
                visited.add(current)
                depth += 1
            depths[cls.id] = depth
        return depths

    def _find_import_cycles(
        self,
        graph: GraphBuildResult,
        files: list[GraphNode],
    ) -> list[list[str]]:
        """DFS cycle detection over FILE -> FILE IMPORTS edges.
        Returns the first detected cycle as a list of file labels/paths."""
        adjacency: dict[str, list[str]] = {}
        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                adjacency.setdefault(edge.source_id, []).append(edge.target_id)

        file_ids = {f.id for f in files}
        label_by_id = {n.id: n.properties.get("path", n.label) for n in graph.nodes}

        visited: set[str] = set()
        rec_stack: list[str] = []
        cycles: list[list[str]] = []

        def dfs(node_id: str) -> None:
            if cycles:
                return  # first cycle found is enough
            visited.add(node_id)
            rec_stack.append(node_id)
            for neighbor in adjacency.get(node_id, []):
                if neighbor not in file_ids:
                    continue
                if neighbor in rec_stack:
                    cycle_start = rec_stack.index(neighbor)
                    cycle_ids = rec_stack[cycle_start:] + [neighbor]
                    cycles.append([label_by_id.get(cid, cid) for cid in cycle_ids])
                    return
                if neighbor not in visited:
                    dfs(neighbor)
                    if cycles:
                        return
            rec_stack.pop()

        for f in files:
            if f.id not in visited:
                dfs(f.id)
            if cycles:
                break

        return cycles

    def _node_by_id(self, graph: GraphBuildResult, node_id: str) -> GraphNode | None:
        for n in graph.nodes:
            if n.id == node_id:
                return n
        return None


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
        """Interview questions derived from actual graph structure — god
        classes, fan-out/fan-in, inheritance depth, import cycles — rather
        than a fixed generic template. See GraphInterviewQuestionGenerator."""
        return GraphInterviewQuestionGenerator().generate(graph, repo_name)

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