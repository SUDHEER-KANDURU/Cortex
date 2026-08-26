// =============================================================================
// Job Detail Page — /jobs/[jobId]
// Fully theme-aware: uses CSS variables throughout, no hardcoded dark colors.
// =============================================================================

'use client';

import React, { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, RotateCcw } from 'lucide-react';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useRetryJob } from '@/features/jobs/hooks/useRetryJob';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useGraphData } from '@/features/graph/hooks/useGraphData';
import ArtifactViewer from '@/features/artifacts/components/ArtifactViewer';
import GraphCanvas from '@/features/graph/components/GraphCanvas';
import StatusBadge from '@/components/shared/StatusBadge';
import Navbar from '@/components/layout/Navbar';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { formatDate } from '@/lib/utils/formatDate';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { InlineLoader } from '@/components/shared/BrandedLoader';

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
  const router = useRouter();
  const jobId = typeof params.jobId === 'string' ? params.jobId : null;

  const { job, isLoading: jobLoading, error: jobError } = useJobPolling(jobId);
  const { retriedJob, isRetrying, error: retryError, retry } = useRetryJob();
  const { artifacts, isLoading: artifactsLoading, error: artifactsError } = useArtifact(
    job?.status === 'completed' ? jobId : null
  );
  const { nodes, edges, isLoading: graphLoading, error: graphError } = useGraphData(
    job?.status === 'completed' && job.artifact_type && GRAPH_ARTIFACT_TYPES.has(job.artifact_type)
      ? jobId
      : null
  );

  // Navigate to the new job page when retry creates a replacement
  useEffect(() => {
    if (retriedJob) {
      router.push(`/jobs/${retriedJob.id}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retriedJob]);

  if (!jobId) {
    return (
      <div className="min-h-screen" style={{ background: 'transparent' }}>
        <Navbar />
        <div className="px-8 py-6">
          <p style={{ fontSize: 13, color: 'var(--danger)' }}>Invalid job ID in URL.</p>
          <Link href="/dashboard" style={{ marginTop: 12, display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)', textDecoration: 'none' }}>
            <ArrowLeft style={{ width: 14, height: 14 }} /> Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const repoName = job ? extractRepoName(job.repo_url) : null;

  return (
    <div className="min-h-screen" style={{ background: 'transparent' }}>
      <Navbar />

      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 px-8 pb-4 pt-6" style={{ fontSize: 13, color: 'var(--text-muted)' }} aria-label="Breadcrumb">
        <Link href="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', textDecoration: 'none', transition: 'color 0.2s' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
          <ArrowLeft style={{ width: 14, height: 14 }} /> Dashboard
        </Link>
        {repoName && (
          <>
            <span style={{ color: 'var(--border)' }}>/</span>
            <span style={{ color: 'var(--text-secondary)' }}>{repoName}</span>
          </>
        )}
        {job && (
          <>
            <span style={{ color: 'var(--border)' }}>/</span>
            <span style={{ color: 'var(--text-muted)' }}>{ARTIFACT_TYPE_LABELS[job.artifact_type]}</span>
          </>
        )}
      </nav>

      {/* Loading */}
      {jobLoading && !job && (
        <div className="px-8 flex justify-center py-12">
          <InlineLoader stage="loading" message="Loading Job…" />
        </div>
      )}

      {/* Error */}
      {jobError && (
        <div className="px-8">
          <p style={{ fontSize: 13, color: 'var(--danger)' }}>{jobError}</p>
          <Link href="/dashboard" style={{ marginTop: 12, display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)', textDecoration: 'none' }}>
            <ArrowLeft style={{ width: 14, height: 14 }} /> Back to Dashboard
          </Link>
        </div>
      )}

      {job && (
        <div className="px-8 pb-12">

          {/* Metadata card */}
          <div style={{
            marginBottom: 24, borderRadius: 'var(--radius-lg)', padding: 24,
            background: 'var(--card)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-md)',
            transition: 'background 0.3s ease, border-color 0.3s ease',
          }}>
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, minWidth: 0 }}>
                <h1 style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', margin: 0 }}>
                  {repoName}
                </h1>
                <a href={job.repo_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: 'var(--text-muted)', flexShrink: 0, transition: 'color 0.2s' }}
                  aria-label="Open repository"
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
                  <ExternalLink style={{ width: 13, height: 13 }} />
                </a>
              </div>
              <StatusBadge status={job.status} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px 32px' }} className="sm:grid-cols-4">
              {[
                { label: 'Type',    value: ARTIFACT_TYPE_LABELS[job.artifact_type] },
                { label: 'Created', value: formatDate(job.created_at) },
                { label: 'Updated', value: formatDate(job.updated_at) },
                { label: 'Job ID',  value: job.id, mono: true, truncate: true },
              ].map(({ label, value, mono, truncate }) => (
                <div key={label}>
                  <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--text-muted)', margin: '0 0 4px', fontFamily: 'var(--font-mono)' }}>{label}</p>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, fontFamily: mono ? 'var(--font-mono)' : undefined, overflow: truncate ? 'hidden' : undefined, textOverflow: truncate ? 'ellipsis' : undefined, whiteSpace: truncate ? 'nowrap' : undefined }}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Running */}
          {job.status === 'running' && (
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'center' }}>
              <InlineLoader stage="building_graph" message="Analyzing Repository…" />
            </div>
          )}

          {/* Tabs */}
          {job.status === 'completed' && (
            <Tabs defaultValue="artifacts">
              <TabsList style={{
                marginBottom: 24,
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: 4,
                transition: 'background 0.3s ease, border-color 0.3s ease',
              }}>
                <TabsTrigger
                  value="artifacts"
                  style={{ borderRadius: 'var(--radius-sm)', padding: '6px 16px', fontSize: 13, color: 'var(--text-muted)', transition: 'all 0.2s' }}
                  className="data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:shadow-sm"
                >
                  Artifacts
                </TabsTrigger>
                {GRAPH_ARTIFACT_TYPES.has(job.artifact_type) && (
                  <TabsTrigger
                    value="graph"
                    style={{ borderRadius: 'var(--radius-sm)', padding: '6px 16px', fontSize: 13, color: 'var(--text-muted)', transition: 'all 0.2s' }}
                    className="data-[state=active]:bg-[var(--surface)] data-[state=active]:text-[var(--text)] data-[state=active]:shadow-sm"
                  >
                    Knowledge Graph
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="artifacts">
                {artifactsLoading && <InlineLoader stage="generating_artifact" message="Loading Artifacts…" />}
                {artifactsError && <p style={{ fontSize: 13, color: 'var(--danger)' }}>{artifactsError}</p>}
                {!artifactsLoading && artifacts.length === 0 && (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No artifacts found for this job.</p>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
                  {artifacts.map(artifact => (
                    <div key={artifact.id}>
                      {/* Content-type label */}
                      <p style={{
                        display: 'inline-flex', alignItems: 'center', marginBottom: 12,
                        borderRadius: 'var(--radius-full)', border: '1px solid var(--border-hover)',
                        background: 'var(--primary-dim)', padding: '3px 12px',
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.10em',
                        textTransform: 'uppercase', color: 'var(--primary)',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        {artifact.content_type}
                      </p>
                      <ArtifactViewer artifact={artifact} />
                    </div>
                  ))}
                </div>
              </TabsContent>

              {GRAPH_ARTIFACT_TYPES.has(job.artifact_type) && (
                <TabsContent value="graph">
                  {graphLoading && <InlineLoader stage="building_graph" message="Loading Knowledge Graph…" />}
                  {graphError && <p style={{ fontSize: 13, color: 'var(--danger)' }}>{graphError}</p>}
                  {!graphLoading && <GraphCanvas nodes={nodes} edges={edges} />}
                </TabsContent>
              )}
            </Tabs>
          )}

          {/* Terminal states */}
          {(job.status === 'failed' || job.status === 'cancelled') && (
            <div style={{
              borderRadius: 'var(--radius-lg)', padding: 24,
              background: 'var(--card)',
              border: '1px solid var(--border)',
              boxShadow: 'var(--shadow-md)',
              display: 'flex', flexDirection: 'column', gap: 16,
            }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                Job {job.status}. No artifacts are available.
              </p>

              {/* Show error details for failed jobs */}
              {job.status === 'failed' && job.error_message && (
                <div style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '12px 16px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--danger-dim)', border: '1px solid var(--danger-dim)',
                }}>
                  <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0, fontFamily: 'var(--font-mono)', lineHeight: 1.6 }}>
                    {job.error_message}
                  </p>
                </div>
              )}

              {/* Retry button for failed jobs */}
              {job.status === 'failed' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
                  <button
                    type="button"
                    onClick={() => retry(job.id)}
                    disabled={isRetrying}
                    aria-busy={isRetrying}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '10px 22px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--danger-dim)',
                      background: 'var(--danger-dim)', color: 'var(--danger)',
                      fontSize: 13, fontWeight: 600,
                      cursor: isRetrying ? 'not-allowed' : 'pointer',
                      opacity: isRetrying ? 0.6 : 1,
                      transition: 'background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease',
                    }}
                    onMouseEnter={e => { if (!isRetrying) { e.currentTarget.style.background = 'rgba(239,68,68,0.16)'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.55)'; }}}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.35)'; }}
                  >
                    <RotateCcw
                      style={{ width: 14, height: 14, flexShrink: 0, animation: isRetrying ? 'spin 0.8s linear infinite' : 'none' }}
                      aria-hidden="true"
                    />
                    {isRetrying ? 'Retrying…' : 'Retry Job'}
                  </button>
                  {retryError && (
                    <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0 }}>{retryError}</p>
                  )}
                </div>
              )}
            </div>
          )}
          {job.status === 'pending' && (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Job is queued and waiting to start.</p>
          )}
        </div>
      )}
    </div>
  );
}
