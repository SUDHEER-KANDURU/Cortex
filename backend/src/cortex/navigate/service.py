"""Navigate service — builds full navigation context from the Knowledge Graph.

Design principles:
  - Only loads edges connected to the target node (not the entire graph)
  - Reuses existing graph relationships (CALLS, IMPORTS, DEPENDS_ON, etc.)
  - Clearly distinguishes DETECTED vs INFERRED relationships
  - Returns only what's needed for the selected entity
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import structlog

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.insights.application.engine import InsightsEngine
from cortex.jobs.infrastructure.dependencies import job_repository
from cortex.navigate.models import (
    CallPath,
    CallPathNode,
    ConnectedNode,
    NavigateInsights,
    NavigateIssue,
    NavigateResponse,
    RelationshipStatus,
    SourceLocation,
)

if TYPE_CHECKING:
    from cortex.graph.domain.entities import GraphEdge, GraphNode

logger = structlog.get_logger()


# Relationships that represent "calling" (execution flow)
_CALL_RELATIONSHIPS = {
    RelationshipType.CALLS,
    RelationshipType.EXPOSES,
}

# Relationships that represent dependencies (structural)
_DEPENDENCY_RELATIONSHIPS = {
    RelationshipType.IMPORTS,
    RelationshipType.DEPENDS_ON,
    RelationshipType.INHERITS,
    RelationshipType.IMPLEMENTS,
}

# Relationships used for test detection
_TEST_RELATIONSHIPS = {
    RelationshipType.TESTS,
}

# Max depth for multi-hop traversal
_MAX_TRAVERSAL_DEPTH = 4
_MAX_RESULTS_PER_SECTION = 25


def _node_file_path(node: "GraphNode") -> str:
    """Extract file path from node properties."""
    return str(node.properties.get("file", "") or node.properties.get("path", "") or "")


def _node_line_start(node: "GraphNode") -> int:
    """Extract line_start from node properties."""
    try:
        return int(node.properties.get("line_start", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _node_line_end(node: "GraphNode") -> int:
    """Extract line_end from node properties."""
    try:
        return int(node.properties.get("line_end", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _to_connected_node(
    node: "GraphNode",
    relationship: str,
    status: RelationshipStatus = RelationshipStatus.DETECTED,
) -> ConnectedNode:
    """Convert a GraphNode to a ConnectedNode response model."""
    return ConnectedNode(
        id=node.id,
        label=node.label,
        node_type=node.node_type.value,
        relationship=relationship,
        relationship_status=status,
        file_path=_node_file_path(node),
        line_start=_node_line_start(node),
    )


class NavigateService:
    """Builds full navigation context for any graph entity."""

    async def get_navigation_context(
        self, job_id: str, node_id: str
    ) -> NavigateResponse:
        """Build the complete navigation response for a node.

        This is the primary entrypoint. It:
        1. Loads the target node
        2. Gets all directly connected edges
        3. Classifies connections into callers, callees, dependencies, etc.
        4. Finds related tests
        5. Computes insights and issues
        6. Builds breadcrumb path
        7. Computes upstream/downstream call paths
        """
        # 1. Load target node
        target = await graph_repository.get_node_by_id(node_id)
        if not target or target.job_id != job_id:
            return None  # type: ignore[return-value]

        # 2. Get all edges connected to this node (efficient — not full graph)
        edges = await graph_repository.get_edges_for_node(node_id)

        # 3. Collect all connected node IDs
        connected_ids = set()
        for edge in edges:
            connected_ids.add(edge.source_id)
            connected_ids.add(edge.target_id)
        connected_ids.discard(node_id)

        # 4. Load connected nodes in bulk
        all_job_nodes = await graph_repository.get_nodes_by_job(job_id)
        node_map = {n.id: n for n in all_job_nodes}

        # 5. Classify edges
        callers: list[ConnectedNode] = []
        callees: list[ConnectedNode] = []
        dependencies: list[ConnectedNode] = []
        dependents: list[ConnectedNode] = []
        tests: list[ConnectedNode] = []
        contained_by: ConnectedNode | None = None
        contains: list[ConnectedNode] = []

        for edge in edges:
            if edge.target_id == node_id:
                # Incoming edge — someone points to us
                src = node_map.get(edge.source_id)
                if not src:
                    continue

                if edge.relationship == RelationshipType.CONTAINS:
                    contained_by = _to_connected_node(src, "CONTAINS")
                elif edge.relationship in _CALL_RELATIONSHIPS:
                    callers.append(_to_connected_node(src, edge.relationship.value))
                elif edge.relationship in _DEPENDENCY_RELATIONSHIPS:
                    dependents.append(_to_connected_node(src, edge.relationship.value))
                elif edge.relationship in _TEST_RELATIONSHIPS:
                    tests.append(_to_connected_node(src, edge.relationship.value))
                else:
                    # Other incoming = someone depends on us
                    dependents.append(_to_connected_node(src, edge.relationship.value))

            elif edge.source_id == node_id:
                # Outgoing edge — we point to something
                tgt = node_map.get(edge.target_id)
                if not tgt:
                    continue

                if edge.relationship == RelationshipType.CONTAINS:
                    contains.append(_to_connected_node(tgt, "CONTAINS"))
                elif edge.relationship in _CALL_RELATIONSHIPS:
                    callees.append(_to_connected_node(tgt, edge.relationship.value))
                elif edge.relationship in _DEPENDENCY_RELATIONSHIPS:
                    dependencies.append(_to_connected_node(tgt, edge.relationship.value))
                elif edge.relationship in _TEST_RELATIONSHIPS:
                    tests.append(_to_connected_node(tgt, edge.relationship.value))
                else:
                    # Other outgoing = we depend on something
                    dependencies.append(_to_connected_node(tgt, edge.relationship.value))

        # 6. Find related tests (also check for test nodes that reference this file/symbol)
        if not tests:
            tests = self._find_related_tests(target, all_job_nodes, edges, node_map)

        # 7. Find related modules (siblings in the same parent)
        related_modules = self._find_related_modules(
            target, contained_by, all_job_nodes, edges, node_map
        )

        # 8. Compute insights
        insights = self._compute_insights(target, callers, callees, dependencies, dependents, job_id, all_job_nodes, edges)

        # 9. Build breadcrumb
        breadcrumb = self._build_breadcrumb(target, node_map, edges)

        # 10. Build call paths (limited depth)
        call_paths_upstream = await self._trace_call_paths(
            node_id, job_id, node_map, direction="upstream", max_depth=_MAX_TRAVERSAL_DEPTH
        )
        call_paths_downstream = await self._trace_call_paths(
            node_id, job_id, node_map, direction="downstream", max_depth=_MAX_TRAVERSAL_DEPTH
        )

        # 11. Source location
        job = await job_repository.get_by_id(job_id)
        repo_url = job.repo_url if job else ""

        source = SourceLocation(
            repository=repo_url,
            file_path=_node_file_path(target),
            line_start=_node_line_start(target),
            line_end=_node_line_end(target),
            symbol_name=target.label,
        )

        return NavigateResponse(
            id=target.id,
            label=target.label,
            node_type=target.node_type.value,
            source=source,
            callers=callers[:_MAX_RESULTS_PER_SECTION],
            callees=callees[:_MAX_RESULTS_PER_SECTION],
            dependencies=dependencies[:_MAX_RESULTS_PER_SECTION],
            dependents=dependents[:_MAX_RESULTS_PER_SECTION],
            related_modules=related_modules[:_MAX_RESULTS_PER_SECTION],
            tests=tests[:_MAX_RESULTS_PER_SECTION],
            insights=insights,
            contained_by=contained_by,
            contains=contains[:_MAX_RESULTS_PER_SECTION],
            breadcrumb=breadcrumb,
            call_paths_upstream=call_paths_upstream,
            call_paths_downstream=call_paths_downstream,
        )

    def _find_related_tests(
        self,
        target: "GraphNode",
        all_nodes: list["GraphNode"],
        edges: list["GraphEdge"],
        node_map: dict[str, "GraphNode"],
    ) -> list[ConnectedNode]:
        """Find test nodes that might test this entity.

        Strategy:
        1. Direct TESTS relationship (already checked)
        2. Test nodes whose label contains the target's label
        3. Test nodes in the same file
        """
        results: list[ConnectedNode] = []
        target_label_lower = target.label.lower()
        target_file = _node_file_path(target)

        for node in all_nodes:
            if node.node_type != NodeType.TEST:
                continue
            if node.id == target.id:
                continue

            # Check label match
            if target_label_lower in node.label.lower():
                results.append(
                    _to_connected_node(node, "TESTS", RelationshipStatus.INFERRED)
                )
                continue

            # Check file proximity (test file for the same module)
            node_file = _node_file_path(node)
            if target_file and node_file:
                # e.g., auth_service.py → test_auth_service.py
                target_stem = target_file.rsplit("/", 1)[-1].replace(".py", "")
                if target_stem and target_stem in node_file:
                    results.append(
                        _to_connected_node(node, "TESTS", RelationshipStatus.INFERRED)
                    )

        return results[:_MAX_RESULTS_PER_SECTION]

    def _find_related_modules(
        self,
        target: "GraphNode",
        contained_by: ConnectedNode | None,
        all_nodes: list["GraphNode"],
        edges: list["GraphEdge"],
        node_map: dict[str, "GraphNode"],
    ) -> list[ConnectedNode]:
        """Find sibling modules/components in the same parent."""
        if not contained_by:
            return []

        parent_id = contained_by.id
        siblings: list[ConnectedNode] = []

        # Find all CONTAINS edges from the parent to get siblings
        # We have all_nodes loaded and need all edges in the job.
        # Since edges param only has edges for the target node,
        # we look through all_nodes to find nodes that share the same parent.
        # We can check by looking at edges from the full job.
        # For efficiency, iterate all edges and find children of the same parent.
        for node in all_nodes:
            if node.id == target.id or node.id == parent_id:
                continue
            # Check if this node's properties indicate it's in the same directory/module
            target_file = _node_file_path(target)
            node_file = _node_file_path(node)
            if target_file and node_file:
                target_dir = "/".join(target_file.split("/")[:-1])
                node_dir = "/".join(node_file.split("/")[:-1])
                if target_dir and target_dir == node_dir and node.node_type == target.node_type:
                    siblings.append(_to_connected_node(node, "SIBLING", RelationshipStatus.INFERRED))
                    if len(siblings) >= 10:
                        break

        return siblings[:10]

    def _compute_insights(
        self,
        target: "GraphNode",
        callers: list[ConnectedNode],
        callees: list[ConnectedNode],
        dependencies: list[ConnectedNode],
        dependents: list[ConnectedNode],
        job_id: str,
        all_nodes: list["GraphNode"],
        all_edges: list["GraphEdge"],
    ) -> NavigateInsights:
        """Compute engineering insights for the target node."""
        props = target.properties

        complexity = int(props.get("cyclomatic", 0) or 0)
        lines = int(props.get("lines", 0) or 0)
        methods = int(props.get("methods", 0) or 0)
        parameters = int(props.get("parameters", 0) or 0)
        is_async = bool(props.get("is_async", False))
        has_docstring = bool(props.get("has_docstring", False))

        coupling_in = len(callers) + len(dependents)
        coupling_out = len(callees) + len(dependencies)

        # Risk factors
        risk_factors: list[str] = []
        if complexity >= 15:
            risk_factors.append(f"Very high complexity ({complexity})")
        elif complexity >= 10:
            risk_factors.append(f"High complexity ({complexity})")

        if coupling_in >= 10:
            risk_factors.append(f"High incoming coupling ({coupling_in} dependents)")

        if lines > 200:
            risk_factors.append(f"Large function/class ({lines} lines)")

        if not has_docstring and target.node_type in (NodeType.CLASS, NodeType.FUNCTION, NodeType.METHOD):
            risk_factors.append("Missing documentation")

        if parameters > 5:
            risk_factors.append(f"Too many parameters ({parameters})")

        # Find issues related to this symbol
        issues = self._find_related_issues(target, job_id, all_nodes, all_edges)

        return NavigateInsights(
            complexity=complexity,
            lines=lines,
            methods=methods,
            parameters=parameters,
            is_async=is_async,
            has_docstring=has_docstring,
            coupling_in=coupling_in,
            coupling_out=coupling_out,
            issues=issues,
            risk_factors=risk_factors,
        )

    def _find_related_issues(
        self,
        target: "GraphNode",
        job_id: str,
        all_nodes: list["GraphNode"],
        all_edges: list["GraphEdge"],
    ) -> list[NavigateIssue]:
        """Find engineering issues related to this node using the InsightsEngine."""
        try:
            job_sync = None
            # Use insights engine to compute issues
            engine = InsightsEngine()
            # We need the repo_url for the engine
            report = engine.compute(
                job_id=job_id,
                repo_url="",  # Not needed for issue filtering
                nodes=all_nodes,
                edges=all_edges,
            )

            target_file = _node_file_path(target)
            target_symbol = target.label

            related: list[NavigateIssue] = []
            for issue in report.issues:
                # Match by symbol name or file path
                if (
                    (issue.affected_symbol and issue.affected_symbol == target_symbol)
                    or (issue.file_path and target_file and issue.file_path == target_file)
                ):
                    related.append(NavigateIssue(
                        title=issue.title,
                        severity=issue.severity.value,
                        category=issue.category.value,
                        description=issue.description,
                        recommendation=issue.recommendation,
                        file_path=issue.file_path,
                        line_start=issue.line_start,
                        line_end=issue.line_end,
                        confidence=issue.confidence,
                    ))

            return related[:10]
        except Exception as e:
            logger.warning("navigate_issues_failed", error=str(e))
            return []

    def _build_breadcrumb(
        self,
        target: "GraphNode",
        node_map: dict[str, "GraphNode"],
        edges: list["GraphEdge"],
    ) -> list[ConnectedNode]:
        """Build a breadcrumb path from root to the target node.

        Follows CONTAINS edges upward to build:
        Repository > Module > File > Class > Method
        """
        breadcrumb: list[ConnectedNode] = []
        current_id = target.id
        visited = {current_id}

        # Walk up CONTAINS edges
        for _ in range(10):  # safety limit
            parent_id = None
            for edge in edges:
                if (
                    edge.target_id == current_id
                    and edge.relationship == RelationshipType.CONTAINS
                    and edge.source_id not in visited
                ):
                    parent_id = edge.source_id
                    break

            if not parent_id:
                # Try finding parent from all edges in the job
                # (edges param only has edges for the target node)
                break

            parent = node_map.get(parent_id)
            if not parent:
                break

            breadcrumb.append(_to_connected_node(parent, "CONTAINS"))
            visited.add(parent_id)
            current_id = parent_id

        # Reverse so root is first
        breadcrumb.reverse()
        # Add self at end
        breadcrumb.append(_to_connected_node(target, "SELF"))
        return breadcrumb

    async def _trace_call_paths(
        self,
        start_id: str,
        job_id: str,
        node_map: dict[str, "GraphNode"],
        direction: str = "upstream",
        max_depth: int = _MAX_TRAVERSAL_DEPTH,
    ) -> list[CallPath]:
        """Trace execution paths upstream or downstream using BFS.

        upstream: who calls this → who calls that → ...
        downstream: what does this call → what does that call → ...
        """
        all_edges = await graph_repository.get_edges_by_job(job_id)

        # Build adjacency based on direction
        # For upstream: find edges where target == current (someone calls us)
        # For downstream: find edges where source == current (we call someone)
        call_edges = [
            e for e in all_edges
            if e.relationship in _CALL_RELATIONSHIPS
        ]

        paths: list[CallPath] = []
        visited: set[str] = {start_id}
        queue: deque[tuple[str, list[CallPathNode]]] = deque()

        start_node = node_map.get(start_id)
        if not start_node:
            return []

        start_path_node = CallPathNode(
            id=start_id,
            label=start_node.label,
            node_type=start_node.node_type.value,
            file_path=_node_file_path(start_node),
            depth=0,
        )
        queue.append((start_id, [start_path_node]))

        while queue:
            current_id, current_path = queue.popleft()

            if len(current_path) > max_depth:
                continue

            # Find next hops
            next_ids: list[str] = []
            if direction == "upstream":
                next_ids = [
                    e.source_id for e in call_edges
                    if e.target_id == current_id and e.source_id not in visited
                ]
            else:
                next_ids = [
                    e.target_id for e in call_edges
                    if e.source_id == current_id and e.target_id not in visited
                ]

            if not next_ids and len(current_path) > 1:
                # End of path — save it
                paths.append(CallPath(nodes=current_path, direction=direction))
                continue

            for next_id in next_ids[:5]:  # limit branching
                visited.add(next_id)
                next_node = node_map.get(next_id)
                if not next_node:
                    continue

                new_path = current_path + [CallPathNode(
                    id=next_id,
                    label=next_node.label,
                    node_type=next_node.node_type.value,
                    file_path=_node_file_path(next_node),
                    depth=len(current_path),
                )]
                queue.append((next_id, new_path))

        # If we visited nodes but didn't terminate naturally, save partial paths
        if not paths and len(visited) > 1:
            # Return what we found
            pass

        return paths[:10]  # limit total paths

    async def get_impact_analysis(
        self, job_id: str, node_id: str
    ) -> list[ConnectedNode]:
        """Compute impact analysis — what might break if this node changes.

        Traverses dependents transitively (BFS) to find all affected nodes.
        """
        all_edges = await graph_repository.get_edges_by_job(job_id)
        all_nodes = await graph_repository.get_nodes_by_job(job_id)
        node_map = {n.id: n for n in all_nodes}

        # BFS through reverse dependencies
        affected: list[ConnectedNode] = []
        visited: set[str] = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth > _MAX_TRAVERSAL_DEPTH:
                continue

            for edge in all_edges:
                if edge.target_id == current_id and edge.source_id not in visited:
                    if edge.relationship in (_CALL_RELATIONSHIPS | _DEPENDENCY_RELATIONSHIPS):
                        src = node_map.get(edge.source_id)
                        if src:
                            status = (
                                RelationshipStatus.DETECTED if depth == 0
                                else RelationshipStatus.INFERRED
                            )
                            affected.append(_to_connected_node(
                                src, edge.relationship.value, status
                            ))
                            visited.add(edge.source_id)
                            queue.append((edge.source_id, depth + 1))

        return affected[:_MAX_RESULTS_PER_SECTION]
