import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Badge — Premium glass pill with strong contrast in both themes
// =============================================================================

const badgeVariants = cva(
  [
    'inline-flex items-center gap-1.5 rounded-full border',
    'px-2.5 py-0.5 text-[11px] font-semibold tracking-[0.04em]',
    'transition-colors duration-150',
    'focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          // Soft slate — matches the reference accent
          'border-[var(--primary-dim)]',
          'bg-[var(--primary-dim)] text-[var(--primary)]',
          'hover:bg-[var(--primary-glow)]',
        ].join(' '),
        secondary: [
          'border-[var(--border)]',
          'bg-[var(--surface)] text-[var(--text-secondary)]',
          'hover:bg-[var(--card)] hover:text-[var(--text)]',
        ].join(' '),
        destructive: [
          'border-[var(--danger-dim)]',
          'bg-[var(--danger-dim)] text-[var(--danger)]',
          'hover:bg-[rgba(185,64,64,0.16)]',
        ].join(' '),
        outline: [
          'border-[var(--border)]',
          'bg-transparent text-[var(--text-secondary)]',
          'hover:border-[var(--border-hover)] hover:text-[var(--text)]',
        ].join(' '),
        success: [
          'border-[var(--success-dim)]',
          'bg-[var(--success-dim)] text-[var(--success)]',
        ].join(' '),
        warning: [
          'border-[var(--warning-dim)]',
          'bg-[var(--warning-dim)] text-[var(--warning)]',
        ].join(' '),
      },
    },
    defaultVariants: { variant: 'default' },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
