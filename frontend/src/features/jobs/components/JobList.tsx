// =============================================================================
// JobList — Renders a scrollable list of JobCards
// =============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import type { Job } from '@/types';
import { listJobs } from '@/lib/api/jobs.api';
import JobCard from './JobCard';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorAlert from '@/components/shared/ErrorAlert';

export interface JobListProps {
  /** The currently selected job ID (for highlighting) */
  selectedJobId?: string | null;
  /** Called when the user selects a job from the list */
  onJobSelected: (job: Job) => void;
  /** Optional external list of jobs to display instead of fetching */
  jobs?: Job[];
}

export default function JobList({ selectedJobId, onJobSelected, jobs: externalJobs }: JobListProps) {
  const [jobs, setJobs] = useState<Job[]>(externalJobs ?? []);
  const [isLoading, setIsLoading] = useState(!externalJobs);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If an external list is provided, don't fetch
    if (externalJobs) {
      setJobs(externalJobs);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setError(null);

    listJobs()
      .then((data) => {
        if (isActive) setJobs(data);
      })
      .catch((err: unknown) => {
        if (!isActive) return;
        const message = err instanceof Error ? err.message : 'Failed to load jobs.';
        setError(message);
      })
      .finally(() => {
        if (isActive) setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [externalJobs]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner label="Loading jobs…" />
      </div>
    );
  }

  if (error) {
    return <ErrorAlert message={error} title="Could not load jobs" />;
  }

  if (jobs.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No jobs yet. Submit a repository above to get started.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-2" role="list" aria-label="Job list">
      {jobs.map((job) => (
        <li key={job.id}>
          <JobCard
            job={job}
            isSelected={job.id === selectedJobId}
            onClick={onJobSelected}
          />
        </li>
      ))}
    </ul>
  );
}
