"""Architecture Diagram Generator — Mermaid-based architecture artifact.

Produces a Markdown document containing Mermaid flowchart diagrams at two
complementary levels:

  System view  — one node per real architectural module, cross-module edges.
  Layer flow   — one node per detected layer, aggregated inter-layer edges.

──────────────────────────────────────────────────────────────────────────────
Design rules (what makes this NOT a dependency dump)
──────────────────────────────────────────────────────────────────────────────
1. ONLY architecturally meaningful modules are shown.
   Pure container directories — those whose name matches _GENERIC_CONTAINERS
   (src, backend, frontend, lib, app…) — are skipped.  Every repo has these
   structural wrapping directories; they add no architectural signal.

2. Module names are UNIQUE in the diagram.  The graph can contain two modules
   both named "src" (one under backend/, one under frontend/).  Both are
   excluded as generic containers.  If a name collision survives, the full
   path is used as the display label.

3. Edges are AGGREGATED.  Many file-level imports between the same two modules
   become ONE edge labelled with the count.  Bidirectional pairs are collapsed
   to a single arrow annotated "↔".

4. Minimum edge weight is 1.  A single cross-module import IS an
   architectural dependency and MUST be shown.

5. Layer classification uses ALL path segments of the files a module owns so
   that classification is based on evidence, not on a single directory name.

6. Layer-violation detection: edges that cross layers in the wrong direction
   are rendered as red dashed arrows with a ⚠ annotation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cortex.graph.domain.entities import GraphNode, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.pipeline.infrastructure.layered_diagram_generator import (
    _classify_layer_from_paths,
    _top_level_module,
    _LAYER_ORDER,
    MAX_SYSTEM_NODES,
    MAX_SYSTEM_EDGES,
)


# ── Module representation ──────────────────────────────────────────────────────


@dataclass
class _ModNode:
    """A module as it appears in the system architecture view."""
    id: str            # unique, Mermaid-safe
    name: str          # display name
    path: str          # full module path (for deduplication)
    layer: str
    file_count: int = 0
    class_count: int = 0
    endpoint_count: int = 0
    complexity: int = 0


@dataclass
class _ModEdge:
    """Aggregated dependency between two modules."""
    source: str   # module name
    target: str   # module name
    weight: int = 1
    is_bidir: bool = False


# ── Constants ──────────────────────────────────────────────────────────────────

# Generic container-directory names that carry no architectural meaning on
# their own.  Modules whose ONLY name matches one of these are excluded from
# the diagram.  (Shared with layered_diagram_generator via the imported helper.)
_GENERIC_CONTAINERS: frozenset[str] = frozenset({
    "src", "backend", "frontend", "lib", "app", "core", "main",
    "source", "sources", "pkg", "packages", "modules",
})

# Expected layer rank for violation detection (lower = closer to user).
_LAYER_RANK: dict[str, int] = {
    "Presentation": 0,
    "Frontend":     0,
    "Application":  1,
    "Domain":       2,
    "Infrastructure": 3,
    "Shared":       4,
    "Testing":      5,
    "Other":        3,
}


class ArchitectureDiagramGenerator:
    """Generates a Markdown + Mermaid architecture artifact from the graph."""

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Return the full Markdown architecture document."""
        files = graph.nodes_by_type(NodeType.FILE)
        if not files:
            return f"# Architecture — {repo_name}\n\n_No code structure detected._\n"

        mod_nodes, mod_edges = self._build_module_graph(graph, files)

        if not mod_nodes:
            return (
                f"# Architecture — {repo_name}\n\n"
                "_No architectural modules detected.  "
                "The repository may use a flat structure or a non-standard layout._\n"
            )

        lines: list[str] = []
        lines += [
            f"# Architecture — {repo_name}",
            "",
            "> **Architecture diagram** — each box is a top-level module; "
            "arrows show which modules depend on which.  "
            "An arrow from **A → B** means A imports something from B.",
            "",
        ]

        # ── Section 1: System overview ────────────────────────────────────────
        lines += [
            "## System Architecture",
            "",
            "One node per top-level module.  "
            "Arrow thickness reflects the number of individual imports "
            "(thick = strong coupling, thin = light coupling).",
            "",
            "```mermaid",
            self._render_system_mermaid(mod_nodes, mod_edges, repo_name),
            "```",
            "",
        ]

        # ── Section 2: Module summary table ───────────────────────────────────
        lines += [
            "### Module Summary",
            "",
            "| Module | Layer | Files | Classes | Endpoints | Complexity |",
            "|--------|-------|-------|---------|-----------|-----------|",
        ]
        for mod in sorted(mod_nodes, key=lambda m: (_LAYER_ORDER.index(m.layer)
                                                     if m.layer in _LAYER_ORDER else 99,
                                                     m.name)):
            lines.append(
                f"| `{mod.name}` | {mod.layer} | {mod.file_count} | "
                f"{mod.class_count} | {mod.endpoint_count} | {mod.complexity} |"
            )
        lines.append("")

        hidden = getattr(self, "_hidden_count", 0)
        if hidden:
            lines += [
                f"_Showing the {len(mod_nodes)} most significant modules; "
                f"{hidden} smaller module(s) omitted for readability._",
                "",
            ]

        # ── Section 3: Layer grouping ──────────────────────────────────────────
        by_layer: dict[str, list[_ModNode]] = defaultdict(list)
        for m in mod_nodes:
            by_layer[m.layer].append(m)

        lines += ["## Layer Architecture", ""]
        for layer in _LAYER_ORDER:
            mods = by_layer.get(layer, [])
            if not mods:
                continue
            mod_names = ", ".join(f"`{m.name}`" for m in mods)
            lines += [f"**{layer}:** {mod_names}", ""]

        # ── Section 4: Layer violations ────────────────────────────────────────
        violations = self._detect_violations(mod_nodes, mod_edges)
        if violations:
            lines += ["### ⚠ Layer Violations", ""]
            for v in violations[:5]:
                lines.append(f"- {v}")
            lines.append("")

        # ── Section 5: Layer flow diagram ──────────────────────────────────────
        layer_flow = self._render_layer_flow(mod_nodes, mod_edges)
        if layer_flow:
            lines += [
                "## Dependency Flow",
                "",
                "Aggregated to the layer level.  "
                "Solid arrows follow the intended top-to-bottom flow; "
                "**red dashed arrows** point upward (architectural violations to review).",
                "",
                "```mermaid",
                layer_flow,
                "```",
                "",
            ]

        return "\n".join(lines)

    # ── Internal: build module graph ──────────────────────────────────────────

    def _build_module_graph(
        self,
        graph: GraphBuildResult,
        files: list[GraphNode],
    ) -> tuple[list[_ModNode], list[_ModEdge]]:
        """Derive the module-level dependency graph from file-level imports.

        Steps:
          1. Group files by their architecturally meaningful module name
             (via _top_level_module) — NOT by graph MODULE nodes (which
             include generic container directories like 'src', 'backend').
          2. Skip modules whose name is in _GENERIC_CONTAINERS if more
             specifically-named modules exist.
          3. Count cross-module IMPORTS edges, collapse bidirectional pairs.
          4. Cap to MAX_SYSTEM_NODES by architectural significance.
        """
        # 1. Group files → module name
        mod_files: dict[str, list[GraphNode]] = defaultdict(list)
        for f in files:
            path = str(f.properties.get("path", f.label))
            name = _top_level_module(path)
            mod_files[name].append(f)

        # 2. If there are non-generic modules, drop generic containers
        has_non_generic = any(
            name not in _GENERIC_CONTAINERS for name in mod_files
        )
        if has_non_generic:
            mod_files = {
                name: flist
                for name, flist in mod_files.items()
                if name not in _GENERIC_CONTAINERS
            }

        # 3. Skip infrastructure noise directories
        _skip = {"__pycache__", "node_modules", ".git", "dist", "build",
                 ".venv", "venv", ".next", "coverage", ".pytest_cache"}
        mod_files = {k: v for k, v in mod_files.items() if k not in _skip}

        if not mod_files:
            return [], []

        # Build file_id → module_name for edge traversal
        file_to_mod: dict[str, str] = {}
        for name, flist in mod_files.items():
            for f in flist:
                file_to_mod[f.id] = name

        # Build class_id → file_id (for class counting)
        class_to_file: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship == RelationshipType.CONTAINS:
                src = graph.node_by_id.get(e.source_id)
                tgt = graph.node_by_id.get(e.target_id)
                if src and tgt:
                    if src.node_type == NodeType.FILE and \
                       tgt.node_type in (NodeType.CLASS, NodeType.INTERFACE):
                        class_to_file[tgt.id] = src.id

        # Collect metrics per module
        classes_all = graph.nodes_by_type(NodeType.CLASS) + \
                      graph.nodes_by_type(NodeType.INTERFACE)

        pre_nodes: list[_ModNode] = []
        for name, flist in sorted(mod_files.items()):
            file_ids = {f.id for f in flist}
            cls_count = sum(
                1 for c in classes_all if class_to_file.get(c.id) in file_ids
            )
            ep_count  = sum(int(f.properties.get("endpoints", 0)) for f in flist)
            complexity = sum(
                int(f.properties.get("total_complexity", 0)) for f in flist
            )
            file_paths = [str(f.properties.get("path", f.label)) for f in flist]
            layer = _classify_layer_from_paths(file_paths)

            # Unique, collision-safe Mermaid ID: use the name alone (names
            # are unique here after deduplication above).
            safe_id = self._safe_id(name)

            pre_nodes.append(_ModNode(
                id=safe_id,
                name=name,
                path=name,  # top-level name is the unique key
                layer=layer,
                file_count=len(flist),
                class_count=cls_count,
                endpoint_count=ep_count,
                complexity=complexity,
            ))

        # 4. Cap by significance
        def _sig(m: _ModNode) -> tuple[int, int, int]:
            return (m.endpoint_count, m.class_count, m.file_count)

        pre_nodes.sort(key=_sig, reverse=True)
        nodes = pre_nodes[:MAX_SYSTEM_NODES]
        self._hidden_count = len(pre_nodes) - len(nodes)
        kept_names = {m.name for m in nodes}

        # 5. Aggregate edges
        pair_count: dict[tuple[str, str], int] = defaultdict(int)
        for e in graph.edges:
            if e.relationship not in (
                RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON
            ):
                continue
            src_mod = file_to_mod.get(e.source_id)
            tgt_mod = file_to_mod.get(e.target_id)
            if not src_mod or not tgt_mod or src_mod == tgt_mod:
                continue
            if src_mod not in kept_names or tgt_mod not in kept_names:
                continue
            pair_count[(src_mod, tgt_mod)] += 1

        # Collapse bidirectional pairs
        seen: set[frozenset[str]] = set()
        edges: list[_ModEdge] = []
        for (src, tgt), cnt in sorted(pair_count.items(), key=lambda x: -x[1]):
            key = frozenset({src, tgt})
            if key in seen:
                continue
            seen.add(key)
            rev = pair_count.get((tgt, src), 0)
            if rev > cnt:
                edges.append(_ModEdge(tgt, src, rev, is_bidir=True))
            else:
                edges.append(_ModEdge(src, tgt, cnt, is_bidir=(rev > 0)))

        # Cap edges
        edges = edges[:MAX_SYSTEM_EDGES]
        return nodes, edges

    # ── Internal: Mermaid renderers ───────────────────────────────────────────

    def _render_system_mermaid(
        self,
        nodes: list[_ModNode],
        edges: list[_ModEdge],
        repo_name: str,
    ) -> str:
        """System-level Mermaid diagram with layer subgraphs."""
        by_layer: dict[str, list[_ModNode]] = defaultdict(list)
        for m in nodes:
            by_layer[m.layer].append(m)

        lines: list[str] = ["graph TB"]
        for layer in _LAYER_ORDER:
            layer_mods = by_layer.get(layer, [])
            if not layer_mods:
                continue
            safe_layer = layer.replace(" ", "_")
            lines.append(f'    subgraph {safe_layer}["{layer}"]')
            for m in layer_mods:
                # Build a readable label with the most important metric
                if m.endpoint_count:
                    extra = f" [{m.endpoint_count} ep]"
                elif m.class_count:
                    extra = f" [{m.class_count} cls]"
                elif m.file_count:
                    extra = f" [{m.file_count} files]"
                else:
                    extra = ""
                label = self._esc(m.name + extra)
                lines.append(f'        {m.id}["{label}"]')
            lines.append("    end")

        # Edges — thick (==>) for strong coupling, thin (-->) for light
        for e in edges:
            src_id = self._safe_id(e.source)
            tgt_id = self._safe_id(e.target)
            direction = " ↔" if e.is_bidir else ""
            if e.weight >= 5:
                lines.append(f"    {src_id} ==>|\"{e.weight}{direction}\"| {tgt_id}")
            else:
                lines.append(f"    {src_id} -->|\"{e.weight}{direction}\"| {tgt_id}")

        return "\n".join(lines)

    def _render_layer_flow(
        self,
        nodes: list[_ModNode],
        edges: list[_ModEdge],
    ) -> str:
        """Single-node-per-layer Mermaid diagram with violation highlighting."""
        name_to_layer = {m.name: m.layer for m in nodes}

        present_layers = [
            l for l in _LAYER_ORDER
            if any(m.layer == l for m in nodes)
        ]
        if not present_layers:
            return ""

        # Aggregate module edges → layer edges
        forward:  dict[tuple[str, str], int] = defaultdict(int)
        backward: dict[tuple[str, str], int] = defaultdict(int)

        for e in edges:
            sl = name_to_layer.get(e.source, "Other")
            tl = name_to_layer.get(e.target, "Other")
            if sl == tl:
                continue
            sr = _LAYER_RANK.get(sl, 3)
            tr = _LAYER_RANK.get(tl, 3)
            is_up = (
                sr > tr
                and sl not in ("Shared", "Testing", "Other")
                and tl not in ("Shared", "Testing", "Other")
            )
            key = (sl, tl)
            (backward if is_up else forward)[key] += e.weight

        # If there's nothing interesting to show, skip the diagram
        if not forward and not backward:
            return ""

        lines: list[str] = ["graph TB"]
        for layer in present_layers:
            mod_count = sum(1 for m in nodes if m.layer == layer)
            sid = self._safe_id(layer)
            s = "s" if mod_count != 1 else ""
            lines.append(f'    {sid}["{layer}<br/>{mod_count} module{s}"]')

        for (sl, tl), w in sorted(forward.items(), key=lambda x: -x[1]):
            lines.append(
                f"    {self._safe_id(sl)} -->|\"{w}\"| {self._safe_id(tl)}"
            )
        for (sl, tl), w in sorted(backward.items(), key=lambda x: -x[1]):
            lines.append(
                f"    {self._safe_id(sl)} -.->|\"{w} ⚠\"| {self._safe_id(tl)}"
            )

        # Colour backward edges red
        if backward:
            n_fwd = len(forward)
            n_bwd = len(backward)
            for i in range(n_fwd, n_fwd + n_bwd):
                lines.append(
                    f"    linkStyle {i} stroke:#e5484d,stroke-width:2px"
                )

        return "\n".join(lines)

    # ── Internal: violation detection ────────────────────────────────────────

    def _detect_violations(
        self,
        nodes: list[_ModNode],
        edges: list[_ModEdge],
    ) -> list[str]:
        name_to_layer = {m.name: m.layer for m in nodes}
        violations: list[str] = []
        for e in edges:
            sl = name_to_layer.get(e.source, "Other")
            tl = name_to_layer.get(e.target, "Other")
            if sl in ("Shared", "Testing", "Other"):
                continue
            if tl in ("Shared", "Testing", "Other"):
                continue
            sr = _LAYER_RANK.get(sl, 3)
            tr = _LAYER_RANK.get(tl, 3)
            if sr > tr:
                violations.append(
                    f"`{e.source}` ({sl}) → `{e.target}` ({tl}) "
                    f"— dependency flows upward"
                )
        return violations

    # ── Internal: helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _safe_id(name: str) -> str:
        """Create a Mermaid-safe node ID."""
        return (
            name.replace("-", "_").replace(".", "_")
                .replace("/", "_").replace(" ", "_")
        )

    @staticmethod
    def _esc(text: str) -> str:
        """Escape text for use in a Mermaid double-quoted label."""
        return (
            text.replace('"', "'")
                .replace("\n", " ")
                .replace("[", "(").replace("]", ")")
                .replace("<", "").replace(">", "")
                .replace("#", "").replace("&", "and")
                .replace("{", "").replace("}", "")
                .replace("|", "-")
                .strip()[:48]
        )
