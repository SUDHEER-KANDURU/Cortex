"""Graph application layer — all business logic for the knowledge graph."""

from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from cortex.graph.domain.interfaces import (
    AbstractGraphRepository,
    AbstractGraphService,
)
from shared.exceptions import NotFoundError, ValidationError
import structlog

logger = structlog.get_logger()


class GraphService(AbstractGraphService):

    def __init__(self, repository: AbstractGraphRepository) -> None:
        self._repo = repository

    async def add_node(
        self,
        job_id: str,
        node_id: str,
        label: str,
        node_type: NodeType,
        properties: dict | None = None,
    ) -> GraphNode:
        """Create and persist a graph node."""
        node = GraphNode(
            id=node_id,
            label=label,
            node_type=node_type,
            job_id=job_id,
            properties=properties or {},
        )
        saved = await self._repo.save_node(node)
        logger.info(
            "graph_node_added",
            node_id=node_id,
            job_id=job_id,
            node_type=node_type.value,
        )
        return saved

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
        # Validate source and target nodes exist
        source = await self._repo.get_node_by_id(source_id)
        target = await self._repo.get_node_by_id(target_id)

        if not source:
            raise NotFoundError(
                f"Source node not found: {source_id}"
            )
        if not target:
            raise NotFoundError(
                f"Target node not found: {target_id}"
            )

        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            job_id=job_id,
            properties=properties or {},
        )
        saved = await self._repo.save_edge(edge)
        logger.info(
            "graph_edge_added",
            edge_id=edge_id,
            job_id=job_id,
            relationship=relationship.value,
        )
        return saved

    async def get_graph_for_job(
        self,
        job_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Return all nodes and edges for a job."""
        nodes = await self._repo.get_nodes_by_job(job_id)
        edges = await self._repo.get_edges_by_job(job_id)
        return nodes, edges

    async def get_nodes(
        self,
        job_id: str,
        node_type: NodeType | None = None,
    ) -> list[GraphNode]:
        """Return nodes for a job, optionally filtered by type."""
        if node_type:
            return await self._repo.get_nodes_by_type(
                job_id, node_type
            )
        return await self._repo.get_nodes_by_job(job_id)

    async def get_edges(
        self,
        job_id: str,
        relationship: RelationshipType | None = None,
    ) -> list[GraphEdge]:
        """Return edges for a job, optionally filtered by type."""
        if relationship:
            return await self._repo.get_edges_by_relationship(
                job_id, relationship
            )
        return await self._repo.get_edges_by_job(job_id)

    async def delete_graph(self, job_id: str) -> dict[str, int]:
        """Delete all graph data for a job."""
        nodes_deleted, edges_deleted = await self._repo.delete_by_job(
            job_id
        )
        logger.info(
            "graph_deleted",
            job_id=job_id,
            nodes_deleted=nodes_deleted,
            edges_deleted=edges_deleted,
        )
        return {
            "nodes_deleted": nodes_deleted,
            "edges_deleted": edges_deleted,
        }