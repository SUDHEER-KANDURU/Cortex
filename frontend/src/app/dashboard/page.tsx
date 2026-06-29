// =============================================================================
// Dashboard Page — Main Cortex interface
// Left panel: job submission form + job list
// Right panel: artifact viewer for the selected job
// =============================================================================

'use client';

import React, { useState, useCallback } from 'react';
import type { Job } from '@/types';
import JobSubmitForm from '@/features/jobs/components/JobSubmitForm';
import JobList from '@/features/jobs/components/JobList';
import ArtifactViewer from '@/features/artifacts/components/ArtifactViewer';
import StatusBadge from '@/components/shared/StatusBadge';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorAlert from '@/components/shared/ErrorAlert';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { formatDate } from '@/lib/utils/formatDate';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { GitBranch, Inbox } from 'lucide-react';

export default function DashboardPage() {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  // Accumulate submitted jobs so they appear at the top of the list immediately
  const [submittedJobs, setSubmittedJobs] = useState<Job[]>([]);

  // Poll the selected job's status
  const { job: polledJob, isLoading: isPolling, error: pollError } = useJobPolling(
    selectedJob?.id ?? null
  );

  // Fetch artifacts for the selected job
  const { artifacts, isLoading: artifactsLoading, error: artifactsError } = useArtifact(
    selectedJob?.id ?? null
  );

  // Use the polled job data if available (more up-to-date than initial selection)
  const activeJob = polledJob ?? selectedJob;

  const handleJobSubmitted = useCallback((job: Job) => {
    setSubmittedJobs((prev) => [job, ...prev]);
    setSelectedJob(job);
  }, []);

  const handleJobSelected = useCallback((job: Job) => {
    setSelectedJob(job);
  }, []);

  return (
    <div className="flex h-full flex-1 overflow-hidden">
      {/* ── Left Panel ─────────────────────────────────────────────────────── */}
      <aside className="flex w-full max-w-sm shrink-0 flex-col gap-4 overflow-y-auto border-r border-gray-800 p-5 md:w-80 lg:w-96">
        {/* Job submission form */}
        <section aria-labelledby="submit-heading">
          <h2
            id="submit-heading"
            className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500"
          >
            Analyze a Repository
          </h2>
          <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-4">
            <JobSubmitForm onJobSubmitted={handleJobSubmitted} />
          </div>
        </section>

        {/* Recent jobs list */}
        <section aria-labelledby="jobs-heading" className="flex-1">
          <h2
            id="jobs-heading"
            className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500"
          >
            Recent Jobs
          </h2>
          <JobList
            jobs={submittedJobs.length > 0 ? submittedJobs : undefined}
            selectedJobId={selectedJob?.id}
            onJobSelected={handleJobSelected}
          />
        </section>
      </aside>

      {/* ── Right Panel ────────────────────────────────────────────────────── */}
      <section
        className="flex flex-1 flex-col overflow-y-auto p-6"
        aria-label="Job artifacts"
      >
        {!activeJob ? (
          // Empty state
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <Inbox className="h-12 w-12 text-gray-700" aria-hidden="true" />
            <p className="text-sm text-gray-500">
              Select a job from the list, or submit a new repository above.
            </p>
          </div>
        ) : (
          <>
            {/* Job metadata header */}
            <header className="mb-6 flex flex-wrap items-start justify-between gap-3 rounded-lg border border-gray-700/50 bg-gray-800/30 p-4">
              <div className="flex items-center gap-2 min-w-0">
                <GitBranch className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                <span className="truncate text-sm font-medium text-gray-200">
                  {activeJob.repo_url}
                </span>
              </div>
              <StatusBadge status={activeJob.status} />
              <div className="w-full flex flex-wrap gap-4 text-xs text-gray-500">
                <span>
                  <span className="text-gray-400">Type: </span>
                  {ARTIFACT_TYPE_LABELS[activeJob.artifact_type]}
                </span>
                <span>
                  <span className="text-gray-400">Created: </span>
                  {formatDate(activeJob.created_at)}
                </span>
              </div>
            </header>

            {/* Polling / status feedback */}
            {isPolling && activeJob.status === 'running' && (
              <div className="mb-4">
                <LoadingSpinner label="Analyzing repository…" size="sm" />
              </div>
            )}
            {pollError && (
              <ErrorAlert className="mb-4" message={pollError} title="Status poll failed" />
            )}

            {/* Artifacts */}
            {activeJob.status === 'completed' ? (
              <>
                {artifactsLoading && (
                  <LoadingSpinner label="Loading artifacts…" className="mb-4" />
                )}
                {artifactsError && (
                  <ErrorAlert message={artifactsError} title="Could not load artifacts" />
                )}
                {!artifactsLoading && artifacts.length === 0 && (
                  <p className="text-sm text-gray-500">No artifacts generated yet.</p>
                )}
                <div className="flex flex-col gap-6">
                  {artifacts.map((artifact) => (
                    <ArtifactViewer key={artifact.id} artifact={artifact} />
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-500">
                {activeJob.status === 'pending' && 'Job is queued and waiting to start.'}
                {activeJob.status === 'running' && 'Job is running — artifacts will appear when complete.'}
                {activeJob.status === 'failed' && 'Job failed. Check logs for details.'}
                {activeJob.status === 'cancelled' && 'Job was cancelled.'}
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
