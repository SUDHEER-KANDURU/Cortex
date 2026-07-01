// =============================================================================
// Dashboard Page — Premium redesign
// All logic unchanged — only layout and styling updated.
// =============================================================================

'use client';

import React, { useState, useCallback } from 'react';
import type { Job, ArtifactType } from '@/types';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useSubmitJob } from '@/features/jobs/hooks/useSubmitJob';
import ArtifactViewer from '@/features/artifacts/components/ArtifactViewer';
import StatusBadge from '@/components/shared/StatusBadge';
import Navbar from '@/components/layout/Navbar';
import { listJobs } from '@/lib/api/jobs.api';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { Github, ChevronDown, Sparkles, Code2 } from 'lucide-react';

// ── Artifact type options ─────────────────────────────────────────────────────

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

      {/* Submit */}
      <button
        type="submit"
        disabled={isSubmitting || !repoUrl.trim()}
        aria-busy={isSubmitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-violet-500 hover:shadow-[0_0_16px_rgba(124,58,237,0.3)] active:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
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
      {/* Form section */}
      <div className="border-b border-[#1A2340] p-5">
        <SidebarForm onJobSubmitted={onJobSubmitted} />
      </div>

      {/* Jobs list section */}
      <div className="flex flex-1 flex-col p-5">
        <p className="mb-3 text-[10px] font-medium uppercase tracking-[0.15em] text-slate-500">
          Recent Jobs
        </p>

        {jobsLoading && (
          <p className="py-4 text-center text-xs text-slate-600">Loading…</p>
        )}
        {jobsError && (
          <p className="px-1 py-2 text-xs text-red-400">Could not load jobs</p>
        )}
        {!jobsLoading && jobs.length === 0 && (
          <p className="py-8 text-center text-xs text-slate-600">No jobs yet</p>
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
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900">
          <Code2 className="h-7 w-7 text-slate-600" aria-hidden="true" />
        </div>
        <p className="text-sm text-slate-500">Select a repository to analyze</p>
        <p className="text-xs text-slate-600">Submit a GitHub URL to get started</p>
      </div>
    );
  }

  const repoName = extractRepoName(activeJob.repo_url);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-[#1A2340] px-6 py-4">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="truncate text-base font-medium text-white">{repoName}</span>
          <span className="shrink-0 text-sm text-slate-500">
            {ARTIFACT_TYPE_LABELS[activeJob.artifact_type]}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge status={activeJob.status} />
          {activeJob.status === 'running' && (
            <span className="animate-pulse text-xs text-violet-400">Analyzing...</span>
          )}
        </div>
      </div>

      {/* Artifacts area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Running skeleton */}
        {activeJob.status === 'running' && artifacts.length === 0 && (
          <div className="space-y-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-slate-800" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-slate-800" />
            <div className="mt-4 h-32 animate-pulse rounded-lg bg-slate-800/50" />
          </div>
        )}

        {/* Non-completed status messages */}
        {activeJob.status === 'pending' && (
          <p className="text-sm text-slate-500">Job is queued and waiting to start.</p>
        )}
        {activeJob.status === 'failed' && (
          <p className="text-sm text-red-400">Job failed. Check logs for details.</p>
        )}
        {activeJob.status === 'cancelled' && (
          <p className="text-sm text-slate-500">Job was cancelled.</p>
        )}

        {/* Artifacts */}
        {artifactsLoading && (
          <div className="space-y-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-slate-800" />
            <div className="h-32 animate-pulse rounded-lg bg-slate-800/50" />
          </div>
        )}
        {artifactsError && (
          <p className="text-xs text-red-400">{artifactsError}</p>
        )}
        {!artifactsLoading && activeJob.status === 'completed' && artifacts.length === 0 && (
          <p className="text-sm text-slate-500">No artifacts generated yet.</p>
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

  // Auto-refetch artifacts when job completes
  React.useEffect(() => {
    if (polledJob?.status === 'completed') refetch();
  }, [polledJob?.status, refetch]);

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
