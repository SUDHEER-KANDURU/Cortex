// =============================================================================
// Graph API
// API calls for querying the Neo4j-backed code knowledge graph.
// Endpoints: GET /graph/nodes?job_id=, GET /graph/relationships?job_id=
// =============================================================================

import type { GraphNode, GraphEdge } from '@/types';
import { apiClient } from './client';

/**
 * Fetch graph nodes for a specific job.
 * GET /api/v1/graph/nodes?job_id=:jobId
 */
export async function getGraphNodes(jobId: string): Promise<GraphNode[]> {
  const response = await apiClient.get<GraphNode[]>('/graph/nodes', {
    params: { job_id: jobId },
  });
  return response.data;
}

/**
 * Fetch graph relationships (edges) for a specific job.
 * GET /api/v1/graph/relationships?job_id=:jobId
 */
export async function getGraphEdges(jobId: string): Promise<GraphEdge[]> {
  const response = await apiClient.get<GraphEdge[]>('/graph/relationships', {
    params: { job_id: jobId },
  });
  return response.data;
}
