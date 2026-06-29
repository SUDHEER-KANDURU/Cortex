// =============================================================================
// ErrorAlert — Displays an error message in a styled alert box
// =============================================================================

import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface ErrorAlertProps {
  /** The error message to display */
  message: string;
  /** Optional title override (defaults to "Error") */
  title?: string;
  /** Optional dismiss handler — renders an X button when provided */
  onDismiss?: () => void;
  /** Optional extra class names */
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
        'flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400',
        className
      )}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-red-300">{title}</p>
        <p className="mt-0.5 text-red-400/90 break-words">{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="shrink-0 rounded p-0.5 hover:bg-red-500/20 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
