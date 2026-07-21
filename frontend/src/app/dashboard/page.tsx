// =============================================================================
// Dashboard Page — Premium redesign
// Progressive loading: shell renders immediately, content loads progressively.
// =============================================================================

'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { Job, ArtifactType } from '@/types';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useSubmitJob } from '@/features/jobs/hooks/useSubmitJob';
import StatusBadge from '@/components/shared/StatusBadge';
import Navbar from '@/components/layout/Navbar';
import { listJobs } from '@/lib/api/jobs.api';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { Github, ChevronDown, Sparkles, Code2 } from 'lucide-react';
import dynamic from 'next/dynamic';

// Lazy-load the heavy ArtifactViewer — it may include Mermaid/ReactFlow
const ArtifactViewer = dynamic(
  () => import('@/features/artifacts/components/ArtifactViewer'),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-3">
        <div className="h-4 w-3/4 animate-pulse rounded bg-slate-800" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-slate-800" />
        <div className="mt-4 h-48 animate-pulse rounded-lg bg-slate-800/50" />
      </div>
    ),
  }
);

// ── Skeleton components for progressive loading ───────────────────────────────

function JobRowSkeleton() {
  return (
    <div className="rounded-lg px-3 py-2.5 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex-1 pr-4 space-y-1.5">
          <div className="h-3 w-2/3 rounded bg-slate-800" />
          <div className="h-2.5 w-1/2 rounded bg-slate-800/70" />
        </div>
        <div className="h-5 w-14 rounded-full bg-slate-800/60" />
      </div>
    </div>
  );
}

function SidebarJobsSkeleton() {
  return (
    <div className="flex flex-col gap-1">
      {[1, 2, 3].map(i => <JobRowSkeleton key={i} />)}
    </div>
  );
}

const ARTIFACT_TYPES: ArtifactType[] = [
  'folder_structure',
  'module_breakdown',
  'architecture_diagram',
  'database_schema',
  'api_spec',
  'learning_path',
  'interview_questions',
];

const GITHUB_URL_RE = /^https:\/\/github\.com\/[\w-]+\/[\w-]+\/?$/;

function extractRepoName(url: string): string {
  const parts = url.replace(/\/$/, '').split('/');
  return parts[parts.length - 1] ?? url;
}

// ── Sidebar form ──────────────────────────────────────────────────────────────

interface SidebarFormProps {
  onJobSubmitted: (job: Job) => void;
}

function SidebarForm({ onJobSubmitted }: SidebarFormProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [artifactType, setArtifactType] = useState<ArtifactType>('architecture_diagram');
  const [urlError, setUrlError] = useState<string | null>(null);
  const { isSubmitting, error: apiError, submitJob, submittedJob } = useSubmitJob();

  React.useEffect(() => {
    if (submittedJob) {
      onJobSubmitted(submittedJob);
      setRepoUrl('');
      setArtifactType('architecture_diagram');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedJob]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setUrlError(null);
    const trimmed = repoUrl.trim();
    if (!trimmed) { setUrlError('Enter a GitHub URL'); return; }
    if (!GITHUB_URL_RE.test(trimmed)) { setUrlError('Must be https://github.com/owner/repo'); return; }
    await submitJob({ repo_url: trimmed, artifact_type: artifactType });
  };

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Submit a new Cortex job">
      <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.15em] text-slate-500">
        Analyze Repository
      </p>

      {/* URL input */}
      <div className="relative mb-2">
        <Github className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500 pointer-events-none" aria-hidden="true" />
        <input
          type="url"
          value={repoUrl}
          onChange={e => { setRepoUrl(e.target.value); setUrlError(null); }}
          placeholder="https://github.com/owner/repo"
          disabled={isSubmitting}
          aria-label="GitHub repository URL"
          aria-invalid={!!urlError}
          className="w-full rounded-lg border border-[#1A2340] bg-[#0F1629] py-2.5 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-600 outline-none transition-all duration-200 hover:border-[#2A3A60] focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 disabled:opacity-50"
        />
      </div>
      {urlError && (
        <p className="mb-2 text-[11px] text-red-400">{urlError}</p>
      )}
      {apiError && (
        <p className="mb-2 text-[11px] text-red-400">{apiError}</p>
      )}

      {/* Artifact type select */}
      <div className="relative mb-3">
        <select
          value={artifactType}
          onChange={e => setArtifactType(e.target.value as ArtifactType)}
          disabled={isSubmitting}
          aria-label="Artifact type"
          className="w-full appearance-none rounded-lg border border-[#1A2340] bg-[#0F1629] px-3 py-2.5 text-sm text-slate-200 outline-none transition-all duration-200 hover:border-[#2A3A60] focus:border-violet-500/50 disabled:opacity-50 cursor-pointer"
        >
          {ARTIFACT_TYPES.map(t => (
            <option key={t} value={t}>{ARTIFACT_TYPE_LABELS[t]}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
      </div>

      {/* Submit — Liquid Glass dark button */}
      <button
        type="submit"
        disabled={isSubmitting || !repoUrl.trim()}
        aria-busy={isSubmitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          background: isSubmitting
            ? 'rgba(124,58,237,0.7)'
            : 'rgba(124,58,237,0.92)',
          // Liquid Glass: top sheen + depth shadow + rim
          boxShadow: [
            '0 2px 12px rgba(124,58,237,0.30)',
            '0 1px 3px rgba(0,0,0,0.24)',
            '0 0 0 1px rgba(255,255,255,0.06)',
            'inset 0 1px 0 rgba(255,255,255,0.14)',
            'inset 0 -1px 0 rgba(0,0,0,0.18)',
          ].join(', '),
          transition: 'background 0.2s ease, box-shadow 0.2s ease',
        }}
        onMouseEnter={e => {
          if (!isSubmitting) {
            const el = e.currentTarget
            el.style.background = 'rgba(124,58,237,1)'
            el.style.boxShadow = [
              '0 4px 20px rgba(124,58,237,0.40)',
              '0 1px 3px rgba(0,0,0,0.24)',
              '0 0 0 1px rgba(255,255,255,0.08)',
              'inset 0 1px 0 rgba(255,255,255,0.16)',
              'inset 0 -1px 0 rgba(0,0,0,0.18)',
            ].join(', ')
          }
        }}
        onMouseLeave={e => {
          if (!isSubmitting) {
            const el = e.currentTarget
            el.style.background = 'rgba(124,58,237,0.92)'
            el.style.boxShadow = [
              '0 2px 12px rgba(124,58,237,0.30)',
              '0 1px 3px rgba(0,0,0,0.24)',
              '0 0 0 1px rgba(255,255,255,0.06)',
              'inset 0 1px 0 rgba(255,255,255,0.14)',
              'inset 0 -1px 0 rgba(0,0,0,0.18)',
            ].join(', ')
          }
        }}
      >
        {isSubmitting ? (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        ) : (
          <Sparkles size={14} aria-hidden="true" />
        )}
        {isSubmitting ? 'Analyzing…' : 'Analyze Repository'}
      </button>
    </form>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────

interface JobRowProps {
  job: Job;
  isSelected: boolean;
  onClick: () => void;
}

function JobRow({ job, isSelected, onClick }: JobRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative w-full cursor-pointer rounded-lg px-3 py-2.5 text-left transition-all duration-150 ${
        isSelected
          ? 'border-l-2 border-violet-500 bg-[#0F1629] pl-[10px]'
          : 'hover:bg-[#0F1629]'
      }`}
      aria-pressed={isSelected}
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0 pr-2">
          <p className="truncate text-sm font-medium text-slate-200">
            {extractRepoName(job.repo_url)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {ARTIFACT_TYPE_LABELS[job.artifact_type]}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>
    </button>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

interface SidebarProps {
  jobs: Job[];
  jobsLoading: boolean;
  jobsError: string | null;
  selectedJobId: string | null;
  onJobSelected: (job: Job) => void;
  onJobSubmitted: (job: Job) => void;
}

function Sidebar({ jobs, jobsLoading, jobsError, selectedJobId, onJobSelected, onJobSubmitted }: SidebarProps) {
  return (
    <aside
      className="flex shrink-0 flex-col overflow-y-auto border-r border-[#1A2340]"
      style={{ width: 360, background: '#0A0F1A' }}
      aria-label="Sidebar"
    >
      {/* Form section — glass panel header */}
      <div className="p-5"
        style={{
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          boxShadow: 'inset 0 -1px 0 rgba(0,0,0,0.18)',
        }}>
        <SidebarForm onJobSubmitted={onJobSubmitted} />
      </div>

      {/* Jobs list section */}
      <div className="flex flex-1 flex-col p-5">
        <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.15em] text-slate-500">
          Recent Jobs
        </p>

        {jobsLoading && <SidebarJobsSkeleton />}
        {jobsError && (
          <p className="px-1 py-2 text-xs text-red-400">Could not load jobs</p>
        )}
        {!jobsLoading && jobs.length === 0 && (
          <div className="py-8 text-center">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/50">
              <Code2 className="h-4 w-4 text-slate-600" />
            </div>
            <p className="text-xs text-slate-600">No jobs yet</p>
            <p className="mt-1 text-[11px] text-slate-700">Submit a URL above to start</p>
          </div>
        )}

        <div className="flex flex-col gap-0.5">
          {jobs.map(job => (
            <JobRow
              key={job.id}
              job={job}
              isSelected={job.id === selectedJobId}
              onClick={() => onJobSelected(job)}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}

// ── Right panel ───────────────────────────────────────────────────────────────

interface RightPanelProps {
  activeJob: Job | null;
  artifacts: ReturnType<typeof useArtifact>['artifacts'];
  artifactsLoading: boolean;
  artifactsError: string | null;
}

function RightPanel({ activeJob, artifacts, artifactsLoading, artifactsError }: RightPanelProps) {
  if (!activeJob) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900">
          <Code2 className="h-7 w-7 text-slate-600" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-400">No repository selected</p>
          <p className="mt-1 text-xs text-slate-600 max-w-[200px]">Paste a GitHub URL in the sidebar and click Analyze</p>
        </div>
      </div>
    );
  }

  const repoName = extractRepoName(activeJob.repo_url);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Top bar — Liquid Glass panel header */}
      <div className="flex items-center justify-between px-6 py-4"
        style={{
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(15,22,41,0.85)',
          backdropFilter: 'blur(12px) saturate(150%)',
          WebkitBackdropFilter: 'blur(12px) saturate(150%)',
          // Dual-tone: top highlight + bottom separator
          boxShadow: [
            'inset 0 1px 0 rgba(255,255,255,0.07)',
            'inset 0 -1px 0 rgba(0,0,0,0.20)',
          ].join(', '),
        }}>
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="truncate text-base font-medium text-white">{repoName}</span>
          <span className="shrink-0 text-sm text-slate-500">
            {ARTIFACT_TYPE_LABELS[activeJob.artifact_type]}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge status={activeJob.status} />
          {activeJob.status === 'running' && (
            <span className="animate-pulse text-xs text-violet-400">Analyzing…</span>
          )}
        </div>
      </div>

      {/* Artifacts area */}
      <div className="flex-1 overflow-y-auto px-6 py-5">

        {/* Pending */}
        {activeJob.status === 'pending' && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-slate-500" />
            <p className="text-sm text-slate-500">Queued — waiting for a worker</p>
          </div>
        )}

        {/* Running skeleton — progressive staggered bars */}
        {activeJob.status === 'running' && artifacts.length === 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-violet-400">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-violet-800 border-t-violet-400" />
              Building knowledge graph…
            </div>
            <div className="space-y-2.5">
              {[75, 55, 85, 45, 65].map((w, i) => (
                <div key={i} className="animate-pulse rounded bg-slate-800"
                  style={{ height: i === 2 ? 80 : 12, width: `${w}%`, animationDelay: `${i * 150}ms` }} />
              ))}
            </div>
          </div>
        )}

        {/* Failed */}
        {activeJob.status === 'failed' && (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-red-900/40 bg-red-950/30">
              <span className="text-lg">✕</span>
            </div>
            <p className="text-sm font-medium text-red-400">Analysis failed</p>
            <p className="text-xs text-slate-600">Check backend logs for details</p>
          </div>
        )}

        {/* Cancelled */}
        {activeJob.status === 'cancelled' && (
          <p className="py-8 text-center text-sm text-slate-500">Job was cancelled.</p>
        )}

        {/* Artifacts loading skeleton */}
        {artifactsLoading && (
          <div className="space-y-4">
            <div className="h-3.5 w-2/3 animate-pulse rounded bg-slate-800" />
            <div className="h-56 animate-pulse rounded-lg bg-slate-800/50" />
          </div>
        )}

        {artifactsError && (
          <p className="py-4 text-xs text-red-400">{artifactsError}</p>
        )}

        {!artifactsLoading && activeJob.status === 'completed' && artifacts.length === 0 && (
          <p className="py-8 text-center text-sm text-slate-500">No artifacts generated yet.</p>
        )}

        <div className="space-y-6">
          {artifacts.map(artifact => (
            <div key={artifact.id}>
              <p className="mb-3 inline-flex items-center rounded border border-cyan-400/20 bg-cyan-400/5 px-2 py-0.5 text-[10px] uppercase tracking-widest text-cyan-400">
                {artifact.content_type}
              </p>
              <ArtifactViewer artifact={artifact} />
              <div className="mt-6 border-t border-[#1A2340]" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);

  // Initial jobs fetch
  React.useEffect(() => {
    let active = true;
    setJobsLoading(true);
    listJobs()
      .then(data => { if (active) setJobs(data); })
      .catch(err => { if (active) setJobsError(err instanceof Error ? err.message : 'Failed'); })
      .finally(() => { if (active) setJobsLoading(false); });
    return () => { active = false; };
  }, []);

  // Poll selected job
  const { job: polledJob } = useJobPolling(selectedJob?.id ?? null);
  const activeJob = polledJob ?? selectedJob;

  // Artifacts for selected job
  const { artifacts, isLoading: artifactsLoading, error: artifactsError, refetch } = useArtifact(
    selectedJob?.id ?? null
  );

  const completedJobRef = useRef<string | null>(null);

  // Auto-refetch artifacts exactly once when the selected job reaches a completed state.
  useEffect(() => {
    if (!polledJob || polledJob.status !== 'completed') {
      return;
    }

    if (completedJobRef.current === polledJob.id) {
      return;
    }

    completedJobRef.current = polledJob.id;
    refetch();
  }, [polledJob?.id, polledJob?.status, refetch]);

  const handleJobSubmitted = useCallback((job: Job) => {
    setJobs(prev => [job, ...prev]);
    setSelectedJob(job);
  }, []);

  const handleJobSelected = useCallback((job: Job) => {
    setSelectedJob(job);
  }, []);

  return (
    <div className="flex flex-col min-h-screen" style={{ background: '#020408' }}>
      <Navbar />
      <div
        className="flex flex-1 overflow-hidden"
        style={{ height: 'calc(100vh - 48px)' }}
      >
        <Sidebar
        jobs={jobs}
        jobsLoading={jobsLoading}
        jobsError={jobsError}
        selectedJobId={selectedJob?.id ?? null}
        onJobSelected={handleJobSelected}
        onJobSubmitted={handleJobSubmitted}
      />
      <RightPanel
        activeJob={activeJob}
        artifacts={artifacts}
        artifactsLoading={artifactsLoading}
        artifactsError={artifactsError}
      />
      </div>
    </div>
  );
}
