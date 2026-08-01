import * as React from 'react';
import { cn } from '@/lib/utils/cn';

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

// =============================================================================
// Textarea — Premium textarea with design system tokens
// Uses CSS variables — adapts to dark/light theme automatically
// =============================================================================

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full px-3 py-2',
          'rounded-[var(--radius-md)]',
          'bg-[rgba(255,255,255,0.05)] text-[var(--text)]',
          'border border-[var(--border)]',
          'placeholder:text-[var(--text-muted)]',
          'focus:outline-none focus:border-[var(--primary)]',
          'focus:shadow-[0_0_0_3px_var(--primary-dim)]',
          'focus:bg-[rgba(255,255,255,0.07)]',
          'hover:border-[var(--border-hover)]',
          'transition-all duration-200 ease-out',
          'text-sm font-normal leading-relaxed resize-y',
          'disabled:cursor-not-allowed disabled:opacity-45',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';

export { Textarea };
