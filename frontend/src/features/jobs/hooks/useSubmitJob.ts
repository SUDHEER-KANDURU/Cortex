// =============================================================================
// useSubmitJob — Hook for submitting a new Cortex job
// Wraps createJob API call with loading and error state management.
// =============================================================================

'use client';

import { useState } from 'react';
import type { Job, JobCreateRequest } from '@/types';
import { createJob } from '@/lib/api/jobs.api';

export interface UseSubmitJobReturn {
  submittedJob: Job | null;
  isSubmitting: boolean;
  error: string | null;
  submitJob: (request: JobCreateRequest) => Promise<void>;
}

export function useSubmitJob(): UseSubmitJobReturn {
  const [submittedJob, setSubmittedJob] = useState<Job | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitJob = async (request: JobCreateRequest): Promise<void> => {
    setIsSubmitting(true);
    setError(null);
    setSubmittedJob(null);

    try {
      const job = await createJob(request);
      setSubmittedJob(job);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to submit job. Is the Cortex backend running?';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submittedJob, isSubmitting, error, submitJob };
}
