// =============================================================================
// Job Detail Page — /jobs/[jobId]
// Premium redesign — logic unchanged, visual overhaul.
// =============================================================================

'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useGraphData } from '@/features/graph/hooks/useGraphData';
import ArtifactViewer from '@/features/artifacts/components/ArtifactViewer';
import GraphCanvas from '@/features/graph/components/GraphCanvas';
import StatusBadge from '@/components/shared/StatusBadge';
import Navbar from '@/components/layout/Navbar';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { formatDate } from '@/lib/utils/formatDate';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';

const GRAPH_ARTIFACT_TYPES = new Set([
  'module_breakdown',
  'architecture_diagram',
  'folder_structure',
]);

function extractRepoName(url: string): string {
  const parts = url.replace(/\/$/, '').split('/');
  return parts[parts.length - 1] ?? url;
}

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

  if (!jobId) {
    return (
      <div className="min-h-screen" style={{ background: '#020408' }}>
        <Navbar />
        <div className="px-8 py-6">
          <p className="text-sm text-red-400">Invalid job ID in URL.</p>
          <Link href="/dashboard" className="mt-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const repoName = job ? extractRepoName(job.repo_url) : null;

  return (
    <div className="min-h-screen" style={{ background: '#020408' }}>
      <Navbar />
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 px-8 pb-4 pt-6 text-sm text-slate-500" aria-label="Breadcrumb">
        <Link href="/dashboard" className="flex items-center gap-1.5 transition-colors hover:text-slate-300">
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        {repoName && (
          <>
            <span className="text-slate-700">/</span>
            <span className="text-slate-400">{repoName}</span>
          </>
        )}
        {job && (
          <>
            <span className="text-slate-700">/</span>
            <span className="text-slate-500">{ARTIFACT_TYPE_LABELS[job.artifact_type]}</span>
          </>
        )}
      </nav>

      {/* Loading state */}
      {jobLoading && !job && (
        <div className="space-y-3 px-8">
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-800" />
          <div className="h-32 animate-pulse rounded-xl bg-slate-800/50" />
        </div>
      )}

      {/* Error state */}
      {jobError && (
        <div className="px-8">
          <p className="text-sm text-red-400">{jobError}</p>
          <Link href="/dashboard" className="mt-3 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
        </div>
      )}

      {job && (
        <div className="px-8 pb-12">
          {/* Metadata card */}
          <div
            className="mb-6 rounded-xl border border-[#1A2340] p-6"
            style={{ background: '#0A0F1A' }}
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-baseline gap-3 min-w-0">
                <h1 className="truncate text-lg font-medium text-white">{repoName}</h1>
                <a
                  href={job.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-slate-600 hover:text-slate-400 transition-colors"
                  aria-label="Open repository"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
              <StatusBadge status={job.status} />
            </div>

            <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-slate-600">Type</p>
                <p className="mt-1 text-sm text-slate-300">{ARTIFACT_TYPE_LABELS[job.artifact_type]}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-slate-600">Created</p>
                <p className="mt-1 text-sm text-slate-300">{formatDate(job.created_at)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-slate-600">Updated</p>
                <p className="mt-1 text-sm text-slate-300">{formatDate(job.updated_at)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-slate-600">Job ID</p>
                <p className="mt-1 truncate font-mono text-xs text-slate-500">{job.id}</p>
              </div>
            </div>
          </div>

          {/* Running indicator */}
          {job.status === 'running' && (
            <p className="mb-4 animate-pulse text-xs text-violet-400">Analyzing repository…</p>
          )}

          {/* Tabs */}
          {job.status === 'completed' && (
            <Tabs defaultValue="artifacts">
              <TabsList className="mb-6 border border-[#1A2340] bg-[#0A0F1A] p-1">
                <TabsTrigger
                  value="artifacts"
                  className="rounded-md px-4 py-1.5 text-sm text-slate-400 transition-all data-[state=active]:bg-[#0F1629] data-[state=active]:text-white"
                >
                  Artifacts
                </TabsTrigger>
                {GRAPH_ARTIFACT_TYPES.has(job.artifact_type) && (
                  <TabsTrigger
                    value="graph"
                    className="rounded-md px-4 py-1.5 text-sm text-slate-400 transition-all data-[state=active]:bg-[#0F1629] data-[state=active]:text-white"
                  >
                    Knowledge Graph
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="artifacts">
                {artifactsLoading && (
                  <div className="space-y-3">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-slate-800" />
                    <div className="h-32 animate-pulse rounded-lg bg-slate-800/50" />
                  </div>
                )}
                {artifactsError && (
                  <p className="text-sm text-red-400">{artifactsError}</p>
                )}
                {!artifactsLoading && artifacts.length === 0 && (
                  <p className="text-sm text-slate-500">No artifacts found for this job.</p>
                )}
                <div className="space-y-8">
                  {artifacts.map(artifact => (
                    <div key={artifact.id}>
                      <p className="mb-3 inline-flex items-center rounded border border-cyan-400/20 bg-cyan-400/5 px-2 py-0.5 text-[10px] uppercase tracking-widest text-cyan-400">
                        {artifact.content_type}
                      </p>
                      <ArtifactViewer artifact={artifact} />
                    </div>
                  ))}
                </div>
              </TabsContent>

              {GRAPH_ARTIFACT_TYPES.has(job.artifact_type) && (
                <TabsContent value="graph">
                  {graphLoading && (
                    <div className="h-32 animate-pulse rounded-lg bg-slate-800/50" />
                  )}
                  {graphError && (
                    <p className="text-sm text-red-400">{graphError}</p>
                  )}
                  {!graphLoading && (
                    <GraphCanvas nodes={nodes} edges={edges} />
                  )}
                </TabsContent>
              )}
            </Tabs>
          )}

          {/* Non-completed terminal states */}
          {(job.status === 'failed' || job.status === 'cancelled') && (
            <p className="text-sm text-slate-500">
              Job {job.status}. No artifacts are available.
            </p>
          )}
          {job.status === 'pending' && (
            <p className="text-sm text-slate-500">Job is queued and waiting to start.</p>
          )}
        </div>
      )}
    </div>
  );
}
