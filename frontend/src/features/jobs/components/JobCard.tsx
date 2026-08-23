// =============================================================================
// JobCard — Premium summary card for a single Cortex job
// Uses design system tokens — adapts to dark/light theme automatically
// =============================================================================

import React, { useEffect } from 'react';
import { GitBranch, Clock, RotateCcw } from 'lucide-react';
import type { Job } from '@/types';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatRelativeDate } from '@/lib/utils/formatDate';
import { cn } from '@/lib/utils/cn';
import { useRetryJob } from '@/features/jobs/hooks/useRetryJob';

export interface JobCardProps {
  job: Job;
  isSelected?: boolean;
  onClick?: (job: Job) => void;
  /** Called with the new replacement job after a successful retry */
  onRetried?: (newJob: Job) => void;
}

export default function JobCard({ job, isSelected = false, onClick, onRetried }: JobCardProps) {
  const displayUrl = job.repo_url.replace('https://github.com/', '');
  const { retriedJob, isRetrying, error: retryError, retry } = useRetryJob();

  // Notify parent when retry succeeds
  useEffect(() => {
    if (retriedJob) {
      onRetried?.(retriedJob);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retriedJob]);

  const handleRetry = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation(); // don't select the card while retrying
    await retry(job.id);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => onClick?.(job)}
        className={cn(
          'w-full rounded-[var(--radius-md)] border p-4 text-left',
          'transition-all duration-200 ease-out',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1',
          isSelected
            ? [
                'border-[var(--primary)] bg-[var(--primary-dim)]',
                'shadow-[var(--shadow-sm)]',
              ].join(' ')
            : [
                'border-[var(--border)] bg-[var(--card)]',
                'hover:border-[var(--border-hover)] hover:bg-[var(--surface)]',
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

      {/* Retry row — only shown for failed jobs */}
      {job.status === 'failed' && (
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={handleRetry}
            disabled={isRetrying}
            className={cn(
              'flex items-center justify-center gap-1.5 w-full rounded-[var(--radius-sm)] border px-3 py-1.5',
              'text-[11px] font-medium transition-all duration-150',
              'border-[var(--danger-dim)] text-[var(--danger)] bg-[var(--danger-dim)]',
              'hover:opacity-80 hover:border-[var(--danger)]',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--danger)]',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            aria-busy={isRetrying}
          >
            <RotateCcw
              className={cn('h-3 w-3 shrink-0', isRetrying && 'animate-spin')}
              aria-hidden="true"
            />
            {isRetrying ? 'Retrying…' : 'Retry Job'}
          </button>

          {retryError && (
            <p className="text-[10px] text-[var(--danger)] px-1">{retryError}</p>
          )}
        </div>
      )}
    </div>
  );
}
