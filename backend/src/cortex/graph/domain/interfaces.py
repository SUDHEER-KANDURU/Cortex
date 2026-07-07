"""Abstract repository and service interfaces for the graph domain."""

from abc import ABC, abstractmethod
from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)


class AbstractGraphRepository(ABC):

    @abstractmethod
    async def save_node(self, node: GraphNode) -> GraphNode:
        """Persist a graph node and return it."""
        ...

    @abstractmethod
    async def save_edge(self, edge: GraphEdge) -> GraphEdge:
        """Persist a graph edge and return it."""
        ...

    @abstractmethod
    async def get_node_by_id(self, node_id: str) -> GraphNode | None:
        """Return a node by ID. Returns None if not found."""
        ...

    @abstractmethod
    async def get_nodes_by_job(self, job_id: str) -> list[GraphNode]:
        """Return all nodes for a given job."""
        ...

    @abstractmethod
    async def get_nodes_by_type(
        self,
        job_id: str,
        node_type: NodeType,
    ) -> list[GraphNode]:
        """Return all nodes of a specific type for a job."""
        ...

    @abstractmethod
    async def get_edges_by_job(self, job_id: str) -> list[GraphEdge]:
        """Return all edges for a given job."""
        ...

    @abstractmethod
    async def get_edges_by_relationship(
        self,
        job_id: str,
        relationship: RelationshipType,
    ) -> list[GraphEdge]:
        """Return all edges of a specific relationship type."""
        ...

    @abstractmethod
    async def get_edges_for_node(
        self,
        node_id: str,
    ) -> list[GraphEdge]:
        """Return all edges connected to a specific node."""
        ...

    @abstractmethod
    async def delete_by_job(self, job_id: str) -> tuple[int, int]:
        """Delete all nodes and edges for a job.
        Returns (nodes_deleted, edges_deleted)."""
        ...

    @abstractmethod
    async def count_by_job(self, job_id: str) -> dict[str, int]:
        """Return node and edge counts for a job."""
        ...


class AbstractGraphService(ABC):

    @abstractmethod
    async def add_node(
        self,
        job_id: str,
        node_id: str,
        label: str,
        node_type: NodeType,
        properties: dict | None = None,
    ) -> GraphNode:
        """Create and persist a graph node."""
        ...

    @abstractmethod
    async def add_edge(
        self,
        job_id: str,
        edge_id: str,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        properties: dict | None = None,
    ) -> GraphEdge:
        """Create and persist a graph edge."""
        ...

    @abstractmethod
    async def get_graph_for_job(
        self,
        job_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Return all nodes and edges for a job."""
        ...

    @abstractmethod
    async def get_nodes(
        self,
        job_id: str,
        node_type: NodeType | None = None,
    ) -> list[GraphNode]:
        """Return nodes for a job, optionally filtered by type."""
        ...

    @abstractmethod
    async def get_edges(
        self,
        job_id: str,
        relationship: RelationshipType | None = None,
    ) -> list[GraphEdge]:
        """Return edges for a job, optionally filtered by type."""
        ...

    @abstractmethod
    async def delete_graph(self, job_id: str) -> dict[str, int]:
        """Delete all graph data for a job."""
        ...