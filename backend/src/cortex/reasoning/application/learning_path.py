"""Learning Path Generator — produces a repository-specific onboarding path.

Uses graph topology (dependency order, centrality, complexity) to determine
what a new developer should learn and in what order.

This is NOT a generic learning path. It is specific to the analyzed repo.
"""

from __future__ import annotations

from collections import defaultdict

import structlog

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.reasoning.domain.entities import (
    LearningDifficulty,
    LearningPath,
    LearningStep,
    RepositoryUnderstanding,
)

logger = structlog.get_logger()


class LearningPathGenerator:
    """Generates a repository-specific learning path from graph intelligence.

    Strategy:
    1. START HERE: Entry points and bootstrapping code
    2. FOUNDATIONS: Most-depended-on modules (high fan-in)
    3. CORE FLOW: Main execution paths (endpoint → service → repo)
    4. IMPORTANT MODULES: Feature modules sorted by significance
    5. ADVANCED AREAS: Complex code and architecture patterns
    6. KNOWN RISKS: Issues, debt, and gotchas
    """

    def generate(
        self,
        understanding: RepositoryUnderstanding,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> LearningPath:
        """Generate a complete learning path from repository understanding."""
        path = LearningPath(repo_name=understanding.repo_name)

        # Build helper indexes
        node_map = {n.id: n for n in nodes}
        edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            edges_to[edge.target_id].append(edge)

        # Calculate centrality (how many things depend on each node)
        centrality: dict[str, int] = defaultdict(int)
        for edge in edges:
            if edge.relationship in (
                RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS, RelationshipType.INHERITS,
            ):
                centrality[edge.target_id] += 1

        step_order = 0

        # ── 1. START HERE ─────────────────────────────────────────────────────
        start_steps = self._generate_start_here(understanding, node_map, step_order)
        path.start_here = start_steps
        step_order += len(start_steps)

        # ── 2. FOUNDATIONS ────────────────────────────────────────────────────
        foundation_steps = self._generate_foundations(
            understanding, node_map, centrality, step_order
        )
        path.foundations = foundation_steps
        step_order += len(foundation_steps)

        # ── 3. CORE FLOW ─────────────────────────────────────────────────────
        core_flow_steps = self._generate_core_flow(understanding, step_order)
        path.core_flow = core_flow_steps
        step_order += len(core_flow_steps)

        # ── 4. IMPORTANT MODULES ──────────────────────────────────────────────
        module_steps = self._generate_module_steps(understanding, step_order)
        path.important_modules = module_steps
        step_order += len(module_steps)

        # ── 5. ADVANCED AREAS ─────────────────────────────────────────────────
        advanced_steps = self._generate_advanced(understanding, node_map, step_order)
        path.advanced_areas = advanced_steps
        step_order += len(advanced_steps)

        # ── 6. KNOWN RISKS ────────────────────────────────────────────────────
        risk_steps = self._generate_risks(understanding, step_order)
        path.known_risks = risk_steps
        step_order += len(risk_steps)

        # Summary
        path.total_steps = step_order
        path.estimated_hours = round(step_order * 0.3, 1)  # ~18 min per step avg

        return path

    def _generate_start_here(
        self,
        understanding: RepositoryUnderstanding,
        node_map: dict[str, GraphNode],
        start_order: int,
    ) -> list[LearningStep]:
        """Generate START HERE steps — the very first things to read."""
        steps: list[LearningStep] = []

        # Entry point file
        if understanding.start_here_file:
            steps.append(LearningStep(
                order=start_order + len(steps),
                title=f"Start with {understanding.start_here}",
                what_to_read=[understanding.start_here_file],
                why=understanding.start_here_reason,
                symbols=[understanding.start_here],
                difficulty=LearningDifficulty.BEGINNER,
                what_to_understand="How the application bootstraps and what components it wires together.",
            ))

        # First endpoint (if any) to understand the public interface
        if understanding.entry_points:
            first_ep = next(
                (ep for ep in understanding.entry_points if ep.kind == "http_endpoint"),
                None,
            )
            if first_ep and first_ep.file_path:
                steps.append(LearningStep(
                    order=start_order + len(steps),
                    title=f"Trace a request: {first_ep.method} {first_ep.route or first_ep.label}",
                    what_to_read=[first_ep.file_path],
                    why="Follow one real request from entry to response to understand the flow.",
                    symbols=[first_ep.label],
                    difficulty=LearningDifficulty.BEGINNER,
                    what_to_understand="How a single request flows through the system layers.",
                ))

        return steps

    def _generate_foundations(
        self,
        understanding: RepositoryUnderstanding,
        node_map: dict[str, GraphNode],
        centrality: dict[str, int],
        start_order: int,
    ) -> list[LearningStep]:
        """Generate FOUNDATIONS steps — most-depended-on code."""
        steps: list[LearningStep] = []

        # Find the most central modules (highest fan-in)
        foundational_modules = [
            m for m in understanding.modules
            if len(m.dependents) >= 2 or m.architecture_role in ("core", "domain")
        ]
        foundational_modules.sort(key=lambda m: len(m.dependents), reverse=True)

        for module in foundational_modules[:3]:
            steps.append(LearningStep(
                order=start_order + len(steps),
                title=f"Understand {module.name} (foundation)",
                what_to_read=[module.path],
                why=(
                    f"Depended on by {len(module.dependents)} other modules. "
                    f"This is foundational code that the rest of the system builds on."
                ),
                symbols=module.key_classes[:3] + module.key_functions[:2],
                prerequisites=[understanding.start_here] if understanding.start_here else [],
                difficulty=LearningDifficulty.INTERMEDIATE,
                what_to_understand=f"The core abstractions in {module.name} and how they're used by dependent modules.",
                module=module.name,
            ))

        return steps

    def _generate_core_flow(
        self,
        understanding: RepositoryUnderstanding,
        start_order: int,
    ) -> list[LearningStep]:
        """Generate CORE FLOW steps — main execution paths."""
        steps: list[LearningStep] = []

        for flow in understanding.data_flows[:3]:
            files = list(dict.fromkeys(  # deduplicate while preserving order
                step.file_path for step in flow.steps if step.file_path
            ))
            symbols = [step.symbol for step in flow.steps]

            if files:
                steps.append(LearningStep(
                    order=start_order + len(steps),
                    title=f"Trace flow: {flow.name}",
                    what_to_read=files[:4],
                    why=f"This execution path shows how data moves from {flow.entry_point} through the system.",
                    symbols=symbols[:5],
                    difficulty=LearningDifficulty.INTERMEDIATE,
                    what_to_understand="How the request is handled at each layer and how data transforms along the way.",
                ))

        return steps

    def _generate_module_steps(
        self,
        understanding: RepositoryUnderstanding,
        start_order: int,
    ) -> list[LearningStep]:
        """Generate IMPORTANT MODULES steps — feature modules by significance."""
        steps: list[LearningStep] = []

        # Skip modules already covered in foundations
        foundation_names = {
            m.name for m in understanding.modules
            if len(m.dependents) >= 2 or m.architecture_role in ("core", "domain")
        }

        important_modules = [
            m for m in understanding.modules
            if m.name not in foundation_names
            and m.architecture_role not in ("testing", "configuration")
            and m.file_count >= 2
        ]

        for module in important_modules[:5]:
            difficulty = LearningDifficulty.INTERMEDIATE
            if module.max_complexity > 15 or module.is_god_module:
                difficulty = LearningDifficulty.ADVANCED

            role_desc = f" ({module.architecture_role})" if module.architecture_role else ""
            steps.append(LearningStep(
                order=start_order + len(steps),
                title=f"Explore {module.name}{role_desc}",
                what_to_read=[module.path],
                why=(
                    f"{module.file_count} files, {module.class_count} classes. "
                    f"Dependencies: {', '.join(module.dependencies[:3]) or 'none'}."
                ),
                symbols=module.key_classes[:3],
                prerequisites=[],
                difficulty=difficulty,
                what_to_understand=f"What {module.name} is responsible for and how it interacts with its dependencies.",
                module=module.name,
                estimated_minutes=max(10, module.file_count * 5),
            ))

        return steps

    def _generate_advanced(
        self,
        understanding: RepositoryUnderstanding,
        node_map: dict[str, GraphNode],
        start_order: int,
    ) -> list[LearningStep]:
        """Generate ADVANCED steps — complex areas and patterns."""
        steps: list[LearningStep] = []

        # Complexity hotspots
        if understanding.complexity_hotspots:
            hotspot_files = list(dict.fromkeys(
                h["file"] for h in understanding.complexity_hotspots if h.get("file")
            ))
            hotspot_symbols = [h["symbol"] for h in understanding.complexity_hotspots]

            if hotspot_files:
                steps.append(LearningStep(
                    order=start_order + len(steps),
                    title="Study complexity hotspots",
                    what_to_read=hotspot_files[:3],
                    why=(
                        "These are the most complex functions in the codebase. "
                        "Understanding them is key to safe modifications."
                    ),
                    symbols=hotspot_symbols[:5],
                    difficulty=LearningDifficulty.ADVANCED,
                    what_to_understand="Why these functions are complex and what would break if they changed.",
                ))

        # Architecture patterns
        if understanding.architecture_style != "unknown":
            steps.append(LearningStep(
                order=start_order + len(steps),
                title=f"Understand the {understanding.architecture_style.value} architecture",
                what_to_read=[],
                why=understanding.architecture_description,
                symbols=[],
                difficulty=LearningDifficulty.ADVANCED,
                what_to_understand=(
                    "How the architecture constrains what goes where, "
                    "and why certain dependencies would violate boundaries."
                ),
            ))

        return steps

    def _generate_risks(
        self,
        understanding: RepositoryUnderstanding,
        start_order: int,
    ) -> list[LearningStep]:
        """Generate KNOWN RISKS steps — issues, debt, and gotchas."""
        steps: list[LearningStep] = []

        if understanding.architectural_risks:
            steps.append(LearningStep(
                order=start_order + len(steps),
                title="Known architectural risks",
                what_to_read=[],
                why="Be aware of these risks before making changes in these areas.",
                symbols=[],
                difficulty=LearningDifficulty.EXPERT,
                what_to_understand=(
                    "Risks:\n" + "\n".join(f"- {r}" for r in understanding.architectural_risks[:5])
                ),
            ))

        # God modules
        god_modules = [m for m in understanding.modules if m.is_god_module]
        if god_modules:
            steps.append(LearningStep(
                order=start_order + len(steps),
                title="Over-sized modules (potential refactoring targets)",
                what_to_read=[m.path for m in god_modules[:3]],
                why="These modules have too many responsibilities and are prime refactoring candidates.",
                symbols=[m.name for m in god_modules[:3]],
                difficulty=LearningDifficulty.EXPERT,
                what_to_understand="What responsibilities could be extracted into separate modules.",
            ))

        return steps
