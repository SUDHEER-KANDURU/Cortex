"""Neo4j graph repository — replaces InMemoryGraphRepository.
Uses the official neo4j-python-driver with async sessions.
Ready to swap in when Docker is running."""

from neo4j import AsyncGraphDatabase, AsyncDriver
from cortex.graph.domain.entities import (
    GraphNode, GraphEdge, NodeType, RelationshipType,
)
from cortex.graph.domain.interfaces import AbstractGraphRepository
from shared.exceptions import NotFoundError, InfrastructureError
import structlog

logger = structlog.get_logger()


class Neo4jGraphRepository(AbstractGraphRepository):
    """Neo4j implementation of AbstractGraphRepository.

    Uses Cypher queries — the graph query language.
    Each method shows you a real Cypher pattern worth learning.

    To switch from in-memory to Neo4j:
    1. Start Docker: docker compose -f docker/docker-compose.yml up
    2. Open Neo4j browser: http://localhost:7474
    3. In graph/presentation/router.py change:
       _repository = InMemoryGraphRepository()
       to:
       _repository = Neo4jGraphRepository(uri, user, password)

    Cypher basics used here:
    - MERGE: create if not exists (idempotent)
    - MATCH: find nodes/relationships
    - CREATE: create relationship between existing nodes
    - DETACH DELETE: delete node and all its relationships
    - WITH: pipe results between clauses
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
    ) -> None:
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(user, password)
        )

    async def close(self) -> None:
        """Close the driver connection pool."""
        await self._driver.close()

    async def save_node(self, node: GraphNode) -> GraphNode:
        """Save a node using MERGE — creates if not exists,
        updates if already there. Idempotent and safe to retry."""
        async with self._driver.session() as session:
            try:
                # MERGE on id means we never create duplicates
                # SET updates all properties on each call
                await session.run(
                    f"""
                    MERGE (n:{node.node_type.value} {{id: $id}})
                    SET n.label = $label,
                        n.job_id = $job_id,
                        n.properties = $properties,
                        n.created_at = $created_at
                    """,
                    id=node.id,
                    label=node.label,
                    job_id=node.job_id,
                    properties=str(node.properties),
                    created_at=node.created_at.isoformat(),
                )
                logger.info(
                    "neo4j_node_saved",
                    node_id=node.id,
                    node_type=node.node_type.value,
                )
                return node
            except Exception as e:
                raise InfrastructureError(
                    f"Failed to save node {node.id}: {e}"
                )

    async def save_edge(self, edge: GraphEdge) -> GraphEdge:
        """Save a relationship using MATCH + MERGE.
        First finds both nodes, then creates the relationship
        between them if it doesn't exist yet."""
        async with self._driver.session() as session:
            try:
                await session.run(
                    f"""
                    MATCH (src {{id: $source_id}})
                    MATCH (tgt {{id: $target_id}})
                    MERGE (src)-[r:{edge.relationship.value} {{id: $id}}]->(tgt)
                    SET r.job_id = $job_id,
                        r.created_at = $created_at
                    """,
                    id=edge.id,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    job_id=edge.job_id,
                    created_at=edge.created_at.isoformat(),
                )
                return edge
            except Exception as e:
                raise InfrastructureError(
                    f"Failed to save edge {edge.id}: {e}"
                )

    async def get_node_by_id(
        self, node_id: str
    ) -> GraphNode | None:
        """Find a node by its id property.
        Returns None if not found — never raises."""
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=node_id,
            )
            record = await result.single()
            if not record:
                return None
            return self._record_to_node(record["n"])

    async def get_nodes_by_job(
        self, job_id: str
    ) -> list[GraphNode]:
        """Get all nodes for a job using job_id property filter."""
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (n {job_id: $job_id}) RETURN n",
                job_id=job_id,
            )
            records = await result.data()
            return [self._record_to_node(r["n"]) for r in records]

    async def get_nodes_by_type(
        self,
        job_id: str,
        node_type: NodeType,
    ) -> list[GraphNode]:
        """Get nodes filtered by both job_id and label (node type).
        The label in Cypher IS the node type — Repository, Module, etc."""
        async with self._driver.session() as session:
            result = await session.run(
                f"MATCH (n:{node_type.value} {{job_id: $job_id}}) "
                f"RETURN n",
                job_id=job_id,
            )
            records = await result.data()
            return [self._record_to_node(r["n"]) for r in records]

    async def get_edges_by_job(
        self, job_id: str
    ) -> list[GraphEdge]:
        """Get all relationships for a job.
        The pattern (src)-[r]->(tgt) matches any relationship type."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (src)-[r {job_id: $job_id}]->(tgt)
                RETURN r, src.id as source_id, tgt.id as target_id,
                       type(r) as rel_type
                """,
                job_id=job_id,
            )
            records = await result.data()
            return [
                self._record_to_edge(r) for r in records
            ]

    async def get_edges_by_relationship(
        self,
        job_id: str,
        relationship: RelationshipType,
    ) -> list[GraphEdge]:
        """Filter edges by relationship type using the Cypher type."""
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (src)-[r:{relationship.value} {{job_id: $job_id}}]
                ->(tgt)
                RETURN r, src.id as source_id, tgt.id as target_id,
                       type(r) as rel_type
                """,
                job_id=job_id,
            )
            records = await result.data()
            return [self._record_to_edge(r) for r in records]

    async def get_edges_for_node(
        self, node_id: str
    ) -> list[GraphEdge]:
        """Get all edges connected to a node in either direction."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (src)-[r]->(tgt)
                WHERE src.id = $node_id OR tgt.id = $node_id
                RETURN r, src.id as source_id, tgt.id as target_id,
                       type(r) as rel_type
                """,
                node_id=node_id,
            )
            records = await result.data()
            return [self._record_to_edge(r) for r in records]

    async def delete_by_job(
        self, job_id: str
    ) -> tuple[int, int]:
        """Delete all nodes and edges for a job.
        DETACH DELETE removes the node AND all its relationships."""
        async with self._driver.session() as session:
            try:
                # Count first
                node_result = await session.run(
                    "MATCH (n {job_id: $job_id}) RETURN count(n) as cnt",
                    job_id=job_id,
                )
                node_count_record = await node_result.single()
                node_count = node_count_record["cnt"] if node_count_record else 0

                edge_result = await session.run(
                    """
                    MATCH ()-[r {job_id: $job_id}]->()
                    RETURN count(r) as cnt
                    """,
                    job_id=job_id,
                )
                edge_count_record = await edge_result.single()
                edge_count = edge_count_record["cnt"] if edge_count_record else 0

                # DETACH DELETE removes node + all connected relationships
                await session.run(
                    "MATCH (n {job_id: $job_id}) DETACH DELETE n",
                    job_id=job_id,
                )

                logger.info(
                    "neo4j_graph_deleted",
                    job_id=job_id,
                    nodes=node_count,
                    edges=edge_count,
                )
                return int(node_count), int(edge_count)

            except Exception as e:
                raise InfrastructureError(
                    f"Failed to delete graph for job {job_id}: {e}"
                )

    async def count_by_job(self, job_id: str) -> dict[str, int]:
        """Return node and edge counts for a job."""
        async with self._driver.session() as session:
            node_result = await session.run(
                "MATCH (n {job_id: $job_id}) RETURN count(n) as cnt",
                job_id=job_id,
            )
            node_record = await node_result.single()

            edge_result = await session.run(
                "MATCH ()-[r {job_id: $job_id}]->() "
                "RETURN count(r) as cnt",
                job_id=job_id,
            )
            edge_record = await edge_result.single()

            return {
                "nodes": node_record["cnt"] if node_record else 0,
                "edges": edge_record["cnt"] if edge_record else 0,
            }

    def _record_to_node(self, node_data: dict) -> GraphNode:
        """Convert a Neo4j node record to a domain entity."""
        import ast as _ast
        from datetime import datetime
        props_raw = node_data.get("properties", "{}")
        try:
            props = _ast.literal_eval(str(props_raw))
        except Exception:
            props = {}

        created_raw = node_data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(str(created_raw))
        except Exception:
            created_at = datetime.utcnow()

        return GraphNode(
            id=str(node_data["id"]),
            label=str(node_data.get("label", "")),
            node_type=NodeType(
                node_data.get("node_type", NodeType.FILE.value)
            ),
            job_id=str(node_data.get("job_id", "")),
            properties=props if isinstance(props, dict) else {},
            created_at=created_at,
        )

    def _record_to_edge(self, record: dict) -> GraphEdge:
        """Convert a Neo4j relationship record to a domain entity."""
        from datetime import datetime
        r = record.get("r", {})
        created_raw = r.get("created_at", "") if r else ""
        try:
            created_at = datetime.fromisoformat(str(created_raw))
        except Exception:
            created_at = datetime.utcnow()

        return GraphEdge(
            id=str(r.get("id", "")) if r else "",
            source_id=str(record.get("source_id", "")),
            target_id=str(record.get("target_id", "")),
            relationship=RelationshipType(
                record.get("rel_type", RelationshipType.CONTAINS.value)
            ),
            job_id=str(r.get("job_id", "")) if r else "",
            created_at=created_at,
        )