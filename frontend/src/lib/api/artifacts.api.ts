// =============================================================================
// Artifacts API
// All API calls related to Cortex Artifacts.
// Endpoints: GET /artifacts/:id, GET /artifacts/job/:jobId
// =============================================================================

import type { Artifact } from '@/types';
import { apiClient } from './client';

/**
 * Fetch a single artifact by its UUID.
 * GET /api/v1/artifacts/:artifactId
 */
export async function getArtifact(artifactId: string): Promise<Artifact> {
  const response = await apiClient.get<Artifact>(`/artifacts/${artifactId}`);
  return response.data;
}

/**
 * Fetch all artifacts produced by a specific job.
 * GET /api/v1/artifacts/job/:jobId
 */
export async function getArtifactsForJob(jobId: string): Promise<Artifact[]> {
  const response = await apiClient.get<{ artifacts: Artifact[]; total: number }>(`/artifacts/job/${jobId}`);
  return response.data.artifacts;
}
