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
import StatusBadge from '@/components/shared/StatusBadge';
import { listJobs } from '@/lib/api/jobs.api';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { InlineLoader } from '@/components/shared/BrandedLoader';
import {
  Github, ChevronDown, Sparkles, Code2, LayoutDashboard,
  GitBranch, ExternalLink, Clock, AlertCircle, CheckCircle2,
  Loader2, XCircle, ArrowLeft, Sun, Moon,
  Cpu, Database, FileCode, Check,
} from 'lucide-react';
import * as Select from '@radix-ui/react-select';
import Link from 'next/link';
import dynamic from 'next/dynamic';

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
];
const GITHUB_URL_RE = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

function extractRepoName(url: string) {
  return url.replace(/\/$/, '').split('/').slice(-2).join('/');
}
function extractShortName(url: string) {
  return url.replace(/\/$/, '').split('/').pop() ?? url;
}

// ── Theme boot ────────────────────────────────────────────────────────────────
function getInitialTheme(): boolean {
  if (typeof window === 'undefined') return true;
  try { const s = localStorage.getItem('cortex-theme'); return s ? s === 'dark' : true; }
  catch { return true; }
}

// ── Theme-aware surface helpers ───────────────────────────────────────────────
// Returns a thin surface tint that reads correctly in both themes.
// Dark = white veil  /  Light = black veil
function tint(d: boolean, s: 'xs' | 'sm' | 'md' = 'sm'): string {
  const dk = { xs: 'rgba(255,255,255,0.025)', sm: 'rgba(255,255,255,0.05)', md: 'rgba(255,255,255,0.09)' };
  const lt = { xs: 'rgba(0,0,0,0.025)',       sm: 'rgba(0,0,0,0.04)',       md: 'rgba(0,0,0,0.07)'      };
  return d ? dk[s] : lt[s];
}
function tintBorder(d: boolean) { return d ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.09)'; }
function hoverBg(d: boolean)    { return d ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.05)'; }
function selectedBg(d: boolean) { return d ? 'rgba(0,229,168,0.08)'   : 'rgba(0,179,122,0.10)'; }
function rowHoverBg(d: boolean) { return d ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'; }
function logBg(d: boolean)      { return d ? 'rgba(0,0,0,0.35)'       : 'rgba(0,0,0,0.04)'; }
function logDimLine(d: boolean) { return d ? 'rgba(255,255,255,0.32)' : 'rgba(0,0,0,0.35)'; }

// ── Dashboard background ──────────────────────────────────────────────────────
function DashboardBackground({ isDark }: { isDark: boolean }) {
  return (
    <div aria-hidden="true" style={{
      position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
      background: isDark
        ? `radial-gradient(ellipse 70% 45% at 75% -5%, rgba(108,124,255,0.10) 0%, transparent 55%),
           radial-gradient(ellipse 55% 40% at 5% 100%, rgba(0,229,168,0.06) 0%, transparent 50%),
           var(--bg)`
        : `radial-gradient(ellipse 70% 45% at 75% -5%, rgba(93,107,255,0.05) 0%, transparent 55%),
           radial-gradient(ellipse 55% 40% at 5% 100%, rgba(0,179,122,0.04) 0%, transparent 50%),
           var(--bg)`,
    }} />
  );
}

// ── Navbar ────────────────────────────────────────────────────────────────────
interface NavbarProps { isDark: boolean; onToggleTheme: () => void }

function DashboardNavbar({ isDark, onToggleTheme }: NavbarProps) {
  const hov = hoverBg(isDark);
  const bdr = tintBorder(isDark);
  return (
    <header style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
      display: 'flex', justifyContent: 'center', padding: '14px 24px', pointerEvents: 'none',
    }}>
      <nav aria-label="Dashboard navigation" style={{
        pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 4,
        padding: '7px 10px', borderRadius: 24, width: '100%', maxWidth: 960,
        background: 'var(--glass)',
        backdropFilter: 'blur(40px) saturate(220%)', WebkitBackdropFilter: 'blur(40px) saturate(220%)',
        border: `1px solid ${bdr}`,
        boxShadow: isDark
          ? 'var(--shadow-xl), inset 0 1px 0 rgba(255,255,255,0.07)'
          : 'var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.80)',
        transition: 'background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
      }}>
        {/* Logo */}
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 12px', borderRadius: 16, textDecoration: 'none', flexShrink: 0, transition: 'background 0.2s ease' }}
          onMouseEnter={e => (e.currentTarget.style.background = hov)}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
          <span style={{ width: 24, height: 24, borderRadius: 7, flexShrink: 0, background: 'var(--primary-dim)', border: '1px solid rgba(0,229,168,0.28)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <LayoutDashboard style={{ width: 12, height: 12, color: 'var(--primary)' }} />
          </span>
          <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text)', fontFamily: 'var(--font-sans)' }}>Cortex</span>
        </Link>
        {/* Center pill */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', background: tint(isDark, 'xs'), border: `1px solid ${bdr}`, borderRadius: 100, padding: '4px 14px' }}>Dashboard</span>
        </div>
        {/* Right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <Link href="/" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', padding: '6px 14px', borderRadius: 14, textDecoration: 'none', transition: 'all 0.2s ease', display: 'flex', alignItems: 'center', gap: 6 }}
            onMouseEnter={e => { e.currentTarget.style.background = hov; e.currentTarget.style.color = 'var(--text)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
            <ArrowLeft style={{ width: 13, height: 13 }} /> Home
          </Link>
          <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', padding: '6px 14px', borderRadius: 14, textDecoration: 'none', transition: 'all 0.2s ease' }}
            onMouseEnter={e => { e.currentTarget.style.background = hov; e.currentTarget.style.color = 'var(--text)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
            GitHub
          </a>
          <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 4px' }} />
          <button onClick={onToggleTheme} aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            style={{ width: 36, height: 36, borderRadius: 12, background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', transition: 'all 0.2s ease' }}
            onMouseEnter={e => { e.currentTarget.style.background = hov; e.currentTarget.style.color = 'var(--primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
            {isDark ? <Sun style={{ width: 16, height: 16 }} /> : <Moon style={{ width: 16, height: 16 }} />}
          </button>
        </div>
      </nav>
    </header>
  );
}

// ── Sidebar submit form ───────────────────────────────────────────────────────
interface SidebarFormProps { isDark: boolean; onJobSubmitted: (job: Job) => void }

function SidebarForm({ isDark, onJobSubmitted }: SidebarFormProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [artifactType, setArtifactType] = useState<ArtifactType>('architecture_diagram');
  const [urlError, setUrlError] = useState<string | null>(null);
  const { isSubmitting, error: apiError, submitJob, submittedJob } = useSubmitJob();

  React.useEffect(() => {
    if (submittedJob) { onJobSubmitted(submittedJob); setRepoUrl(''); setArtifactType('architecture_diagram'); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedJob]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setUrlError(null);
    const t = repoUrl.trim();
    if (!t) { setUrlError('Enter a GitHub URL'); return; }
    if (!GITHUB_URL_RE.test(t)) { setUrlError('Must be https://github.com/owner/repo'); return; }
    await submitJob({ repo_url: t, artifact_type: artifactType });
  };

  const bdr = tintBorder(isDark);
  const inputStyle: React.CSSProperties = {
    width: '100%', borderRadius: 14, padding: '10px 12px', fontSize: 13,
    background: tint(isDark, 'xs'), color: 'var(--text)',
    border: `1px solid ${bdr}`, outline: 'none',
    transition: 'border-color 0.2s ease, box-shadow 0.2s ease, background 0.3s ease',
    fontFamily: 'var(--font-sans)', boxSizing: 'border-box' as const,
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
        <Select.Trigger aria-label="Artifact type"
          style={{ ...inputStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', userSelect: 'none' }}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--primary-dim)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = bdr; e.currentTarget.style.boxShadow = 'none'; }}>
          <Select.Value />
          <Select.Icon asChild><ChevronDown style={{ width: 14, height: 14, color: 'var(--text-muted)', flexShrink: 0 }} /></Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content position="popper" sideOffset={6} style={{
            width: 'var(--radix-select-trigger-width)', background: 'var(--surface)',
            border: `1px solid ${bdr}`, borderRadius: 14,
            boxShadow: isDark ? 'var(--shadow-lg)' : '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)',
            backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
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
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = hoverBg(isDark); (e.currentTarget as HTMLElement).style.color = 'var(--text)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
                  onFocus={e => { (e.currentTarget as HTMLElement).style.background = hoverBg(isDark); (e.currentTarget as HTMLElement).style.color = 'var(--text)'; }}
                  onBlur={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
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
        background: 'linear-gradient(135deg, var(--primary) 0%, #00c9a7 100%)',
        color: '#07090d', border: 'none',
        boxShadow: '0 4px 16px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)',
        transition: 'filter 0.2s ease, opacity 0.2s ease', fontFamily: 'var(--font-sans)',
      }}
        onMouseEnter={e => { if (!isSubmitting && repoUrl.trim()) e.currentTarget.style.filter = 'brightness(1.08)'; }}
        onMouseLeave={e => { e.currentTarget.style.filter = ''; }}>
        {isSubmitting
          ? <><Loader2 style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} />Analyzing…</>
          : <><Sparkles style={{ width: 13, height: 13 }} />Analyze Repository</>}
      </button>
    </form>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────
interface JobRowProps { job: Job; isSelected: boolean; isDark: boolean; onClick: () => void }

const JobRow = React.memo(function JobRow({ job, isSelected, isDark, onClick }: JobRowProps) {
  const short = extractShortName(job.repo_url);
  const owner = extractRepoName(job.repo_url).split('/')[0] ?? '';
  const isRunning = job.status === 'running';
  const dot: Record<string, string> = {
    completed: 'var(--success)', running: 'var(--primary)',
    failed: 'var(--danger)', pending: 'var(--text-muted)', cancelled: 'var(--text-muted)',
  };
  const dotColor = dot[job.status] ?? 'var(--text-muted)';
  return (
    <button type="button" onClick={onClick} aria-pressed={isSelected}
      aria-label={`Job: ${short}, status: ${job.status}`}
      style={{
        width: '100%', textAlign: 'left', cursor: 'pointer', borderRadius: 14, padding: '10px 12px',
        border: 'none', background: isSelected ? selectedBg(isDark) : 'transparent',
        borderLeft: `2px solid ${isSelected ? 'var(--primary)' : 'transparent'}`,
        transition: 'background 0.2s ease, border-color 0.2s ease', boxSizing: 'border-box',
      }}
      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = rowHoverBg(isDark); }}
      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: dotColor, flexShrink: 0,
              boxShadow: isRunning ? `0 0 6px ${dotColor}` : 'none',
              animation: isRunning ? 'pulse-dot 1.8s ease-in-out infinite' : 'none',
            }} aria-hidden="true" />
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{short}</span>
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
            {owner} · {ARTIFACT_TYPE_LABELS[job.artifact_type]}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>
    </button>
  );
});

// ── Sidebar ───────────────────────────────────────────────────────────────────
interface SidebarProps {
  isDark: boolean; jobs: Job[]; jobsLoading: boolean; jobsError: string | null;
  selectedJobId: string | null; onJobSelected: (job: Job) => void; onJobSubmitted: (job: Job) => void;
}

function Sidebar({ isDark, jobs, jobsLoading, jobsError, selectedJobId, onJobSelected, onJobSubmitted }: SidebarProps) {
  const bdr = tintBorder(isDark);
  return (
    <aside aria-label="Repository sidebar" style={{
      background: 'var(--glass)', backdropFilter: 'blur(24px) saturate(180%)', WebkitBackdropFilter: 'blur(24px) saturate(180%)',
      border: `1px solid ${bdr}`,
      boxShadow: isDark ? 'var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.06)' : 'var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.80)',
      width: 300, minWidth: 300, maxWidth: 300,
      display: 'flex', flexDirection: 'column', borderRadius: 20, overflow: 'hidden', flexShrink: 0,
      transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
    }}>
      <div style={{ padding: '20px 18px', borderBottom: `1px solid ${bdr}` }}>
        <SidebarForm isDark={isDark} onJobSubmitted={onJobSubmitted} />
      </div>
      <div className="dash-scroll" style={{ flex: 1, overflowY: 'auto', padding: '16px 10px 12px' }}>
        <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10, paddingLeft: 4, fontFamily: 'var(--font-mono)' }}>Recent Jobs</p>
        {jobsLoading && <InlineLoader stage="loading" message="Loading Jobs…" size={24} />}
        {jobsError && <p style={{ fontSize: 12, color: 'var(--danger)', padding: '8px 4px' }}>Could not load jobs</p>}
        {!jobsLoading && jobs.length === 0 && !jobsError && (
          <div style={{ textAlign: 'center', padding: '32px 16px' }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: tint(isDark, 'xs'), border: `1px solid ${bdr}`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
              <Code2 style={{ width: 16, height: 16, color: 'var(--text-muted)' }} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>No jobs yet</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, opacity: 0.65 }}>Submit a URL above</p>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {jobs.map(job => (
            <JobRow key={job.id} job={job} isDark={isDark} isSelected={job.id === selectedJobId} onClick={() => onJobSelected(job)} />
          ))}
        </div>
      </div>
    </aside>
  );
}

// ── Animated pipeline (running state) ────────────────────────────────────────
const PIPELINE_STEPS = [
  { icon: GitBranch, label: 'Clone Repo', key: 'clone'    },
  { icon: Cpu,       label: 'Parse AST',  key: 'parse'    },
  { icon: Database,  label: 'Build Graph',key: 'graph'    },
  { icon: FileCode,  label: 'Generate',   key: 'generate' },
];
const LOG_LINES = ['Cloning repository…', 'Parsing AST nodes…', 'Writing graph nodes…', 'Generating artifact…'];

function AnimatedPipeline({ jobId, isDark }: { jobId: string; isDark: boolean }) {
  const [activeStep, setActiveStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    startRef.current = Date.now();
    const st = setInterval(() => { if (document.visibilityState !== 'hidden') setActiveStep(s => (s + 1) % PIPELINE_STEPS.length); }, 3000);
    const et = setInterval(() => { if (document.visibilityState !== 'hidden') setElapsed(Math.floor((Date.now() - startRef.current) / 1000)); }, 1000);
    return () => { clearInterval(st); clearInterval(et); };
  }, [jobId]);

  const bdr = tintBorder(isDark);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28, padding: '32px 24px', alignItems: 'center' }}>
      {/* Status pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px', borderRadius: 100, background: 'var(--primary-dim)', border: '1px solid rgba(0,229,168,0.28)' }}>
        <Loader2 style={{ width: 14, height: 14, color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
        <span style={{ fontSize: 13, color: 'var(--primary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
          Analyzing repository · {elapsed}s elapsed
        </span>
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center', gap: 0 }}>
        {PIPELINE_STEPS.map((step, i) => {
          const Icon = step.icon;
          const isDone = i < activeStep, isCurrent = i === activeStep;
          return (
            <React.Fragment key={step.key}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, transition: 'all 0.35s cubic-bezier(0.16,1,0.3,1)' }}>
                <div style={{
                  width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: (isDone || isCurrent) ? 'var(--primary-dim)' : tint(isDark, 'xs'),
                  border: `1px solid ${(isDone || isCurrent) ? 'rgba(0,229,168,0.35)' : bdr}`,
                  boxShadow: isCurrent ? '0 0 16px var(--primary-glow)' : 'none',
                  transform: isCurrent ? 'scale(1.12)' : 'scale(1)',
                  transition: 'all 0.35s cubic-bezier(0.16,1,0.3,1)',
                }}>
                  {isDone
                    ? <CheckCircle2 style={{ width: 18, height: 18, color: 'var(--primary)' }} />
                    : <Icon style={{ width: 18, height: 18, color: isCurrent ? 'var(--primary)' : 'var(--text-muted)', animation: isCurrent ? 'pulse-dot 1.8s ease-in-out infinite' : 'none' }} />}
                </div>
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', whiteSpace: 'nowrap', color: (isDone || isCurrent) ? 'var(--text)' : 'var(--text-muted)', fontFamily: 'var(--font-mono)', transition: 'color 0.3s ease' }}>
                  {step.label}
                </span>
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div style={{ width: 40, height: 2, margin: '0 4px', marginBottom: 20, borderRadius: 1, background: i < activeStep ? 'linear-gradient(90deg, var(--primary), rgba(0,229,168,0.3))' : bdr, transition: 'background 0.5s ease' }} aria-hidden="true" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Terminal log — fully theme-aware */}
      <div style={{
        width: '100%', maxWidth: 480,
        background: logBg(isDark), border: `1px solid ${bdr}`,
        borderRadius: 'var(--radius-md)', padding: '14px 18px',
        fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 2, color: 'var(--text-muted)',
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}>
        {LOG_LINES.slice(0, activeStep + 1).map((line, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: i < activeStep ? 'var(--success)' : 'var(--primary)', fontSize: 10 }}>{i < activeStep ? '✓' : '›'}</span>
            <span style={{ color: i < activeStep ? logDimLine(isDark) : 'var(--text-secondary)' }}>{line}</span>
          </div>
        ))}
        <span style={{ display: 'inline-block', width: 7, height: 13, background: 'var(--primary)', verticalAlign: 'middle', animation: 'blink 1s step-end infinite', marginLeft: 4 }} aria-hidden="true" />
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', margin: 0 }}>
        This usually takes 30–60 seconds
      </p>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState({ isDark }: { isDark: boolean }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24, padding: 48 }}>
      <div style={{
        width: 80, height: 80, borderRadius: '50%', flexShrink: 0,
        background: isDark
          ? 'radial-gradient(circle at 35% 35%, var(--primary-dim) 0%, rgba(108,124,255,0.06) 60%, transparent 100%)'
          : 'radial-gradient(circle at 35% 35%, rgba(0,179,122,0.12) 0%, rgba(93,107,255,0.06) 60%, transparent 100%)',
        border: '1px solid rgba(0,229,168,0.18)', boxShadow: '0 0 40px var(--primary-glow)',
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
          <span key={label} style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', padding: '5px 14px', borderRadius: 100, background: tint(isDark, 'xs'), border: `1px solid ${tintBorder(isDark)}`, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{label}</span>
        ))}
      </div>
    </div>
  );
}

// ── Panel header ──────────────────────────────────────────────────────────────
function PanelHeader({ activeJob, isDark }: { activeJob: Job; isDark: boolean }) {
  const repoName = extractShortName(activeJob.repo_url);
  const repoFull = extractRepoName(activeJob.repo_url);
  const bdr = tintBorder(isDark);
  const statusIcon = {
    completed: <CheckCircle2 style={{ width: 14, height: 14, color: 'var(--success)' }} />,
    running:   <Loader2 style={{ width: 14, height: 14, color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />,
    failed:    <XCircle style={{ width: 14, height: 14, color: 'var(--danger)' }} />,
    pending:   <Clock style={{ width: 14, height: 14, color: 'var(--text-muted)' }} />,
    cancelled: <XCircle style={{ width: 14, height: 14, color: 'var(--text-muted)' }} />,
  }[activeJob.status] ?? null;

  return (
    <div style={{ padding: '16px 24px', borderBottom: `1px solid ${bdr}`, background: tint(isDark, 'xs'), display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexShrink: 0, transition: 'background 0.3s ease, border-color 0.3s ease' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, flexShrink: 0, background: 'var(--primary-dim)', border: '1px solid rgba(0,229,168,0.22)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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

// ── Right panel ───────────────────────────────────────────────────────────────
interface RightPanelProps {
  isDark: boolean; activeJob: Job | null;
  artifacts: ReturnType<typeof useArtifact>['artifacts'];
  artifactsLoading: boolean; artifactsError: string | null;
}

function RightPanel({ isDark, activeJob, artifacts, artifactsLoading, artifactsError }: RightPanelProps) {
  if (!activeJob) return <EmptyState isDark={isDark} />;
  const bdr = tintBorder(isDark);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
      <PanelHeader activeJob={activeJob} isDark={isDark} />
      <div className="dash-scroll" style={{ flex: 1, overflowY: 'auto', padding: 24 }}>

        {/* Pending */}
        {activeJob.status === 'pending' && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
            <InlineLoader stage="connecting" message="Queued — Waiting for Worker…" size={36} />
          </div>
        )}

        {/* Running */}
        {activeJob.status === 'running' && artifacts.length === 0 && (
          <AnimatedPipeline jobId={activeJob.id} isDark={isDark} />
        )}

        {/* Failed */}
        {activeJob.status === 'failed' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '48px 0', textAlign: 'center' }}>
            <div style={{ width: 52, height: 52, borderRadius: 16, background: 'var(--danger-dim)', border: '1px solid rgba(239,83,80,0.22)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <XCircle style={{ width: 22, height: 22, color: 'var(--danger)' }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--danger)', margin: 0 }}>Analysis failed</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>Check backend logs for details</p>
          </div>
        )}

        {/* Cancelled */}
        {activeJob.status === 'cancelled' && (
          <p style={{ textAlign: 'center', padding: '48px 0', fontSize: 13, color: 'var(--text-muted)' }}>Job was cancelled.</p>
        )}

        {/* Artifacts loading */}
        {artifactsLoading && (
          <InlineLoader stage="generating_artifact" message="Loading Artifacts…" size={32} />
        )}

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
          {artifacts.map(artifact => (
            <div key={artifact.id} style={{
              borderRadius: 'var(--radius-lg)', overflow: 'hidden',
              background: tint(isDark, 'xs'), border: `1px solid ${bdr}`,
              boxShadow: isDark ? 'var(--shadow-md)' : '0 2px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
              transition: 'background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
            }}>
              <div style={{ padding: '12px 18px', borderBottom: `1px solid ${bdr}`, background: tint(isDark, 'xs'), display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--primary)', padding: '3px 10px', borderRadius: 100, background: 'var(--primary-dim)', border: '1px solid rgba(0,229,168,0.22)', fontFamily: 'var(--font-mono)' }}>
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
  const [isDark, setIsDark] = useState(getInitialTheme);

  // Sync theme to DOM — runs synchronously on first render via getInitialTheme to avoid flash
  React.useEffect(() => {
    const theme = isDark ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.toggle('dark', isDark);
    try { localStorage.setItem('cortex-theme', theme); } catch {}
  }, [isDark]);

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

  const { job: polledJob } = useJobPolling(selectedJob?.id ?? null);
  const activeJob = polledJob ?? selectedJob;

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

  return (
    <>
      <style>{`
        @keyframes spin      { to { transform: rotate(360deg); } }
        @keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.6;transform:scale(.85)} }
        @keyframes blink     { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes dash-select-in { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }

        .dash-scroll::-webkit-scrollbar       { width: 4px; }
        .dash-scroll::-webkit-scrollbar-track { background: transparent; }
        .dash-scroll::-webkit-scrollbar-thumb { background: rgba(128,128,128,0.18); border-radius: 4px; }
        .dash-scroll::-webkit-scrollbar-thumb:hover { background: rgba(128,128,128,0.30); }

        /* pre/code in artifact viewer */
        .dash-content pre { border-color: var(--border) !important; color: var(--text-secondary) !important; }
        [data-theme="dark"]  .dash-content pre { background: rgba(0,0,0,0.38) !important; }
        [data-theme="light"] .dash-content pre { background: rgba(0,0,0,0.04) !important; border-color: rgba(0,0,0,0.09) !important; }
        .react-flow__attribution { display: none; }
      `}</style>

      <DashboardBackground isDark={isDark} />

      <div style={{ position: 'fixed', inset: 0, zIndex: 1, display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
        <DashboardNavbar isDark={isDark} onToggleTheme={() => setIsDark(d => !d)} />

        <div style={{ flex: 1, display: 'flex', paddingTop: 80, paddingBottom: 20, paddingLeft: 20, paddingRight: 20, gap: 16, overflow: 'hidden', boxSizing: 'border-box' }}>
          {/* Sidebar */}
          <div className="dash-scroll" style={{ display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'auto', height: '100%' }}>
            <Sidebar isDark={isDark} jobs={jobs} jobsLoading={jobsLoading} jobsError={jobsError}
              selectedJobId={selectedJob?.id ?? null}
              onJobSelected={handleJobSelected} onJobSubmitted={handleJobSubmitted} />
          </div>

          {/* Main glass panel */}
          <main className="dash-content" style={{
            background: 'var(--glass)', backdropFilter: 'blur(24px) saturate(180%)', WebkitBackdropFilter: 'blur(24px) saturate(180%)',
            border: `1px solid ${tintBorder(isDark)}`,
            boxShadow: isDark ? 'var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.06)' : 'var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.80)',
            flex: 1, borderRadius: 20, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0,
            transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
          }}>
            <RightPanel isDark={isDark} activeJob={activeJob}
              artifacts={artifacts} artifactsLoading={artifactsLoading} artifactsError={artifactsError} />
          </main>
        </div>
      </div>
    </>
  );
}
