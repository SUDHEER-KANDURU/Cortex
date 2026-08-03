// =============================================================================
// Insights API
// Endpoints: GET /insights/:jobId, GET /insights/:jobId/export
// =============================================================================

import type { InsightsReport } from '@/types';
import { apiClient } from './client';

/**
 * Fetch the engineering health report for a completed job.
 * GET /api/v1/insights/:jobId
 */
export async function getInsights(jobId: string): Promise<InsightsReport> {
  const response = await apiClient.get<InsightsReport>(`/insights/${jobId}`);
  return response.data;
}

/**
 * Download the full engineering report as Markdown.
 * GET /api/v1/insights/:jobId/export
 */
export async function exportInsightsMarkdown(jobId: string): Promise<string> {
  const response = await apiClient.get<string>(`/insights/${jobId}/export`, {
    headers: { Accept: 'text/plain' },
    responseType: 'text',
  });
  return response.data;
}
