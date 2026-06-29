// =============================================================================
// useGraphData — Fetches nodes and edges for a given job's code graph
// =============================================================================

'use client';

import { useState, useEffect } from 'react';
import type { GraphNode, GraphEdge } from '@/types';
import { getGraphForJob } from '@/lib/api/graph.api';

export interface UseGraphDataReturn {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetch graph nodes and edges for a specific job.
 * Re-fetches whenever jobId changes.
 *
 * @param jobId - UUID of the job whose graph to fetch, or null to skip
 */
export function useGraphData(jobId: string | null): UseGraphDataReturn {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  useEffect(() => {
    if (!jobId) {
      setNodes([]);
      setEdges([]);
      setError(null);
      return;
    }

    let isActive = true;

    const fetchGraph = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getGraphForJob(jobId);
        if (isActive) {
          setNodes(data.nodes);
          setEdges(data.edges);
        }
      } catch (err: unknown) {
        if (!isActive) return;
        const message =
          err instanceof Error ? err.message : 'Failed to fetch graph data.';
        setError(message);
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    void fetchGraph();

    return () => {
      isActive = false;
    };
  }, [jobId, fetchTrigger]);

  const refetch = (): void => setFetchTrigger((n) => n + 1);

  return { nodes, edges, isLoading, error, refetch };
}
