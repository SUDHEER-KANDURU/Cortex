// =============================================================================
// JobCard — Displays a summary of a single Cortex job
// =============================================================================

import React from 'react';
import { GitBranch, Clock } from 'lucide-react';
import type { Job } from '@/types';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatRelativeDate } from '@/lib/utils/formatDate';
import { cn } from '@/lib/utils/cn';

export interface JobCardProps {
  /** The job to display */
  job: Job;
  /** Whether this card is currently selected */
  isSelected?: boolean;
  /** Callback fired when the card is clicked */
  onClick?: (job: Job) => void;
}

export default function JobCard({ job, isSelected = false, onClick }: JobCardProps) {
  // Truncate long repo URLs for display
  const displayUrl = job.repo_url.replace('https://github.com/', '');

  return (
    <button
      type="button"
      onClick={() => onClick?.(job)}
      className={cn(
        'w-full rounded-lg border p-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500',
        isSelected
          ? 'border-violet-500/50 bg-violet-500/10'
          : 'border-gray-700/50 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
      )}
      aria-pressed={isSelected}
      aria-label={`Job for ${displayUrl}, status: ${job.status}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <GitBranch className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
          <span
            className="truncate text-sm font-medium text-gray-200"
            title={job.repo_url}
          >
            {displayUrl}
          </span>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {ARTIFACT_TYPE_LABELS[job.artifact_type] ?? job.artifact_type}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="h-3 w-3" aria-hidden="true" />
          {formatRelativeDate(job.created_at)}
        </span>
      </div>
    </button>
  );
}
