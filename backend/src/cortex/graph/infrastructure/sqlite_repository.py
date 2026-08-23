"""SQLite graph repository — persists knowledge graph nodes and edges.
Replaces InMemoryGraphRepository with real storage.
Uses the shared SQLAlchemy async engine as jobs and artifacts."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import select, delete, func
from cortex.db import get_engine
from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from cortex.graph.domain.interfaces import AbstractGraphRepository
from cortex.schema.models import GraphNodeModel, GraphEdgeModel
from shared.exceptions import InfrastructureError
import structlog
import json

logger = structlog.get_logger()


def _model_to_node(model: GraphNodeModel) -> GraphNode:
    """Convert SQLAlchemy model to domain entity."""
    try:
        props = (
            json.loads(model.properties)
            if isinstance(model.properties, str)
            else model.properties or {}
        )
    except Exception:
        props = {}

    return GraphNode(
        id=model.id,
        label=model.label,
        node_type=NodeType(model.node_type),
        job_id=model.job_id,
        properties=props,
        created_at=model.created_at,
    )


def _node_to_model(node: GraphNode) -> GraphNodeModel:
    """Convert domain entity to SQLAlchemy model."""
    return GraphNodeModel(
        id=node.id,
        label=node.label,
        node_type=node.node_type.value,
        job_id=node.job_id,
        properties=node.properties,
        created_at=node.created_at,
    )


def _model_to_edge(model: GraphEdgeModel) -> GraphEdge:
    """Convert SQLAlchemy model to domain entity."""
    try:
        props = (
            json.loads(model.properties)
            if isinstance(model.properties, str)
            else model.properties or {}
        )
    except Exception:
        props = {}

    return GraphEdge(
        id=model.id,
        source_id=model.source_id,
        target_id=model.target_id,
        relationship=RelationshipType(model.relationship),
        job_id=model.job_id,
        properties=props,
        created_at=model.created_at,
    )


def _edge_to_model(edge: GraphEdge) -> GraphEdgeModel:
    """Convert domain entity to SQLAlchemy model."""
    return GraphEdgeModel(
        id=edge.id,
        source_id=edge.source_id,
        target_id=edge.target_id,
        relationship=edge.relationship.value,
        job_id=edge.job_id,
        properties=edge.properties,
        created_at=edge.created_at,
    )


class SQLiteGraphRepository(AbstractGraphRepository):
    """SQLite implementation of AbstractGraphRepository.

    Stores graph nodes and edges in the same cortex.db file
    as jobs and artifacts. No Neo4j or Docker required.

    When you're ready for Neo4j later, swap this for
    Neo4jGraphRepository — the interface is identical.
    """

    def __init__(self, database_url: str) -> None:
        self._engine = get_engine(database_url)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save_nodes_bulk(self, nodes: list[GraphNode]) -> None:
        """Insert all nodes in a single transaction.

        This is dramatically faster than calling save_node() in a loop —
        one BEGIN/COMMIT wrapping all inserts instead of one per node.
        Existing nodes (same id) are skipped to stay idempotent.
        """
        if not nodes:
            return
        async with self._session_factory() as session:
            try:
                # Fetch all existing IDs in one query to decide skip/insert
                existing_result = await session.execute(
                    select(GraphNodeModel.id).where(
                        GraphNodeModel.id.in_([n.id for n in nodes])
                    )
                )
                existing_ids = {row[0] for row in existing_result.all()}

                for node in nodes:
                    if node.id not in existing_ids:
                        session.add(_node_to_model(node))

                await session.commit()
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to bulk-save {len(nodes)} nodes: {e}"
                )

    async def save_edges_bulk(self, edges: list[GraphEdge]) -> None:
        """Insert all edges in a single transaction.

        Same rationale as save_nodes_bulk — one transaction for the full
        set instead of one per edge.
        """
        if not edges:
            return
        async with self._session_factory() as session:
            try:
                existing_result = await session.execute(
                    select(GraphEdgeModel.id).where(
                        GraphEdgeModel.id.in_([e.id for e in edges])
                    )
                )
                existing_ids = {row[0] for row in existing_result.all()}

                for edge in edges:
                    if edge.id not in existing_ids:
                        session.add(_edge_to_model(edge))

                await session.commit()
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to bulk-save {len(edges)} edges: {e}"
                )

    async def save_node(self, node: GraphNode) -> GraphNode:
        async with self._session_factory() as session:
            try:
                # Check if node already exists — update if so
                result = await session.execute(
                    select(GraphNodeModel).where(
                        GraphNodeModel.id == node.id
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.label = node.label
                    existing.node_type = node.node_type.value
                    existing.properties = node.properties
                else:
                    model = _node_to_model(node)
                    session.add(model)

                await session.commit()
                return node
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to save node {node.id}: {e}"
                )

    async def save_edge(self, edge: GraphEdge) -> GraphEdge:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(GraphEdgeModel).where(
                        GraphEdgeModel.id == edge.id
                    )
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    model = _edge_to_model(edge)
                    session.add(model)
                    await session.commit()

                return edge
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to save edge {edge.id}: {e}"
                )

    async def get_node_by_id(
        self, node_id: str
    ) -> GraphNode | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphNodeModel).where(
                    GraphNodeModel.id == node_id
                )
            )
            model = result.scalar_one_or_none()
            return _model_to_node(model) if model else None

    async def get_nodes_by_job(
        self, job_id: str
    ) -> list[GraphNode]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphNodeModel).where(
                    GraphNodeModel.job_id == job_id
                )
            )
            return [
                _model_to_node(m)
                for m in result.scalars().all()
            ]

    async def get_nodes_by_type(
        self,
        job_id: str,
        node_type: NodeType,
    ) -> list[GraphNode]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphNodeModel).where(
                    GraphNodeModel.job_id == job_id,
                    GraphNodeModel.node_type == node_type.value,
                )
            )
            return [
                _model_to_node(m)
                for m in result.scalars().all()
            ]

    async def get_edges_by_job(
        self, job_id: str
    ) -> list[GraphEdge]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphEdgeModel).where(
                    GraphEdgeModel.job_id == job_id
                )
            )
            return [
                _model_to_edge(m)
                for m in result.scalars().all()
            ]

    async def get_edges_by_relationship(
        self,
        job_id: str,
        relationship: RelationshipType,
    ) -> list[GraphEdge]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphEdgeModel).where(
                    GraphEdgeModel.job_id == job_id,
                    GraphEdgeModel.relationship == relationship.value,
                )
            )
            return [
                _model_to_edge(m)
                for m in result.scalars().all()
            ]

    async def get_edges_for_node(
        self, node_id: str
    ) -> list[GraphEdge]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GraphEdgeModel).where(
                    (GraphEdgeModel.source_id == node_id) |
                    (GraphEdgeModel.target_id == node_id)
                )
            )
            return [
                _model_to_edge(m)
                for m in result.scalars().all()
            ]

    async def delete_by_job(
        self, job_id: str
    ) -> tuple[int, int]:
        async with self._session_factory() as session:
            try:
                # Count before deleting using scalar COUNT queries — avoids
                # loading full ORM rows (including JSON properties) just to
                # call len() on them. Same pattern as count_by_job().
                node_count_result = await session.execute(
                    select(func.count())
                    .select_from(GraphNodeModel)
                    .where(GraphNodeModel.job_id == job_id)
                )
                node_count = node_count_result.scalar_one()

                edge_count_result = await session.execute(
                    select(func.count())
                    .select_from(GraphEdgeModel)
                    .where(GraphEdgeModel.job_id == job_id)
                )
                edge_count = edge_count_result.scalar_one()

                # Delete edges first (foreign key constraint)
                await session.execute(
                    delete(GraphEdgeModel).where(
                        GraphEdgeModel.job_id == job_id
                    )
                )
                await session.execute(
                    delete(GraphNodeModel).where(
                        GraphNodeModel.job_id == job_id
                    )
                )
                await session.commit()

                logger.info(
                    "graph_deleted_from_sqlite",
                    job_id=job_id,
                    nodes=node_count,
                    edges=edge_count,
                )
                return node_count, edge_count

            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to delete graph for job {job_id}: {e}"
                )

    async def count_by_job(self, job_id: str) -> dict[str, int]:
        async with self._session_factory() as session:
            node_result = await session.execute(
                select(func.count())
                .select_from(GraphNodeModel)
                .where(GraphNodeModel.job_id == job_id)
            )
            edge_result = await session.execute(
                select(func.count())
                .select_from(GraphEdgeModel)
                .where(GraphEdgeModel.job_id == job_id)
            )
            return {
                "nodes": node_result.scalar_one(),
                "edges": edge_result.scalar_one(),
            }