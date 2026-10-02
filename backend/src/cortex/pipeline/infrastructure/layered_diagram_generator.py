"""Layered Diagram Generator — produces structured JSON for a multi-level
architecture diagram (React Flow frontend).

Three zoom levels:
  Level 1 — System View: one node per top-level module, aggregated edges.
  Level 2 — Module Detail: classes/files inside one module + collapsed deps.
  Level 3 — Class Detail: methods, callers, callees, inheritance chain.

Output is plain dicts/lists (JSON-serializable) that the frontend React Flow
component consumes directly. No Mermaid syntax.

──────────────────────────────────────────────────────────────────────────────
Architecture model, not a dependency dump
──────────────────────────────────────────────────────────────────────────────
The system view must answer "how is this codebase organised?" not
"show every file and import".  Key invariants enforced here:

  • One node per TOP-LEVEL architectural module (not every subdirectory).
  • Edges are AGGREGATED: multiple file-level imports between the same two
    modules produce exactly ONE edge with a weight counter — never duplicates.
  • MIN_EDGE_WEIGHT is 1 (not 2).  A single cross-module import IS an
    architectural relationship and must be shown.  The old value of 2 silently
    dropped most edges in typical repos.
  • Container-directory names (src, backend, frontend, lib, app…) that add no
    architectural meaning are excluded from the system view when real
    named modules exist under them.
  • Node count is capped at MAX_SYSTEM_NODES and edges at MAX_SYSTEM_EDGES so
    the canvas never becomes a hairball.  Nodes are ranked by architectural
    significance (endpoints > classes > files > lines) before capping.
  • Cycles are detected with Tarjan's SCC and shown explicitly — not hidden.
  • Layer classification uses ALL path segments of contained files so that
    a module whose files live under presentation/, application/, domain/ or
    infrastructure/ sub-paths is correctly labelled.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from cortex.graph.domain.entities import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


# ── Data structures for the JSON response ────────────────────────────────────


@dataclass
class DiagramNode:
    """A single node in the diagram."""
    id: str
    label: str
    node_type: str          # "module" | "file" | "class" | "function" | "external"
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    line_count: int = 0
    health: str = "healthy" # "healthy" | "warning" | "critical"
    health_reason: str = ""
    in_cycle: bool = False
    layer: str = ""         # architectural layer label
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            "fileCount": self.file_count,
            "classCount": self.class_count,
            "functionCount": self.function_count,
            "lineCount": self.line_count,
            "health": self.health,
            "healthReason": self.health_reason,
            "inCycle": self.in_cycle,
            "layer": self.layer,
            "properties": self.properties,
        }


@dataclass
class DiagramEdge:
    """A single edge in the diagram."""
    id: str
    source: str
    target: str
    label: str = ""
    edge_type: str = "imports"  # "imports" | "inherits" | "calls" | "contains"
    weight: int = 1
    is_cycle: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "type": self.edge_type,
            "weight": self.weight,
            "isCycle": self.is_cycle,
        }


@dataclass
class DiagramResult:
    """Complete diagram response for one level."""
    level: str
    title: str
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    breadcrumb: list[dict[str, str]] = field(default_factory=list)
    drilldown_targets: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "title": self.title,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "cycles": self.cycles,
            "breadcrumb": self.breadcrumb,
            "drilldownTargets": self.drilldown_targets,
        }


# ── Constants ─────────────────────────────────────────────────────────────────

# Generic container-directory names that carry no architectural meaning on
# their own.  A module whose ONLY name is one of these is skipped in the
# system view when more specifically named modules exist at deeper levels.
_GENERIC_CONTAINERS: frozenset[str] = frozenset({
    "src", "backend", "frontend", "lib", "app", "core", "main",
    "source", "sources", "pkg", "packages", "modules",
})

# Layer classification — ordered from most to least specific so the first
# match wins.  Each entry is (path-segment-keyword, layer-name).
_LAYER_KEYWORDS: list[tuple[str, str]] = [
    # Presentation / API
    ("presentation", "Presentation"),
    ("router",       "Presentation"),
    ("routers",      "Presentation"),
    ("controller",   "Presentation"),
    ("controllers",  "Presentation"),
    ("handler",      "Presentation"),
    ("handlers",     "Presentation"),
    ("endpoint",     "Presentation"),
    ("endpoints",    "Presentation"),
    ("api",          "Presentation"),
    ("view",         "Presentation"),
    ("views",        "Presentation"),
    ("rest",         "Presentation"),
    ("graphql",      "Presentation"),
    # Application / Use-cases
    ("application",  "Application"),
    ("use_case",     "Application"),
    ("usecases",     "Application"),
    ("use_cases",    "Application"),
    ("service",      "Application"),
    ("services",     "Application"),
    ("usecase",      "Application"),
    ("interactor",   "Application"),
    # Domain / Business logic
    ("domain",       "Domain"),
    ("entity",       "Domain"),
    ("entities",     "Domain"),
    ("model",        "Domain"),
    ("models",       "Domain"),
    ("schema",       "Domain"),
    ("schemas",      "Domain"),
    ("dto",          "Domain"),
    ("value_object", "Domain"),
    ("aggregate",    "Domain"),
    # Infrastructure / Data
    ("infrastructure", "Infrastructure"),
    ("repository",     "Infrastructure"),
    ("repositories",   "Infrastructure"),
    ("persistence",    "Infrastructure"),
    ("database",       "Infrastructure"),
    ("db",             "Infrastructure"),
    ("dao",            "Infrastructure"),
    ("adapter",        "Infrastructure"),
    ("adapters",       "Infrastructure"),
    ("client",         "Infrastructure"),
    ("clients",        "Infrastructure"),
    ("cache",          "Infrastructure"),
    ("queue",          "Infrastructure"),
    ("storage",        "Infrastructure"),
    # Frontend
    ("component",  "Frontend"),
    ("components", "Frontend"),
    ("page",       "Frontend"),
    ("pages",      "Frontend"),
    ("hook",       "Frontend"),
    ("hooks",      "Frontend"),
    ("feature",    "Frontend"),
    ("features",   "Frontend"),
    ("store",      "Frontend"),
    ("context",    "Frontend"),
    ("layout",     "Frontend"),
    # Shared / Cross-cutting
    ("shared",  "Shared"),
    ("common",  "Shared"),
    ("utils",   "Shared"),
    ("util",    "Shared"),
    ("helper",  "Shared"),
    ("helpers", "Shared"),
    ("config",  "Shared"),
    ("configs", "Shared"),
    ("lib",     "Shared"),
    # Tests
    ("test",   "Testing"),
    ("tests",  "Testing"),
    ("spec",   "Testing"),
    ("specs",  "Testing"),
    ("mock",   "Testing"),
    ("mocks",  "Testing"),
    ("fixture","Testing"),
]

# Canonical top-to-bottom rendering order for layers.
_LAYER_ORDER: list[str] = [
    "Presentation", "Frontend", "Application",
    "Domain", "Infrastructure", "Shared", "Testing", "Other",
]

# System-view caps — keep the diagram readable.
MAX_SYSTEM_NODES = 20
MAX_SYSTEM_EDGES = 30


# ── Helpers ────────────────────────────────────────────────────────────────────


def _top_level_module(path: str) -> str:
    """Extract the architecturally meaningful top-level module name.

    Skips generic container directories (src, backend, frontend, lib, app…)
    and returns the first segment that has a real domain name.

    Examples:
        "backend/src/cortex/chat/application/service.py"  → "chat"
        "frontend/src/features/jobs/JobCard.tsx"           → "jobs"
        "src/auth/login.py"                                → "auth"
        "app/models/user.py"                               → "models"
    """
    parts = [p for p in path.replace("\\", "/").split("/") if p]

    # Known structural prefixes to skip (ordered longest-first so multi-segment
    # prefixes are consumed before single-segment ones).
    skip_prefixes: list[list[str]] = [
        ["backend", "src", "cortex"],
        ["backend", "src"],
        ["frontend", "src", "features"],
        ["frontend", "src"],
        ["src", "cortex"],
        ["src"],
        ["backend"],
        ["frontend"],
    ]
    for prefix in skip_prefixes:
        n = len(prefix)
        if parts[:n] == prefix and len(parts) > n:
            candidate = parts[n]
            if "." not in candidate:
                return candidate

    # Fallback: first segment that isn't a generic container and isn't a file
    for p in parts:
        if p not in _GENERIC_CONTAINERS and "." not in p:
            return p

    return parts[0] if parts else "root"


def _classify_layer_from_paths(file_paths: list[str]) -> str:
    """Classify a module's architectural layer by examining the paths of all
    files it contains.

    We collect every path segment across all contained files and score each
    layer keyword.  The layer with the highest total score wins.  This works
    for both:
      • Repos where layer is in the module-directory name
        (backend/cortex/chat/application/service.py → Application)
      • Repos where layer is in a file-name suffix
        (UserRepository.java, ChatService.java → Infrastructure / Application)
    """
    segment_counts: dict[str, int] = defaultdict(int)
    for fp in file_paths:
        parts = [p.lower().replace("\\", "/") for p in fp.replace("\\", "/").split("/") if p]
        for part in parts:
            # Also check filename without extension (e.g. "chat_service" → "service")
            base = part.split(".")[0]
            segment_counts[base] += 1
            # Split on underscores/hyphens for compound names
            for token in base.replace("-", "_").split("_"):
                if len(token) > 2:
                    segment_counts[token] += 1

    layer_score: dict[str, int] = defaultdict(int)
    for keyword, layer in _LAYER_KEYWORDS:
        score = segment_counts.get(keyword, 0)
        if score:
            layer_score[layer] += score

    if not layer_score:
        return "Other"

    # Return the layer with the highest score; break ties by layer order
    best_layer = max(
        layer_score.keys(),
        key=lambda l: (layer_score[l], -_LAYER_ORDER.index(l) if l in _LAYER_ORDER else -99),
    )
    return best_layer


def _detect_cycles_tarjan(adj: dict[str, set[str]]) -> list[list[str]]:
    """Iterative Tarjan's SCC — returns all SCCs with size > 1 (true cycles)."""
    index_map: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = [0]

    def _strongconnect(root: str) -> None:
        call_stack: list[tuple[str, Any]] = []

        def _visit(v: str) -> None:
            index_map[v] = counter[0]
            lowlink[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack[v] = True
            call_stack.append((v, iter(adj.get(v, set()))))

        _visit(root)
        while call_stack:
            v, nbrs = call_stack[-1]
            advanced = False
            for w in nbrs:
                if w not in index_map:
                    _visit(w)
                    advanced = True
                    break
                elif on_stack.get(w, False):
                    lowlink[v] = min(lowlink[v], index_map[w])
            if not advanced:
                call_stack.pop()
                if call_stack:
                    parent = call_stack[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])
                if lowlink[v] == index_map[v]:
                    scc: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        scc.append(w)
                        if w == v:
                            break
                    if len(scc) > 1:
                        sccs.append(scc)

    for node_id in list(adj.keys()):
        if node_id not in index_map:
            _strongconnect(node_id)

    return sccs


# ── Main Generator ─────────────────────────────────────────────────────────────


class LayeredDiagramGenerator:
    """Produces structured diagram data at three zoom levels."""

    def __init__(self, graph: GraphBuildResult) -> None:
        self._graph = graph
        self._node_by_id: dict[str, GraphNode] = {n.id: n for n in graph.nodes}

        self._files  = graph.nodes_by_type(NodeType.FILE)
        self._classes = graph.nodes_by_type(NodeType.CLASS)
        self._functions = graph.nodes_by_type(NodeType.FUNCTION)

        self._edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        self._edges_to:   dict[str, list[GraphEdge]] = defaultdict(list)
        for e in graph.edges:
            self._edges_from[e.source_id].append(e)
            self._edges_to[e.target_id].append(e)

        # file_id → top-level module name (architecturally meaningful)
        self._file_to_module: dict[str, str] = {}
        # module_name → list of file paths (for layer classification)
        self._module_file_paths: dict[str, list[str]] = defaultdict(list)
        for f in self._files:
            path = str(f.properties.get("path", f.label))
            mod = _top_level_module(path)
            self._file_to_module[f.id] = mod
            self._module_file_paths[mod].append(path)

        # class_id → file_id
        self._class_to_file: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship == RelationshipType.CONTAINS:
                src = self._node_by_id.get(e.source_id)
                tgt = self._node_by_id.get(e.target_id)
                if src and tgt:
                    if src.node_type == NodeType.FILE and tgt.node_type in (
                        NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
                    ):
                        self._class_to_file[tgt.id] = src.id

        # function_id → class_id
        self._function_to_class: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship == RelationshipType.CONTAINS:
                src = self._node_by_id.get(e.source_id)
                tgt = self._node_by_id.get(e.target_id)
                if src and tgt:
                    if src.node_type in (NodeType.CLASS, NodeType.INTERFACE) and \
                       tgt.node_type in (NodeType.FUNCTION, NodeType.METHOD):
                        self._function_to_class[tgt.id] = src.id

    # ── Level 1: System View ──────────────────────────────────────────────────

    def generate_system_view(self, repo_name: str = "") -> DiagramResult:
        """One node per top-level architectural module, aggregated edges.

        Target: ≤ MAX_SYSTEM_NODES nodes, ≤ MAX_SYSTEM_EDGES edges.

        The key design decisions:
        • MIN_EDGE_WEIGHT = 1.  Any cross-module import is an architectural
          relationship that must be shown.
        • Bidirectional edges (A→B and B→A) are collapsed to one edge
          annotated with "↔" so the diagram stays readable.
        • Modules are ranked by architectural significance and only the top
          MAX_SYSTEM_NODES are kept; the remainder are noted in drilldown.
        """
        _skip = {"__pycache__", "node_modules", ".git", "dist", "build",
                 ".venv", "venv", ".next", "coverage", ".pytest_cache"}

        # ── Collect modules and their file/class/line counts ─────────────────
        module_files:  dict[str, list[GraphNode]] = defaultdict(list)
        for f in self._files:
            mod = self._file_to_module.get(f.id, "other")
            if mod not in _skip:
                module_files[mod].append(f)

        # ── Build DiagramNode objects ─────────────────────────────────────────
        pre_nodes: list[DiagramNode] = []
        module_file_ids: dict[str, set[str]] = {}

        for mod_name, files in sorted(module_files.items()):
            if not files:
                continue
            file_ids = {f.id for f in files}
            module_file_ids[mod_name] = file_ids

            cls_count = sum(
                1 for c in self._classes
                if self._class_to_file.get(c.id) in file_ids
            )
            fn_count = sum(
                1 for fn in self._functions
                if any(
                    e.source_id in file_ids
                    for e in self._edges_to.get(fn.id, [])
                    if e.relationship == RelationshipType.CONTAINS
                )
            )
            line_count = sum(int(f.properties.get("lines", 0)) for f in files)
            endpoint_count = sum(int(f.properties.get("endpoints", 0)) for f in files)

            # Architectural layer using ALL file paths this module owns
            all_paths = self._module_file_paths.get(mod_name, [f.properties.get("path", "") for f in files])
            layer = _classify_layer_from_paths([str(p) for p in all_paths])

            pre_nodes.append(DiagramNode(
                id=f"mod_{mod_name}",
                label=mod_name,
                node_type="module",
                file_count=len(files),
                class_count=cls_count,
                function_count=fn_count,
                line_count=line_count,
                layer=layer,
                properties={"endpoint_count": endpoint_count},
            ))

        # ── Rank by architectural significance and cap ────────────────────────
        # Priority: endpoints > classes > file count > line count
        def _significance(n: DiagramNode) -> tuple[int, int, int, int]:
            ep = int(n.properties.get("endpoint_count", 0))
            return (ep, n.class_count, n.file_count, n.line_count)

        pre_nodes.sort(key=_significance, reverse=True)
        nodes = pre_nodes[:MAX_SYSTEM_NODES]
        hidden_count = len(pre_nodes) - len(nodes)

        kept_module_names: set[str] = {n.label for n in nodes}

        # ── Aggregate cross-module IMPORTS/DEPENDS_ON edges ───────────────────
        # Count raw imports per (source_module, target_module) pair.
        pair_count: dict[tuple[str, str], int] = defaultdict(int)
        for e in self._graph.edges:
            if e.relationship not in (
                RelationshipType.IMPORTS,
                RelationshipType.DEPENDS_ON,
            ):
                continue
            src_mod = self._file_to_module.get(e.source_id)
            tgt_mod = self._file_to_module.get(e.target_id)
            if not src_mod or not tgt_mod or src_mod == tgt_mod:
                continue
            if src_mod in _skip or tgt_mod in _skip:
                continue
            # Only count edges between modules that survived the cap.
            if src_mod not in kept_module_names or tgt_mod not in kept_module_names:
                continue
            pair_count[(src_mod, tgt_mod)] += 1

        # Collapse bidirectional pairs: keep the dominant direction, mark ↔.
        seen_pairs: set[frozenset[str]] = set()
        collapsed: list[tuple[str, str, int, bool]] = []  # (src, tgt, count, bidir)

        for (src, tgt), count in sorted(pair_count.items(), key=lambda x: -x[1]):
            key = frozenset({src, tgt})
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            rev = pair_count.get((tgt, src), 0)
            is_bidir = rev > 0
            if rev > count:
                collapsed.append((tgt, src, rev, is_bidir))
            else:
                collapsed.append((src, tgt, count, is_bidir))

        # Build DiagramEdge list — MIN_EDGE_WEIGHT = 1 (every import counts).
        edges: list[DiagramEdge] = []
        for src, tgt, count, is_bidir in collapsed:
            src_id = f"mod_{src}"
            tgt_id = f"mod_{tgt}"
            # Sanity-check: both nodes must be in the visible set.
            if src_id not in {n.id for n in nodes}:
                continue
            if tgt_id not in {n.id for n in nodes}:
                continue

            label = f"{count}" + (" ↔" if is_bidir else "")
            edges.append(DiagramEdge(
                id=f"e_{src}__{tgt}",
                source=src_id,
                target=tgt_id,
                label=label,
                edge_type="imports",
                weight=count,
            ))
            if len(edges) >= MAX_SYSTEM_EDGES:
                break

        # ── Cycle detection ───────────────────────────────────────────────────
        mod_adj: dict[str, set[str]] = defaultdict(set)
        for (src, tgt) in pair_count:
            mod_adj[f"mod_{src}"].add(f"mod_{tgt}")

        cycles = _detect_cycles_tarjan(mod_adj)

        cycle_node_ids: set[str] = set()
        for cycle in cycles:
            cycle_node_ids.update(cycle)

        for node in nodes:
            if node.id in cycle_node_ids:
                node.in_cycle = True
                node.health = "critical"
                node.health_reason = "Circular dependency detected"

        cycle_pairs: set[tuple[str, str]] = set()
        for cycle in cycles:
            for i in range(len(cycle)):
                a, b = cycle[i], cycle[(i + 1) % len(cycle)]
                cycle_pairs.add((a, b))
                cycle_pairs.add((b, a))

        for edge in edges:
            if (edge.source, edge.target) in cycle_pairs:
                edge.is_cycle = True

        # ── Health scoring (god class / large module) ─────────────────────────
        for node in nodes:
            if node.health != "critical":
                file_ids = module_file_ids.get(node.label, set())
                max_methods = max(
                    (int(c.properties.get("methods", 0))
                     for c in self._classes
                     if self._class_to_file.get(c.id) in file_ids),
                    default=0,
                )
                if max_methods > 20:
                    node.health = "warning"
                    node.health_reason = f"God class detected ({max_methods} methods)"
                elif node.file_count > 20:
                    node.health = "warning"
                    node.health_reason = f"Large module ({node.file_count} files)"

        drilldown = [
            {"id": n.id, "label": n.label, "type": "module"}
            for n in nodes
        ]
        if hidden_count:
            drilldown.append({
                "id": "_hidden",
                "label": f"+{hidden_count} more modules",
                "type": "info",
            })

        return DiagramResult(
            level="system",
            title=repo_name or "System Architecture",
            nodes=nodes,
            edges=edges,
            cycles=cycles,
            breadcrumb=[{"label": repo_name or "System", "level": "system"}],
            drilldown_targets=drilldown,
        )

    # ── Level 2: Module Detail ────────────────────────────────────────────────

    def generate_module_detail(
        self, module_name: str, repo_name: str = ""
    ) -> DiagramResult:
        """Classes and key files inside one module, plus collapsed external deps."""
        mod_files: list[GraphNode] = []
        mod_file_ids: set[str] = set()
        for f in self._files:
            if self._file_to_module.get(f.id) == module_name:
                mod_files.append(f)
                mod_file_ids.add(f.id)

        if not mod_files:
            return DiagramResult(
                level="module",
                title=f"{module_name} (not found)",
                breadcrumb=[
                    {"label": repo_name or "System", "level": "system"},
                    {"label": module_name, "level": "module"},
                ],
            )

        nodes: list[DiagramNode] = []
        edges: list[DiagramEdge] = []

        # Classes in this module
        mod_classes: list[GraphNode] = [
            c for c in self._classes
            if self._class_to_file.get(c.id) in mod_file_ids
        ]

        for c in mod_classes:
            methods = int(c.properties.get("methods", 0))
            lines   = int(c.properties.get("lines", 0))
            health, health_reason = "healthy", ""
            if methods > 20:
                health, health_reason = "critical", f"God class: {methods} methods"
            elif methods > 12:
                health, health_reason = "warning",  f"Large class: {methods} methods"

            # Determine sub-layer from file path for display
            file_id  = self._class_to_file.get(c.id, "")
            file_node = self._node_by_id.get(file_id)
            fp = str(file_node.properties.get("path", "")) if file_node else ""
            sub_layer = _classify_layer_from_paths([fp]) if fp else ""

            nodes.append(DiagramNode(
                id=c.id,
                label=c.label,
                node_type="class",
                function_count=methods,
                line_count=lines,
                health=health,
                health_reason=health_reason,
                layer=sub_layer,
                properties={"file": file_id},
            ))

        # File nodes that have no classes (scripted files, config, etc.)
        class_file_ids = {self._class_to_file.get(c.id) for c in mod_classes}
        for f in mod_files:
            fn_count  = int(f.properties.get("functions", 0))
            cls_count = int(f.properties.get("classes", 0))
            if f.id in class_file_ids and fn_count == 0:
                continue
            if fn_count == 0 and cls_count == 0:
                continue
            fp = str(f.properties.get("path", f.label))
            sub_layer = _classify_layer_from_paths([fp])
            nodes.append(DiagramNode(
                id=f.id,
                label=f.label,
                node_type="file",
                function_count=fn_count,
                line_count=int(f.properties.get("lines", 0)),
                layer=sub_layer,
            ))

        node_ids = {n.id for n in nodes}

        # Inheritance edges between classes in this module
        for e in self._graph.edges:
            if e.relationship == RelationshipType.INHERITS:
                if e.source_id in node_ids and e.target_id in node_ids:
                    edges.append(DiagramEdge(
                        id=e.id,
                        source=e.source_id,
                        target=e.target_id,
                        label="extends",
                        edge_type="inherits",
                    ))

        # Import edges between nodes inside this module (deduped)
        seen: set[tuple[str, str]] = set()
        for e in self._graph.edges:
            if e.relationship not in (
                RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON
            ):
                continue
            sid = e.source_id if e.source_id in node_ids else None
            tid = e.target_id if e.target_id in node_ids else None
            if sid and tid and sid != tid:
                pair = (sid, tid)
                if pair not in seen:
                    seen.add(pair)
                    edges.append(DiagramEdge(
                        id=f"e_{sid}__{tid}",
                        source=sid,
                        target=tid,
                        edge_type="imports",
                    ))

        # External dependency summary (collapsed, top 8 by import count)
        external_counts: dict[str, int] = defaultdict(int)
        for f in mod_files:
            for e in self._edges_from.get(f.id, []):
                if e.relationship not in (
                    RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON
                ):
                    continue
                tgt_mod = self._file_to_module.get(e.target_id)
                if tgt_mod and tgt_mod != module_name:
                    external_counts[tgt_mod] += 1

        # Root node representing "this module" for external edges
        root_id = f"modroot_{module_name}"
        has_external = bool(external_counts)
        if has_external:
            nodes.insert(0, DiagramNode(
                id=root_id,
                label=f"{module_name}/",
                node_type="module",
                file_count=len(mod_files),
                class_count=len(mod_classes),
            ))

        for ext_mod, count in sorted(
            external_counts.items(), key=lambda x: -x[1]
        )[:8]:
            ext_id = f"ext_{ext_mod}"
            nodes.append(DiagramNode(
                id=ext_id,
                label=ext_mod,
                node_type="external",
                properties={"collapsed": True},
            ))
            edges.append(DiagramEdge(
                id=f"e_{module_name}__{ext_mod}",
                source=root_id,
                target=ext_id,
                label=f"{count}",
                edge_type="imports",
                weight=count,
            ))

        # Cycle detection within this module
        internal_adj: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.edge_type == "imports" and \
               edge.source in node_ids and edge.target in node_ids:
                internal_adj[edge.source].add(edge.target)

        cycles = _detect_cycles_tarjan(internal_adj)
        cycle_ids: set[str] = {n for scc in cycles for n in scc}
        for node in nodes:
            if node.id in cycle_ids:
                node.in_cycle = True
                if node.health == "healthy":
                    node.health = "warning"
                    node.health_reason = "Part of circular dependency"

        drilldown = [
            {"id": n.id, "label": n.label, "type": "class"}
            for n in nodes if n.node_type == "class"
        ]

        return DiagramResult(
            level="module",
            title=f"{module_name}/",
            nodes=nodes,
            edges=edges,
            cycles=cycles,
            breadcrumb=[
                {"label": repo_name or "System", "level": "system"},
                {"label": module_name, "level": "module", "module": module_name},
            ],
            drilldown_targets=drilldown,
        )

    # ── Level 3: Class Detail ─────────────────────────────────────────────────

    def generate_class_detail(
        self, class_name: str, repo_name: str = ""
    ) -> DiagramResult:
        """Methods, callers, callees, and inheritance chain for one class."""
        target: GraphNode | None = next(
            (c for c in self._classes if c.label == class_name), None
        )
        if not target:
            return DiagramResult(
                level="class",
                title=f"{class_name} (not found)",
                breadcrumb=[
                    {"label": repo_name or "System", "level": "system"},
                    {"label": class_name, "level": "class"},
                ],
            )

        file_id   = self._class_to_file.get(target.id, "")
        module_name = self._file_to_module.get(file_id, "unknown")

        nodes: list[DiagramNode] = []
        edges: list[DiagramEdge] = []

        # Central node
        nodes.append(DiagramNode(
            id=target.id,
            label=target.label,
            node_type="class",
            function_count=int(target.properties.get("methods", 0)),
            line_count=int(target.properties.get("lines", 0)),
            properties={"central": True},
        ))

        # Methods
        for e in self._edges_from.get(target.id, []):
            if e.relationship == RelationshipType.CONTAINS:
                method = self._node_by_id.get(e.target_id)
                if method and method.node_type in (NodeType.FUNCTION, NodeType.METHOD):
                    nodes.append(DiagramNode(
                        id=method.id,
                        label=method.label,
                        node_type="function",
                        line_count=int(method.properties.get("lines", 0)),
                        properties={
                            "decorators": method.properties.get("decorators", "")
                        },
                    ))
                    edges.append(DiagramEdge(
                        id=f"e_has_{target.id}__{method.id}",
                        source=target.id,
                        target=method.id,
                        edge_type="contains",
                        label="has",
                    ))

        # Parents (what this class extends)
        for e in self._edges_from.get(target.id, []):
            if e.relationship == RelationshipType.INHERITS:
                parent = self._node_by_id.get(e.target_id)
                if parent:
                    nodes.append(DiagramNode(
                        id=parent.id,
                        label=parent.label,
                        node_type="class",
                        properties={"role": "parent"},
                    ))
                    edges.append(DiagramEdge(
                        id=f"e_inherits_{target.id}__{parent.id}",
                        source=target.id,
                        target=parent.id,
                        edge_type="inherits",
                        label="extends",
                    ))

        # Children (what extends this class)
        for e in self._edges_to.get(target.id, []):
            if e.relationship == RelationshipType.INHERITS:
                child = self._node_by_id.get(e.source_id)
                if child:
                    nodes.append(DiagramNode(
                        id=child.id,
                        label=child.label,
                        node_type="class",
                        properties={"role": "child"},
                    ))
                    edges.append(DiagramEdge(
                        id=f"e_inherits_{child.id}__{target.id}",
                        source=child.id,
                        target=target.id,
                        edge_type="inherits",
                        label="extends",
                    ))

        # Callers (files that import the file containing this class)
        if file_id:
            for e in self._edges_to.get(file_id, []):
                if e.relationship in (
                    RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON
                ):
                    caller = self._node_by_id.get(e.source_id)
                    if caller and caller.node_type == NodeType.FILE:
                        caller_mod = self._file_to_module.get(caller.id, "")
                        caller_id  = f"caller_{caller.id}"
                        label = f"{caller_mod}/{caller.label}" if caller_mod else caller.label
                        nodes.append(DiagramNode(
                            id=caller_id,
                            label=label,
                            node_type="file",
                            properties={"role": "caller"},
                        ))
                        edges.append(DiagramEdge(
                            id=f"e_uses_{caller.id}__{target.id}",
                            source=caller_id,
                            target=target.id,
                            edge_type="imports",
                            label="uses",
                        ))

        # Callees (files this class's file imports)
        if file_id:
            for e in self._edges_from.get(file_id, []):
                if e.relationship in (
                    RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON
                ):
                    dep = self._node_by_id.get(e.target_id)
                    if dep and dep.node_type == NodeType.FILE:
                        dep_mod = self._file_to_module.get(dep.id, "")
                        dep_id  = f"dep_{dep.id}"
                        label   = f"{dep_mod}/{dep.label}" if dep_mod else dep.label
                        nodes.append(DiagramNode(
                            id=dep_id,
                            label=label,
                            node_type="file",
                            properties={"role": "dependency"},
                        ))
                        edges.append(DiagramEdge(
                            id=f"e_dep_{target.id}__{dep.id}",
                            source=target.id,
                            target=dep_id,
                            edge_type="imports",
                            label="depends on",
                        ))

        # Cap callers / callees at 8 each
        def _cap_by_role(role: str, cap: int) -> None:
            role_nodes = [n for n in nodes if n.properties.get("role") == role]
            if len(role_nodes) <= cap:
                return
            excess = role_nodes[cap:]
            excess_ids = {n.id for n in excess}
            nodes[:] = [n for n in nodes if n.id not in excess_ids]
            edges[:] = [e for e in edges
                        if e.source not in excess_ids and e.target not in excess_ids]
            overflow_id = f"overflow_{role}"
            nodes.append(DiagramNode(
                id=overflow_id,
                label=f"+{len(excess)} more {role}s",
                node_type="external",
            ))
            if role == "caller":
                edges.append(DiagramEdge(
                    id=f"e_{overflow_id}",
                    source=overflow_id,
                    target=target.id,
                    edge_type="imports",
                ))
            else:
                edges.append(DiagramEdge(
                    id=f"e_{overflow_id}",
                    source=target.id,
                    target=overflow_id,
                    edge_type="imports",
                ))

        _cap_by_role("caller", 8)
        _cap_by_role("dependency", 8)

        return DiagramResult(
            level="class",
            title=class_name,
            nodes=nodes,
            edges=edges,
            cycles=[],
            breadcrumb=[
                {"label": repo_name or "System", "level": "system"},
                {"label": module_name, "level": "module", "module": module_name},
                {"label": class_name, "level": "class", "class": class_name},
            ],
            drilldown_targets=[],
        )
