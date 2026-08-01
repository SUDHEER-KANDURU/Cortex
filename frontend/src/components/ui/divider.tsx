import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Divider — horizontal or vertical rule using design system border token
// =============================================================================

export interface DividerProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical';
  label?: string;
}

const Divider = React.forwardRef<HTMLDivElement, DividerProps>(
  ({ className, orientation = 'horizontal', label, ...props }, ref) => {
    if (label) {
      return (
        <div
          ref={ref}
          role="separator"
          className={cn('flex items-center gap-3', className)}
          {...props}
        >
          <div className="flex-1 h-px bg-[var(--border)]" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)] font-mono shrink-0">
            {label}
          </span>
          <div className="flex-1 h-px bg-[var(--border)]" />
        </div>
      );
    }

    return (
      <div
        ref={ref}
        role="separator"
        className={cn(
          orientation === 'horizontal'
            ? 'w-full h-px bg-[var(--border)]'
            : 'h-full w-px bg-[var(--border)]',
          className
        )}
        {...props}
      />
    );
  }
);
Divider.displayName = 'Divider';

export { Divider };
