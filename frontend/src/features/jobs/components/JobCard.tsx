// =============================================================================
// JobCard — Premium summary card for a single Cortex job
// Uses design system tokens — adapts to dark/light theme automatically
// =============================================================================

import React from 'react';
import { GitBranch, Clock } from 'lucide-react';
import type { Job } from '@/types';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatRelativeDate } from '@/lib/utils/formatDate';
import { cn } from '@/lib/utils/cn';

export interface JobCardProps {
  job: Job;
  isSelected?: boolean;
  onClick?: (job: Job) => void;
}

export default function JobCard({ job, isSelected = false, onClick }: JobCardProps) {
  const displayUrl = job.repo_url.replace('https://github.com/', '');

  return (
    <button
      type="button"
      onClick={() => onClick?.(job)}
      className={cn(
        'w-full rounded-[var(--radius-md)] border p-4 text-left',
        'transition-all duration-200 ease-out',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1',
        isSelected
          ? [
              'border-[rgba(0,229,168,0.35)] bg-[rgba(0,229,168,0.06)]',
              'shadow-[0_0_0_1px_rgba(0,229,168,0.15),var(--shadow-sm)]',
            ].join(' ')
          : [
              'border-[var(--border)] bg-[var(--card)]',
              'hover:border-[var(--border-hover)] hover:bg-[rgba(255,255,255,0.04)]',
              'hover:shadow-[var(--shadow-md)] hover:-translate-y-[1px]',
            ].join(' ')
      )}
      aria-pressed={isSelected}
      aria-label={`Job for ${displayUrl}, status: ${job.status}`}
    >
      {/* Top row: repo name + badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <GitBranch
            className={cn(
              'h-3.5 w-3.5 shrink-0',
              isSelected ? 'text-[var(--primary)]' : 'text-[var(--text-muted)]'
            )}
            aria-hidden="true"
          />
          <span
            className="truncate text-sm font-semibold text-[var(--text)]"
            title={job.repo_url}
          >
            {displayUrl}
          </span>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Bottom row: artifact type + time */}
      <div className="mt-2.5 flex items-center justify-between">
        <span className="text-[11px] font-medium text-[var(--text-muted)] font-mono tracking-wide">
          {ARTIFACT_TYPE_LABELS[job.artifact_type] ?? job.artifact_type}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
          <Clock className="h-3 w-3" aria-hidden="true" />
          {formatRelativeDate(job.created_at)}
        </span>
      </div>
    </button>
  );
}
