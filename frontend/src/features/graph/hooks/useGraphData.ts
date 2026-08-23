'use client';

import { useState, useEffect } from 'react';
import type { GraphNode, GraphEdge } from '@/types';
import { getGraph } from '@/lib/api/graph.api';
import { sessionCache, cacheKey, TTL } from '@/lib/cache';

export interface UseGraphDataReturn {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isLoading: boolean;
  error: string | null;
}

interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }

export function useGraphData(jobId: string | null): UseGraphDataReturn {
  const [nodes, setNodes] = useState<GraphNode[]>(() => {
    if (!jobId) return [];
    return sessionCache.get<GraphData>(cacheKey.graph(jobId))?.nodes ?? [];
  });
  const [edges, setEdges] = useState<GraphEdge[]>(() => {
    if (!jobId) return [];
    return sessionCache.get<GraphData>(cacheKey.graph(jobId))?.edges ?? [];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setNodes([]);
      setEdges([]);
      setError(null);
      return;
    }

    const cached = sessionCache.get<GraphData>(cacheKey.graph(jobId));
    if (cached) {
      setNodes(cached.nodes);
      setEdges(cached.edges);
      return;
    }

    let isActive = true;

    const fetchGraph = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        // Single call to GET /graph/jobs/:jobId returns both nodes and edges —
        // previously made two parallel requests (getGraphNodes + getGraphEdges)
        // which wasted one full round-trip per graph load.
        const data = await getGraph(jobId);
        if (!isActive) return;
        setNodes(data.nodes);
        setEdges(data.edges);
        sessionCache.set(
          cacheKey.graph(jobId),
          { nodes: data.nodes, edges: data.edges },
          TTL.GRAPH,
        );
      } catch (err: unknown) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch graph data.');
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    void fetchGraph();
    return () => { isActive = false; };
  }, [jobId]);

  return { nodes, edges, isLoading, error };
}
