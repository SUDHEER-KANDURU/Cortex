// =============================================================================
// StatusBadge — Liquid Glass micro-surface treatment
// Applied to a small pill badge — appropriate scope, high impact.
// Backdrop blur at 4px is imperceptible as overhead but adds the glass quality.
// =============================================================================

import React from 'react';
import type { JobStatus } from '@/types';
import { cn } from '@/lib/utils/cn';

export interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

// Base color tokens — unchanged from original
const STATUS_COLOR: Record<JobStatus, {
  text: string;
  bg: string;
  border: string;
  dot: string;
}> = {
  pending:   { text: 'text-slate-400',   bg: 'bg-slate-400/8',   border: 'rgba(148,163,184,0.22)', dot: 'bg-slate-400'   },
  running:   { text: 'text-yellow-400',  bg: 'bg-yellow-400/8',  border: 'rgba(250,204,21,0.25)',  dot: 'bg-yellow-400'  },
  completed: { text: 'text-emerald-400', bg: 'bg-emerald-400/8', border: 'rgba(52,211,153,0.25)',  dot: 'bg-emerald-400' },
  failed:    { text: 'text-red-400',     bg: 'bg-red-400/8',     border: 'rgba(248,113,113,0.25)', dot: 'bg-red-400'     },
  cancelled: { text: 'text-slate-500',   bg: 'bg-slate-500/8',   border: 'rgba(100,116,139,0.20)', dot: 'bg-slate-500'   },
};

const STATUS_LABELS: Record<JobStatus, string> = {
  pending:   'Pending',
  running:   'Running',
  completed: 'Completed',
  failed:    'Failed',
  cancelled: 'Cancelled',
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const c = STATUS_COLOR[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5',
        'text-[10px] font-medium uppercase tracking-wider',
        'px-2 py-0.5 rounded-full',
        c.text,
        className,
      )}
      style={{
        // Liquid Glass micro-surface: very light blur + layered border
        background: 'rgba(15,22,41,0.55)',
        backdropFilter: 'blur(4px) saturate(160%)',
        WebkitBackdropFilter: 'blur(4px) saturate(160%)',
        border: `1px solid ${c.border}`,
        // Top highlight: glass sheen on the dark surface
        boxShadow: [
          `inset 0 1px 0 rgba(255,255,255,0.06)`,
          `inset 0 -1px 0 rgba(0,0,0,0.15)`,
        ].join(', '),
      }}
      data-testid="status-badge"
      data-status={status}
    >
      {status === 'running' ? (
        <span className={cn('w-1.5 h-1.5 rounded-full animate-pulse', c.dot)} />
      ) : (
        <span className={cn('w-1.5 h-1.5 rounded-full', c.dot)} />
      )}
      {STATUS_LABELS[status]}
    </span>
  );
}
