"""Layered Diagram Generator — produces structured JSON for a multi-level
architecture diagram (React Flow frontend).

Three zoom levels:
  Level 1 — System View: one node per top-level module, aggregated edges.
  Level 2 — Module Detail: classes/files inside one module + collapsed deps.
  Level 3 — Class Detail: methods, callers, callees, inheritance chain.

Output is plain dicts/lists (JSON-serializable) that the frontend React Flow
component consumes directly. No Mermaid syntax.
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


# ── Data structures for the JSON response ─────────────────────────────────────


@dataclass
class DiagramNode:
    """A single node in the diagram."""
    id: str
    label: str
    node_type: str  # "module", "file", "class", "function", "external"
    # Metadata for visual encoding
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    line_count: int = 0
    # Health coloring
    health: str = "healthy"  # "healthy", "warning", "critical"
    health_reason: str = ""
    # Whether this node is part of a cycle
    in_cycle: bool = False
    # Extra properties for the frontend
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
            "properties": self.properties,
        }


@dataclass
class DiagramEdge:
    """A single edge in the diagram."""
    id: str
    source: str
    target: str
    label: str = ""
    edge_type: str = "imports"  # "imports", "inherits", "calls", "contains"
    weight: int = 1  # aggregated count for system view
    is_cycle: bool = False  # part of a circular dependency

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
    level: str  # "system", "module", "class"
    title: str
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    # Cycles detected at this level (lists of node IDs)
    cycles: list[list[str]] = field(default_factory=list)
    # Breadcrumb path for navigation
    breadcrumb: list[dict[str, str]] = field(default_factory=list)
    # Available drill-down targets
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


# ── Helpers ───────────────────────────────────────────────────────────────────


def _top_level_module(path: str) -> str:
    """Extract the top-level module name from a file/module path.

    e.g. "backend/src/cortex/chat/application/chat_service.py" -> "chat"
         "frontend/src/features/jobs/components/JobCard.tsx" -> "features"

    Strategy: look for known container dirs (src/cortex, src/app, src/features,
    src/lib, src/components) and take the next segment. Fall back to first
    meaningful directory.
    """
    parts = path.replace("\\", "/").split("/")
    # Strip empty parts
    parts = [p for p in parts if p]

    # Known container patterns — we want the segment AFTER these
    containers = [
        ["backend", "src", "cortex"],
        ["src", "cortex"],
        ["frontend", "src"],
        ["src"],
    ]

    for container in containers:
        clen = len(container)
        for i in range(len(parts) - clen):
            if parts[i:i + clen] == container:
                # The next part is the top-level module
                idx = i + clen
                if idx < len(parts):
                    candidate = parts[idx]
                    # Don't return a filename as a module
                    if "." not in candidate:
                        return candidate
                    # If it's a file directly in the container, use the container's last part
                    return container[-1]

    # Fallback: first directory that isn't a known root
    skip = {"backend", "frontend", "src", "lib", "app"}
    for p in parts:
        if p not in skip and "." not in p:
            return p

    return parts[0] if parts else "root"


def _detect_cycles_tarjan(
    adj: dict[str, set[str]],
) -> list[list[str]]:
    """Iterative Tarjan's SCC — returns all cycles (SCCs with size > 1)."""
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


# ── Main Generator ────────────────────────────────────────────────────────────


class LayeredDiagramGenerator:
    """Produces structured diagram data at three zoom levels."""

    def __init__(self, graph: GraphBuildResult) -> None:
        self._graph = graph
        self._node_by_id: dict[str, GraphNode] = {n.id: n for n in graph.nodes}

        # Pre-compute indices
        self._files = graph.nodes_by_type(NodeType.FILE)
        self._classes = graph.nodes_by_type(NodeType.CLASS)
        self._functions = graph.nodes_by_type(NodeType.FUNCTION)
        self._modules = graph.nodes_by_type(NodeType.MODULE)

        # Edge indices
        self._edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        self._edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for e in graph.edges:
            self._edges_from[e.source_id].append(e)
            self._edges_to[e.target_id].append(e)

        # File -> module mapping
        self._file_to_module: dict[str, str] = {}
        for f in self._files:
            path = str(f.properties.get("path", f.label))
            self._file_to_module[f.id] = _top_level_module(path)

        # Class -> file mapping
        self._class_to_file: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship == RelationshipType.CONTAINS:
                src = self._node_by_id.get(e.source_id)
                tgt = self._node_by_id.get(e.target_id)
                if src and tgt:
                    if src.node_type == NodeType.FILE and tgt.node_type == NodeType.CLASS:
                        self._class_to_file[tgt.id] = src.id

        # Function -> class mapping
        self._function_to_class: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship == RelationshipType.CONTAINS:
                src = self._node_by_id.get(e.source_id)
                tgt = self._node_by_id.get(e.target_id)
                if src and tgt:
                    if src.node_type == NodeType.CLASS and tgt.node_type == NodeType.FUNCTION:
                        self._function_to_class[tgt.id] = src.id

    # ── Level 1: System View ─────────────────────────────────────────────────

    def generate_system_view(self, repo_name: str = "") -> DiagramResult:
        """One node per top-level module, aggregated edges with counts.

        Target: <20 nodes, <30 edges for a typical mid-size repo.
        """
        # Group files by top-level module
        module_files: dict[str, list[GraphNode]] = defaultdict(list)
        for f in self._files:
            mod = self._file_to_module.get(f.id, "other")
            module_files[mod].append(f)

        # Skip modules with zero meaningful content
        skip_modules = {"__pycache__", "node_modules", ".git", "dist", "build"}

        # Build module nodes
        nodes: list[DiagramNode] = []
        module_file_ids: dict[str, set[str]] = {}  # module_name -> set of file IDs

        for mod_name, files in sorted(module_files.items()):
            if mod_name in skip_modules:
                continue
            if not files:
                continue

            file_ids = {f.id for f in files}
            module_file_ids[mod_name] = file_ids

            # Count classes and functions in this module
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
                or self._function_to_class.get(fn.id) in {
                    c.id for c in self._classes
                    if self._class_to_file.get(c.id) in file_ids
                }
            )
            line_count = sum(int(f.properties.get("lines", 0)) for f in files)

            nodes.append(DiagramNode(
                id=f"mod_{mod_name}",
                label=mod_name,
                node_type="module",
                file_count=len(files),
                class_count=cls_count,
                function_count=fn_count,
                line_count=line_count,
            ))

        # Build aggregated edges between modules
        # Count imports between each module pair
        module_pair_count: dict[tuple[str, str], int] = defaultdict(int)

        for e in self._graph.edges:
            if e.relationship not in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                continue
            src_mod = self._file_to_module.get(e.source_id)
            tgt_mod = self._file_to_module.get(e.target_id)
            if src_mod and tgt_mod and src_mod != tgt_mod:
                if src_mod not in skip_modules and tgt_mod not in skip_modules:
                    module_pair_count[(src_mod, tgt_mod)] += 1

        # Deduplicate bidirectional edges: if A->B and B->A both exist,
        # keep only the stronger direction and note it's bidirectional
        seen_pairs: set[frozenset[str]] = set()
        deduped_edges: list[tuple[str, str, int, bool]] = []  # src, tgt, count, is_bidir

        for (src_mod, tgt_mod), count in sorted(
            module_pair_count.items(), key=lambda x: x[1], reverse=True
        ):
            pair_key = frozenset([src_mod, tgt_mod])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            reverse_count = module_pair_count.get((tgt_mod, src_mod), 0)
            is_bidir = reverse_count > 0
            # Keep the stronger direction
            if reverse_count > count:
                deduped_edges.append((tgt_mod, src_mod, reverse_count, is_bidir))
            else:
                deduped_edges.append((src_mod, tgt_mod, count, is_bidir))

        edges: list[DiagramEdge] = []
        # Only keep edges with meaningful weight (>=2 imports) and cap at 25
        # to stay within the "under 30 edges" target. Sorted by weight desc
        # so we keep the most significant relationships.
        MAX_SYSTEM_EDGES = 25
        MIN_EDGE_WEIGHT = 2

        for (src_mod, tgt_mod, count, is_bidir) in deduped_edges:
            if count < MIN_EDGE_WEIGHT:
                continue
                continue
            # Only include edges where both modules are in our node set
            src_id = f"mod_{src_mod}"
            tgt_id = f"mod_{tgt_mod}"
            if not any(n.id == src_id for n in nodes):
                continue
            if not any(n.id == tgt_id for n in nodes):
                continue

            edges.append(DiagramEdge(
                id=f"e_{src_mod}__{tgt_mod}",
                source=src_id,
                target=tgt_id,
                label=f"{count} imports{'  ↔' if is_bidir else ''}",
                edge_type="imports",
                weight=count,
            ))
            if len(edges) >= MAX_SYSTEM_EDGES:
                break

        # Detect cycles at module level
        mod_adj: dict[str, set[str]] = defaultdict(set)
        for (src, tgt) in module_pair_count.keys():
            mod_adj[f"mod_{src}"].add(f"mod_{tgt}")

        cycles = _detect_cycles_tarjan(mod_adj)

        # Mark nodes and edges that are part of cycles
        cycle_node_ids: set[str] = set()
        for cycle in cycles:
            cycle_node_ids.update(cycle)

        for node in nodes:
            if node.id in cycle_node_ids:
                node.in_cycle = True
                node.health = "critical"
                node.health_reason = "Circular dependency detected"

        # Mark cycle edges
        cycle_pairs: set[tuple[str, str]] = set()
        for cycle in cycles:
            for i in range(len(cycle)):
                a = cycle[i]
                b = cycle[(i + 1) % len(cycle)]
                cycle_pairs.add((a, b))
                cycle_pairs.add((b, a))

        for edge in edges:
            if (edge.source, edge.target) in cycle_pairs:
                edge.is_cycle = True

        # Health scoring: god classes, high coupling
        for node in nodes:
            if node.health != "critical":  # don't override cycle status
                if node.class_count > 0:
                    # Check for god classes (>20 methods in any class)
                    mod_files = module_file_ids.get(node.label, set())
                    max_methods = 0
                    for c in self._classes:
                        if self._class_to_file.get(c.id) in mod_files:
                            methods = int(c.properties.get("methods", 0))
                            max_methods = max(max_methods, methods)
                    if max_methods > 20:
                        node.health = "warning"
                        node.health_reason = f"God class detected ({max_methods} methods)"
                    elif node.file_count > 15:
                        node.health = "warning"
                        node.health_reason = f"Large module ({node.file_count} files)"

        # Build drilldown targets
        drilldown = [
            {"id": n.id, "label": n.label, "type": "module"}
            for n in nodes
        ]

        return DiagramResult(
            level="system",
            title=repo_name or "System Architecture",
            nodes=nodes,
            edges=edges,
            cycles=[c for c in cycles],
            breadcrumb=[{"label": repo_name or "System", "level": "system"}],
            drilldown_targets=drilldown,
        )

    # ── Level 2: Module Detail ────────────────────────────────────────────────

    def generate_module_detail(
        self, module_name: str, repo_name: str = ""
    ) -> DiagramResult:
        """Shows classes and key files inside ONE module, plus collapsed external deps.

        Nodes: classes and important files within the module.
        External dependencies shown as collapsed single-node references.
        """
        # Find all files in this module
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
        mod_classes: list[GraphNode] = []
        for c in self._classes:
            file_id = self._class_to_file.get(c.id)
            if file_id in mod_file_ids:
                mod_classes.append(c)

        # Add class nodes
        for c in mod_classes:
            methods = int(c.properties.get("methods", 0))
            lines = int(c.properties.get("lines", 0))
            health = "healthy"
            health_reason = ""
            if methods > 20:
                health = "critical"
                health_reason = f"God class: {methods} methods"
            elif methods > 12:
                health = "warning"
                health_reason = f"Large class: {methods} methods"

            nodes.append(DiagramNode(
                id=c.id,
                label=c.label,
                node_type="class",
                function_count=methods,
                line_count=lines,
                health=health,
                health_reason=health_reason,
                properties={"file": self._class_to_file.get(c.id, "")},
            ))

        # Add file nodes (only files that have no classes, or are important)
        class_file_ids = {self._class_to_file.get(c.id) for c in mod_classes}
        for f in mod_files:
            # Skip files that are already represented by their classes
            if f.id in class_file_ids and int(f.properties.get("functions", 0)) == 0:
                continue
            fn_count = int(f.properties.get("functions", 0))
            if fn_count == 0 and int(f.properties.get("classes", 0)) == 0:
                continue  # Skip empty/trivial files

            nodes.append(DiagramNode(
                id=f.id,
                label=f.label,
                node_type="file",
                function_count=fn_count,
                line_count=int(f.properties.get("lines", 0)),
            ))

        # Internal edges: inheritance between classes in this module
        for e in self._graph.edges:
            if e.relationship == RelationshipType.INHERITS:
                src_in = any(n.id == e.source_id for n in nodes)
                tgt_in = any(n.id == e.target_id for n in nodes)
                if src_in and tgt_in:
                    edges.append(DiagramEdge(
                        id=e.id,
                        source=e.source_id,
                        target=e.target_id,
                        label="extends",
                        edge_type="inherits",
                    ))

        # Internal edges: imports between files/classes in this module
        node_ids = {n.id for n in nodes}
        seen_pairs: set[tuple[str, str]] = set()
        for e in self._graph.edges:
            if e.relationship not in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                continue
            # Map to our visible nodes
            src_id = e.source_id if e.source_id in node_ids else None
            tgt_id = e.target_id if e.target_id in node_ids else None
            if src_id and tgt_id and src_id != tgt_id:
                pair = (src_id, tgt_id)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    edges.append(DiagramEdge(
                        id=f"e_{src_id}__{tgt_id}",
                        source=src_id,
                        target=tgt_id,
                        edge_type="imports",
                    ))

        # External dependencies: collapsed boxes for other modules
        external_modules: dict[str, int] = defaultdict(int)  # mod_name -> import count
        for f in mod_files:
            for e in self._edges_from.get(f.id, []):
                if e.relationship not in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                    continue
                tgt_mod = self._file_to_module.get(e.target_id)
                if tgt_mod and tgt_mod != module_name:
                    external_modules[tgt_mod] += 1

        for ext_mod, count in sorted(external_modules.items(), key=lambda x: -x[1])[:8]:
            ext_id = f"ext_{ext_mod}"
            nodes.append(DiagramNode(
                id=ext_id,
                label=ext_mod,
                node_type="external",
                properties={"collapsed": True},
            ))
            edges.append(DiagramEdge(
                id=f"e_{module_name}__{ext_mod}",
                source=f"mod_{module_name}",  # Will be mapped to first internal node
                target=ext_id,
                label=f"{count} imports",
                edge_type="imports",
                weight=count,
            ))

        # Fix external edge sources — point to the module's internal nodes collectively
        # We'll use a special "module root" node
        if external_modules:
            # Replace the source with a virtual module-root node
            root_id = f"modroot_{module_name}"
            nodes.insert(0, DiagramNode(
                id=root_id,
                label=f"{module_name}/",
                node_type="module",
                file_count=len(mod_files),
                class_count=len(mod_classes),
            ))
            for edge in edges:
                if edge.source == f"mod_{module_name}":
                    edge.source = root_id

        # Detect cycles within this module
        internal_adj: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.edge_type == "imports" and edge.source in node_ids and edge.target in node_ids:
                internal_adj[edge.source].add(edge.target)

        cycles = _detect_cycles_tarjan(internal_adj)
        cycle_ids: set[str] = set()
        for cycle in cycles:
            cycle_ids.update(cycle)
        for node in nodes:
            if node.id in cycle_ids:
                node.in_cycle = True
                if node.health == "healthy":
                    node.health = "warning"
                    node.health_reason = "Part of circular dependency"

        # Drilldown targets: classes that can be clicked
        drilldown = [
            {"id": n.id, "label": n.label, "type": "class"}
            for n in nodes
            if n.node_type == "class"
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
        """Shows one class's methods, callers/callees, and inheritance chain."""
        # Find the class node
        target_class: GraphNode | None = None
        for c in self._classes:
            if c.label == class_name:
                target_class = c
                break

        if not target_class:
            return DiagramResult(
                level="class",
                title=f"{class_name} (not found)",
                breadcrumb=[
                    {"label": repo_name or "System", "level": "system"},
                    {"label": class_name, "level": "class"},
                ],
            )

        # Determine which module this class belongs to
        file_id = self._class_to_file.get(target_class.id, "")
        module_name = self._file_to_module.get(file_id, "unknown")

        nodes: list[DiagramNode] = []
        edges: list[DiagramEdge] = []

        # The class itself as the central node
        methods_count = int(target_class.properties.get("methods", 0))
        nodes.append(DiagramNode(
            id=target_class.id,
            label=target_class.label,
            node_type="class",
            function_count=methods_count,
            line_count=int(target_class.properties.get("lines", 0)),
            properties={"central": True},
        ))

        # Methods of this class
        for e in self._edges_from.get(target_class.id, []):
            if e.relationship == RelationshipType.CONTAINS:
                method = self._node_by_id.get(e.target_id)
                if method and method.node_type == NodeType.FUNCTION:
                    nodes.append(DiagramNode(
                        id=method.id,
                        label=method.label,
                        node_type="function",
                        line_count=int(method.properties.get("lines", 0)),
                        properties={"decorators": method.properties.get("decorators", "")},
                    ))
                    edges.append(DiagramEdge(
                        id=f"e_contains_{target_class.id}__{method.id}",
                        source=target_class.id,
                        target=method.id,
                        edge_type="contains",
                        label="has",
                    ))

        # Inheritance: what this class extends
        for e in self._edges_from.get(target_class.id, []):
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
                        id=f"e_inherits_{target_class.id}__{parent.id}",
                        source=target_class.id,
                        target=parent.id,
                        edge_type="inherits",
                        label="extends",
                    ))

        # Inheritance: what extends this class
        for e in self._edges_to.get(target_class.id, []):
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
                        id=f"e_inherits_{child.id}__{target_class.id}",
                        source=child.id,
                        target=target_class.id,
                        edge_type="inherits",
                        label="extends",
                    ))

        # Callers: who imports the file containing this class
        if file_id:
            for e in self._edges_to.get(file_id, []):
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                    caller_file = self._node_by_id.get(e.source_id)
                    if caller_file and caller_file.node_type == NodeType.FILE:
                        caller_mod = self._file_to_module.get(caller_file.id, "")
                        caller_id = f"caller_{caller_file.id}"
                        nodes.append(DiagramNode(
                            id=caller_id,
                            label=f"{caller_mod}/{caller_file.label}" if caller_mod else caller_file.label,
                            node_type="file",
                            properties={"role": "caller"},
                        ))
                        edges.append(DiagramEdge(
                            id=f"e_calls_{caller_file.id}__{target_class.id}",
                            source=caller_id,
                            target=target_class.id,
                            edge_type="imports",
                            label="uses",
                        ))

        # Callees: what this class's file imports
        if file_id:
            for e in self._edges_from.get(file_id, []):
                if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                    dep_file = self._node_by_id.get(e.target_id)
                    if dep_file and dep_file.node_type == NodeType.FILE:
                        dep_mod = self._file_to_module.get(dep_file.id, "")
                        dep_id = f"dep_{dep_file.id}"
                        nodes.append(DiagramNode(
                            id=dep_id,
                            label=f"{dep_mod}/{dep_file.label}" if dep_mod else dep_file.label,
                            node_type="file",
                            properties={"role": "dependency"},
                        ))
                        edges.append(DiagramEdge(
                            id=f"e_dep_{target_class.id}__{dep_file.id}",
                            source=target_class.id,
                            target=dep_id,
                            edge_type="imports",
                            label="depends on",
                        ))

        # Cap callers/callees to prevent overload
        caller_nodes = [n for n in nodes if n.properties.get("role") == "caller"]
        dep_nodes = [n for n in nodes if n.properties.get("role") == "dependency"]

        if len(caller_nodes) > 8:
            # Keep top 8 callers, remove the rest
            excess = caller_nodes[8:]
            excess_ids = {n.id for n in excess}
            nodes = [n for n in nodes if n.id not in excess_ids]
            edges = [e for e in edges if e.source not in excess_ids and e.target not in excess_ids]
            # Add summary node
            nodes.append(DiagramNode(
                id="callers_overflow",
                label=f"+{len(excess)} more callers",
                node_type="external",
            ))
            edges.append(DiagramEdge(
                id="e_callers_overflow",
                source="callers_overflow",
                target=target_class.id,
                edge_type="imports",
            ))

        if len(dep_nodes) > 8:
            excess = dep_nodes[8:]
            excess_ids = {n.id for n in excess}
            nodes = [n for n in nodes if n.id not in excess_ids]
            edges = [e for e in edges if e.source not in excess_ids and e.target not in excess_ids]
            nodes.append(DiagramNode(
                id="deps_overflow",
                label=f"+{len(excess)} more dependencies",
                node_type="external",
            ))
            edges.append(DiagramEdge(
                id="e_deps_overflow",
                source=target_class.id,
                target="deps_overflow",
                edge_type="imports",
            ))

        return DiagramResult(
            level="class",
            title=target_class.label,
            nodes=nodes,
            edges=edges,
            cycles=[],
            breadcrumb=[
                {"label": repo_name or "System", "level": "system"},
                {"label": module_name, "level": "module", "module": module_name},
                {"label": target_class.label, "level": "class", "class": class_name},
            ],
            drilldown_targets=[],
        )
