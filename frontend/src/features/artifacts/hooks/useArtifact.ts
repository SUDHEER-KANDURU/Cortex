'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Artifact } from '@/types';
import { getArtifactsForJob } from '@/lib/api/artifacts.api';
import { sessionCache, cacheKey, TTL } from '@/lib/cache';

export interface UseArtifactReturn {
  artifacts: Artifact[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useArtifact(jobId: string | null): UseArtifactReturn {
  const [artifacts, setArtifacts] = useState<Artifact[]>(() => {
    // Initialise from cache immediately — zero-flicker on revisit
    if (!jobId) return [];
    return sessionCache.get<Artifact[]>(cacheKey.artifacts(jobId)) ?? [];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  useEffect(() => {
    if (!jobId) {
      setArtifacts([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    // Serve from cache if available — completed artifact lists never change
    const cached = sessionCache.get<Artifact[]>(cacheKey.artifacts(jobId));
    if (cached && cached.length > 0) {
      setArtifacts(cached);
      setIsLoading(false);
      return;
    }

    let isActive = true;

    const fetchArtifacts = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getArtifactsForJob(jobId);
        if (!isActive) return;
        setArtifacts(data);
        // Cache completed job artifacts indefinitely for this session
        sessionCache.set(cacheKey.artifacts(jobId), data, TTL.ARTIFACTS);
      } catch (err: unknown) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch artifacts.');
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    void fetchArtifacts();
    return () => { isActive = false; };
  }, [jobId, fetchTrigger]);

  const refetch = useCallback((): void => {
    if (jobId) sessionCache.invalidatePrefix(cacheKey.artifacts(jobId));
    setFetchTrigger(n => n + 1);
  }, [jobId]);

  return { artifacts, isLoading, error, refetch };
}
