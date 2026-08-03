// =============================================================================
// Graph API
// Endpoints: GET /graph/jobs/:jobId, GET /graph/nodes, GET /graph/relationships
// =============================================================================

import type { GraphNode, GraphEdge } from '@/types';
import { apiClient } from './client';

interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

/**
 * Fetch the full knowledge graph for a job.
 * GET /api/v1/graph/jobs/:jobId
 */
export async function getGraph(jobId: string): Promise<GraphResponse> {
  const response = await apiClient.get<GraphResponse>(`/graph/jobs/${jobId}`);
  return response.data;
}

/**
 * Fetch graph nodes for a job, optionally filtered by type.
 * GET /api/v1/graph/nodes?job_id=&node_type=
 */
export async function getGraphNodes(
  jobId: string,
  nodeType?: GraphNode['node_type'],
): Promise<GraphNode[]> {
  const params: Record<string, string> = { job_id: jobId };
  if (nodeType) params.node_type = nodeType;
  const response = await apiClient.get<GraphNode[]>('/graph/nodes', { params });
  return response.data;
}

/**
 * Fetch graph edges for a job, optionally filtered by relationship type.
 * GET /api/v1/graph/relationships?job_id=&relationship=
 */
export async function getGraphEdges(
  jobId: string,
  relationship?: GraphEdge['relationship'],
): Promise<GraphEdge[]> {
  const params: Record<string, string> = { job_id: jobId };
  if (relationship) params.relationship = relationship;
  const response = await apiClient.get<GraphEdge[]>('/graph/relationships', { params });
  return response.data;
}
