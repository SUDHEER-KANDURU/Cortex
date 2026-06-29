// =============================================================================
// StatusBadge — Colored badge for Cortex job statuses
// Maps each JobStatus to a distinct Tailwind color scheme.
// =============================================================================

import React from 'react';
import type { JobStatus } from '@/types';
import { cn } from '@/lib/utils/cn';

export interface StatusBadgeProps {
  /** The current status of the job */
  status: JobStatus;
  /** Optional extra class names */
  className?: string;
}

const STATUS_STYLES: Record<JobStatus, string> = {
  pending:   'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  running:   'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  completed: 'bg-green-500/20 text-green-400 border border-green-500/30',
  failed:    'bg-red-500/20 text-red-400 border border-red-500/30',
  cancelled: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
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
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_STYLES[status],
        className
      )}
      data-testid="status-badge"
      data-status={status}
    >
      {/* Animated pulse dot for running status */}
      {status === 'running' && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-blue-500" />
        </span>
      )}
      {STATUS_LABELS[status]}
    </span>
  );
}
