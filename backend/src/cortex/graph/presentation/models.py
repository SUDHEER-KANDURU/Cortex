"""Pydantic models for the Graph API."""

from datetime import datetime
from pydantic import BaseModel
from cortex.graph.domain.entities import NodeType, RelationshipType


class GraphNodeCreate(BaseModel):
    id: str
    label: str
    node_type: NodeType
    properties: dict[str, str | int | float | bool] | None = None


class GraphEdgeCreate(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    properties: dict[str, str | int | float | bool] | None = None


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    node_type: NodeType
    job_id: str
    properties: dict[str, str | int | float | bool]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_node(cls, node: "GraphNode") -> "GraphNodeResponse":  # type: ignore[name-defined]
        return cls(
            id=node.id,
            label=node.label,
            node_type=node.node_type,
            job_id=node.job_id,
            properties=node.properties,
            created_at=node.created_at,
        )


class GraphEdgeResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    job_id: str
    properties: dict[str, str | int | float | bool]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_edge(cls, edge: "GraphEdge") -> "GraphEdgeResponse":  # type: ignore[name-defined]
        return cls(
            id=edge.id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            relationship=edge.relationship,
            job_id=edge.job_id,
            properties=edge.properties,
            created_at=edge.created_at,
        )


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    node_count: int
    edge_count: int

    @classmethod
    def from_graph(
        cls,
        nodes: list,
        edges: list,
    ) -> "GraphResponse":
        return cls(
            nodes=[GraphNodeResponse.from_node(n) for n in nodes],
            edges=[GraphEdgeResponse.from_edge(e) for e in edges],
            node_count=len(nodes),
            edge_count=len(edges),
        )