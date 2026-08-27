"""Interview Questions Generator — repository-specific engineering questions.

NEVER generates generic questions like "What is dependency injection?"
ALWAYS derives questions from ACTUAL repository evidence:
  - Architectural patterns detected in the graph
  - God classes with high method counts
  - Cyclic dependencies between modules
  - Fan-out/fan-in extremes
  - Inheritance hierarchies
  - API design decisions
  - Complexity hotspots

Each question includes:
  - The question itself (references real code)
  - Difficulty level
  - Category
  - Source evidence (files, symbols, metrics)
  - Expected concepts in the answer
  - Model answer outline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class InterviewQuestion:
    """A single interview question with full evidence trail."""
    question: str
    category: str  # Architecture, Debugging, Design, Dependencies, Performance, Testing, Security
    difficulty: str  # Junior, Mid, Senior, Staff
    # Evidence
    source_files: list[str] = field(default_factory=list)
    source_symbols: list[str] = field(default_factory=list)
    evidence_metric: str = ""  # e.g. "cyclomatic_complexity=23"
    reason: str = ""  # Why this question is relevant to this repo
    # Answer guidance
    expected_concepts: list[str] = field(default_factory=list)
    model_answer_outline: str = ""


@dataclass
class InterviewQuestionsResult:
    """Complete set of interview questions for a repository."""
    repo_name: str
    total_questions: int = 0
    questions: list[InterviewQuestion] = field(default_factory=list)


class InterviewQuestionsGenerator:
    """Generates repository-specific interview questions from graph evidence.

    Question generation pipeline:
      1. Detect architectural patterns → architecture questions
      2. Find complexity hotspots → debugging/performance questions
      3. Analyze dependency structure → design decision questions
      4. Find god classes → refactoring questions
      5. Analyze inheritance → OOP design questions
      6. Check API design → API/security questions
      7. Analyze test structure → testing strategy questions
    """

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate interview questions as Markdown."""
        result = self.analyze(graph, repo_name)
        return self._render_markdown(result)

    def analyze(self, graph: GraphBuildResult, repo_name: str) -> InterviewQuestionsResult:
        """Generate all interview questions from graph analysis."""
        result = InterviewQuestionsResult(repo_name=repo_name)

        classes = [n for n in graph.nodes if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
        )]
        functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT
        )]
        modules = graph.nodes_by_type(NodeType.MODULE)
        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)
        interfaces = graph.nodes_by_type(NodeType.INTERFACE)
        tests = graph.nodes_by_type(NodeType.TEST)

        # Build edge indices
        edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in graph.edges:
            edges_from[edge.source_id].append(edge)
            edges_to[edge.target_id].append(edge)

        # Generate questions from different analysis angles
        result.questions.extend(
            self._architecture_questions(classes, interfaces, modules, graph, edges_from, edges_to)
        )
        result.questions.extend(
            self._complexity_questions(functions, classes, graph)
        )
        result.questions.extend(
            self._dependency_questions(modules, graph, edges_from)
        )
        result.questions.extend(
            self._design_questions(classes, interfaces, graph, edges_from, edges_to)
        )
        result.questions.extend(
            self._api_questions(endpoints, graph, edges_from)
        )
        result.questions.extend(
            self._testing_questions(tests, modules, graph, edges_to)
        )

        result.total_questions = len(result.questions)
        return result

    def _architecture_questions(
        self, classes, interfaces, modules, graph, edges_from, edges_to
    ) -> list[InterviewQuestion]:
        """Questions about architectural decisions found in the code."""
        questions: list[InterviewQuestion] = []

        # Q: Why this layered architecture?
        layer_modules = [
            m for m in modules
            if any(kw in str(m.properties.get("path", "")).lower()
                   for kw in ("domain", "application", "infrastructure", "presentation"))
        ]
        if len(layer_modules) >= 3:
            paths = [str(m.properties.get("path", m.label)) for m in layer_modules[:6]]
            questions.append(InterviewQuestion(
                question=(
                    f"This repository uses a layered architecture with modules like "
                    f"{', '.join(f'`{p}`' for p in paths[:4])}. "
                    f"What problem does this layering solve, and what would break "
                    f"if a developer imported directly from infrastructure in the domain layer?"
                ),
                category="Architecture",
                difficulty="Mid",
                source_files=paths[:4],
                reason="Layered architecture detected from module naming patterns.",
                expected_concepts=[
                    "Dependency inversion", "Separation of concerns",
                    "Testability", "Domain independence from frameworks",
                ],
                model_answer_outline=(
                    "Layering ensures the domain doesn't depend on implementation details. "
                    "If domain imports infrastructure, you can't test domain logic without "
                    "a real database. The dependency rule flows inward: presentation → "
                    "application → domain."
                ),
            ))

        # Q: Interface usage
        if interfaces:
            iface_names = [i.label for i in interfaces[:4]]
            iface_files = [str(i.properties.get("file", "")) for i in interfaces[:4]]
            # Find implementors
            implementors = []
            for edge in graph.edges:
                if edge.relationship == RelationshipType.IMPLEMENTS:
                    src = graph.node_by_id.get(edge.source_id)
                    if src:
                        implementors.append(src.label)

            questions.append(InterviewQuestion(
                question=(
                    f"This codebase defines interfaces/abstract classes like "
                    f"{', '.join(f'`{n}`' for n in iface_names)}. "
                    f"Why use an abstract interface instead of directly using the "
                    f"concrete implementation? What benefit does this provide for testing?"
                ),
                category="Design",
                difficulty="Mid",
                source_files=iface_files,
                source_symbols=iface_names + implementors[:3],
                reason=f"{len(interfaces)} interfaces detected with {len(implementors)} implementations.",
                expected_concepts=[
                    "Dependency inversion principle", "Test doubles/mocks",
                    "Swappable implementations", "Open/closed principle",
                ],
                model_answer_outline=(
                    "Interfaces define contracts without implementation. This lets you: "
                    "(1) swap implementations (SQLite in dev, Postgres in prod), "
                    "(2) inject mocks in tests, (3) add new implementations without "
                    "changing consumers."
                ),
            ))

        return questions

    def _complexity_questions(self, functions, classes, graph) -> list[InterviewQuestion]:
        """Questions about complexity hotspots."""
        questions: list[InterviewQuestion] = []

        # Find most complex function
        complex_fns = sorted(
            [f for f in functions if int(f.properties.get("cyclomatic", 0) or 0) >= 8],
            key=lambda f: int(f.properties.get("cyclomatic", 0) or 0),
            reverse=True,
        )

        if complex_fns:
            fn = complex_fns[0]
            cc = int(fn.properties.get("cyclomatic", 0) or 0)
            lines = int(fn.properties.get("lines", 0) or 0)
            file_path = str(fn.properties.get("file", ""))

            questions.append(InterviewQuestion(
                question=(
                    f"`{fn.label}` in `{file_path.split('/')[-1]}` has cyclomatic "
                    f"complexity {cc} and is {lines} lines long. How would you "
                    f"refactor this to reduce complexity while preserving behavior?"
                ),
                category="Debugging",
                difficulty="Senior",
                source_files=[file_path],
                source_symbols=[fn.label],
                evidence_metric=f"cyclomatic_complexity={cc}, lines={lines}",
                reason="Highest complexity function in the codebase — likely bug-prone.",
                expected_concepts=[
                    "Extract method", "Strategy pattern", "Guard clauses",
                    "Polymorphism over conditionals", "Single responsibility",
                ],
                model_answer_outline=(
                    "Strategies: (1) Replace nested ifs with guard clauses/early returns, "
                    "(2) Extract each branch into a named method, (3) Use strategy pattern "
                    "if branching on type, (4) Replace complex conditionals with lookup "
                    "tables or polymorphic dispatch."
                ),
            ))

        # God class question
        god_classes = sorted(
            [c for c in classes if int(c.properties.get("methods", 0) or 0) >= 10],
            key=lambda c: int(c.properties.get("methods", 0) or 0),
            reverse=True,
        )

        if god_classes:
            cls = god_classes[0]
            method_count = int(cls.properties.get("methods", 0) or 0)
            lines = int(cls.properties.get("lines", 0) or 0)
            file_path = str(cls.properties.get("file", ""))

            questions.append(InterviewQuestion(
                question=(
                    f"`{cls.label}` has {method_count} methods and spans {lines} lines. "
                    f"What heuristics would you use to decide how to split it, and what "
                    f"would be your first refactoring step?"
                ),
                category="Design",
                difficulty="Senior",
                source_files=[file_path],
                source_symbols=[cls.label],
                evidence_metric=f"methods={method_count}, lines={lines}",
                reason="Potential god class — high method count suggests multiple responsibilities.",
                expected_concepts=[
                    "Single Responsibility Principle", "Cohesion",
                    "Extract class", "Identify responsibility groups",
                ],
                model_answer_outline=(
                    "Step 1: Group methods by what data they access (high cohesion clusters). "
                    "Step 2: Name each cluster as a potential new class. "
                    "Step 3: Extract the smallest, most cohesive cluster first. "
                    "Step 4: Use composition — the original class delegates to the new one."
                ),
            ))

        return questions

    def _dependency_questions(self, modules, graph, edges_from) -> list[InterviewQuestion]:
        """Questions about dependency structure."""
        questions: list[InterviewQuestion] = []

        # Find circular dependencies
        # Build module dependency map
        contains: dict[str, str] = {}
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains[edge.target_id] = edge.source_id

        module_ids = {m.id for m in modules}
        node_to_module: dict[str, str] = {}

        def assign(mod_id: str) -> None:
            for edge in edges_from.get(mod_id, []):
                if edge.relationship == RelationshipType.CONTAINS:
                    node_to_module[edge.target_id] = mod_id
                    assign(edge.target_id)

        for m in modules:
            assign(m.id)

        # Find cross-module imports
        module_deps: dict[str, set[str]] = defaultdict(set)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.IMPORTS:
                src_mod = node_to_module.get(edge.source_id)
                tgt_mod = node_to_module.get(edge.target_id)
                if src_mod and tgt_mod and src_mod != tgt_mod:
                    module_deps[src_mod].add(tgt_mod)

        # Find high fan-out module
        if module_deps:
            high_fanout = max(module_deps.items(), key=lambda x: len(x[1]), default=None)
            if high_fanout and len(high_fanout[1]) >= 3:
                mod_node = graph.node_by_id.get(high_fanout[0])
                if mod_node:
                    mod_name = str(mod_node.properties.get("path", mod_node.label))
                    dep_names = []
                    for dep_id in list(high_fanout[1])[:5]:
                        dep_node = graph.node_by_id.get(dep_id)
                        if dep_node:
                            dep_names.append(str(dep_node.properties.get("path", dep_node.label)).split("/")[-1])

                    questions.append(InterviewQuestion(
                        question=(
                            f"Module `{mod_name.split('/')[-1]}` depends on "
                            f"{len(high_fanout[1])} other modules ({', '.join(f'`{d}`' for d in dep_names)}). "
                            f"What architectural problem does high fan-out indicate, "
                            f"and how would you reduce it?"
                        ),
                        category="Dependencies",
                        difficulty="Senior",
                        source_files=[mod_name],
                        evidence_metric=f"fan_out={len(high_fanout[1])}",
                        reason="Highest fan-out module — changes here may cascade widely.",
                        expected_concepts=[
                            "Coupling", "Mediator pattern", "Facade pattern",
                            "Dependency injection", "Module boundaries",
                        ],
                        model_answer_outline=(
                            "High fan-out means this module knows about too many others — "
                            "it's a coupling hub. Solutions: (1) Introduce a mediator/facade "
                            "to consolidate dependencies, (2) Invert dependencies using "
                            "interfaces, (3) Split the module if it has multiple responsibilities."
                        ),
                    ))

        return questions

    def _design_questions(self, classes, interfaces, graph, edges_from, edges_to) -> list[InterviewQuestion]:
        """Questions about design patterns and decisions."""
        questions: list[InterviewQuestion] = []

        # Find classes with deep inheritance
        inheritance_depth: dict[str, int] = {}
        class_map = {c.id: c for c in classes}

        for cls in classes:
            depth = 0
            current = cls
            visited = set()
            while True:
                inherits_edges = [
                    e for e in edges_from.get(current.id, [])
                    if e.relationship == RelationshipType.INHERITS
                ]
                if not inherits_edges:
                    break
                parent = graph.node_by_id.get(inherits_edges[0].target_id)
                if not parent or parent.id in visited:
                    break
                visited.add(parent.id)
                depth += 1
                current = parent
            inheritance_depth[cls.id] = depth

        deep_classes = [(cls, d) for cls, d in
                        [(graph.node_by_id.get(cid), depth)
                         for cid, depth in inheritance_depth.items()]
                        if cls and d >= 2]

        if deep_classes:
            cls, depth = max(deep_classes, key=lambda x: x[1])
            file_path = str(cls.properties.get("file", ""))
            bases = str(cls.properties.get("base_classes", ""))

            questions.append(InterviewQuestion(
                question=(
                    f"`{cls.label}` has an inheritance depth of {depth} "
                    f"(base: `{bases}`). When does deep inheritance become "
                    f"problematic, and what alternative would you suggest?"
                ),
                category="Design",
                difficulty="Mid",
                source_files=[file_path],
                source_symbols=[cls.label],
                evidence_metric=f"inheritance_depth={depth}",
                reason="Deep inheritance detected — potential fragile base class problem.",
                expected_concepts=[
                    "Composition over inheritance", "Fragile base class",
                    "Liskov Substitution Principle", "Mixin pattern",
                ],
                model_answer_outline=(
                    "Deep inheritance creates tight coupling between layers. "
                    "Changes to base classes ripple unpredictably. Prefer composition: "
                    "inject behavior via constructor parameters or use mixins/traits "
                    "for cross-cutting concerns."
                ),
            ))

        return questions

    def _api_questions(self, endpoints, graph, edges_from) -> list[InterviewQuestion]:
        """Questions about API design."""
        questions: list[InterviewQuestion] = []

        if len(endpoints) >= 3:
            routes = [
                str(ep.properties.get("route_info", ep.label))
                for ep in endpoints[:8]
                if ep.properties.get("route_info")
            ]

            # Check for unauthenticated mutation endpoints
            unprotected = [
                ep for ep in endpoints
                if str(ep.properties.get("route_info", "")).startswith(("POST", "PUT", "DELETE", "PATCH"))
            ]

            if unprotected:
                ep = unprotected[0]
                questions.append(InterviewQuestion(
                    question=(
                        f"Endpoint `{ep.properties.get('route_info', ep.label)}` mutates state. "
                        f"What security considerations should apply to mutation endpoints, "
                        f"and how would you implement them in this framework?"
                    ),
                    category="Security",
                    difficulty="Mid",
                    source_files=[str(ep.properties.get("file", ""))],
                    source_symbols=[ep.label],
                    reason="Mutation endpoint detected — security posture should be evaluated.",
                    expected_concepts=[
                        "Authentication", "Authorization", "Input validation",
                        "Rate limiting", "CSRF protection",
                    ],
                    model_answer_outline=(
                        "Mutation endpoints need: (1) Authentication (verify identity), "
                        "(2) Authorization (verify permission), (3) Input validation "
                        "(reject malformed data), (4) Rate limiting (prevent abuse), "
                        "(5) Audit logging (track who changed what)."
                    ),
                ))

            # General API design question
            if routes:
                questions.append(InterviewQuestion(
                    question=(
                        f"This API exposes {len(endpoints)} endpoints including: "
                        f"{', '.join(f'`{r}`' for r in routes[:5])}. "
                        f"How would you design API versioning for this system, "
                        f"and when would you introduce a breaking change?"
                    ),
                    category="Architecture",
                    difficulty="Senior",
                    source_symbols=routes[:5],
                    reason=f"{len(endpoints)} API endpoints form the public contract.",
                    expected_concepts=[
                        "Semantic versioning", "URL vs header versioning",
                        "Backward compatibility", "Deprecation strategy",
                    ],
                    model_answer_outline=(
                        "Options: (1) URL prefix (/v1/, /v2/) — simple, explicit. "
                        "(2) Header-based (Accept: application/vnd.api+json;v=2) — cleaner URLs. "
                        "Breaking changes should only happen when: removing fields, changing "
                        "semantics, altering auth. Additive changes (new fields) are non-breaking."
                    ),
                ))

        return questions

    def _testing_questions(self, tests, modules, graph, edges_to) -> list[InterviewQuestion]:
        """Questions about testing strategy."""
        questions: list[InterviewQuestion] = []

        if tests:
            test_files = list(set(str(t.properties.get("file", "")) for t in tests[:20]))

            questions.append(InterviewQuestion(
                question=(
                    f"This repository has {len(tests)} test functions across "
                    f"files like `{test_files[0].split('/')[-1] if test_files else 'test_*.py'}`. "
                    f"How would you determine which modules have insufficient test coverage "
                    f"without running the test suite?"
                ),
                category="Testing",
                difficulty="Mid",
                source_files=test_files[:4],
                evidence_metric=f"test_count={len(tests)}",
                reason="Test infrastructure exists — coverage analysis is relevant.",
                expected_concepts=[
                    "Static coverage heuristics", "Test file naming conventions",
                    "Module-to-test mapping", "Risk-based testing",
                ],
                model_answer_outline=(
                    "Without running tests: (1) Map test files to source modules by naming "
                    "convention (test_X.py → X.py), (2) Identify source modules with NO "
                    "corresponding test file, (3) Prioritize testing for high-complexity, "
                    "high-coupling modules first. These are heuristics — actual coverage "
                    "requires runtime instrumentation."
                ),
            ))
        else:
            questions.append(InterviewQuestion(
                question=(
                    f"No test files were detected in this repository. "
                    f"If you were to add a testing strategy from scratch, "
                    f"which module would you test first and why?"
                ),
                category="Testing",
                difficulty="Junior",
                reason="No tests detected — testing strategy is a critical gap.",
                expected_concepts=[
                    "Test pyramid", "Unit vs integration tests",
                    "High-value test targets", "Risk-based prioritization",
                ],
                model_answer_outline=(
                    "Start with the domain/core layer — it has the most business logic "
                    "and fewest external dependencies (easiest to unit test). Then add "
                    "integration tests for API endpoints. Test the highest-complexity "
                    "functions first — they have the most branches to cover."
                ),
            ))

        return questions

    def _render_markdown(self, result: InterviewQuestionsResult) -> str:
        """Render interview questions as structured Markdown."""
        lines: list[str] = []

        lines.append(f"# Interview Questions — {result.repo_name}")
        lines.append("")
        lines.append(
            "> **What are these?** These are interview questions that test whether "
            "someone truly understands THIS specific codebase — not generic programming "
            "trivia. Each question is generated from actual patterns, problems, and "
            "design decisions Cortex found in the code. They're perfect for:"
        )
        lines.append(">")
        lines.append("> - **Hiring:** Test if a candidate can reason about real code")
        lines.append("> - **Onboarding:** Help new team members explore the system deeply")
        lines.append("> - **Self-study:** Challenge yourself to understand WHY things are built this way")
        lines.append("")
        lines.append(
            f"**{result.total_questions} questions** generated from actual code patterns."
        )
        lines.append("")
        lines.append("**Difficulty:** 🟢 Junior — 🟡 Mid — 🟠 Senior — 🔴 Staff")
        lines.append("")

        # Group by category
        by_category: dict[str, list[InterviewQuestion]] = defaultdict(list)
        for q in result.questions:
            by_category[q.category].append(q)

        category_order = [
            "Architecture", "Design", "Dependencies",
            "Debugging", "Security", "Testing", "Performance",
        ]

        for category in category_order:
            cat_questions = by_category.get(category, [])
            if not cat_questions:
                continue

            lines.append(f"## {category}")
            lines.append("")

            for i, q in enumerate(cat_questions, 1):
                difficulty_badge = {
                    "Junior": "🟢", "Mid": "🟡", "Senior": "🟠", "Staff": "🔴"
                }.get(q.difficulty, "")

                lines.append(f"### Q{i}. {difficulty_badge} {q.difficulty}")
                lines.append("")
                lines.append(f"**{q.question}**")
                lines.append("")

                # Evidence
                if q.source_files or q.source_symbols or q.evidence_metric:
                    lines.append("<details>")
                    lines.append("<summary>Evidence & Answer Guide</summary>")
                    lines.append("")
                    if q.source_files:
                        lines.append(f"**Source:** {', '.join(f'`{f.split(\"/\")[-1]}`' for f in q.source_files[:4])}")
                        lines.append("")
                    if q.source_symbols:
                        lines.append(f"**Symbols:** {', '.join(f'`{s}`' for s in q.source_symbols[:5])}")
                        lines.append("")
                    if q.evidence_metric:
                        lines.append(f"**Metric:** `{q.evidence_metric}`")
                        lines.append("")
                    if q.reason:
                        lines.append(f"**Why relevant:** {q.reason}")
                        lines.append("")
                    if q.expected_concepts:
                        lines.append(f"**Expected concepts:** {', '.join(q.expected_concepts)}")
                        lines.append("")
                    if q.model_answer_outline:
                        lines.append(f"**Model answer:** {q.model_answer_outline}")
                        lines.append("")
                    lines.append("</details>")
                    lines.append("")

        return "\n".join(lines)
