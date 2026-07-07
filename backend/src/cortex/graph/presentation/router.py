"""Graph API router — complete and production-ready."""

from fastapi import APIRouter, HTTPException, Query, Depends
from cortex.graph.application.use_cases import GraphService
from cortex.graph.infrastructure.repository import InMemoryGraphRepository
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.graph.presentation.models import (
    GraphNodeCreate,
    GraphEdgeCreate,
    GraphNodeResponse,
    GraphEdgeResponse,
    GraphResponse,
)
from shared.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/graph", tags=["graph"])

_repository = InMemoryGraphRepository()


def get_graph_service() -> GraphService:
    return GraphService(_repository)


@router.post(
    "/jobs/{job_id}/nodes",
    response_model=GraphNodeResponse,
    status_code=201,
    summary="Add a node to the knowledge graph",
)
async def add_node(
    job_id: str,
    request: GraphNodeCreate,
    service: GraphService = Depends(get_graph_service),
) -> GraphNodeResponse:
    try:
        node = await service.add_node(
            job_id=job_id,
            node_id=request.id,
            label=request.label,
            node_type=request.node_type,
            properties=request.properties or {},
        )
        return GraphNodeResponse.from_node(node)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/jobs/{job_id}/edges",
    response_model=GraphEdgeResponse,
    status_code=201,
    summary="Add an edge to the knowledge graph",
)
async def add_edge(
    job_id: str,
    request: GraphEdgeCreate,
    service: GraphService = Depends(get_graph_service),
) -> GraphEdgeResponse:
    try:
        edge = await service.add_edge(
            job_id=job_id,
            edge_id=request.id,
            source_id=request.source_id,
            target_id=request.target_id,
            relationship=request.relationship,
            properties=request.properties or {},
        )
        return GraphEdgeResponse.from_edge(edge)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "/jobs/{job_id}",
    response_model=GraphResponse,
    summary="Get full graph for a job",
    description="Returns all nodes and edges for a job.",
)
async def get_graph(
    job_id: str,
    service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    nodes, edges = await service.get_graph_for_job(job_id)
    return GraphResponse.from_graph(nodes, edges)


@router.get(
    "/nodes",
    response_model=list[GraphNodeResponse],
    summary="Query graph nodes",
    description="Returns nodes filtered by job_id and optionally node_type.",
)
async def get_nodes(
    job_id: str = Query(...),
    node_type: NodeType | None = Query(default=None),
    service: GraphService = Depends(get_graph_service),
) -> list[GraphNodeResponse]:
    nodes = await service.get_nodes(job_id=job_id, node_type=node_type)
    return [GraphNodeResponse.from_node(n) for n in nodes]


@router.get(
    "/relationships",
    response_model=list[GraphEdgeResponse],
    summary="Query graph relationships",
    description="Returns edges filtered by job_id and optionally relationship type.",
)
async def get_edges(
    job_id: str = Query(...),
    relationship: RelationshipType | None = Query(default=None),
    service: GraphService = Depends(get_graph_service),
) -> list[GraphEdgeResponse]:
    edges = await service.get_edges(
        job_id=job_id, relationship=relationship
    )
    return [GraphEdgeResponse.from_edge(e) for e in edges]


@router.delete(
    "/jobs/{job_id}",
    summary="Delete graph for a job",
    description="Permanently deletes all nodes and edges for a job.",
)
async def delete_graph(
    job_id: str,
    service: GraphService = Depends(get_graph_service),
) -> dict:
    return await service.delete_graph(job_id)