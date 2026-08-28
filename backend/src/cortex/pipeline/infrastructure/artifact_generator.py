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
    """Generates clean, readable Mermaid architecture diagrams.

    Layout strategy — top-down layered swimlanes:
      - graph TB (top-bottom) for the outer flow
      - One subgraph per architecture layer, arranged vertically
      - Files are nodes INSIDE their layer's subgraph
      - Import edges only cross between layers (no intra-layer clutter)
      - Class nodes shown inline in the label, not as separate nodes
      - Edges strictly capped and deduplicated

    This eliminates the spaghetti fan-out from a single REPO root and
    keeps lines short — each edge only spans one or two layers.
    """

    _LAYER_PATTERNS: list = [
        ("domain",         "Domain",       "domain"),
        ("entities",       "Domain",       "domain"),
        ("models",         "Domain",       "domain"),
        ("model",          "Domain",       "domain"),
        ("entity",         "Domain",       "domain"),
        ("dto",            "Domain",       "domain"),
        ("application",    "Application",  "app"),
        ("use_cases",      "Application",  "app"),
        ("services",       "Application",  "app"),
        ("service",        "Application",  "app"),
        ("usecase",        "Application",  "app"),
        ("infrastructure", "Infra",        "infra"),
        ("repository",     "Infra",        "infra"),
        ("repositories",   "Infra",        "infra"),
        ("persistence",    "Infra",        "infra"),
        ("database",       "Infra",        "infra"),
        ("dao",            "Infra",        "infra"),
        ("presentation",   "Presentation", "pres"),
        ("routers",        "Presentation", "pres"),
        ("controllers",    "Presentation", "pres"),
        ("controller",     "Presentation", "pres"),
        ("router",         "Presentation", "pres"),
        ("handler",        "Presentation", "pres"),
        ("components",     "Frontend",     "front"),
        ("frontend",       "Frontend",     "front"),
        ("pages",          "Frontend",     "front"),
        ("hooks",          "Frontend",     "front"),
        ("features",       "Frontend",     "front"),
        ("shared",         "Shared",       "shared"),
        ("utils",          "Shared",       "shared"),
        ("common",         "Shared",       "shared"),
        ("config",         "Shared",       "shared"),
        ("exception",      "Shared",       "shared"),
        ("exceptions",     "Shared",       "shared"),
    ]

    # Canonical layer order — top of diagram (user-facing) → bottom (data)
    LAYER_ORDER = [
        "Frontend",
        "Presentation",
        "Application",
        "Domain",
        "Infra",
        "Shared",
        "Other",
    ]

    _SKIP_FILES = {
        "__init__.py", "__init__.ts", "index.ts", "index.js", "conftest.py",
    }
    _SKIP_DIRS = {
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        "dist", "build", ".next", "coverage", ".pytest_cache",
    }

    @staticmethod
    def _esc(text: str) -> str:
        """Make text safe for Mermaid double-quoted labels."""
        return (
            text.replace('"', "'")
                .replace("\n", " ")
                .replace("[", "(").replace("]", ")")
                .replace("<", "").replace(">", "")
                .replace("#", "").replace("&", "and")
                .replace("{", "").replace("}", "")
                .replace("|", "-")
                .strip()[:40]
        )

    def _detect_layer(self, path: str) -> tuple[str, str]:
        pl = path.lower().replace("\\", "/")
        for frag, name, css in self._LAYER_PATTERNS:
            if f"/{frag}/" in pl or f"/{frag}." in pl:
                return name, css
        # Java suffix fallback
        fname = pl.split("/")[-1]
        java_suffix_map = [
            ("repository",  "Infra",        "infra"),
            ("dao",         "Infra",        "infra"),
            ("service",     "Application",  "app"),
            ("usecase",     "Application",  "app"),
            ("controller",  "Presentation", "pres"),
            ("handler",     "Presentation", "pres"),
            ("router",      "Presentation", "pres"),
            ("entity",      "Domain",       "domain"),
            ("model",       "Domain",       "domain"),
            ("dto",         "Domain",       "domain"),
            ("exception",   "Shared",       "shared"),
            ("config",      "Shared",       "shared"),
            ("util",        "Shared",       "shared"),
        ]
        for suffix, name, css in java_suffix_map:
            base = fname.replace(".java","").replace(".py","").replace(".ts","")
            if base.endswith(suffix) or base.endswith(f"_{suffix}") or base.endswith(f"-{suffix}"):
                return name, css
        return "Other", "other"

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        from collections import defaultdict
        import re

        nby_id: dict[str, GraphNode] = {n.id: n for n in graph.nodes}

        import_edges = [
            e for e in graph.edges
            if e.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)
        ]
        inherits_edges = [
            e for e in graph.edges
            if e.relationship == RelationshipType.INHERITS
        ]

        files   = graph.nodes_by_type(NodeType.FILE)
        classes = graph.nodes_by_type(NodeType.CLASS)
        modules = graph.nodes_by_type(NodeType.MODULE)
        all_files = graph.nodes_by_type(NodeType.FILE)

        # ── Filter noise ──────────────────────────────────────────────────────
        _TEST_PATH_RE = re.compile(
            r'(^|/)(tests?/|__tests__/|test_[^/]+\.|[^/]+_test\.[^/]+$)',
            re.IGNORECASE,
        )
        _TEST_LABELS  = re.compile(r'^(test_|.*_test$|conftest)', re.IGNORECASE)
        _NOISE_LABELS = re.compile(
            r'^(tmp_|temp_|\.env|env\.|debug_|check_|rebuild_|run_)', re.IGNORECASE
        )

        def _skip(f: GraphNode) -> bool:
            if f.label in self._SKIP_FILES:
                return True
            path  = str(f.properties.get("path", ""))
            label = f.label
            for d in self._SKIP_DIRS:
                if f"/{d}/" in path:
                    return True
            if _TEST_PATH_RE.search(path) or _TEST_LABELS.match(label):
                return True
            if _NOISE_LABELS.match(label):
                return True
            if label in (".env", "env", ".env.local", ".env.example"):
                return True
            return (
                int(f.properties.get("lines", 0)) == 0
                and int(f.properties.get("classes", 0)) == 0
                and int(f.properties.get("functions", 0)) == 0
            )

        src_files = [f for f in files if not _skip(f)]

        # ── Score by structural importance ────────────────────────────────────
        fan_in:  dict[str, int] = defaultdict(int)
        fan_out: dict[str, int] = defaultdict(int)
        seen_p:  set = set()
        for e in import_edges:
            p = (e.source_id, e.target_id)
            if p not in seen_p:
                seen_p.add(p)
                fan_in[e.target_id]  += 1
                fan_out[e.source_id] += 1

        def _score(f: GraphNode) -> float:
            return (
                fan_in.get(f.id, 0)  * 3
                + int(f.properties.get("classes",   0)) * 2
                + fan_out.get(f.id, 0) * 1.5
                + min(int(f.properties.get("lines", 0)) / 100, 4)
            )

        # ── Group files into layers ───────────────────────────────────────────
        layer_files: dict[str, list[GraphNode]] = defaultdict(list)
        file_layer:  dict[str, str] = {}
        file_css:    dict[str, str] = {}

        for f in src_files:
            path       = str(f.properties.get("path", f.label))
            ln, css    = self._detect_layer(path)
            layer_files[ln].append(f)
            file_layer[f.id] = ln
            file_css[f.id]   = css

        for f in all_files:
            if f.id in file_layer:
                continue
            path = str(f.properties.get("path", f.label))
            ln, css = self._detect_layer(path)
            file_layer[f.id] = ln
            file_css[f.id] = css

        # Cap: max 6 files per layer, max 30 total
        # Keep files with real architecture content even when their structural
        # score is low; otherwise small but important files (e.g., config files
        # containing classes) disappear from the generated diagram.
        MAX_PER_LAYER = 6
        MAX_TOTAL     = 30
        selected: list[GraphNode] = []
        for ln in self.LAYER_ORDER:
            lf = layer_files.get(ln, [])
            selected.extend(sorted(lf, key=_score, reverse=True)[:MAX_PER_LAYER])

        all_files = graph.nodes_by_type(NodeType.FILE)
        keep_ids = {
            f.id
            for f in all_files
            if int(f.properties.get("classes", 0)) > 0 or int(f.properties.get("functions", 0)) > 0
        }
        keep_ids |= {
            e.source_id
            for e in graph.edges
            if e.relationship == RelationshipType.CONTAINS
            and nby_id.get(e.target_id) is not None
            and nby_id[e.target_id].node_type == NodeType.CLASS
            and nby_id.get(e.source_id) is not None
            and nby_id[e.source_id].node_type == NodeType.FILE
        }
        selected.extend(f for f in all_files if f.id in keep_ids and f not in selected)
        selected = sorted({f.id: f for f in selected}.values(), key=_score, reverse=True)[:MAX_TOTAL]

        required_class_ids = {
            e.target_id
            for e in graph.edges
            if e.relationship == RelationshipType.CONTAINS
            and nby_id.get(e.target_id) is not None
            and nby_id[e.target_id].node_type == NodeType.CLASS
            and nby_id.get(e.source_id) is not None
            and nby_id[e.source_id].node_type == NodeType.FILE
        }
        for cls in classes:
            if cls.id in required_class_ids and cls not in selected:
                selected.append(cls)

        selected = sorted({f.id: f for f in selected}.values(), key=_score, reverse=True)[:MAX_TOTAL]
        sel_ids  = {f.id for f in selected}

        # ── Map classes to files ──────────────────────────────────────────────
        cls_file: dict[str, str] = {}
        for e in graph.edges:
            if e.relationship != RelationshipType.CONTAINS:
                continue
            s = nby_id.get(e.source_id)
            t = nby_id.get(e.target_id)
            if s and t and s.node_type == NodeType.FILE and t.node_type == NodeType.CLASS:
                cls_file[t.id] = s.id

        module_by_layer: dict[str, list[GraphNode]] = defaultdict(list)
        for module in modules:
            path = str(module.properties.get("path", ""))
            layer, _ = self._detect_layer(path)
            module_by_layer[layer].append(module)

        # Top 2 classes per file (by method count, methods > 0 only)
        file_top_cls: dict[str, list[GraphNode]] = defaultdict(list)
        for cls in classes:
            fid     = cls_file.get(cls.id, "")
            methods = int(cls.properties.get("methods", 0))
            if fid in sel_ids and methods > 0:
                file_top_cls[fid].append(cls)
        for fid in file_top_cls:
            file_top_cls[fid] = sorted(
                file_top_cls[fid],
                key=lambda c: int(c.properties.get("methods", 0)),
                reverse=True,
            )[:2]

        # ── Assign stable Mermaid IDs ─────────────────────────────────────────
        id_map: dict[str, str] = {}
        ctr = [0]

        def _mid(nid: str, pfx: str) -> str:
            if nid not in id_map:
                ctr[0] += 1
                id_map[nid] = f"{pfx}{ctr[0]}"
            return id_map[nid]

        for module in modules:
            _mid(module.id, "M")
        for f in selected:
            _mid(f.id, "F")
        for f in selected:
            for cls in file_top_cls.get(f.id, []):
                _mid(cls.id, "C")

        # ── Disambiguate duplicate file labels ────────────────────────────────
        name_count: dict[str, int] = defaultdict(int)
        for f in selected:
            name_count[f.label] += 1

        def _file_label(f: GraphNode) -> str:
            label = f.label
            for ext in (".tsx", ".jsx", ".ts", ".js", ".py", ".java", ".kt"):
                label = label.replace(ext, "")
            if name_count[f.label] > 1:
                path  = str(f.properties.get("path", "")).replace("\\", "/")
                parts = [p for p in path.split("/")[:-1]
                         if p not in ("src", "lib", "app", "")]
                if parts:
                    label = f"{parts[-1]}/{label}"
            fn_c  = int(f.properties.get("functions", 0))
            cls_c = int(f.properties.get("classes",   0))
            hint  = f" [{cls_c}c/{fn_c}f]" if (cls_c or fn_c) else ""
            return self._esc(label + hint)

        # ── Build diagram ─────────────────────────────────────────────────────
        # graph TB (top-to-bottom) stacks architecture layers vertically —
        # Frontend at the top, Infra/Domain at the bottom — matching the
        # natural reading direction of a layered architecture.
        #
        # Previously used graph LR which spread layers horizontally, producing
        # a wide diagram that compressed into overlapping thin horizontal lines
        # inside the fixed-height canvas. graph TB works correctly with the
        # dynamic canvas height and produces a readable top-down flow.
        #
        # Each layer is a subgraph with direction LR so its file nodes lay out
        # side-by-side within the row — combining TB between layers with LR
        # within each layer gives the classic "swimlane" architecture view.
        out: list[str] = ["graph TB"]

        # Colour palette — one classDef per layer
        out += [
            "  classDef repo   fill:#7C3AED,stroke:#5B21B6,color:#fff,font-weight:bold",
            "  classDef domain fill:#064E3B,stroke:#10B981,color:#D1FAE5",
            "  classDef app    fill:#1E3A8A,stroke:#3B82F6,color:#DBEAFE",
            "  classDef infra  fill:#7C2D12,stroke:#F97316,color:#FED7AA",
            "  classDef pres   fill:#4C1D95,stroke:#8B5CF6,color:#EDE9FE",
            "  classDef front  fill:#831843,stroke:#EC4899,color:#FCE7F3",
            "  classDef shared fill:#1F2937,stroke:#6B7280,color:#D1D5DB",
            "  classDef cls    fill:#0C1929,stroke:#38BDF8,color:#7DD3FC",
            "  classDef other  fill:#111827,stroke:#374151,color:#9CA3AF",
            "",
        ]

        # ── Subgraph per layer (only non-empty layers) ────────────────────────
        # Subgraph IDs must be alphanumeric — we use SG + layer abbreviation
        sg_id: dict[str, str] = {
            "Frontend":    "SGFRONT",
            "Presentation":"SGPRES",
            "Application": "SGAPP",
            "Domain":      "SGDOM",
            "Infra":       "SGINF",
            "Shared":      "SGSHR",
            "Other":       "SGOTH",
        }

        present_layers = [ln for ln in self.LAYER_ORDER
                          if any(file_layer.get(f.id) == ln for f in selected)
                          or module_by_layer.get(ln)]

        for ln in present_layers:
            lfiles = [f for f in selected if file_layer.get(f.id) == ln]
            lmodules = module_by_layer.get(ln, [])
            if not lfiles and not lmodules:
                continue

            sid = sg_id.get(ln, f"SG{ln[:4].upper()}")
            out.append(f"  subgraph {sid} [{ln}]")
            # Nodes within a layer flow left-to-right so files sit side-by-side
            # in a horizontal row rather than stacking vertically inside the band.
            out.append(f"    direction LR")

            for module in lmodules:
                mid = id_map[module.id]
                mlabel = self._esc(f"{module.label}")
                out.append(f'    {mid}["{mlabel}"]:::shared')

            for f in lfiles:
                fmid   = id_map[f.id]
                flabel = _file_label(f)
                css    = file_css.get(f.id, "other")
                out.append(f'    {fmid}["{flabel}"]:::{css}')

                # Class nodes directly beneath their file, inside same subgraph
                for cls in file_top_cls.get(f.id, []):
                    cmid   = id_map[cls.id]
                    m      = int(cls.properties.get("methods", 0))
                    clabel = self._esc(f"{cls.label} ({m}m)")
                    out.append(f'    {cmid}("{clabel}"):::cls')
                    out.append(f"    {fmid} --> {cmid}")

            out.append("  end")
            out.append("")

        # ── Inter-layer import edges ──────────────────────────────────────────
        # ONLY show edges that cross layer boundaries — intra-layer edges
        # add visual noise without conveying architectural information.
        # Cap at 20 edges, sorted by fan-in (most-depended-on targets first).
        import_lines: list[str] = []
        seen_e: set = set()

        sorted_imports = sorted(
            import_edges,
            key=lambda e: fan_in.get(e.target_id, 0),
            reverse=True,
        )
        for e in sorted_imports:
            if e.source_id not in sel_ids or e.target_id not in sel_ids:
                continue
            sm = id_map.get(e.source_id)
            tm = id_map.get(e.target_id)
            if not sm or not tm or sm == tm:
                continue
            # Skip intra-layer edges — they just create noise inside the subgraph
            src_layer = file_layer.get(e.source_id, "")
            tgt_layer = file_layer.get(e.target_id, "")
            if src_layer == tgt_layer:
                continue
            pair = (sm, tm)
            if pair in seen_e:
                continue
            seen_e.add(pair)
            import_lines.append(f"  {sm} --> {tm}")
            if len(import_lines) >= 20:
                break

        if import_lines:
            out.append("  %% Cross-layer dependencies")
            out.extend(import_lines)
            out.append("")

        # ── Inheritance edges (capped at 6) ───────────────────────────────────
        inh_lines: list[str] = []
        for e in inherits_edges:
            sm = id_map.get(e.source_id)
            tm = id_map.get(e.target_id)
            if sm and tm and len(inh_lines) < 6:
                inh_lines.append(f"  {sm} -.->|extends| {tm}")

        if inh_lines:
            out.append("  %% Inheritance")
            out.extend(inh_lines)

        return "\n".join(out)


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
            "**What this tests:**",
            "",
            "- Can the candidate reason about real code from evidence?",
            "- Do they understand the engineering trade-offs involved?",
            "- Can they propose concrete improvements with justification?",
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
        # Use the pre-built O(1) dict on GraphBuildResult instead of a
        # linear scan over all nodes (previously O(N) per call, called
        # inside an edge loop making it O(E×N) total).
        return graph.node_by_id.get(node_id)


class MarkdownReportGenerator:
    """Generates detailed markdown reports from the knowledge graph."""

    def generate_module_breakdown(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate evidence-backed module breakdown with dependency analysis,
        architectural role detection, and coupling metrics."""
        from cortex.pipeline.infrastructure.module_breakdown_generator import (
            ModuleBreakdownGenerator,
        )
        return ModuleBreakdownGenerator().generate(graph, repo_name)

    def generate_learning_path(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate a repository-specific learning path with topological
        dependency order, entry point detection, and difficulty progression."""
        from cortex.pipeline.infrastructure.learning_path_generator import (
            LearningPathGenerator,
        )
        return LearningPathGenerator().generate(graph, repo_name)

    def generate_interview_questions(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate repository-specific interview questions with evidence,
        model answers, and difficulty levels."""
        from cortex.pipeline.infrastructure.interview_generator import (
            InterviewQuestionsGenerator,
        )
        return InterviewQuestionsGenerator().generate(graph, repo_name)

    def generate_api_spec(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate evidence-backed API surface analysis with endpoint
        detection, call chain tracing, and quality assessment."""
        from cortex.pipeline.infrastructure.api_features_generator import (
            APIFeaturesGenerator,
        )
        return APIFeaturesGenerator().generate(graph, repo_name)

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