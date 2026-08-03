'use client';

import { useState, useEffect, useCallback } from 'react';
import type { InsightsReport } from '@/types';
import { getInsights } from '@/lib/api/insights.api';
import { sessionCache, cacheKey, TTL } from '@/lib/cache';

interface UseInsightsState {
  report: InsightsReport | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useInsights(jobId: string | null): UseInsightsState {
  const [report, setReport] = useState<InsightsReport | null>(() => {
    if (!jobId) return null;
    return sessionCache.get<InsightsReport>(cacheKey.insights(jobId));
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!jobId) return;

    const cached = sessionCache.get<InsightsReport>(cacheKey.insights(jobId));
    if (cached) {
      setReport(cached);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await getInsights(jobId);
      setReport(data);
      sessionCache.set(cacheKey.insights(jobId), data, TTL.INSIGHTS);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load insights');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    const cached = sessionCache.get<InsightsReport>(jobId ? cacheKey.insights(jobId) : '');
    if (!cached) setReport(null);
    void fetch();
  }, [fetch, jobId]);

  const refetch = useCallback(() => {
    if (jobId) sessionCache.invalidatePrefix(cacheKey.insights(jobId));
    void fetch();
  }, [fetch, jobId]);

  return { report, isLoading, error, refetch };
}
