// =============================================================================
// LoadingSpinner — Accessible animated loading indicator
// =============================================================================

import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface LoadingSpinnerProps {
  /** Visual size of the spinner */
  size?: 'sm' | 'md' | 'lg';
  /** Optional label shown next to the spinner */
  label?: string;
  /** Optional extra class names */
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<LoadingSpinnerProps['size']>, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-10 w-10 border-[3px]',
};

export default function LoadingSpinner({
  size = 'md',
  label,
  className,
}: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label ?? 'Loading…'}
      className={cn('flex items-center gap-2', className)}
    >
      <span
        className={cn(
          'animate-spin rounded-full border-gray-600 border-t-blue-500',
          SIZE_CLASSES[size]
        )}
      />
      {label && (
        <span className="text-sm text-gray-400">{label}</span>
      )}
      <span className="sr-only">{label ?? 'Loading…'}</span>
    </div>
  );
}
