// =============================================================================
// useJobPolling — Polls a job's status until it reaches a terminal state.
// Automatically stops polling when status is completed, failed, or cancelled.
// Cleans up the interval on component unmount.
// =============================================================================

'use client';

import { useState, useEffect, useRef } from 'react';
import type { Job, JobStatus } from '@/types';
import { getJob } from '@/lib/api/jobs.api';

const POLL_INTERVAL_MS = 3000;

/** Statuses that indicate no further progress will occur */
const TERMINAL_STATUSES: JobStatus[] = ['completed', 'failed', 'cancelled'];

export interface UseJobPollingReturn {
  job: Job | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Poll the backend for job status updates every 3 seconds.
 * Stops automatically when the job reaches a terminal state.
 *
 * @param jobId - UUID of the job to poll, or null to skip polling
 */
export function useJobPolling(jobId: string | null): UseJobPollingReturn {
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep a ref to the interval so the cleanup function always has the latest ID
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setError(null);
      return;
    }

    let isActive = true; // guard against state updates after unmount

    const fetchJob = async (): Promise<void> => {
      try {
        const fetched = await getJob(jobId);
        if (!isActive) return;

        setJob(fetched);
        setError(null);

        // Stop polling once the job reaches a terminal state
        if (TERMINAL_STATUSES.includes(fetched.status)) {
          if (intervalRef.current !== null) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch (err: unknown) {
        if (!isActive) return;
        const message =
          err instanceof Error ? err.message : 'Failed to fetch job status.';
        setError(message);
      } finally {
        if (isActive) setIsLoading(false);
      }
    };

    // Fetch immediately, then set up the polling interval
    setIsLoading(true);
    void fetchJob();

    intervalRef.current = setInterval(() => {
      void fetchJob();
    }, POLL_INTERVAL_MS);

    // Cleanup: stop polling when jobId changes or component unmounts
    return () => {
      isActive = false;
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId]);

  return { job, isLoading, error };
}
