// =============================================================================
// Graph API
// API calls for querying the Neo4j-backed code knowledge graph.
// Endpoints: GET /graph/nodes, GET /graph/relationships
// =============================================================================

import type { GraphNode, GraphEdge } from '@/types';
import { apiClient } from './client';

/** Query params accepted by the nodes endpoint */
export interface GraphNodesParams {
  repo_id?: string;
  type?: string;
  limit?: number;
}

/** Query params accepted by the relationships endpoint */
export interface GraphEdgesParams {
  repo_id?: string;
  relationship?: string;
  limit?: number;
}

/**
 * Fetch graph nodes, optionally filtered by repository or node type.
 * GET /api/v1/graph/nodes
 */
export async function getGraphNodes(params?: GraphNodesParams): Promise<GraphNode[]> {
  const response = await apiClient.get<GraphNode[]>('/graph/nodes', { params });
  return response.data;
}

/**
 * Fetch graph relationships (edges), optionally filtered.
 * GET /api/v1/graph/relationships
 */
export async function getGraphEdges(params?: GraphEdgesParams): Promise<GraphEdge[]> {
  const response = await apiClient.get<GraphEdge[]>('/graph/relationships', { params });
  return response.data;
}

/**
 * Fetch the complete graph for a specific job/repository in one call.
 * GET /api/v1/graph?job_id=:jobId
 */
export async function getGraphForJob(
  jobId: string
): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const response = await apiClient.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>('/graph', {
    params: { job_id: jobId },
  });
  return response.data;
}
