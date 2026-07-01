// =============================================================================
// StatusBadge — Premium status indicator for Cortex jobs
// =============================================================================

import React from 'react';
import type { JobStatus } from '@/types';
import { cn } from '@/lib/utils/cn';

export interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const STATUS_STYLES: Record<JobStatus, string> = {
  pending:   'text-slate-400 bg-slate-400/10 border-slate-400/20',
  running:   'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  completed: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  failed:    'text-red-400 bg-red-400/10 border-red-400/20',
  cancelled: 'text-slate-500 bg-slate-500/10 border-slate-500/20',
};

const STATUS_DOT: Record<JobStatus, string> = {
  pending:   'bg-slate-400',
  running:   'bg-yellow-400',
  completed: 'bg-emerald-400',
  failed:    'bg-red-400',
  cancelled: 'bg-slate-500',
};

const STATUS_LABELS: Record<JobStatus, string> = {
  pending:   'Pending',
  running:   'Running',
  completed: 'Completed',
  failed:    'Failed',
  cancelled: 'Cancelled',
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border',
        STATUS_STYLES[status],
        className
      )}
      data-testid="status-badge"
      data-status={status}
    >
      {status === 'running' ? (
        <span className={cn('w-1.5 h-1.5 rounded-full animate-pulse', STATUS_DOT[status])} />
      ) : (
        <span className={cn('w-1.5 h-1.5 rounded-full', STATUS_DOT[status])} />
      )}
      {STATUS_LABELS[status]}
    </span>
  );
}
