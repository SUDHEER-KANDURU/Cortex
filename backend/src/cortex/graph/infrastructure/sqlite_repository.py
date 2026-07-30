"""SQLite graph repository — persists knowledge graph nodes and edges.
Replaces InMemoryGraphRepository with real storage.
Uses the same SQLAlchemy async engine as jobs and artifacts."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from cortex.graph.domain.interfaces import AbstractGraphRepository
from cortex.schema.models import GraphNodeModel, GraphEdgeModel
from shared.exceptions import NotFoundError, InfrastructureError
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
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}

        self._engine = create_async_engine(
            database_url,
            echo=False,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
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
                # Count before deleting
                node_result = await session.execute(
                    select(GraphNodeModel).where(
                        GraphNodeModel.job_id == job_id
                    )
                )
                node_count = len(node_result.scalars().all())

                edge_result = await session.execute(
                    select(GraphEdgeModel).where(
                        GraphEdgeModel.job_id == job_id
                    )
                )
                edge_count = len(edge_result.scalars().all())

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
                select(GraphNodeModel).where(
                    GraphNodeModel.job_id == job_id
                )
            )
            edge_result = await session.execute(
                select(GraphEdgeModel).where(
                    GraphEdgeModel.job_id == job_id
                )
            )
            return {
                "nodes": len(node_result.scalars().all()),
                "edges": len(edge_result.scalars().all()),
            }