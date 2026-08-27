"""Repository Intelligence — shared reasoning layer for all artifacts.

This module computes the core engineering intelligence ONCE from the
knowledge graph, providing a unified model that all artifact generators
consume. This prevents contradictory outputs between artifacts and
eliminates duplicated computation.

Architecture:
    Knowledge Graph (GraphBuildResult)
           │
           ▼
    RepositoryIntelligence.analyze()
           │
    ┌──────┼──────┐──────┐──────┐
    ▼      ▼      ▼      ▼      ▼
  Module  API   Learning  Report  Schema
  Break   Feat  Path     Generator Generator
  down    ures

Shared computations:
  - Module dependency graph (fan-in, fan-out, instability, circular deps)
  - Layer classification per module
  - Entry point detection
  - Complexity rankings
  - Documentation coverage
  - Test coverage heuristics
  - Design pattern detection
  - Key symbols by importance (in-degree)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


# ─── Layer classification (single source of truth) ────────────────────────────

LAYER_KEYWORDS: dict[str, list[str]] = {
    "Presentation": [
        "presentation", "router", "routers", "controller", "controllers",
        "handler", "handlers", "api", "endpoint", "endpoints", "view", "views",
        "rest", "graphql",
    ],
    "Application": [
        "application", "service", "services", "use_case", "use_cases",
        "usecase", "usecases", "interactor", "interactors", "command", "commands",
    ],
    "Domain": [
        "domain", "entity", "entities", "model", "models", "core",
        "value_objects", "aggregates",
    ],
    "Infrastructure": [
        "infrastructure", "repository", "repositories", "persistence",
        "db", "database", "client", "clients", "adapter", "adapters",
        "external", "gateway",
    ],
    "Frontend": [
        "component", "components", "page", "pages", "hook", "hooks",
        "feature", "features", "frontend", "ui", "widget",
    ],
    "Shared": [
        "shared", "common", "utils", "utilities", "helpers", "lib",
        "config", "settings", "exceptions",
    ],
    "Testing": [
        "test", "tests", "spec", "specs", "fixture", "fixtures",
        "__tests__", "conftest",
    ],
}

LAYER_ORDER = [
    "Presentation", "Frontend", "Application",
    "Domain", "Infrastructure", "Shared", "Testing", "Other",
]

# Expected dependency direction (index 0 = highest, can depend on higher index)
LAYER_RANK: dict[str, int] = {
    "Presentation": 0, "Frontend": 0,
    "Application": 1,
    "Domain": 2,
    "Infrastructure": 3,
    "Shared": 99,  # Shared is depended on by everyone — never a violation
    "Testing": 99,
    "Other": 3,
}


@dataclass
class ModuleIntel:
    """Intelligence computed for a single module."""
    id: str
    name: str
    path: str
    layer: str
    # Metrics
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    endpoint_count: int = 0
    test_count: int = 0
    line_count: int = 0
    total_complexity: int = 0
    documentation_ratio: float = 0.0
    # Dependency metrics
    fan_out: int = 0
    fan_in: int = 0
    instability: float = 0.5
    depends_on: list[str] = field(default_factory=list)  # module names
    depended_on_by: list[str] = field(default_factory=list)  # module names


@dataclass
class RepositoryIntelligence:
    """Unified intelligence model for the entire repository.

    Computed once, consumed by all artifact generators.
    This is the single source of truth for:
      - module structure and dependencies
      - architectural layer assignments
      - quality metrics
      - importance rankings
    """
    repo_name: str
    repo_url: str = ""

    # Counts
    total_files: int = 0
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_endpoints: int = 0
    total_tests: int = 0
    total_lines: int = 0
    languages: list[str] = field(default_factory=list)

    # Module intelligence
    modules: list[ModuleIntel] = field(default_factory=list)
    module_by_id: dict[str, ModuleIntel] = field(default_factory=dict)

    # Dependency intelligence
    circular_dependencies: list[tuple[str, str]] = field(default_factory=list)
    layer_violations: list[str] = field(default_factory=list)

    # Quality metrics
    avg_complexity: float = 0.0
    max_complexity: int = 0
    max_complexity_symbol: str = ""
    documentation_ratio: float = 0.0
    test_ratio: float = 0.0

    # Entry points (important starting files)
    entry_points: list[GraphNode] = field(default_factory=list)

    # Most important symbols (by in-degree)
    key_classes: list[GraphNode] = field(default_factory=list)

    # Detected patterns
    detected_layers: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)

    # Raw node/edge indices for generators that need them
    node_to_module: dict[str, str] = field(default_factory=dict)  # node_id → module_id
    module_deps: dict[str, set[str]] = field(default_factory=dict)  # module_id → set of dep module_ids


def classify_layer(path: str) -> str:
    """Classify a path into an architectural layer. Single source of truth."""
    path_lower = path.lower()
    for layer, keywords in LAYER_KEYWORDS.items():
        for kw in keywords:
            if kw in path_lower:
                return layer
    return "Other"


def compute_intelligence(graph: GraphBuildResult, repo_name: str) -> RepositoryIntelligence:
    """Compute the unified intelligence model from the knowledge graph.

    This is the main entry point. Call this ONCE per analysis, then pass
    the result to all artifact generators that need shared data.
    """
    intel = RepositoryIntelligence(
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

    # ── Basic counts ─────────────────────────────────────────────────────────
    intel.total_files = len(files)
    intel.total_modules = len(modules)
    intel.total_classes = len(classes)
    intel.total_functions = len(functions)
    intel.total_endpoints = len(endpoints)
    intel.total_tests = len(tests)
    intel.total_lines = sum(int(f.properties.get("lines", 0) or 0) for f in files)

    # Languages
    lang_counts: dict[str, int] = defaultdict(int)
    for f in files:
        lang = str(f.properties.get("language", "unknown"))
        if lang != "unknown":
            lang_counts[lang] += 1
    intel.languages = sorted(lang_counts.keys(), key=lambda l: lang_counts[l], reverse=True)

    # ── Build containment index ──────────────────────────────────────────────
    contains_children: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.relationship == RelationshipType.CONTAINS:
            contains_children[edge.source_id].append(edge.target_id)

    # Map every node to its parent module
    module_ids = {m.id for m in modules}
    node_to_module: dict[str, str] = {}

    def assign_module(mod_id: str) -> None:
        for child_id in contains_children.get(mod_id, []):
            node_to_module[child_id] = mod_id
            assign_module(child_id)

    for m in modules:
        assign_module(m.id)

    intel.node_to_module = node_to_module

    # ── Compute module dependencies ──────────────────────────────────────────
    module_deps: dict[str, set[str]] = {m.id: set() for m in modules}
    for edge in graph.edges:
        if edge.relationship == RelationshipType.IMPORTS:
            src_mod = node_to_module.get(edge.source_id)
            tgt_mod = node_to_module.get(edge.target_id)
            if src_mod and tgt_mod and src_mod != tgt_mod:
                if src_mod in module_deps:
                    module_deps[src_mod].add(tgt_mod)

    intel.module_deps = module_deps

    # ── Analyze each module ──────────────────────────────────────────────────
    # Compute fan-in for all modules
    fan_in_counts: dict[str, int] = defaultdict(int)
    for deps in module_deps.values():
        for dep_id in deps:
            fan_in_counts[dep_id] += 1

    for module in modules:
        path = str(module.properties.get("path", module.label))
        name = path.rstrip("/").split("/")[-1]
        layer = classify_layer(path)

        # Count contained elements
        children = _get_all_descendants(module.id, contains_children)
        file_count = sum(1 for c in children if _node_type(graph, c) == NodeType.FILE)
        class_count = sum(1 for c in children if _node_type(graph, c) in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM))
        function_count = sum(1 for c in children if _node_type(graph, c) in (NodeType.FUNCTION, NodeType.METHOD))
        endpoint_count = sum(1 for c in children if _node_type(graph, c) == NodeType.ENDPOINT)
        test_count = sum(1 for c in children if _node_type(graph, c) == NodeType.TEST)
        line_count = sum(
            int(graph.node_by_id[c].properties.get("lines", 0) or 0)
            for c in children if c in graph.node_by_id and _node_type(graph, c) == NodeType.FILE
        )
        total_complexity = sum(
            int(graph.node_by_id[c].properties.get("cyclomatic", 0) or 0)
            for c in children if c in graph.node_by_id
        )

        fan_out = len(module_deps.get(module.id, set()))
        fan_in = fan_in_counts.get(module.id, 0)
        total_coupling = fan_in + fan_out
        instability = round(fan_out / total_coupling if total_coupling > 0 else 0.5, 2)

        # Dependency names
        depends_on_names = []
        for dep_id in module_deps.get(module.id, set()):
            dep_node = graph.node_by_id.get(dep_id)
            if dep_node:
                dep_path = str(dep_node.properties.get("path", dep_node.label))
                depends_on_names.append(dep_path.rstrip("/").split("/")[-1])

        depended_on_by_names = []
        for other_id, other_deps in module_deps.items():
            if module.id in other_deps:
                other_node = graph.node_by_id.get(other_id)
                if other_node:
                    other_path = str(other_node.properties.get("path", other_node.label))
                    depended_on_by_names.append(other_path.rstrip("/").split("/")[-1])

        mod_intel = ModuleIntel(
            id=module.id,
            name=name,
            path=path,
            layer=layer,
            file_count=file_count,
            class_count=class_count,
            function_count=function_count,
            endpoint_count=endpoint_count,
            test_count=test_count,
            line_count=line_count,
            total_complexity=total_complexity,
            fan_out=fan_out,
            fan_in=fan_in,
            instability=instability,
            depends_on=depends_on_names,
            depended_on_by=depended_on_by_names,
        )
        intel.modules.append(mod_intel)
        intel.module_by_id[module.id] = mod_intel

    # Sort by importance (fan_in descending)
    intel.modules.sort(key=lambda m: m.fan_in, reverse=True)

    # ── Circular dependencies ────────────────────────────────────────────────
    seen_pairs: set[tuple[str, str]] = set()
    for src_id, targets in module_deps.items():
        for tgt_id in targets:
            if tgt_id in module_deps and src_id in module_deps[tgt_id]:
                pair = tuple(sorted([src_id, tgt_id]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    src_intel = intel.module_by_id.get(src_id)
                    tgt_intel = intel.module_by_id.get(tgt_id)
                    if src_intel and tgt_intel:
                        intel.circular_dependencies.append((src_intel.name, tgt_intel.name))

    # ── Layer violations ─────────────────────────────────────────────────────
    for src_id, targets in module_deps.items():
        src_intel = intel.module_by_id.get(src_id)
        if not src_intel:
            continue
        src_rank = LAYER_RANK.get(src_intel.layer, 3)
        for tgt_id in targets:
            tgt_intel = intel.module_by_id.get(tgt_id)
            if not tgt_intel:
                continue
            tgt_rank = LAYER_RANK.get(tgt_intel.layer, 3)
            # Violation: deeper layer depends on shallower (domain → presentation)
            if src_rank > tgt_rank and src_intel.layer != "Other" and tgt_intel.layer not in ("Shared", "Testing", "Other"):
                intel.layer_violations.append(
                    f"`{src_intel.name}` ({src_intel.layer}) → `{tgt_intel.name}` ({tgt_intel.layer})"
                )

    # ── Detected layers ──────────────────────────────────────────────────────
    intel.detected_layers = sorted(set(m.layer for m in intel.modules if m.layer != "Other"))

    # ── Quality metrics ──────────────────────────────────────────────────────
    complexities = [
        (int(fn.properties.get("cyclomatic", 0) or 0), fn.label)
        for fn in functions
        if int(fn.properties.get("cyclomatic", 0) or 0) > 0
    ]
    if complexities:
        intel.avg_complexity = round(sum(c for c, _ in complexities) / len(complexities), 2)
        max_cc, max_name = max(complexities, key=lambda x: x[0])
        intel.max_complexity = max_cc
        intel.max_complexity_symbol = max_name

    documentable = [n for n in functions + classes if n.node_type != NodeType.TEST]
    if documentable:
        documented = sum(1 for n in documentable if n.properties.get("has_docstring"))
        intel.documentation_ratio = round(documented / len(documentable), 2)

    test_files = [f for f in files if f.properties.get("is_test_file")]
    source_files = [f for f in files if not f.properties.get("is_test_file")]
    if source_files:
        intel.test_ratio = round(len(test_files) / len(source_files), 2)

    # ── Entry points ─────────────────────────────────────────────────────────
    _entry_names = {
        "main.py", "app.py", "__main__.py", "index.ts", "index.js",
        "server.py", "server.ts", "manage.py",
    }
    for f in files:
        basename = str(f.properties.get("path", f.label)).split("/")[-1].lower()
        if basename in _entry_names:
            intel.entry_points.append(f)
    intel.entry_points = intel.entry_points[:8]

    # ── Key classes (by in-degree) ───────────────────────────────────────────
    class_in_degree: dict[str, int] = defaultdict(int)
    for edge in graph.edges:
        if edge.relationship in (RelationshipType.INHERITS, RelationshipType.IMPLEMENTS, RelationshipType.CALLS):
            class_in_degree[edge.target_id] += 1

    intel.key_classes = sorted(
        [c for c in classes if class_in_degree.get(c.id, 0) > 0],
        key=lambda c: class_in_degree.get(c.id, 0),
        reverse=True,
    )[:10]

    # ── Design patterns ──────────────────────────────────────────────────────
    all_names = " ".join(n.label.lower() for n in classes + functions)
    _pattern_signals = {
        "Repository Pattern": ["repository"],
        "Factory Pattern": ["factory"],
        "Observer Pattern": ["observer", "listener", "subscriber"],
        "Strategy Pattern": ["strategy"],
        "Middleware Pattern": ["middleware"],
        "Adapter Pattern": ["adapter"],
        "Facade Pattern": ["facade"],
        "Dependency Injection": [],  # Checked separately
    }
    for pattern, signals in _pattern_signals.items():
        for signal in signals:
            if signal in all_names:
                intel.detected_patterns.append(pattern)
                break
    interfaces = graph.nodes_by_type(NodeType.INTERFACE)
    if len(interfaces) >= 2:
        intel.detected_patterns.append("Dependency Injection")

    return intel


def _get_all_descendants(node_id: str, contains: dict[str, list[str]]) -> list[str]:
    """Get all transitive descendants via CONTAINS."""
    result: list[str] = []
    queue = list(contains.get(node_id, []))
    visited: set[str] = set()
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        result.append(current)
        queue.extend(contains.get(current, []))
    return result


def _node_type(graph: GraphBuildResult, node_id: str) -> NodeType | None:
    """Get node type by ID from the graph."""
    node = graph.node_by_id.get(node_id)
    return node.node_type if node else None
