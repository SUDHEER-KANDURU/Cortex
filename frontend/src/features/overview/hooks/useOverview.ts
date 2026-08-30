// =============================================================================
// useOverview — Fetches repository overview data
// =============================================================================

'use client';

import { useEffect, useState } from 'react';
import { getOverview, getHealth, type OverviewData, type HealthData } from '@/lib/api/overview.api';
import { getInsights } from '@/lib/api/insights.api';
import type { AnalysisCoverage } from '@/types';

interface UseOverviewReturn {
  overview: OverviewData | null;
  health: HealthData | null;
  /**
   * Real analysis coverage (analyzed vs. total files) sourced from the insights
   * report. The overview endpoint itself does not expose Coverage, so we read
   * it from `/insights/:jobId` where it is already surfaced (Req 6.4, Task 5).
   * Best-effort: null when the insights report is unavailable — the overview
   * still loads without it.
   */
  coverage: AnalysisCoverage | null;
  isLoading: boolean;
  error: string | null;
}

export function useOverview(jobId: string | null): UseOverviewReturn {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [coverage, setCoverage] = useState<AnalysisCoverage | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setCoverage(null);

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

    // Coverage is fetched separately and never blocks the overview: if the
    // insights report is missing we simply omit the structured coverage stats.
    getInsights(jobId)
      .then((report) => {
        if (!cancelled) setCoverage(report.coverage ?? null);
      })
      .catch(() => {
        if (!cancelled) setCoverage(null);
      });

    return () => { cancelled = true; };
  }, [jobId]);

  return { overview, health, coverage, isLoading, error };
}
