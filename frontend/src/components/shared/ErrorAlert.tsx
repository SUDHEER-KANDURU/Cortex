// =============================================================================
// ErrorAlert — Error message using design system tokens
// =============================================================================

import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface ErrorAlertProps {
  message: string;
  title?: string;
  onDismiss?: () => void;
  className?: string;
}

export default function ErrorAlert({
  message,
  title = 'Error',
  onDismiss,
  className,
}: ErrorAlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 rounded-[var(--radius-sm)]',
        'border border-[rgba(239,83,80,0.28)] bg-[var(--danger-dim)]',
        'px-4 py-3 text-sm',
        className
      )}
    >
      <AlertCircle
        className="mt-0.5 h-4 w-4 shrink-0 text-[var(--danger)]"
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[var(--danger)]">{title}</p>
        <p className="mt-0.5 text-[var(--danger)] opacity-80 break-words text-xs leading-relaxed">
          {message}
        </p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="shrink-0 rounded p-0.5 text-[var(--danger)] hover:bg-[rgba(239,83,80,0.15)] transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
