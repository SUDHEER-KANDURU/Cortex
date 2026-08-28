// =============================================================================
// Delta API — "Since your last analysis" intelligence
// =============================================================================

import { apiClient } from './client';

export interface ScoreChange {
  metric: string;
  previous: number;
  current: number;
  delta: number;
  direction: 'improved' | 'degraded' | 'stable';
}

export interface DeltaData {
  repo_name: string;
  is_first_analysis: boolean;
  analysis_count: number;
  overall_change: ScoreChange | null;
  dimension_changes: ScoreChange[];
  structural_changes: string[];
  improvements: string[];
  degradations: string[];
}

/** Get delta intelligence for a job */
export async function getDelta(jobId: string): Promise<DeltaData> {
  const { data } = await apiClient.get<DeltaData>(`/overview/${jobId}/delta`);
  return data;
}
