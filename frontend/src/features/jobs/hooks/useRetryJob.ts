// =============================================================================
// useRetryJob — Hook for retrying a failed Cortex job
// Calls POST /jobs/:jobId/retry, returns the newly-created replacement job.
// =============================================================================

'use client';

import { useState } from 'react';
import type { Job } from '@/types';
import { retryJob } from '@/lib/api/jobs.api';

export interface UseRetryJobReturn {
  retriedJob: Job | null;
  isRetrying: boolean;
  error: string | null;
  retry: (jobId: string) => Promise<void>;
}

export function useRetryJob(): UseRetryJobReturn {
  const [retriedJob, setRetriedJob] = useState<Job | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retry = async (jobId: string): Promise<void> => {
    setIsRetrying(true);
    setError(null);
    setRetriedJob(null);

    try {
      const job = await retryJob(jobId);
      setRetriedJob(job);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to retry job. Is the Cortex backend running?';
      setError(message);
    } finally {
      setIsRetrying(false);
    }
  };

  return { retriedJob, isRetrying, error, retry };
}
