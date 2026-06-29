// =============================================================================
// Job Detail Page — /jobs/[jobId]
// Shows full job metadata, all artifacts, and a graph canvas if applicable.
// =============================================================================

'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, GitBranch, Calendar, Tag } from 'lucide-react';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useGraphData } from '@/features/graph/hooks/useGraphData';
import ArtifactViewer from '@/features/artifacts/components/ArtifactViewer';
import GraphCanvas from '@/features/graph/components/GraphCanvas';
import StatusBadge from '@/components/shared/StatusBadge';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ErrorAlert from '@/components/shared/ErrorAlert';
import { formatDate } from '@/lib/utils/formatDate';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';

// Artifact types that should also render the graph canvas
const GRAPH_ARTIFACT_TYPES = new Set([
  'module_breakdown',
  'architecture_diagram',
  'folder_structure',
]);

export default function JobDetailPage() {
  const params = useParams();
  const jobId = typeof params.jobId === 'string' ? params.jobId : null;

  const { job, isLoading: jobLoading, error: jobError } = useJobPolling(jobId);
  const { artifacts, isLoading: artifactsLoading, error: artifactsError } = useArtifact(
    job?.status === 'completed' ? jobId : null
  );
  const { nodes, edges, isLoading: graphLoading, error: graphError } = useGraphData(
    job?.status === 'completed' && job.artifact_type && GRAPH_ARTIFACT_TYPES.has(job.artifact_type)
      ? jobId
      : null
  );

  const showGraph =
    job?.status === 'completed' &&
    GRAPH_ARTIFACT_TYPES.has(job.artifact_type) &&
    (nodes.length > 0 || graphLoading);

  if (!jobId) {
    return (
      <div className="p-6">
        <ErrorAlert message="Invalid job ID in URL." title="Not Found" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl w-full p-6">
      {/* Back link */}
      <Link
        href="/dashboard"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors"
        aria-label="Back to dashboard"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      {/* Loading state */}
      {jobLoading && !job && (
        <LoadingSpinner label="Loading job…" className="mt-8 justify-center" />
      )}

      {/* Error state */}
      {jobError && (
        <ErrorAlert message={jobError} title="Could not load job" className="mt-4" />
      )}

      {/* Job content */}
      {job && (
        <>
          {/* Job metadata card */}
          <section
            aria-labelledby="job-heading"
            className="mb-8 rounded-xl border border-gray-700/50 bg-gray-800/30 p-6"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h1
                id="job-heading"
                className="text-lg font-semibold text-white"
              >
                Job Details
              </h1>
              <StatusBadge status={job.status} />
            </div>

            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex items-start gap-2">
                <GitBranch className="mt-0.5 h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                <div>
                  <dt className="text-xs text-gray-500">Repository</dt>
                  <dd className="mt-0.5 break-all text-sm text-gray-200">{job.repo_url}</dd>
                </div>
              </div>

              <div className="flex items-start gap-2">
                <Tag className="mt-0.5 h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                <div>
                  <dt className="text-xs text-gray-500">Artifact Type</dt>
                  <dd className="mt-0.5 text-sm text-gray-200">
                    {ARTIFACT_TYPE_LABELS[job.artifact_type] ?? job.artifact_type}
                  </dd>
                </div>
              </div>

              <div className="flex items-start gap-2">
                <Calendar className="mt-0.5 h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                <div>
                  <dt className="text-xs text-gray-500">Created</dt>
                  <dd className="mt-0.5 text-sm text-gray-200">{formatDate(job.created_at)}</dd>
                </div>
              </div>

              <div className="flex items-start gap-2">
                <Calendar className="mt-0.5 h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                <div>
                  <dt className="text-xs text-gray-500">Last Updated</dt>
                  <dd className="mt-0.5 text-sm text-gray-200">{formatDate(job.updated_at)}</dd>
                </div>
              </div>

              <div>
                <dt className="text-xs text-gray-500">Job ID</dt>
                <dd className="mt-0.5 font-mono text-xs text-gray-400 break-all">{job.id}</dd>
              </div>
            </dl>
          </section>

          {/* Running state feedback */}
          {job.status === 'running' && (
            <div className="mb-6">
              <LoadingSpinner label="Analysis in progress…" size="sm" />
            </div>
          )}

          {/* Graph canvas */}
          {showGraph && (
            <section aria-labelledby="graph-heading" className="mb-8">
              <h2
                id="graph-heading"
                className="mb-3 text-sm font-semibold text-gray-300"
              >
                Code Knowledge Graph
              </h2>
              {graphLoading && <LoadingSpinner label="Loading graph…" />}
              {graphError && (
                <ErrorAlert message={graphError} title="Could not load graph" />
              )}
              {!graphLoading && (
                <GraphCanvas nodes={nodes} edges={edges} />
              )}
            </section>
          )}

          {/* Artifacts */}
          {job.status === 'completed' && (
            <section aria-labelledby="artifacts-heading">
              <h2
                id="artifacts-heading"
                className="mb-4 text-sm font-semibold text-gray-300"
              >
                Artifacts
              </h2>

              {artifactsLoading && <LoadingSpinner label="Loading artifacts…" />}
              {artifactsError && (
                <ErrorAlert message={artifactsError} title="Could not load artifacts" />
              )}
              {!artifactsLoading && artifacts.length === 0 && (
                <p className="text-sm text-gray-500">No artifacts found for this job.</p>
              )}

              <div className="flex flex-col gap-6">
                {artifacts.map((artifact) => (
                  <ArtifactViewer key={artifact.id} artifact={artifact} />
                ))}
              </div>
            </section>
          )}

          {(job.status === 'failed' || job.status === 'cancelled') && (
            <ErrorAlert
              message={`Job ${job.status}. No artifacts are available.`}
              title={`Job ${job.status}`}
            />
          )}
        </>
      )}
    </div>
  );
}
