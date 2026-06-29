// =============================================================================
// ArtifactCard — Summary card for a single artifact (used in lists)
// =============================================================================

import React from 'react';
import { FileText, Clock } from 'lucide-react';
import type { Artifact } from '@/types';
import { formatDate } from '@/lib/utils/formatDate';
import { cn } from '@/lib/utils/cn';

export interface ArtifactCardProps {
  /** The artifact to display */
  artifact: Artifact;
  /** Whether this card is selected */
  isSelected?: boolean;
  /** Callback when the card is clicked */
  onClick?: (artifact: Artifact) => void;
}

// Human-readable labels for known content types
const CONTENT_TYPE_LABELS: Record<string, string> = {
  mermaid: 'Mermaid Diagram',
  'text/markdown': 'Markdown',
  'application/json': 'JSON',
  'text/plain': 'Plain Text',
};

export default function ArtifactCard({ artifact, isSelected = false, onClick }: ArtifactCardProps) {
  const typeLabel = CONTENT_TYPE_LABELS[artifact.content_type] ?? artifact.content_type;

  return (
    <button
      type="button"
      onClick={() => onClick?.(artifact)}
      className={cn(
        'w-full rounded-lg border p-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500',
        isSelected
          ? 'border-violet-500/50 bg-violet-500/10'
          : 'border-gray-700/50 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
      )}
      aria-pressed={isSelected}
    >
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
        <span className="text-sm font-medium text-gray-200">{typeLabel}</span>
      </div>
      <div className="mt-1.5 flex items-center gap-1 text-xs text-gray-500">
        <Clock className="h-3 w-3" aria-hidden="true" />
        {formatDate(artifact.created_at)}
      </div>
      <p className="mt-1 truncate text-xs text-gray-500 font-mono">
        {artifact.id}
      </p>
    </button>
  );
}
