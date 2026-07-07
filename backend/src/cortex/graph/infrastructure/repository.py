"""Graph infrastructure repository — Neo4j driver implementation of GraphRepository."""
"""In-memory graph repository — used until Neo4j is wired in Week 8."""

from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from cortex.graph.domain.interfaces import AbstractGraphRepository
from shared.exceptions import NotFoundError

_nodes: dict[str, GraphNode] = {}
_edges: dict[str, GraphEdge] = {}


class InMemoryGraphRepository(AbstractGraphRepository):

    async def save_node(self, node: GraphNode) -> GraphNode:
        _nodes[node.id] = node
        return node

    async def save_edge(self, edge: GraphEdge) -> GraphEdge:
        _edges[edge.id] = edge
        return edge

    async def get_node_by_id(self, node_id: str) -> GraphNode | None:
        return _nodes.get(node_id)

    async def get_nodes_by_job(self, job_id: str) -> list[GraphNode]:
        return [n for n in _nodes.values() if n.job_id == job_id]

    async def get_nodes_by_type(
        self,
        job_id: str,
        node_type: NodeType,
    ) -> list[GraphNode]:
        return [
            n for n in _nodes.values()
            if n.job_id == job_id and n.node_type == node_type
        ]

    async def get_edges_by_job(self, job_id: str) -> list[GraphEdge]:
        return [e for e in _edges.values() if e.job_id == job_id]

    async def get_edges_by_relationship(
        self,
        job_id: str,
        relationship: RelationshipType,
    ) -> list[GraphEdge]:
        return [
            e for e in _edges.values()
            if e.job_id == job_id
            and e.relationship == relationship
        ]

    async def get_edges_for_node(
        self,
        node_id: str,
    ) -> list[GraphEdge]:
        return [
            e for e in _edges.values()
            if e.source_id == node_id or e.target_id == node_id
        ]

    async def delete_by_job(self, job_id: str) -> tuple[int, int]:
        node_keys = [
            k for k, v in _nodes.items() if v.job_id == job_id
        ]
        edge_keys = [
            k for k, v in _edges.items() if v.job_id == job_id
        ]
        for k in node_keys:
            del _nodes[k]
        for k in edge_keys:
            del _edges[k]
        return len(node_keys), len(edge_keys)

    async def count_by_job(self, job_id: str) -> dict[str, int]:
        return {
            "nodes": sum(
                1 for n in _nodes.values() if n.job_id == job_id
            ),
            "edges": sum(
                1 for e in _edges.values() if e.job_id == job_id
            ),
        }