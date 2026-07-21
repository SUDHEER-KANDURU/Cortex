
'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Artifact } from '@/types';
import { getArtifactsForJob } from '@/lib/api/artifacts.api';

export interface UseArtifactReturn {
  artifacts: Artifact[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useArtifact(jobId: string | null): UseArtifactReturn {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
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

    let isActive = true;

    const fetchArtifacts = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getArtifactsForJob(jobId);
        if (isActive) setArtifacts(data);
      } catch (err: unknown) {
        if (!isActive) return;
        const message =
          err instanceof Error ? err.message : 'Failed to fetch artifacts.';
        setError(message);
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    void fetchArtifacts();

    return () => {
      isActive = false;
    };
  }, [jobId, fetchTrigger]);

  const refetch = useCallback((): void => {
    setFetchTrigger((n) => n + 1);
  }, []);

  return { artifacts, isLoading, error, refetch };
}
