"""Cortex Reasoning Layer — the unified intelligence foundation.

This is the SINGLE shared reasoning pipeline that all product features
consume. It orchestrates graph, insights, memory, search, and blast radius
into coherent intelligence.

Design principles:
  - Every output is grounded in repository evidence
  - NIM is never used for determining objective facts
  - Deterministic: same graph → same understanding
  - All product features call into this layer, never independently
    rediscover the same information
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import structlog

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.insights.application.engine import InsightsEngine
from cortex.pipeline.domain.entities import ManifestInfo
from cortex.reasoning.domain.entities import (
    ArchitectureStyle,
    DataFlow,
    DataFlowStep,
    EntryPoint,
    ModuleIntelligence,
    RepositoryUnderstanding,
)

if TYPE_CHECKING:
    from cortex.insights.domain.entities import InsightsReport

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Graph Indexes
# ═══════════════════════════════════════════════════════════════════════════════


class _GraphIndex:
    """Pre-built indexes over graph data for efficient querying."""

    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.nodes = nodes
        self.edges = edges
        self.node_map: dict[str, GraphNode] = {n.id: n for n in nodes}

        # Index by type
        self.by_type: dict[NodeType, list[GraphNode]] = defaultdict(list)
        for node in nodes:
            self.by_type[node.node_type].append(node)

        # Edge indexes
        self.edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        self.edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            self.edges_from[edge.source_id].append(edge)
            self.edges_to[edge.target_id].append(edge)

        # CONTAINS hierarchy
        self.children: dict[str, list[str]] = defaultdict(list)
        self.parent: dict[str, str] = {}
        for edge in edges:
            if edge.relationship == RelationshipType.CONTAINS:
                self.children[edge.source_id].append(edge.target_id)
                self.parent[edge.target_id] = edge.source_id

    def get_children(self, node_id: str, of_type: NodeType | None = None) -> list[GraphNode]:
        """Get child nodes (via CONTAINS) optionally filtered by type."""
        child_ids = self.children.get(node_id, [])
        children = [self.node_map[cid] for cid in child_ids if cid in self.node_map]
        if of_type:
            children = [c for c in children if c.node_type == of_type]
        return children

    def get_dependents(self, node_id: str) -> list[tuple[GraphNode, RelationshipType]]:
        """Get nodes that depend on this node (reverse dependency edges)."""
        result = []
        for edge in self.edges_to.get(node_id, []):
            if edge.relationship in (
                RelationshipType.IMPORTS,
                RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS,
                RelationshipType.INHERITS,
                RelationshipType.IMPLEMENTS,
            ):
                src = self.node_map.get(edge.source_id)
                if src:
                    result.append((src, edge.relationship))
        return result

    def get_dependencies(self, node_id: str) -> list[tuple[GraphNode, RelationshipType]]:
        """Get nodes this node depends on (forward dependency edges)."""
        result = []
        for edge in self.edges_from.get(node_id, []):
            if edge.relationship in (
                RelationshipType.IMPORTS,
                RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS,
                RelationshipType.INHERITS,
                RelationshipType.IMPLEMENTS,
            ):
                tgt = self.node_map.get(edge.target_id)
                if tgt:
                    result.append((tgt, edge.relationship))
        return result

    def prop(self, node: GraphNode, key: str, default: str = "") -> str:
        """Safe property access."""
        return str(node.properties.get(key, default) or default)

    def int_prop(self, node: GraphNode, key: str) -> int:
        """Safe integer property access."""
        try:
            return int(node.properties.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0


# ═══════════════════════════════════════════════════════════════════════════════
# CortexReasoner — The Unified Intelligence Engine
# ═══════════════════════════════════════════════════════════════════════════════


class CortexReasoner:
    """Unified reasoning engine that produces RepositoryUnderstanding.

    All product features (Overview, Explain, Chat, Learning Path, etc.)
    consume the output of this engine rather than independently querying
    graph/insights/memory.

    This class is pure computation — no database calls, no HTTP, no IO.
    Pass in nodes/edges and get back a complete understanding.
    """

    def __init__(self) -> None:
        self._insights_engine = InsightsEngine()

    def understand(
        self,
        job_id: str,
        repo_url: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        manifests: list[ManifestInfo] | None = None,
    ) -> RepositoryUnderstanding:
        """Produce a complete RepositoryUnderstanding from graph data.

        This is the PRIMARY entry point for the reasoning layer.

        ``manifests`` carries the ``ManifestInfo`` results of parsing the
        repository's dependency/build descriptors. When provided, the
        languages and frameworks they declare are merged into detection in
        addition to import/label signals, so framework identification does not
        rely only on sniffing source imports (Req 2.4).
        """
        repo_name = repo_url.rstrip("/").split("/")[-1]
        idx = _GraphIndex(nodes, edges)

        # Compute insights (reuse existing engine)
        report = self._insights_engine.compute(
            job_id=job_id, repo_url=repo_url, nodes=nodes, edges=edges
        )

        understanding = RepositoryUnderstanding(
            job_id=job_id,
            repo_url=repo_url,
            repo_name=repo_name,
        )

        # ── Structure counts ──────────────────────────────────────────────────
        self._compute_structure(understanding, idx)

        # ── Languages & Frameworks ────────────────────────────────────────────
        self._detect_languages_and_frameworks(understanding, idx, manifests or [])

        # ── Architecture ──────────────────────────────────────────────────────
        self._detect_architecture(understanding, idx)

        # ── Entry Points ──────────────────────────────────────────────────────
        self._detect_entry_points(understanding, idx)

        # ── Module Intelligence ───────────────────────────────────────────────
        self._analyze_modules(understanding, idx, edges)

        # ── Data Flows ────────────────────────────────────────────────────────
        self._trace_data_flows(understanding, idx)

        # ── Health from InsightsEngine ────────────────────────────────────────
        self._apply_health(understanding, report, idx)

        # ── Starting Point ────────────────────────────────────────────────────
        self._determine_starting_point(understanding, idx)

        # ── Top Dependencies ──────────────────────────────────────────────────
        self._detect_top_dependencies(understanding, idx)

        # ── Purpose inference ─────────────────────────────────────────────────
        self._infer_purpose(understanding, idx)

        return understanding

    # ──────────────────────────────────────────────────────────────────────────
    # Structure
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_structure(self, u: RepositoryUnderstanding, idx: _GraphIndex) -> None:
        """Count structural elements from graph."""
        u.total_files = len(idx.by_type[NodeType.FILE])
        u.total_modules = len(idx.by_type[NodeType.MODULE])
        u.total_classes = len(
            idx.by_type[NodeType.CLASS]
            + idx.by_type[NodeType.INTERFACE]
            + idx.by_type[NodeType.ENUM]
        )
        u.total_functions = len(
            idx.by_type[NodeType.FUNCTION] + idx.by_type[NodeType.METHOD]
        )
        u.total_endpoints = len(idx.by_type[NodeType.ENDPOINT])
        u.total_tests = len(idx.by_type[NodeType.TEST])
        u.total_lines = sum(
            idx.int_prop(f, "lines") for f in idx.by_type[NodeType.FILE]
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Languages & Frameworks
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_languages_and_frameworks(
        self,
        u: RepositoryUnderstanding,
        idx: _GraphIndex,
        manifests: list[ManifestInfo],
    ) -> None:
        """Detect languages and frameworks from file properties, manifests, and patterns.

        Languages are counted per source file; languages implied by a manifest
        are folded in as well so an ecosystem is still represented even if its
        source files were not individually language-tagged. The result orders
        the dominant language(s) first while representing all detected
        languages proportionally (Req 2.5).
        """
        lang_counts: dict[str, int] = defaultdict(int)
        for f in idx.by_type[NodeType.FILE]:
            lang = idx.prop(f, "language")
            if lang and lang != "unknown":
                lang_counts[lang] += 1

        # Fold in manifest-declared languages so an ecosystem present only via
        # its manifest (e.g. a Gemfile with no parsed .rb files) still appears.
        for info in manifests:
            for lang in info.languages:
                if lang and lang not in lang_counts:
                    lang_counts[lang] += 1

        # Deterministic order: most files first, ties broken alphabetically.
        u.languages = sorted(
            lang_counts.keys(), key=lambda lang: (-lang_counts[lang], lang)
        )

        # Framework detection from graph patterns
        frameworks: set[str] = set()
        all_labels = {n.label.lower() for n in idx.nodes}
        all_imports = set()
        for n in idx.by_type[NodeType.FILE]:
            imports = n.properties.get("imports", [])
            if isinstance(imports, list):
                all_imports.update(str(i).lower() for i in imports)

        # Detect from node labels and imports
        framework_signals = {
            "fastapi": ["fastapi", "apirouter", "depends"],
            "django": ["django", "models.model", "views.py"],
            "flask": ["flask", "blueprint"],
            "spring": ["springframework", "springboot", "@controller", "@service"],
            "react": ["react", "usestate", "useeffect", "jsx"],
            "nextjs": ["next", "next/router", "getserversideprops"],
            "express": ["express", "router", "app.get", "app.post"],
            "sqlalchemy": ["sqlalchemy", "declarativebase", "mapped_column"],
            "pytest": ["pytest", "conftest"],
        }

        for framework, signals in framework_signals.items():
            for signal in signals:
                if signal in all_labels or signal in all_imports:
                    frameworks.add(framework)
                    break

        # Also detect from endpoint decorators
        for ep in idx.by_type[NodeType.ENDPOINT]:
            route_info = idx.prop(ep, "route_info")
            decorators = idx.prop(ep, "decorators")
            if "fastapi" in route_info.lower() or "@app." in decorators.lower():
                frameworks.add("fastapi")
            if "express" in route_info.lower():
                frameworks.add("express")
            if "@RequestMapping" in decorators or "@GetMapping" in decorators:
                frameworks.add("spring")

        # Manifest-derived frameworks are authoritative signals: a declared
        # dependency (e.g. "react" in package.json) identifies a framework even
        # when no import/label signal was captured in the graph (Req 2.4).
        for info in manifests:
            frameworks.update(info.frameworks)

        u.frameworks = sorted(frameworks)

    # ──────────────────────────────────────────────────────────────────────────
    # Architecture Detection
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_architecture(self, u: RepositoryUnderstanding, idx: _GraphIndex) -> None:
        """Infer architecture style from module structure and patterns."""
        modules = idx.by_type[NodeType.MODULE]
        module_labels = {m.label.lower() for m in modules}
        evidence: list[str] = []

        # Check for layered/hexagonal patterns
        layer_keywords = {"domain", "application", "infrastructure", "presentation",
                          "service", "repository", "controller", "model", "view"}
        hex_keywords = {"port", "adapter", "domain", "application"}
        mvc_keywords = {"model", "view", "controller", "template"}
        pipeline_keywords = {"pipeline", "stage", "step", "processor"}

        matched_layers = layer_keywords & module_labels
        matched_hex = hex_keywords & module_labels
        matched_mvc = mvc_keywords & module_labels
        matched_pipeline = pipeline_keywords & module_labels

        # Score each pattern
        scores: dict[ArchitectureStyle, int] = defaultdict(int)

        if len(matched_layers) >= 3:
            scores[ArchitectureStyle.LAYERED] += 3
            evidence.append(f"Layer modules detected: {', '.join(sorted(matched_layers))}")

        if len(matched_hex) >= 3:
            scores[ArchitectureStyle.HEXAGONAL] += 3
            evidence.append(f"Hexagonal modules: {', '.join(sorted(matched_hex))}")

        if len(matched_mvc) >= 2:
            scores[ArchitectureStyle.MVC] += 2
            evidence.append(f"MVC modules: {', '.join(sorted(matched_mvc))}")

        if matched_pipeline:
            scores[ArchitectureStyle.PIPELINE] += 2
            evidence.append(f"Pipeline modules: {', '.join(sorted(matched_pipeline))}")

        # Module count heuristic
        if len(modules) >= 8:
            scores[ArchitectureStyle.MODULAR] += 2
            evidence.append(f"{len(modules)} distinct modules — highly modular")
        elif len(modules) <= 2:
            scores[ArchitectureStyle.MONOLITHIC] += 2
            evidence.append(f"Only {len(modules)} modules — likely monolithic")

        # Check for repeated internal structure (domain/application/infrastructure per module)
        submodule_pattern_count = 0
        for module in modules:
            children_labels = {
                idx.node_map[cid].label.lower()
                for cid in idx.children.get(module.id, [])
                if cid in idx.node_map
            }
            if {"domain", "application", "infrastructure"} & children_labels:
                submodule_pattern_count += 1

        if submodule_pattern_count >= 3:
            scores[ArchitectureStyle.HEXAGONAL] += 2
            evidence.append(
                f"{submodule_pattern_count} modules use domain/application/infrastructure layering"
            )

        # Determine winner
        if scores:
            u.architecture_style = max(scores, key=lambda s: scores[s])
        else:
            u.architecture_style = ArchitectureStyle.UNKNOWN

        u.architecture_evidence = evidence
        u.architecture_description = self._describe_architecture(u.architecture_style, evidence)

    def _describe_architecture(self, style: ArchitectureStyle, evidence: list[str]) -> str:
        """Generate a concise architecture description from evidence."""
        descriptions = {
            ArchitectureStyle.LAYERED: "Clean layered architecture with separated concerns across domain, application, and infrastructure layers.",
            ArchitectureStyle.HEXAGONAL: "Hexagonal (ports & adapters) architecture with domain isolation and explicit dependency inversion.",
            ArchitectureStyle.MODULAR: "Modular architecture with well-separated feature modules and clear boundaries.",
            ArchitectureStyle.MONOLITHIC: "Monolithic structure with most logic in a single module or package.",
            ArchitectureStyle.MVC: "Model-View-Controller pattern separating data, presentation, and business logic.",
            ArchitectureStyle.PIPELINE: "Pipeline architecture with staged data processing and transformation.",
            ArchitectureStyle.MICROSERVICE: "Microservice architecture with independently deployable services.",
            ArchitectureStyle.EVENT_DRIVEN: "Event-driven architecture with message-based communication.",
            ArchitectureStyle.UNKNOWN: "Architecture style could not be confidently determined from the available structure.",
        }
        return descriptions.get(style, descriptions[ArchitectureStyle.UNKNOWN])

    # ──────────────────────────────────────────────────────────────────────────
    # Entry Points
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_entry_points(self, u: RepositoryUnderstanding, idx: _GraphIndex) -> None:
        """Detect all entry points: endpoints, main functions, CLI commands."""
        entry_points: list[EntryPoint] = []

        # HTTP endpoints
        for ep in idx.by_type[NodeType.ENDPOINT]:
            route = idx.prop(ep, "route_info") or idx.prop(ep, "route")
            method = idx.prop(ep, "http_method") or idx.prop(ep, "method") or "GET"
            entry_points.append(EntryPoint(
                label=ep.label,
                node_id=ep.id,
                node_type=ep.node_type.value,
                file_path=idx.prop(ep, "file"),
                kind="http_endpoint",
                method=method.upper(),
                route=route,
            ))

        # Main functions / entry files
        for fn in idx.by_type[NodeType.FUNCTION]:
            label_lower = fn.label.lower()
            if label_lower in ("main", "__main__", "app", "create_app"):
                entry_points.append(EntryPoint(
                    label=fn.label,
                    node_id=fn.id,
                    node_type=fn.node_type.value,
                    file_path=idx.prop(fn, "file"),
                    kind="main_function",
                ))

        # Sort: main functions first, then endpoints by route
        entry_points.sort(key=lambda e: (
            0 if e.kind == "main_function" else 1,
            e.route or e.label
        ))

        u.entry_points = entry_points[:50]  # cap at 50

    # ──────────────────────────────────────────────────────────────────────────
    # Module Intelligence
    # ──────────────────────────────────────────────────────────────────────────

    def _analyze_modules(
        self, u: RepositoryUnderstanding, idx: _GraphIndex, edges: list[GraphEdge]
    ) -> None:
        """Produce rich intelligence for each detected module."""
        modules: list[ModuleIntelligence] = []

        for module_node in idx.by_type[NodeType.MODULE]:
            mi = ModuleIntelligence(
                name=module_node.label,
                path=idx.prop(module_node, "path") or module_node.label,
                node_id=module_node.id,
            )

            # Collect all descendant nodes (files, classes, functions)
            descendant_ids = self._collect_descendants(module_node.id, idx)
            descendants = [idx.node_map[d] for d in descendant_ids if d in idx.node_map]

            # Count structure
            mi.file_count = sum(1 for d in descendants if d.node_type == NodeType.FILE)
            mi.class_count = sum(
                1 for d in descendants
                if d.node_type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM)
            )
            mi.function_count = sum(
                1 for d in descendants
                if d.node_type in (NodeType.FUNCTION, NodeType.METHOD)
            )
            mi.total_lines = sum(
                idx.int_prop(d, "lines") for d in descendants if d.node_type == NodeType.FILE
            )

            # Complexity
            complexities = [
                idx.int_prop(d, "cyclomatic")
                for d in descendants
                if d.node_type in (NodeType.FUNCTION, NodeType.METHOD)
                and idx.int_prop(d, "cyclomatic") > 0
            ]
            if complexities:
                mi.avg_complexity = round(sum(complexities) / len(complexities), 1)
                mi.max_complexity = max(complexities)

            # Key classes and functions (by complexity / line count)
            classes_in_module = [
                d for d in descendants if d.node_type == NodeType.CLASS
            ]
            classes_in_module.sort(
                key=lambda c: idx.int_prop(c, "method_count") + idx.int_prop(c, "lines"),
                reverse=True,
            )
            mi.key_classes = [c.label for c in classes_in_module[:5]]

            fns_in_module = [
                d for d in descendants
                if d.node_type in (NodeType.FUNCTION, NodeType.METHOD)
            ]
            fns_in_module.sort(key=lambda f: idx.int_prop(f, "cyclomatic"), reverse=True)
            mi.key_functions = [f.label for f in fns_in_module[:5]]

            # Dependencies: modules this module IMPORTS from
            module_descendant_ids = set(descendant_ids) | {module_node.id}
            dep_modules: set[str] = set()
            dependent_modules: set[str] = set()

            for edge in edges:
                if edge.relationship in (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON):
                    if edge.source_id in module_descendant_ids and edge.target_id not in module_descendant_ids:
                        # This module depends on something outside
                        target = idx.node_map.get(edge.target_id)
                        if target:
                            # Find target's parent module
                            target_module = self._find_ancestor_module(target.id, idx)
                            if target_module and target_module != module_node.label:
                                dep_modules.add(target_module)
                    elif edge.target_id in module_descendant_ids and edge.source_id not in module_descendant_ids:
                        # Something outside depends on this module
                        source = idx.node_map.get(edge.source_id)
                        if source:
                            source_module = self._find_ancestor_module(source.id, idx)
                            if source_module and source_module != module_node.label:
                                dependent_modules.add(source_module)

            mi.dependencies = sorted(dep_modules)[:10]
            mi.dependents = sorted(dependent_modules)[:10]

            # Architecture role inference
            mi.architecture_role = self._infer_module_role(module_node, idx)
            mi.layer = self._infer_module_layer(module_node, idx)

            # Coupling: ratio of external edges to total edges
            external_edges = len(dep_modules) + len(dependent_modules)
            total_possible = max(len(idx.by_type[NodeType.MODULE]) - 1, 1)
            mi.coupling_score = round(min(external_edges / total_possible, 1.0), 2)

            # Risks
            if mi.function_count > 50 and mi.class_count > 15:
                mi.risks.append("Module has many responsibilities (god module candidate)")
                mi.is_god_module = True
            if mi.max_complexity > 20:
                mi.risks.append(f"Contains high-complexity function (max CC={mi.max_complexity})")
            if mi.coupling_score > 0.7:
                mi.risks.append("Highly coupled to other modules")

            modules.append(mi)

        # Sort modules by importance (line count × dependents)
        modules.sort(
            key=lambda m: m.total_lines * (len(m.dependents) + 1),
            reverse=True,
        )
        u.modules = modules

    def _collect_descendants(self, node_id: str, idx: _GraphIndex) -> list[str]:
        """BFS to collect all descendants via CONTAINS edges."""
        result: list[str] = []
        queue = list(idx.children.get(node_id, []))
        visited = {node_id}
        while queue:
            child_id = queue.pop(0)
            if child_id in visited:
                continue
            visited.add(child_id)
            result.append(child_id)
            queue.extend(idx.children.get(child_id, []))
        return result

    def _find_ancestor_module(self, node_id: str, idx: _GraphIndex) -> str:
        """Walk up the CONTAINS hierarchy to find the containing module label."""
        current = node_id
        visited: set[str] = set()
        while current in idx.parent:
            current = idx.parent[current]
            if current in visited:
                break
            visited.add(current)
            node = idx.node_map.get(current)
            if node and node.node_type == NodeType.MODULE:
                return node.label
        return ""

    def _infer_module_role(self, module_node: GraphNode, idx: _GraphIndex) -> str:
        """Infer the architectural role of a module from its name and contents."""
        label = module_node.label.lower()

        role_patterns = {
            "core": ["core", "kernel", "engine"],
            "api": ["api", "router", "routes", "endpoint", "controller", "presentation"],
            "infrastructure": ["infrastructure", "infra", "adapter", "driver"],
            "domain": ["domain", "model", "entity", "entities"],
            "utility": ["util", "utils", "helper", "helpers", "common", "shared", "lib"],
            "configuration": ["config", "settings", "configuration"],
            "testing": ["test", "tests", "spec", "specs"],
            "data": ["db", "database", "repository", "repositories", "store", "storage"],
        }

        for role, patterns in role_patterns.items():
            for pattern in patterns:
                if pattern in label:
                    return role

        # Check contents: modules with many endpoints are likely API
        children = [idx.node_map.get(cid) for cid in idx.children.get(module_node.id, []) if cid in idx.node_map]
        endpoint_children = sum(1 for c in children if c and c.node_type == NodeType.ENDPOINT)
        if endpoint_children >= 3:
            return "api"

        return "feature"

    def _infer_module_layer(self, module_node: GraphNode, idx: _GraphIndex) -> str:
        """Infer the architectural layer from module name."""
        label = module_node.label.lower()
        if any(k in label for k in ("presentation", "router", "controller", "api", "view")):
            return "presentation"
        if any(k in label for k in ("application", "service", "use_case")):
            return "application"
        if any(k in label for k in ("domain", "model", "entity")):
            return "domain"
        if any(k in label for k in ("infrastructure", "adapter", "repository", "db")):
            return "infrastructure"
        return ""

    # ──────────────────────────────────────────────────────────────────────────
    # Data Flows
    # ──────────────────────────────────────────────────────────────────────────

    def _trace_data_flows(self, u: RepositoryUnderstanding, idx: _GraphIndex) -> None:
        """Trace request/data flows starting from endpoints.

        For each endpoint, follows CALLS edges to build an execution path.
        """
        flows: list[DataFlow] = []
        endpoints = idx.by_type[NodeType.ENDPOINT]

        for ep in endpoints[:10]:  # Trace up to 10 flows
            route = idx.prop(ep, "route_info") or ep.label
            flow = DataFlow(
                name=f"{idx.prop(ep, 'http_method', 'GET')} {route}",
                entry_point=ep.label,
            )

            # BFS through CALLS edges
            visited: set[str] = set()
            current_layer = [ep.id]
            depth = 0

            while current_layer and depth < 5:
                next_layer: list[str] = []
                for node_id in current_layer:
                    if node_id in visited:
                        continue
                    visited.add(node_id)

                    node = idx.node_map.get(node_id)
                    if not node:
                        continue

                    role = self._infer_flow_role(node, depth, idx)
                    flow.steps.append(DataFlowStep(
                        symbol=node.label,
                        node_id=node.id,
                        node_type=node.node_type.value,
                        file_path=idx.prop(node, "file"),
                        role=role,
                    ))

                    # Follow CALLS edges
                    for edge in idx.edges_from.get(node_id, []):
                        if edge.relationship == RelationshipType.CALLS:
                            if edge.target_id not in visited:
                                next_layer.append(edge.target_id)

                current_layer = next_layer[:5]  # Limit fan-out per level
                depth += 1

            if len(flow.steps) >= 2:
                flows.append(flow)

        u.data_flows = flows

    def _infer_flow_role(self, node: GraphNode, depth: int, idx: _GraphIndex) -> str:
        """Infer the role of a node in a data flow based on type and depth."""
        if node.node_type == NodeType.ENDPOINT:
            return "entry"
        label = node.label.lower()
        if "controller" in label or "handler" in label or "router" in label:
            return "controller"
        if "service" in label or "use_case" in label:
            return "service"
        if "repository" in label or "repo" in label or "store" in label:
            return "repository"
        if "client" in label or "external" in label:
            return "external"
        if depth <= 1:
            return "handler"
        if depth >= 3:
            return "dependency"
        return "service"

    # ──────────────────────────────────────────────────────────────────────────
    # Health
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_health(
        self, u: RepositoryUnderstanding, report: "InsightsReport", idx: _GraphIndex
    ) -> None:
        """Apply health data from InsightsEngine."""
        from cortex.insights.domain.entities import IssueCategory

        u.overall_score = report.overall_score
        u.overall_grade = report.overall_grade

        # Complexity hotspots: top 5 most complex functions
        all_fns = idx.by_type[NodeType.FUNCTION] + idx.by_type[NodeType.METHOD]
        by_complexity = sorted(
            all_fns,
            key=lambda f: idx.int_prop(f, "cyclomatic"),
            reverse=True,
        )

        for fn in by_complexity[:5]:
            cc = idx.int_prop(fn, "cyclomatic")
            if cc > 5:
                u.complexity_hotspots.append({
                    "symbol": fn.label,
                    "file": idx.prop(fn, "file"),
                    "cyclomatic": cc,
                    "lines": idx.int_prop(fn, "lines"),
                    "node_id": fn.id,
                })

        # Architectural risks from issues
        arch_issues = report.issues_by_category(IssueCategory.ARCHITECTURE)
        for issue in arch_issues[:5]:
            u.architectural_risks.append(
                f"{issue.title}: {issue.description}"
            )

        # Also add coupling risks
        coupling_issues = report.issues_by_category(IssueCategory.COUPLING)
        for issue in coupling_issues[:3]:
            u.architectural_risks.append(
                f"{issue.title}: {issue.description}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Starting Point
    # ──────────────────────────────────────────────────────────────────────────

    def _determine_starting_point(
        self, u: RepositoryUnderstanding, idx: _GraphIndex
    ) -> None:
        """Determine where a new developer should start reading.

        Priority:
        1. Main/entry file (if exists)
        2. Most-depended-on module (highest fan-in)
        3. Module with most endpoints
        4. Largest module
        """
        # Check for main entry files
        for fn in idx.by_type[NodeType.FUNCTION]:
            if fn.label.lower() in ("main", "create_app", "app"):
                u.start_here = fn.label
                u.start_here_file = idx.prop(fn, "file")
                u.start_here_reason = "This is the application entry point — it shows how the system bootstraps."
                return

        # Find most-depended-on module
        if u.modules:
            most_depended = max(u.modules, key=lambda m: len(m.dependents))
            if most_depended.dependents:
                u.start_here = most_depended.name
                u.start_here_file = most_depended.path
                u.start_here_reason = (
                    f"This module is depended on by {len(most_depended.dependents)} other modules — "
                    f"it's the foundation that other code builds upon."
                )
                return

        # Fallback: module with most endpoints
        for module in u.modules:
            if any("endpoint" in r.lower() for r in [module.architecture_role]):
                u.start_here = module.name
                u.start_here_file = module.path
                u.start_here_reason = "This module contains the API endpoints — the system's public interface."
                return

        # Final fallback: first/largest module
        if u.modules:
            u.start_here = u.modules[0].name
            u.start_here_file = u.modules[0].path
            u.start_here_reason = "This is the largest module — a good starting point to understand the core logic."

    # ──────────────────────────────────────────────────────────────────────────
    # Top Dependencies
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_top_dependencies(
        self, u: RepositoryUnderstanding, idx: _GraphIndex
    ) -> None:
        """Detect the most important/central nodes by dependency count."""
        # Count how many other nodes depend on each node
        dep_count: dict[str, int] = defaultdict(int)
        for edge in idx.edges:
            if edge.relationship in (
                RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON,
                RelationshipType.CALLS, RelationshipType.INHERITS,
            ):
                dep_count[edge.target_id] += 1

        # Sort by dependency count
        top = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)[:10]
        u.top_dependencies = [
            f"{idx.node_map[nid].label} ({count} dependents)"
            for nid, count in top
            if nid in idx.node_map
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Purpose Inference
    # ──────────────────────────────────────────────────────────────────────────

    def _infer_purpose(self, u: RepositoryUnderstanding, idx: _GraphIndex) -> None:
        """Infer the repository's purpose from its structure and patterns."""
        signals: list[str] = []

        if u.total_endpoints > 0:
            signals.append(f"API service ({u.total_endpoints} endpoints)")
        if u.frameworks:
            signals.append(f"Built with {', '.join(u.frameworks)}")
        if u.total_tests > 0:
            signals.append(f"{u.total_tests} tests")

        # Check for patterns
        patterns = idx.by_type[NodeType.PATTERN]
        if patterns:
            pattern_names = [p.label for p in patterns[:5]]
            signals.append(f"Patterns: {', '.join(pattern_names)}")

        if not signals:
            u.purpose = f"A {u.languages[0] if u.languages else 'software'} project with {u.total_files} files."
        else:
            u.purpose = f"{u.repo_name} — {'; '.join(signals)}."

        u.headline = u.purpose
