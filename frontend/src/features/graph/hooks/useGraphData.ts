'use client';

import { useState, useEffect } from 'react';
import type { GraphNode, GraphEdge } from '@/types';
import { getGraphNodes, getGraphEdges } from '@/lib/api/graph.api';
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
        const [fetchedNodes, fetchedEdges] = await Promise.all([
          getGraphNodes(jobId),
          getGraphEdges(jobId),
        ]);
        if (!isActive) return;
        setNodes(fetchedNodes);
        setEdges(fetchedEdges);
        sessionCache.set(cacheKey.graph(jobId), { nodes: fetchedNodes, edges: fetchedEdges }, TTL.GRAPH);
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
