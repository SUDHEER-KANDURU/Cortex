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
          'border-[rgba(0,229,168,0.22)]',
          'bg-[rgba(0,229,168,0.10)] text-[var(--primary)]',
          'hover:bg-[rgba(0,229,168,0.16)]',
        ].join(' '),
        secondary: [
          'border-[var(--border)]',
          'bg-[rgba(255,255,255,0.06)] text-[var(--text-secondary)]',
          'hover:bg-[rgba(255,255,255,0.09)] hover:text-[var(--text)]',
        ].join(' '),
        destructive: [
          'border-[rgba(239,83,80,0.25)]',
          'bg-[rgba(239,83,80,0.10)] text-[var(--danger)]',
          'hover:bg-[rgba(239,83,80,0.16)]',
        ].join(' '),
        outline: [
          'border-[var(--border)]',
          'bg-transparent text-[var(--text-secondary)]',
          'hover:border-[var(--border-hover)] hover:text-[var(--text)]',
        ].join(' '),
        success: [
          'border-[rgba(22,199,132,0.25)]',
          'bg-[rgba(22,199,132,0.10)] text-[var(--success)]',
        ].join(' '),
        warning: [
          'border-[rgba(245,158,11,0.25)]',
          'bg-[rgba(245,158,11,0.10)] text-[var(--warning)]',
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
