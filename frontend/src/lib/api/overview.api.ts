// =============================================================================
// Overview API — Repository overview and health endpoints
// =============================================================================

import { apiClient } from './client';

export interface OverviewData {
  repo_name: string;
  repo_url: string;
  total_files: number;
  total_lines: number;
  total_modules: number;
  total_classes: number;
  total_functions: number;
  total_endpoints: number;
  total_tests: number;
  languages: string[];
  overall_score: number;
  overall_grade: string;
  avg_complexity: number;
  max_complexity: number;
  documentation_ratio: number;
  test_ratio: number;
}

export interface HealthDimension {
  name: string;
  score: number;
  grade: string;
  summary: string;
  issue_count: number;
}

export interface HealthData {
  overall_score: number;
  overall_grade: string;
  dimensions: HealthDimension[];
  top_issues: Array<{
    title: string;
    severity: string;
    category: string;
    file_path: string;
    symbol: string;
    recommendation: string;
  }>;
}

/** Get repository overview */
export async function getOverview(jobId: string): Promise<OverviewData> {
  const { data } = await apiClient.get<OverviewData>(`/overview/${jobId}`);
  return data;
}

/** Get health dashboard data */
export async function getHealth(jobId: string): Promise<HealthData> {
  const { data } = await apiClient.get<HealthData>(`/overview/${jobId}/health`);
  return data;
}
