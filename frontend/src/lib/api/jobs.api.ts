// =============================================================================
// Jobs API
// All API calls related to Cortex Jobs.
// Endpoints: POST /jobs, GET /jobs, GET /jobs/:id
// =============================================================================

import type { Job, JobCreateRequest } from '@/types';
import { apiClient } from './client';

/**
 * Submit a new job to the Cortex backend.
 * POST /api/v1/jobs
 */
export async function createJob(request: JobCreateRequest): Promise<Job> {
  const response = await apiClient.post<Job>('/jobs', request);
  return response.data;
}

/**
 * Fetch a single job by its UUID.
 * GET /api/v1/jobs/:jobId
 */
export async function getJob(jobId: string): Promise<Job> {
  const response = await apiClient.get<Job>(`/jobs/${jobId}`);
  return response.data;
}

/**
 * Fetch all jobs (most recent first).
 * GET /api/v1/jobs
 */
export async function listJobs(): Promise<Job[]> {
  const response = await apiClient.get<Job[]>('/jobs');
  return response.data;
}

/**
 * Cancel a running or pending job.
 * PATCH /api/v1/jobs/:jobId/cancel
 */
export async function cancelJob(jobId: string): Promise<Job> {
  const response = await apiClient.patch<Job>(`/jobs/${jobId}/cancel`);
  return response.data;
}
