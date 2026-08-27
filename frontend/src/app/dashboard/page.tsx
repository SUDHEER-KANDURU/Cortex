// =============================================================================
// Dashboard Page — Premium redesign, full theme-aware
// Every surface, border, and text color uses CSS vars or isDark-conditional
// values. No hardcoded rgba(255,255,255,*) leaking into light mode.
// =============================================================================

'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { Job, ArtifactType } from '@/types';
import { useJobPolling } from '@/features/jobs/hooks/useJobPolling';
import { useArtifact } from '@/features/artifacts/hooks/useArtifact';
import { useSubmitJob } from '@/features/jobs/hooks/useSubmitJob';
import { useRetryJob } from '@/features/jobs/hooks/useRetryJob';
import StatusBadge from '@/components/shared/StatusBadge';
import { listJobs } from '@/lib/api/jobs.api';
import { deleteJob } from '@/lib/api/jobs.api';
import { sessionCache, cacheKey, TTL } from '@/lib/cache';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { InlineLoader, ButtonSpinner } from '@/components/shared/BrandedLoader';
import { SidebarJobsSkeleton, ArtifactSkeleton, InsightsSkeleton } from '@/components/shared/Skeletons';
import {
  Github, ChevronDown, Sparkles, Code2, LayoutDashboard,
  GitBranch, ExternalLink, Clock, AlertCircle, CheckCircle2,
  XCircle, ArrowLeft, Check, RotateCcw,
} from 'lucide-react';
import AnimatedPipelineComponent from '@/components/pipeline/AnimatedPipeline';
import * as Select from '@radix-ui/react-select';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useInsights } from '@/features/insights/hooks/useInsights';
import InsightsDashboard from '@/features/insights/components/InsightsDashboard';
import { AnimatePresence, motion } from 'framer-motion';

const ArtifactViewer = dynamic(
  () => import('@/features/artifacts/components/ArtifactViewer'),
  {
    ssr: false,
    loading: () => <InlineLoader stage="generating_artifact" message="Loading Artifact…" size={28} />,
  }
);

// ── Constants ─────────────────────────────────────────────────────────────────
const ARTIFACT_TYPES: ArtifactType[] = [
  'folder_structure', 'module_breakdown', 'architecture_diagram',
  'database_schema', 'api_spec', 'learning_path', 'interview_questions',
  'vibe_code_detection',
];
const GITHUB_URL_RE = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

function extractRepoName(url: string) {
  return url.replace(/\/$/, '').split('/').slice(-2).join('/');
}
function extractShortName(url: string) {
  return url.replace(/\/$/, '').split('/').pop() ?? url;
}

// ── Light-only surface helpers ────────────────────────────────────────────────
// Dark mode removed. All values are static light-theme values.
function tintBorder(_d: boolean) { return 'rgba(255,255,255,0.45)'; }
function hoverBg(_d: boolean)    { return 'rgba(255,255,255,0.30)'; }

// ── Dashboard background ──────────────────────────────────────────────────────
// Removed — the global liquid-blob background in layout.tsx covers all pages.

// ── Navbar ────────────────────────────────────────────────────────────────────
const DashboardNavbar = React.memo(function DashboardNavbar() {
  const hov = hoverBg(false);
  const bdr = tintBorder(false);
  return (
    <header style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
      display: 'flex', justifyContent: 'center', padding: '14px 24px', pointerEvents: 'none',
    }}>
      <nav aria-label="Dashboard navigation" style={{
        pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 4,
        padding: '7px 10px', borderRadius: 9999, width: '100%', maxWidth: 960,
        background: 'rgba(255,255,255,0.72)',
        backdropFilter: 'blur(50px) saturate(200%) brightness(1.04)',
        WebkitBackdropFilter: 'blur(50px) saturate(200%) brightness(1.04)',
        border: '0.5px solid rgba(255,255,255,0.90)',
        boxShadow:
          '0 4px 24px rgba(80,60,20,0.09), 0 1px 6px rgba(80,60,20,0.05),' +
          'inset 0 1px 0 rgba(255,255,255,0.98),' +
          'inset 0 -1px 0 rgba(255,255,255,0.55),' +
          'inset 0 0 0 0.5px rgba(255,255,255,0.65)',
      }}>
        {/* Logo */}
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 12px', borderRadius: 16, textDecoration: 'none', flexShrink: 0, transition: 'background 0.2s ease' }}
          onMouseEnter={e => (e.currentTarget.style.background = hov)}
          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0)')}>
          <span style={{ width: 24, height: 24, borderRadius: 7, flexShrink: 0, background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.60)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <LayoutDashboard style={{ width: 12, height: 12, color: 'var(--primary)' }} />
          </span>
          <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text)', fontFamily: 'var(--font-sans)' }}>Cortex</span>
        </Link>
        {/* Center pill */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', background: 'rgba(255,255,255,0.22)', border: `0.5px solid ${bdr}`, borderRadius: 100, padding: '4px 14px' }}>Dashboard</span>
        </div>
        {/* Right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <Link href="/" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', padding: '6px 14px', borderRadius: 14, textDecoration: 'none', transition: 'all 0.2s ease', display: 'flex', alignItems: 'center', gap: 6 }}
            onMouseEnter={e => { e.currentTarget.style.background = hov; e.currentTarget.style.color = 'var(--text)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,0,0,0)'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
            <ArrowLeft style={{ width: 13, height: 13 }} /> Home
          </Link>
          <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', padding: '6px 14px', borderRadius: 14, textDecoration: 'none', transition: 'all 0.2s ease' }}
            onMouseEnter={e => { e.currentTarget.style.background = hov; e.currentTarget.style.color = 'var(--text)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,0,0,0)'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
            GitHub
          </a>
        </div>
      </nav>
    </header>
  );
});

// ── Sidebar submit form ───────────────────────────────────────────────────────
interface SidebarFormProps { onJobSubmitted: (job: Job) => void }

function SidebarForm({ onJobSubmitted }: SidebarFormProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [artifactType, setArtifactType] = useState<ArtifactType>('architecture_diagram');
  const [urlError, setUrlError] = useState<string | null>(null);
  const { isSubmitting, error: apiError, submitJob, submittedJob } = useSubmitJob();

  React.useEffect(() => {
    if (submittedJob) { onJobSubmitted(submittedJob); setRepoUrl(''); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedJob]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setUrlError(null);
    const t = repoUrl.trim();
    if (!t) { setUrlError('Enter a GitHub URL'); return; }
    if (!GITHUB_URL_RE.test(t)) { setUrlError('Must be https://github.com/owner/repo'); return; }
    await submitJob({ repo_url: t, artifact_type: artifactType });
  };

  const bdr = 'rgba(255,255,255,0.45)';
  const inputStyle: React.CSSProperties = {
    width: '100%', borderRadius: 14, padding: '10px 12px', fontSize: 13,
    background: 'rgba(255,255,255,0.68)',
    color: 'var(--text)',
    border: `0.5px solid ${bdr}`, outline: 'none',
    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
    fontFamily: 'var(--font-sans)', boxSizing: 'border-box' as const,
    boxShadow: 'inset 0 1px 3px rgba(255,255,255,0.55)',
  };

  return (
    <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>Analyze Repository</p>

      {/* URL input */}
      <div style={{ position: 'relative' }}>
        <Github style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14, color: 'var(--text-muted)', pointerEvents: 'none' }} />
        <input type="url" value={repoUrl}
          onChange={e => { setRepoUrl(e.target.value); setUrlError(null); }}
          placeholder="https://github.com/owner/repo" disabled={isSubmitting}
          aria-label="GitHub repository URL" aria-invalid={urlError ? 'true' : undefined}
          aria-describedby={urlError ? 'url-error' : undefined}
          style={{ ...inputStyle, paddingLeft: 34 }}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--primary-dim)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = bdr; e.currentTarget.style.boxShadow = 'none'; }}
        />
      </div>
      {(urlError || apiError) && (
        <p id="url-error" role="alert" style={{ fontSize: 11, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <AlertCircle style={{ width: 11, height: 11, flexShrink: 0 }} /> {urlError ?? apiError}
        </p>
      )}

      {/* Artifact type select */}
      <Select.Root value={artifactType} onValueChange={v => setArtifactType(v as ArtifactType)} disabled={isSubmitting}>
        <Select.Trigger
          aria-label="Artifact type"
          suppressHydrationWarning
          style={{ ...inputStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', userSelect: 'none' }}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--primary-dim)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = bdr; e.currentTarget.style.boxShadow = 'none'; }}>
          <Select.Value />
          <Select.Icon asChild><ChevronDown style={{ width: 14, height: 14, color: 'var(--text-muted)', flexShrink: 0 }} /></Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content position="popper" sideOffset={6} style={{
            width: 'var(--radix-select-trigger-width)',
            background: 'rgba(255,255,255,0.88)',
            backdropFilter: 'blur(40px) saturate(200%)',
            WebkitBackdropFilter: 'blur(40px) saturate(200%)',
            border: `0.5px solid rgba(255,255,255,0.60)`, borderRadius: 16,
            boxShadow: '0 8px 40px rgba(80,60,20,0.12), inset 0 2px 8px rgba(255,255,255,0.65)',
            padding: 4, zIndex: 9999, overflow: 'hidden',
            animation: 'dash-select-in 0.15s cubic-bezier(0.16,1,0.3,1)',
          }}>
            <Select.Viewport>
              {ARTIFACT_TYPES.map(t => (
                <Select.Item key={t} value={t} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '9px 12px', borderRadius: 10, fontSize: 13, fontWeight: 500,
                  color: 'var(--text-secondary)', cursor: 'pointer', outline: 'none',
                  transition: 'background 0.15s ease, color 0.15s ease',
                  fontFamily: 'var(--font-sans)', userSelect: 'none',
                }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.35)'; (e.currentTarget as HTMLElement).style.color = 'var(--text)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(0,0,0,0)'; (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
                  onFocus={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.35)'; (e.currentTarget as HTMLElement).style.color = 'var(--text)'; }}
                  onBlur={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(0,0,0,0)'; (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
                >
                  <Select.ItemText>{ARTIFACT_TYPE_LABELS[t]}</Select.ItemText>
                  <Select.ItemIndicator><Check style={{ width: 13, height: 13, color: 'var(--primary)', flexShrink: 0 }} /></Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>

      {/* Submit */}
      <button type="submit" disabled={isSubmitting || !repoUrl.trim()} style={{
        width: '100%', borderRadius: 14, padding: '11px 16px', fontSize: 13, fontWeight: 600,
        cursor: isSubmitting || !repoUrl.trim() ? 'not-allowed' : 'pointer',
        opacity: isSubmitting || !repoUrl.trim() ? 0.5 : 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
        background: 'var(--primary)',
        color: '#FFFFFF', border: 'none',
        boxShadow: 'var(--shadow-sm)',
        transition: 'filter 0.2s ease, opacity 0.2s ease', fontFamily: 'var(--font-sans)',
      }}
        onMouseEnter={e => { if (!isSubmitting && repoUrl.trim()) e.currentTarget.style.filter = 'brightness(1.08)'; }}
        onMouseLeave={e => { e.currentTarget.style.filter = ''; }}>
        {isSubmitting
          ? <><ButtonSpinner size={13} />Analyzing…</>
          : <><Sparkles style={{ width: 13, height: 13 }} />Analyze Repository</>}
      </button>
    </form>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────
interface JobRowProps { job: Job; isSelected: boolean; onClick: () => void; onDelete: (id: string) => void; onRetried: (newJob: Job) => void }

const JobRow = React.memo(function JobRow({ job, isSelected, onClick, onDelete, onRetried }: JobRowProps) {
  const short = extractShortName(job.repo_url);
  const owner = extractRepoName(job.repo_url).split('/')[0] ?? '';
  const isRunning = job.status === 'running';
  const isFailed = job.status === 'failed';
  const [hovered, setHovered] = React.useState(false);
  const [deleteVisible, setDeleteVisible] = React.useState(false);
  const rowRef = React.useRef<HTMLDivElement>(null);
  const { retriedJob, isRetrying, error: retryError, retry } = useRetryJob();

  // Bubble new job up to parent when retry succeeds
  React.useEffect(() => {
    if (retriedJob) onRetried(retriedJob);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retriedJob]);

  const dot: Record<string, string> = {
    completed: 'var(--success)', running: 'var(--primary)',
    failed: 'var(--danger)', pending: 'var(--text-muted)', cancelled: 'var(--text-muted)',
  };
  const dotColor = dot[job.status] ?? 'var(--text-muted)';

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(job.id);
  };

  const handleRetry = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await retry(job.id);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!rowRef.current) return;
    const { left, width } = rowRef.current.getBoundingClientRect();
    const relativeX = e.clientX - left;
    // Show delete button only when cursor is in the rightmost 20% of the row
    setDeleteVisible(relativeX / width >= 0.80);
  };

  const handleMouseLeave = () => {
    setHovered(false);
    setDeleteVisible(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div
        ref={rowRef}
        style={{ position: 'relative', overflow: 'hidden', borderRadius: 14 }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={handleMouseLeave}
        onMouseMove={handleMouseMove}
      >
        {/* ── Main row button — slides left when delete zone is hovered ── */}
        <button
          type="button"
          onClick={onClick}
          aria-pressed={isSelected}
          aria-label={`Job: ${short}, status: ${job.status}`}
          style={{
            width: '100%', textAlign: 'left', cursor: 'pointer', borderRadius: 14,
            padding: '10px 12px', border: 'none',
            background: isSelected ? '#1E2A38' : hovered ? 'rgba(0,0,0,0.06)' : 'rgba(0,0,0,0)',
            borderLeft: `2px solid ${isSelected ? '#1E2A38' : 'rgba(0,0,0,0)'}`,
            boxSizing: 'border-box',
            // Slide left only when cursor is in the right 30% zone
            transform: deleteVisible ? 'translateX(-32px)' : 'translateX(0)',
            transition: 'transform 0.2s cubic-bezier(0.16,1,0.3,1), background 0.15s ease, border-color 0.15s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%', background: dotColor, flexShrink: 0,
                  boxShadow: isRunning ? `0 0 6px ${dotColor}` : 'none',
                  animation: isRunning ? 'pulse-dot 1.8s ease-in-out infinite' : 'none',
                }} aria-hidden="true" />
                <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? '#ffffff' : 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {short}
                </span>
              </div>
              <p style={{ fontSize: 11, color: isSelected ? 'rgba(255,255,255,0.60)' : 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                {owner} · {ARTIFACT_TYPE_LABELS[job.artifact_type]}
              </p>
            </div>
            <StatusBadge status={job.status} />
          </div>
        </button>

        {/* ── Delete button — fixed on the right edge, revealed only in the right 30% zone ── */}
        <button
          type="button"
          onClick={handleDelete}
          aria-label={`Remove ${short} from list`}
          title="Remove from list"
          style={{
            position: 'absolute', right: 0, top: 0, bottom: 0,
            width: 32,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0)',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--danger)',
            opacity: deleteVisible ? 1 : 0,
            transform: deleteVisible ? 'scale(1)' : 'scale(0.7)',
            transition: 'opacity 0.15s ease, transform 0.2s cubic-bezier(0.16,1,0.3,1)',
            pointerEvents: deleteVisible ? 'auto' : 'none',
            padding: 0,
          }}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
            <path d="M1 1L9 9M9 1L1 9" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* ── Retry button — shown only when this failed job is selected ── */}
      {isFailed && isSelected && (
        <div style={{ paddingLeft: 6, paddingRight: 6, display: 'flex', flexDirection: 'column', gap: 3 }}>
          <button
            type="button"
            onClick={handleRetry}
            disabled={isRetrying}
            aria-busy={isRetrying}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
              padding: '5px 10px', borderRadius: 10, border: '1px solid var(--danger-dim)',
              background: 'var(--danger-dim)', color: 'var(--danger)',
              fontSize: 11, fontWeight: 600, cursor: isRetrying ? 'not-allowed' : 'pointer',
              opacity: isRetrying ? 0.6 : 1,
              transition: 'background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease',
              fontFamily: 'var(--font-sans)',
            }}
            onMouseEnter={e => { if (!isRetrying) e.currentTarget.style.opacity = '0.8'; }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
          >
            <RotateCcw style={{ width: 10, height: 10, flexShrink: 0, animation: isRetrying ? 'spin 0.8s linear infinite' : 'none' }} aria-hidden="true" />
            {isRetrying ? 'Retrying…' : 'Retry Job'}
          </button>
          {retryError && (
            <p style={{ fontSize: 10, color: 'var(--danger)', margin: 0, paddingLeft: 2 }}>{retryError}</p>
          )}
        </div>
      )}
    </div>
  );
});

// ── Sidebar ───────────────────────────────────────────────────────────────────
interface SidebarProps {
  jobs: Job[]; jobsLoading: boolean; jobsError: string | null;
  selectedJobId: string | null; onJobSelected: (job: Job) => void;
  onJobSubmitted: (job: Job) => void; onJobDeleted: (id: string) => void;
  onJobRetried: (newJob: Job) => void;
}

const Sidebar = React.memo(function Sidebar({ jobs, jobsLoading, jobsError, selectedJobId, onJobSelected, onJobSubmitted, onJobDeleted, onJobRetried }: SidebarProps) {
  const bdr = 'rgba(255,255,255,0.45)';
  return (
    <aside aria-label="Repository sidebar" style={{
      background: 'rgba(255,255,255,0.68)',
      backdropFilter: 'blur(40px) saturate(180%) brightness(1.03)',
      WebkitBackdropFilter: 'blur(40px) saturate(180%) brightness(1.03)',
      isolation: 'isolate',
      border: '0.5px solid rgba(255,255,255,0.88)',
      boxShadow:
        '0 8px 40px rgba(80,60,20,0.09),' +
        'inset 0 1px 0 rgba(255,255,255,0.98),' +
        'inset 0 0 0 0.5px rgba(255,255,255,0.65)',
      width: 300, minWidth: 300, maxWidth: 300,
      display: 'flex', flexDirection: 'column', borderRadius: 20, overflow: 'hidden', flexShrink: 0,
    }}>
      <div style={{ padding: '20px 18px', borderBottom: `0.5px solid ${bdr}` }}>
        <SidebarForm onJobSubmitted={onJobSubmitted} />
      </div>
      <div className="dash-scroll" style={{ flex: 1, overflowY: 'auto', padding: '16px 10px 12px' }}>
        <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10, paddingLeft: 4, fontFamily: 'var(--font-mono)' }}>Recent Jobs</p>
        {jobsLoading && <SidebarJobsSkeleton count={5} />}
        {jobsError && <p style={{ fontSize: 12, color: 'var(--danger)', padding: '8px 4px' }}>Could not load jobs</p>}
        {!jobsLoading && jobs.length === 0 && !jobsError && (
          <div style={{ textAlign: 'center', padding: '32px 16px' }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.50)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
              <Code2 style={{ width: 16, height: 16, color: 'var(--text-muted)' }} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>No jobs yet</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, opacity: 0.65 }}>Submit a URL above</p>
          </div>
        )}
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 2 }}
          initial="hidden"
          animate="visible"
          variants={{
            hidden:  {},
            visible: { transition: { staggerChildren: 0.045, delayChildren: 0.05 } },
          }}
        >
          <AnimatePresence initial={false}>
            {jobs.map(job => (
              <motion.div
                key={job.id}
                style={{ background: 'none' }}
                variants={{
                  hidden:  { opacity: 0, y: 10, scale: 0.97 },
                  visible: { opacity: 1, y: 0,  scale: 1,
                    transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] } },
                }}
                exit={{
                  opacity: 0,
                  x: -24,
                  scale: 0.95,
                  transition: { duration: 0.18, ease: [0.16, 1, 0.3, 1] },
                }}
                layout
              >
                <JobRow
                  job={job}
                  isSelected={job.id === selectedJobId}
                  onClick={() => onJobSelected(job)}
                  onDelete={onJobDeleted}
                  onRetried={onJobRetried}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      </div>
    </aside>
  );
});

// ── Animated pipeline — delegates to the full Framer Motion component ─────────
// The old inline implementation is replaced. All animation logic lives in
// src/components/pipeline/AnimatedPipeline.tsx
function AnimatedPipeline({ jobId, pipelineStatus, onCompletionEnd }: {
  jobId: string;
  pipelineStatus?: 'idle' | 'running' | 'completed' | 'failed';
  onCompletionEnd?: () => void;
}) {
  return (
    <AnimatedPipelineComponent
      jobId={jobId}
      isDark={false}
      pipelineStatus={pipelineStatus ?? 'running'}
      onCompletionEnd={onCompletionEnd}
    />
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, filter: 'blur(4px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
      style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24, padding: 48 }}
    >
      <div style={{
        width: 80, height: 80, borderRadius: '50%', flexShrink: 0,
        background: 'var(--primary-dim)',
        border: '0.5px solid rgba(255,255,255,0.60)', boxShadow: 'var(--shadow-sm)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <GitBranch style={{ width: 28, height: 28, color: 'var(--primary)' }} />
      </div>
      <div style={{ textAlign: 'center', maxWidth: 280 }}>
        <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>Select a repository</p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.7 }}>
          Paste a GitHub URL in the sidebar and click Analyze to get started
        </p>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
        {['Architecture Diagram', 'Learning Path', 'Interview Prep', 'Knowledge Graph'].map(label => (
          <span key={label} style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', padding: '5px 14px', borderRadius: 100, background: 'rgba(255,255,255,0.25)', border: '0.5px solid rgba(255,255,255,0.50)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{label}</span>
        ))}
      </div>
    </motion.div>
  );
}

// ── Panel header ──────────────────────────────────────────────────────────────
function PanelHeader({ activeJob }: { activeJob: Job }) {
  const repoName = extractShortName(activeJob.repo_url);
  const repoFull = extractRepoName(activeJob.repo_url);
  const bdr = 'rgba(255,255,255,0.45)';
  const statusIcon = {
    completed: <CheckCircle2 style={{ width: 14, height: 14, color: 'var(--success)' }} />,
    running:   <ButtonSpinner size={14} />,
    failed:    <XCircle style={{ width: 14, height: 14, color: 'var(--danger)' }} />,
    pending:   <Clock style={{ width: 14, height: 14, color: 'var(--text-muted)' }} />,
    cancelled: <XCircle style={{ width: 14, height: 14, color: 'var(--text-muted)' }} />,
  }[activeJob.status] ?? null;

  return (
    <div style={{ padding: '16px 24px', borderBottom: `0.5px solid ${bdr}`, background: 'rgba(0,0,0,0)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexShrink: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, flexShrink: 0, background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.60)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <GitBranch style={{ width: 15, height: 15, color: 'var(--primary)' }} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{repoName}</span>
            <a href={activeJob.repo_url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${repoName} on GitHub`}
              style={{ color: 'var(--text-muted)', flexShrink: 0, transition: 'color 0.2s' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
              <ExternalLink style={{ width: 12, height: 12 }} />
            </a>
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {repoFull} · {ARTIFACT_TYPE_LABELS[activeJob.artifact_type]}
          </p>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {statusIcon}
        <StatusBadge status={activeJob.status} />
      </div>
    </div>
  );
}

// ── Insights error classifier ─────────────────────────────────────────────────
function classifyInsightsError(message: string): { heading: string; detail: string } {
  const msg = message.toLowerCase();

  if (msg.includes('job not found')) {
    return {
      heading: 'Job not found',
      detail: 'This job ID does not exist. It may have been deleted or never created.',
    };
  }
  if (msg.includes('not completed') || msg.includes('status:')) {
    // Extract the raw status from the backend message e.g. "status: running"
    const match = message.match(/status[:\s]+([a-z_]+)/i);
    const status = match ? match[1] : 'unknown';
    return {
      heading: `Analysis is not complete yet (status: ${status})`,
      detail: 'Engineering insights are computed from the finished knowledge graph. Wait for the analysis to complete, then reload.',
    };
  }
  if (msg.includes('no graph data')) {
    return {
      heading: 'No graph data found for this job',
      detail: 'The analysis ran but did not produce a knowledge graph. This can happen if the repository had no parseable source files, or if the graph build step failed.',
    };
  }
  if (msg.includes('insights computation failed')) {
    // Surface the inner error from the backend message
    const inner = message.replace(/^insights computation failed[:\s]*/i, '').trim();
    return {
      heading: 'Insights computation failed',
      detail: inner || 'An error occurred while computing metrics from the graph. Check the backend logs for details.',
    };
  }
  if (msg.includes('network error') || msg.includes('econnrefused') || msg.includes('backend running')) {
    return {
      heading: 'Cannot reach the Cortex backend',
      detail: 'Make sure the backend is running on http://localhost:8000 and try again.',
    };
  }
  if (msg.includes('timeout')) {
    return {
      heading: 'Request timed out',
      detail: 'The insights request took too long. The repository may be very large. Try again — subsequent loads are cached.',
    };
  }

  // Fallback — surface whatever the server returned verbatim
  return {
    heading: 'Failed to load engineering insights',
    detail: message,
  };
}

// ── Insights tab — lazy-loaded inside the right panel ────────────────────────
const InsightsTab = React.memo(function InsightsTab({ jobId }: { jobId: string }) {
  const { report, isLoading, error, refetch } = useInsights(jobId);

  if (isLoading) {
    return <InsightsSkeleton />;
  }

  if (error) {
    const { heading, detail } = classifyInsightsError(error);
    return (
      <div style={{
        padding: '20px 24px', borderRadius: 'var(--radius-md)',
        background: 'var(--danger-dim)', border: '1px solid rgba(239,83,80,0.22)',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--danger)', margin: 0 }}>
          {heading}
        </p>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
          {detail}
        </p>
        <button
          onClick={refetch}
          style={{
            alignSelf: 'flex-start', marginTop: 4,
            padding: '5px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600,
            background: 'transparent', border: '1px solid var(--border)',
            color: 'var(--text-muted)', cursor: 'pointer',
            transition: 'color 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text)'; e.currentTarget.style.borderColor = 'var(--border-hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!report) return null;

  return <InsightsDashboard report={report} isDark={false} />;
});

// ── Right panel ───────────────────────────────────────────────────────────────
interface RightPanelProps {
  activeJob: Job | null;
  artifacts: ReturnType<typeof useArtifact>['artifacts'];
  artifactsLoading: boolean; artifactsError: string | null;
  onJobRetried: (newJob: Job) => void;
}

const RightPanel = React.memo(function RightPanel({ activeJob, artifacts, artifactsLoading, artifactsError, onJobRetried }: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<'artifact' | 'insights'>('artifact');
  const { retriedJob, isRetrying, error: retryError, retry } = useRetryJob();

  React.useEffect(() => {
    if (retriedJob) onJobRetried(retriedJob);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retriedJob]);

  React.useEffect(() => {
    setActiveTab('artifact');
  }, [activeJob?.id]);

  if (!activeJob) return <EmptyState />;

  const bdr = 'rgba(255,255,255,0.45)';
  const isCompleted = activeJob.status === 'completed';

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
      <PanelHeader activeJob={activeJob} />

      {/* Tab bar — only show when job is completed */}
      {isCompleted && (
        <div style={{
          display: 'flex', gap: 2, padding: '0 24px',
          borderBottom: `0.5px solid ${bdr}`,
          background: 'rgba(0,0,0,0)',
          flexShrink: 0,
        }}>
          {(['artifact', 'insights'] as const).map(tab => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  position: 'relative',
                  padding: '10px 18px',
                  fontSize: 12, fontWeight: isActive ? 700 : 500,
                  color: isActive ? 'var(--primary)' : 'var(--text-muted)',
                  background: 'rgba(0,0,0,0)', border: 'none', cursor: 'pointer',
                  marginBottom: -1,
                  transition: 'color 0.15s',
                  letterSpacing: '0.02em', fontFamily: 'var(--font-sans)',
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = 'var(--text)'; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = 'var(--text-muted)'; }}
              >
                {tab === 'artifact' ? '📄 Artifact' : '📊 Engineering Insights'}
                {/* Spring-animated active underline indicator */}
                {isActive && (
                  <motion.span
                    layoutId="dash-tab-indicator"
                    style={{
                      position: 'absolute', bottom: -1, left: 0, right: 0,
                      height: 2, borderRadius: 1,
                      background: 'var(--primary)',
                    }}
                    transition={{ type: 'spring', stiffness: 260, damping: 26, mass: 1 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}

      <div className="dash-scroll" style={{ flex: 1, overflowY: 'auto', padding: 24 }}>

        {/* Pending */}
        {activeJob.status === 'pending' && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
            <InlineLoader stage="connecting" message="Queued — Waiting for Worker…" size={36} />
          </div>
        )}

        {/* Running */}
        {activeJob.status === 'running' && artifacts.length === 0 && (
          <AnimatedPipeline jobId={activeJob.id} pipelineStatus="running" />
        )}

        {/* Failed — show pipeline frozen at failure point */}
        {activeJob.status === 'failed' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <AnimatedPipeline jobId={activeJob.id} pipelineStatus="failed" />

            {/* Error message from backend */}
            {activeJob.error_message && (
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '12px 16px', borderRadius: 'var(--radius-sm)',
                background: 'var(--danger-dim)', border: '1px solid rgba(239,83,80,0.22)',
              }}>
                <AlertCircle style={{ width: 14, height: 14, color: 'var(--danger)', flexShrink: 0, marginTop: 1 }} />
                <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0, fontFamily: 'var(--font-mono)', lineHeight: 1.6 }}>
                  {activeJob.error_message}
                </p>
              </div>
            )}

            {/* Retry button */}
            <button
              type="button"
              onClick={() => retry(activeJob.id)}
              disabled={isRetrying}
              aria-busy={isRetrying}
              style={{
                alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 7,
                padding: '9px 20px', borderRadius: 12, border: '1px solid var(--danger-dim)',
                background: 'var(--danger-dim)', color: 'var(--danger)',
                fontSize: 13, fontWeight: 600, cursor: isRetrying ? 'not-allowed' : 'pointer',
                opacity: isRetrying ? 0.6 : 1,
                transition: 'background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease',
                fontFamily: 'var(--font-sans)',
              }}
              onMouseEnter={e => { if (!isRetrying) e.currentTarget.style.opacity = '0.75'; }}
              onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
            >
              <RotateCcw style={{ width: 13, height: 13, flexShrink: 0, animation: isRetrying ? 'spin 0.8s linear infinite' : 'none' }} aria-hidden="true" />
              {isRetrying ? 'Retrying…' : 'Retry Job'}
            </button>
            {retryError && (
              <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0 }}>{retryError}</p>
            )}
          </div>
        )}

        {/* Cancelled */}
        {activeJob.status === 'cancelled' && (
          <p style={{ textAlign: 'center', padding: '48px 0', fontSize: 13, color: 'var(--text-muted)' }}>Job was cancelled.</p>
        )}

        {/* Artifacts loading */}
        {artifactsLoading && <ArtifactSkeleton />}

        {/* Error */}
        {artifactsError && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-dim)', border: '1px solid rgba(239,83,80,0.22)' }}>
            <AlertCircle style={{ width: 14, height: 14, color: 'var(--danger)', flexShrink: 0 }} />
            <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0 }}>{artifactsError}</p>
          </div>
        )}

        {!artifactsLoading && activeJob.status === 'completed' && artifacts.length === 0 && (
          <p style={{ textAlign: 'center', padding: '48px 0', fontSize: 13, color: 'var(--text-muted)' }}>No artifacts generated yet.</p>
        )}

        {/* Artifact cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 6, scale: 0.99 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.99 }}
              transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
              style={{ display: 'flex', flexDirection: 'column', gap: 20 }}
            >
              {activeTab === 'insights' && isCompleted ? (
                <InsightsTab jobId={activeJob.id} />
              ) : (
                artifacts.map(artifact => (
                  <div key={artifact.id} style={{
                    borderRadius: 'var(--radius-lg)', overflow: 'hidden',
                    background: 'rgba(255,255,255,0.30)',
                    border: `0.5px solid rgba(255,255,255,0.50)`,
                    boxShadow: '0 2px 8px rgba(80,60,20,0.06), inset 0 1px 3px rgba(255,255,255,0.60)',
                    transition: 'background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
                  }}>
                    <div style={{ padding: '12px 18px', borderBottom: `0.5px solid rgba(255,255,255,0.45)`, background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--primary)', padding: '3px 10px', borderRadius: 100, background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.60)', fontFamily: 'var(--font-mono)' }}>
                        {artifact.content_type}
                      </span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {artifact.id}
                      </span>
                    </div>
                    <div style={{ padding: '16px 18px' }}>
                      <ArtifactViewer artifact={artifact} />
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
});

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [hiddenJobIds, setHiddenJobIds] = useState<Set<string>>(new Set());
  const [initialLoading, setInitialLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Initial jobs fetch — serve from session cache first to avoid blank sidebar
  React.useEffect(() => {
    const cached = sessionCache.get<Job[]>(cacheKey.jobsList());
    if (cached) {
      setJobs(cached);
      setJobsLoading(false);
      setInitialLoading(false);
      // Still refresh in background
    }

    let active = true;
    setJobsLoading(prev => cached ? false : prev);
    listJobs()
      .then(data => {
        if (active) {
          setJobs(data);
          sessionCache.set(cacheKey.jobsList(), data, TTL.JOBS_LIST);
        }
      })
      .catch(err => { if (active) setJobsError(err instanceof Error ? err.message : 'Failed'); })
      .finally(() => {
        if (active) {
          setJobsLoading(false);
          setInitialLoading(false);
        }
      });
    return () => { active = false; };
  }, []);

  const { job: polledJob } = useJobPolling(selectedJob?.id ?? null);
  const activeJob = polledJob ?? selectedJob;

  // Keep the sidebar list in sync with live poll results —
  // only patch when something actually changed (status or updated_at).
  // Without this guard, every 3-second poll fires setJobs even when the
  // job is completed/unchanged, re-rendering the entire Sidebar tree.
  const polledJobRef = useRef<{ id: string; status: string; updated_at?: string } | null>(null)
  useEffect(() => {
    if (!polledJob) return
    const prev = polledJobRef.current
    if (
      prev &&
      prev.id === polledJob.id &&
      prev.status === polledJob.status &&
      prev.updated_at === polledJob.updated_at
    ) return  // nothing changed — skip the re-render
    polledJobRef.current = { id: polledJob.id, status: polledJob.status, updated_at: polledJob.updated_at }
    setJobs(prev =>
      prev.map(j => j.id === polledJob.id ? { ...j, ...polledJob } : j)
    )
  }, [polledJob])

  const { artifacts, isLoading: artifactsLoading, error: artifactsError, refetch } = useArtifact(
    activeJob?.status === 'completed' ? (selectedJob?.id ?? null) : null
  );

  const completedJobRef = useRef<string | null>(null);
  useEffect(() => {
    if (!polledJob || polledJob.status !== 'completed') return;
    if (completedJobRef.current === polledJob.id) return;
    completedJobRef.current = polledJob.id;
    refetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [polledJob?.id, polledJob?.status, refetch]);

  const handleJobSubmitted = useCallback((job: Job) => {
    setJobs(prev => [job, ...prev]);
    setSelectedJob(job);
  }, []);

  const handleJobSelected = useCallback((job: Job) => { setSelectedJob(job); }, []);

  const handleJobDeleted = useCallback((id: string) => {
    // Optimistically remove from UI immediately
    setHiddenJobIds(prev => new Set([...prev, id]));
    setSelectedJob(prev => prev?.id === id ? null : prev);
    // Fire-and-forget real DB delete — if it fails the job reappears on refresh
    // which is acceptable; the optimistic removal already gave instant feedback
    deleteJob(id).catch(() => {
      // Restore if delete failed
      setHiddenJobIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    });
  }, []);

  // Show full-screen loader until: (a) client is hydrated AND (b) first data fetch done.
  // This replaces the blank flash — the loader stays until the dashboard is ready to paint.
  if (!mounted || initialLoading) {
    return (
      <div
        aria-live="polite"
        aria-busy="true"
        style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--bg)',
        }}
      >
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20,
          padding: '36px 32px',
          background: 'rgba(255,255,255,0.78)',
          border: '0.5px solid rgba(255,255,255,0.92)',
          boxShadow:
            '0 16px 60px rgba(80,60,20,0.10),' +
            'inset 0 1px 0 rgba(255,255,255,0.98),' +
            'inset 0 0 0 0.5px rgba(255,255,255,0.70)',
          backdropFilter: 'blur(40px) saturate(200%)',
          WebkitBackdropFilter: 'blur(40px) saturate(200%)',
          minWidth: 260, maxWidth: 360,
          borderRadius: 26,
        }}>
          {/* Cortex icon */}
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: 'var(--primary-dim)',
            border: '0.5px solid rgba(255,255,255,0.65)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="var(--primary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          {/* Text */}
          <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{
              fontFamily: 'var(--font-display, Syne, sans-serif)',
              fontSize: 15, fontWeight: 700, letterSpacing: '-0.03em',
              color: 'var(--text)',
            }}>Cortex</span>
            <span style={{
              fontFamily: 'var(--font-mono, "JetBrains Mono", monospace)',
              fontSize: 11, letterSpacing: '0.07em',
              color: 'var(--text-muted)', textTransform: 'uppercase' as const,
            }}>Loading Dashboard…</span>
          </div>
          {/* Indeterminate bar */}
          <div style={{
            width: '100%', height: 2, borderRadius: 9999,
            background: 'var(--border)', overflow: 'hidden', position: 'relative',
          }}>
            <div style={{
              position: 'absolute', top: 0, left: 0, height: '100%', width: '40%',
              borderRadius: 9999,
              background: 'var(--primary)',
              opacity: 0.7,
              animation: 'cortex-bar-sweep 1.8s cubic-bezier(0.4,0,0.2,1) infinite',
            }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={{ position: 'fixed', inset: 0, zIndex: 1, display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
        <DashboardNavbar />

        <div style={{ flex: 1, display: 'flex', paddingTop: 80, paddingBottom: 20, paddingLeft: 20, paddingRight: 20, gap: 16, overflow: 'hidden', boxSizing: 'border-box' }}>
          {/* Sidebar */}
          <div className="dash-scroll" style={{ display: 'flex', flexDirection: 'column', flexShrink: 0, overflowY: 'auto', overflowX: 'clip', height: '100%' }}>
            <Sidebar
              jobs={jobs.filter(j => !hiddenJobIds.has(j.id))}
              jobsLoading={jobsLoading}
              jobsError={jobsError}
              selectedJobId={selectedJob?.id ?? null}
              onJobSelected={handleJobSelected}
              onJobSubmitted={handleJobSubmitted}
              onJobDeleted={handleJobDeleted}
              onJobRetried={handleJobSubmitted}
            />
          </div>

          {/* Main glass panel */}
          <main className="dash-content" style={{
            background: 'rgba(255,255,255,0.68)',
            backdropFilter: 'blur(40px) saturate(180%) brightness(1.03)',
            WebkitBackdropFilter: 'blur(40px) saturate(180%) brightness(1.03)',
            isolation: 'isolate',
            border: '0.5px solid rgba(255,255,255,0.88)',
            boxShadow:
              '0 8px 40px rgba(80,60,20,0.09),' +
              'inset 0 1px 0 rgba(255,255,255,0.98),' +
              'inset 0 0 0 0.5px rgba(255,255,255,0.65)',
            flex: 1, borderRadius: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0,
          }}>
            <RightPanel activeJob={activeJob}
              artifacts={artifacts} artifactsLoading={artifactsLoading} artifactsError={artifactsError}
              onJobRetried={handleJobSubmitted} />
          </main>
        </div>
      </div>
    </>
  );
}
