// =============================================================================
// useOverview — Fetches repository overview data
// =============================================================================

'use client';

import { useEffect, useState } from 'react';
import { getOverview, getHealth, type OverviewData, type HealthData } from '@/lib/api/overview.api';

interface UseOverviewReturn {
  overview: OverviewData | null;
  health: HealthData | null;
  isLoading: boolean;
  error: string | null;
}

export function useOverview(jobId: string | null): UseOverviewReturn {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    Promise.all([getOverview(jobId), getHealth(jobId)])
      .then(([overviewData, healthData]) => {
        if (!cancelled) {
          setOverview(overviewData);
          setHealth(healthData);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load overview');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [jobId]);

  return { overview, health, isLoading, error };
}
