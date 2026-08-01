import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// EmptyState — Consistent empty/zero-state UI using design tokens
// =============================================================================

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 py-12 px-6 text-center',
        className
      )}
    >
      {icon && (
        <div
          className="flex items-center justify-center w-14 h-14 rounded-2xl"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border)',
          }}
        >
          {icon}
        </div>
      )}
      <div className="space-y-1.5 max-w-[280px]">
        <p
          className="text-sm font-semibold"
          style={{ color: 'var(--text)' }}
        >
          {title}
        </p>
        {description && (
          <p
            className="text-xs leading-relaxed"
            style={{ color: 'var(--text-muted)' }}
          >
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
