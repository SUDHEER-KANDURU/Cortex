"""Blast Radius — "What happens if I change this?"

Given a node (file, class, function, module), computes:
  1. Direct dependents (nodes that directly import/call this)
  2. Transitive dependents (all nodes reachable via reverse dependency edges)
  3. Affected modules (which modules are impacted)
  4. Affected tests (which tests exercise this code)
  5. Risk assessment (based on count + coupling + complexity)

Uses ONLY graph relationships — no fabrication.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
import structlog

logger = structlog.get_logger()

# Edge types that represent "depends on" direction (target depends on source)
_DEPENDENCY_EDGES = {
    RelationshipType.IMPORTS,
    RelationshipType.DEPENDS_ON,
    RelationshipType.CALLS,
    RelationshipType.INHERITS,
    RelationshipType.IMPLEMENTS,
}


@dataclass
class BlastRadiusNode:
    """A node affected by a change, with distance from origin."""
    id: str
    label: str
    node_type: str
    file_path: str
    distance: int  # hops from the changed node
    relationship: str  # how it's connected


@dataclass
class BlastRadiusResult:
    """Complete blast radius analysis for a node."""
    # The target node being changed
    target_id: str
    target_label: str
    target_type: str
    target_file: str
    # Impact
    direct_dependents: list[BlastRadiusNode] = field(default_factory=list)
    transitive_dependents: list[BlastRadiusNode] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    affected_tests: list[BlastRadiusNode] = field(default_factory=list)
    # Risk assessment
    risk_level: str = "low"  # low, medium, high, critical
    risk_score: int = 0
    risk_factors: list[str] = field(default_factory=list)
    # Graph path evidence
    impact_paths: list[list[str]] = field(default_factory=list)


class BlastRadiusAnalyzer:
    """Computes the blast radius for a node using graph traversal.

    The analysis uses reverse dependency edges to find all nodes
    that would be affected by a change to the target node.
    """

    def analyze(
        self,
        target_node: GraphNode,
        all_nodes: list[GraphNode],
        all_edges: list[GraphEdge],
        max_depth: int = 4,
    ) -> BlastRadiusResult:
        """Compute the full blast radius for a target node."""
        result = BlastRadiusResult(
            target_id=target_node.id,
            target_label=target_node.label,
            target_type=target_node.node_type.value,
            target_file=str(target_node.properties.get("file", target_node.properties.get("path", ""))),
        )

        # Build indices
        node_map = {n.id: n for n in all_nodes}

        # Build reverse dependency index: who depends on X?
        # If A IMPORTS B, then A depends on B. So if B changes, A is affected.
        reverse_deps: dict[str, list[tuple[str, str]]] = defaultdict(list)  # target_id → [(source_id, rel)]
        for edge in all_edges:
            if edge.relationship in _DEPENDENCY_EDGES:
                # source depends on target, so target's change affects source
                reverse_deps[edge.target_id].append(
                    (edge.source_id, edge.relationship.value)
                )

        # Also consider: if we're changing a file, all symbols IN that file are also changed
        # If changing a class, methods in that class are affected downstream
        contains_children: dict[str, list[str]] = defaultdict(list)
        for edge in all_edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains_children[edge.source_id].append(edge.target_id)

        # Expand the target to include its children (a file change affects all its functions/classes)
        seeds = {target_node.id}
        if target_node.node_type in (NodeType.FILE, NodeType.MODULE, NodeType.CLASS):
            for child_id in contains_children.get(target_node.id, []):
                seeds.add(child_id)
                # Also include grandchildren (class → methods)
                for grandchild_id in contains_children.get(child_id, []):
                    seeds.add(grandchild_id)

        # BFS from seeds through reverse dependency edges
        visited: set[str] = set(seeds)
        current_layer = seeds.copy()
        depth = 0

        while current_layer and depth < max_depth:
            depth += 1
            next_layer: set[str] = set()

            for node_id in current_layer:
                for dependent_id, rel in reverse_deps.get(node_id, []):
                    if dependent_id in visited:
                        continue
                    visited.add(dependent_id)
                    next_layer.add(dependent_id)

                    dep_node = node_map.get(dependent_id)
                    if not dep_node:
                        continue

                    blast_node = BlastRadiusNode(
                        id=dependent_id,
                        label=dep_node.label,
                        node_type=dep_node.node_type.value,
                        file_path=str(dep_node.properties.get("file", dep_node.properties.get("path", ""))),
                        distance=depth,
                        relationship=rel,
                    )

                    # Categorize
                    if dep_node.node_type == NodeType.TEST:
                        result.affected_tests.append(blast_node)
                    elif depth == 1:
                        result.direct_dependents.append(blast_node)
                    else:
                        result.transitive_dependents.append(blast_node)

            current_layer = next_layer

        # Find affected modules
        module_names: set[str] = set()
        for node in result.direct_dependents + result.transitive_dependents:
            path = node.file_path
            if path:
                parts = path.replace("\\", "/").split("/")
                # Take the first meaningful directory as module name
                for part in parts:
                    if part and not part.startswith(".") and part not in ("src", "lib", "app"):
                        module_names.add(part)
                        break
        result.affected_modules = sorted(module_names)[:10]

        # Compute risk assessment
        result.risk_score, result.risk_level, result.risk_factors = self._assess_risk(
            target_node, result, all_nodes
        )

        # Build impact paths (up to 3 representative paths)
        result.impact_paths = self._build_impact_paths(
            target_node, result.direct_dependents[:3], node_map, reverse_deps
        )

        return result

    def _assess_risk(
        self,
        target: GraphNode,
        result: BlastRadiusResult,
        all_nodes: list[GraphNode],
    ) -> tuple[int, str, list[str]]:
        """Compute risk score and level from blast radius metrics."""
        score = 0
        factors: list[str] = []

        # Direct dependents
        direct_count = len(result.direct_dependents)
        if direct_count >= 10:
            score += 40
            factors.append(f"{direct_count} direct dependents (critical hub)")
        elif direct_count >= 5:
            score += 25
            factors.append(f"{direct_count} direct dependents (widely used)")
        elif direct_count >= 2:
            score += 10
            factors.append(f"{direct_count} direct dependents")

        # Transitive reach
        transitive_count = len(result.transitive_dependents)
        if transitive_count >= 20:
            score += 30
            factors.append(f"{transitive_count} transitive dependents (deep impact)")
        elif transitive_count >= 10:
            score += 20
            factors.append(f"{transitive_count} transitive dependents")
        elif transitive_count >= 3:
            score += 10
            factors.append(f"{transitive_count} transitive dependents")

        # Affected tests
        test_count = len(result.affected_tests)
        if test_count >= 5:
            score += 10
            factors.append(f"{test_count} tests would need verification")
        elif test_count == 0 and direct_count > 0:
            score += 15
            factors.append("No tests cover this area (changes are unguarded)")

        # Module spread
        module_count = len(result.affected_modules)
        if module_count >= 4:
            score += 15
            factors.append(f"Impacts {module_count} modules (cross-cutting change)")
        elif module_count >= 2:
            score += 5
            factors.append(f"Impacts {module_count} modules")

        # Target complexity
        complexity = int(target.properties.get("cyclomatic", 0) or 0)
        if complexity >= 15:
            score += 10
            factors.append(f"Target has high complexity ({complexity})")

        # Determine level
        if score >= 60:
            level = "critical"
        elif score >= 40:
            level = "high"
        elif score >= 20:
            level = "medium"
        else:
            level = "low"

        return min(score, 100), level, factors

    def _build_impact_paths(
        self,
        target: GraphNode,
        direct_deps: list[BlastRadiusNode],
        node_map: dict[str, GraphNode],
        reverse_deps: dict[str, list[tuple[str, str]]],
    ) -> list[list[str]]:
        """Build representative impact paths from target → affected nodes."""
        paths: list[list[str]] = []

        for dep in direct_deps[:3]:
            path = [target.label, f"—[{dep.relationship}]→", dep.label]
            # Try to extend one more hop
            for next_id, rel in reverse_deps.get(dep.id, [])[:1]:
                next_node = node_map.get(next_id)
                if next_node:
                    path.extend([f"—[{rel}]→", next_node.label])
            paths.append(path)

        return paths
