// =============================================================================
// Jobs API
// All API calls related to Cortex Jobs.
// Endpoints: POST /jobs, GET /jobs, GET /jobs/:id, DELETE /jobs/:id
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
 * Fetch all jobs (most recent first).
 * GET /api/v1/jobs
 */
export async function listJobs(): Promise<Job[]> {
  const response = await apiClient.get<{ jobs: Job[]; total: number }>('/jobs');
  return response.data.jobs;
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
 * Cancel a running or pending job.
 * DELETE /api/v1/jobs/:jobId
 */
export async function cancelJob(jobId: string): Promise<void> {
  await apiClient.delete<{ id: string; status: 'cancelled' }>(`/jobs/${jobId}`);
}
