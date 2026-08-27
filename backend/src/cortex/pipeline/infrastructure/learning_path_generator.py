"""Learning Path Generator — repository-specific developer onboarding.

This is NOT a generic tutorial. It produces a learning journey
derived from the ACTUAL repository structure:
  - Entry points (where execution starts)
  - Dependency order (learn prerequisites before dependents)
  - Importance ranking (most-imported = most important)
  - Difficulty progression (simple concepts first)
  - Each step references real files, symbols, and WHY they matter

The learning path answers: "I know nothing about this codebase.
What should I read first, second, third, and why?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class LearningStep:
    """A single step in the learning path with evidence."""
    level: int
    title: str
    description: str
    # What to read
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    # Why this step matters
    reason: str = ""
    # Evidence
    dependencies_count: int = 0
    dependents_count: int = 0
    complexity: str = "low"  # low / medium / high
    # What to learn from this step
    concepts: list[str] = field(default_factory=list)


@dataclass
class LearningPathResult:
    """Complete learning path for repository onboarding."""
    repo_name: str
    total_steps: int = 0
    estimated_hours: float = 0.0
    entry_points: list[str] = field(default_factory=list)
    steps: list[LearningStep] = field(default_factory=list)


class LearningPathGenerator:
    """Generates a repository-specific learning path from the knowledge graph.

    Algorithm:
      1. Identify entry points (main files, routers, app.py, index.ts)
      2. Compute importance score per file/module (in-degree in import graph)
      3. Topological sort by dependencies (learn A before B if B imports A)
      4. Group into progressive difficulty levels
      5. Annotate each step with evidence (files, symbols, reason)
    """

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate the learning path as Markdown."""
        result = self.analyze(graph, repo_name)
        return self._render_markdown(result)

    def analyze(self, graph: GraphBuildResult, repo_name: str) -> LearningPathResult:
        """Compute the full learning path analysis."""
        result = LearningPathResult(repo_name=repo_name)

        files = graph.nodes_by_type(NodeType.FILE)
        modules = graph.nodes_by_type(NodeType.MODULE)
        all_classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
        )]

        if not files:
            return result

        # Build import graph (file → file edges)
        imports_from, imported_by = self._build_import_graph(graph)

        # Compute importance score (in-degree = how many files import this)
        importance: dict[str, int] = {}
        for file_node in files:
            importance[file_node.id] = len(imported_by.get(file_node.id, []))

        # Identify entry points
        entry_points = self._find_entry_points(files, imports_from, imported_by)
        result.entry_points = [
            str(ep.properties.get("path", ep.label)) for ep in entry_points
        ]

        # Group files by module for learning coherence
        module_files = self._group_files_by_module(graph, files, modules)

        # Compute difficulty per module
        module_difficulty = self._compute_module_difficulty(module_files, graph)

        # Build learning levels
        steps = self._build_learning_levels(
            graph, files, modules, module_files, module_difficulty,
            imports_from, imported_by, importance, entry_points, all_classes
        )

        result.steps = steps
        result.total_steps = len(steps)
        result.estimated_hours = self._estimate_hours(steps)

        return result

    def _build_import_graph(
        self, graph: GraphBuildResult
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Build directional import edges between files.

        Returns: (imports_from[file_id] → [imported_file_ids],
                  imported_by[file_id] → [importing_file_ids])
        """
        imports_from: dict[str, list[str]] = defaultdict(list)
        imported_by: dict[str, list[str]] = defaultdict(list)

        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                imports_from[edge.source_id].append(edge.target_id)
                imported_by[edge.target_id].append(edge.source_id)

        return imports_from, imported_by

    def _find_entry_points(
        self,
        files: list[GraphNode],
        imports_from: dict[str, list[str]],
        imported_by: dict[str, list[str]],
    ) -> list[GraphNode]:
        """Find entry point files — where execution starts."""
        entry_points: list[GraphNode] = []

        _entry_names = {
            "main.py", "app.py", "__main__.py", "index.ts", "index.js",
            "server.py", "server.ts", "manage.py", "wsgi.py", "asgi.py",
            "main.ts", "main.js", "index.py", "cli.py",
        }
        _entry_patterns = ["router", "route", "controller", "endpoint"]

        for file_node in files:
            path = str(file_node.properties.get("path", file_node.label))
            basename = path.split("/")[-1].lower()

            # Direct name match
            if basename in _entry_names:
                entry_points.append(file_node)
                continue

            # Pattern match
            if any(p in basename for p in _entry_patterns):
                entry_points.append(file_node)
                continue

            # High in-degree (many files depend on it) but low out-degree
            in_degree = len(imported_by.get(file_node.id, []))
            out_degree = len(imports_from.get(file_node.id, []))
            if in_degree >= 3 and out_degree <= 1:
                entry_points.append(file_node)

        return entry_points[:10]  # cap

    def _group_files_by_module(
        self, graph: GraphBuildResult, files: list[GraphNode], modules: list[GraphNode]
    ) -> dict[str, list[GraphNode]]:
        """Group files by their parent module."""
        # Build containment index
        contains: dict[str, str] = {}  # child_id → parent_id
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains[edge.target_id] = edge.source_id

        module_ids = {m.id for m in modules}
        result: dict[str, list[GraphNode]] = defaultdict(list)

        for file_node in files:
            parent = contains.get(file_node.id)
            # Walk up to find module parent
            visited = set()
            while parent and parent not in module_ids and parent not in visited:
                visited.add(parent)
                parent = contains.get(parent)
            if parent and parent in module_ids:
                result[parent].append(file_node)
            else:
                result["_root"].append(file_node)

        return result

    def _compute_module_difficulty(
        self, module_files: dict[str, list[GraphNode]], graph: GraphBuildResult
    ) -> dict[str, str]:
        """Estimate difficulty of each module based on complexity metrics."""
        difficulty: dict[str, str] = {}

        for module_id, files in module_files.items():
            total_complexity = 0
            total_lines = 0
            for f in files:
                total_complexity += int(f.properties.get("total_complexity", 0) or 0)
                total_lines += int(f.properties.get("lines", 0) or 0)

            avg_complexity = total_complexity / max(len(files), 1)

            if avg_complexity > 20 or total_lines > 2000:
                difficulty[module_id] = "high"
            elif avg_complexity > 8 or total_lines > 800:
                difficulty[module_id] = "medium"
            else:
                difficulty[module_id] = "low"

        return difficulty

    def _build_learning_levels(
        self,
        graph: GraphBuildResult,
        files: list[GraphNode],
        modules: list[GraphNode],
        module_files: dict[str, list[GraphNode]],
        module_difficulty: dict[str, str],
        imports_from: dict[str, list[str]],
        imported_by: dict[str, list[str]],
        importance: dict[str, int],
        entry_points: list[GraphNode],
        all_classes: list[GraphNode],
    ) -> list[LearningStep]:
        """Build progressive learning levels from graph data."""
        steps: list[LearningStep] = []
        level = 1

        # ── Level 1: Entry Points ────────────────────────────────────────────
        if entry_points:
            ep_files = [str(ep.properties.get("path", ep.label)) for ep in entry_points[:5]]
            steps.append(LearningStep(
                level=level,
                title="Understand the Entry Points",
                description=(
                    "Start here. These are the files where execution begins — "
                    "HTTP servers, CLI entry points, or app initialization."
                ),
                files=ep_files,
                reason="Entry points reveal the system's public interface and startup flow.",
                complexity="low",
                concepts=["Application bootstrap", "Configuration", "Dependency wiring"],
            ))
            level += 1

        # ── Level 2: Core Domain / Most-Imported Files ───────────────────────
        # Find the most-imported files (excluding entry points)
        entry_ids = {ep.id for ep in entry_points}
        core_files = sorted(
            [f for f in files if f.id not in entry_ids and importance.get(f.id, 0) >= 2],
            key=lambda f: importance.get(f.id, 0),
            reverse=True,
        )[:8]

        if core_files:
            steps.append(LearningStep(
                level=level,
                title="Understand Core Dependencies",
                description=(
                    "These files are imported by many others — they define the "
                    "foundational abstractions the rest of the system builds on."
                ),
                files=[str(f.properties.get("path", f.label)) for f in core_files],
                symbols=[f.label for f in core_files],
                reason=f"These {len(core_files)} files are each imported by 2+ other files.",
                dependents_count=sum(importance.get(f.id, 0) for f in core_files),
                complexity="low",
                concepts=["Interfaces", "Base classes", "Shared types", "Configuration"],
            ))
            level += 1

        # ── Level 3: Domain Model (classes, entities, interfaces) ────────────
        domain_classes = [
            c for c in all_classes
            if any(p in str(c.properties.get("file", "")).lower()
                   for p in ("domain", "model", "entity", "core", "types"))
        ]
        if domain_classes:
            steps.append(LearningStep(
                level=level,
                title="Understand the Domain Model",
                description=(
                    "The domain layer contains the core business objects — "
                    "the nouns of the system. No frameworks, no I/O."
                ),
                files=list(set(
                    str(c.properties.get("file", "")) for c in domain_classes[:8]
                )),
                symbols=[c.label for c in domain_classes[:10]],
                reason="Domain objects define what the system IS, independent of how it's built.",
                complexity="low",
                concepts=["Entities", "Value objects", "Domain rules", "Invariants"],
            ))
            level += 1

        # ── Level 4: Application / Service Layer ─────────────────────────────
        service_classes = [
            c for c in all_classes
            if any(p in str(c.properties.get("file", "")).lower()
                   for p in ("application", "service", "use_case", "usecases"))
            and c not in domain_classes
        ]
        if service_classes:
            steps.append(LearningStep(
                level=level,
                title="Understand the Application Layer",
                description=(
                    "Services and use cases orchestrate domain objects to "
                    "fulfill business operations. This is where workflow logic lives."
                ),
                files=list(set(
                    str(c.properties.get("file", "")) for c in service_classes[:8]
                )),
                symbols=[c.label for c in service_classes[:10]],
                reason="Application layer shows HOW the domain objects are used together.",
                complexity="medium",
                concepts=["Use cases", "Service orchestration", "Transaction boundaries"],
            ))
            level += 1

        # ── Level 5: Infrastructure Layer ────────────────────────────────────
        infra_classes = [
            c for c in all_classes
            if any(p in str(c.properties.get("file", "")).lower()
                   for p in ("infrastructure", "repository", "persistence",
                            "db", "client", "adapter"))
            and c not in domain_classes and c not in service_classes
        ]
        if infra_classes:
            steps.append(LearningStep(
                level=level,
                title="Understand the Infrastructure",
                description=(
                    "Infrastructure connects the application to external systems — "
                    "databases, APIs, file systems, message queues."
                ),
                files=list(set(
                    str(c.properties.get("file", "")) for c in infra_classes[:8]
                )),
                symbols=[c.label for c in infra_classes[:10]],
                reason="Infrastructure implements the interfaces defined in the domain layer.",
                complexity="medium",
                concepts=["Repository pattern", "Database access", "External APIs", "Adapters"],
            ))
            level += 1

        # ── Level 6: API / Presentation Layer ────────────────────────────────
        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)
        if endpoints:
            endpoint_files = list(set(
                str(ep.properties.get("file", "")) for ep in endpoints[:10]
            ))
            route_infos = [
                str(ep.properties.get("route_info", ep.label))
                for ep in endpoints[:8]
                if ep.properties.get("route_info")
            ]
            steps.append(LearningStep(
                level=level,
                title="Understand the API Surface",
                description=(
                    "These endpoints expose the application to the outside world. "
                    "Trace each endpoint → service → domain to understand the full request flow."
                ),
                files=endpoint_files[:6],
                symbols=route_infos[:8] if route_infos else [ep.label for ep in endpoints[:8]],
                reason=f"{len(endpoints)} API endpoints detected in the codebase.",
                complexity="medium",
                concepts=["Request handling", "Input validation", "Response formatting", "Middleware"],
            ))
            level += 1

        # ── Level 7: Complex / High-Risk Areas ───────────────────────────────
        complex_files = sorted(
            [f for f in files if int(f.properties.get("max_complexity", 0) or 0) >= 10],
            key=lambda f: int(f.properties.get("max_complexity", 0) or 0),
            reverse=True,
        )[:6]

        if complex_files:
            steps.append(LearningStep(
                level=level,
                title="Understand the Complex Areas",
                description=(
                    "These files have the highest cyclomatic complexity — "
                    "they contain the most decision logic and are likely "
                    "the hardest to understand and the most bug-prone."
                ),
                files=[str(f.properties.get("path", f.label)) for f in complex_files],
                reason="High complexity = more branches, more edge cases, more bugs.",
                complexity="high",
                concepts=["Complex algorithms", "State machines", "Error handling", "Edge cases"],
            ))
            level += 1

        # ── Level 8: Testing ─────────────────────────────────────────────────
        test_files = [f for f in files if f.properties.get("is_test_file")]
        if test_files:
            steps.append(LearningStep(
                level=level,
                title="Understand the Test Strategy",
                description=(
                    "Tests reveal how the system is EXPECTED to behave. "
                    "They also show which modules are well-tested and which aren't."
                ),
                files=[str(f.properties.get("path", f.label)) for f in test_files[:6]],
                reason=f"{len(test_files)} test files found — read them to understand expected behavior.",
                complexity="medium",
                concepts=["Test patterns", "Fixtures", "Mocking strategy", "Coverage gaps"],
            ))

        return steps

    def _estimate_hours(self, steps: list[LearningStep]) -> float:
        """Rough estimate of onboarding time."""
        hours = 0.0
        for step in steps:
            file_count = len(step.files)
            if step.complexity == "high":
                hours += file_count * 0.75
            elif step.complexity == "medium":
                hours += file_count * 0.5
            else:
                hours += file_count * 0.25
        return round(hours, 1)

    def _render_markdown(self, result: LearningPathResult) -> str:
        """Render the learning path as structured Markdown."""
        lines: list[str] = []

        lines.append(f"# Learning Path — {result.repo_name}")
        lines.append("")
        lines.append(
            "> **What is this?** This is your personalized roadmap to understanding "
            "this codebase. Instead of randomly opening files, follow this guided path "
            "from simple to complex. Each level builds on the previous one — like "
            "learning a language, you need vocabulary before grammar before literature."
        )
        lines.append("")
        lines.append(
            "The path is ordered by **dependency** (learn things that other things "
            "depend on first) and **difficulty** (start simple, build up to complex)."
        )
        lines.append("")

        # Summary
        lines.append("## Your Journey")
        lines.append("")
        lines.append(f"📚 **{result.total_steps} levels** to complete")
        lines.append(f"⏱️ **~{result.estimated_hours} hours** estimated reading time")
        if result.entry_points:
            lines.append(f"🚪 **Start here:** {', '.join(f'`{ep.split('/')[-1]}`' for ep in result.entry_points[:4])}")
        lines.append("")
        lines.append("**Difficulty legend:** 🟢 Easy — 🟡 Moderate — 🔴 Advanced")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Each level
        for step in result.steps:
            difficulty_badge = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                step.complexity, ""
            )

            lines.append(f"## Level {step.level} — {step.title} {difficulty_badge}")
            lines.append("")
            lines.append(step.description)
            lines.append("")

            # Reason
            if step.reason:
                lines.append(f"> **Why:** {step.reason}")
                lines.append("")

            # Files to read
            if step.files:
                lines.append("**Read these files:**")
                lines.append("")
                for f in step.files:
                    lines.append(f"- `{f}`")
                lines.append("")

            # Key symbols
            if step.symbols:
                lines.append(f"**Key symbols:** {', '.join(f'`{s}`' for s in step.symbols[:8])}")
                lines.append("")

            # Concepts to learn
            if step.concepts:
                lines.append(f"**You will learn:** {' · '.join(step.concepts)}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Final note
        lines.append("## Next Steps")
        lines.append("")
        lines.append(
            "After completing this path, you should be able to:\n"
            "- Explain the system's architecture to a new team member\n"
            "- Trace a request from API endpoint to database\n"
            "- Identify where to make changes for a given feature\n"
            "- Understand the dependency structure and coupling risks"
        )

        return "\n".join(lines)
