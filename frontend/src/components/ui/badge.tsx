import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils/cn';

const badgeVariants = cva(
  [
    'inline-flex items-center gap-1.5 rounded-full border',
    'px-2.5 py-0.5 text-xs font-medium tracking-wide',
    'transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          'border-transparent',
          'bg-[var(--primary-dim)] text-[var(--primary)]',
          'hover:bg-[var(--primary-glow)]',
        ].join(' '),
        secondary: [
          'border-[var(--border)] bg-[var(--surface)]',
          'text-[var(--text-secondary)]',
          'hover:bg-[var(--card)]',
        ].join(' '),
        destructive: [
          'border-transparent',
          'bg-[var(--danger-dim)] text-[var(--danger)]',
          'hover:bg-[rgba(239,83,80,0.2)]',
        ].join(' '),
        outline: [
          'border-[var(--border)]',
          'text-[var(--text-secondary)]',
          'hover:border-[var(--border-hover)] hover:text-[var(--text)]',
        ].join(' '),
        success: [
          'border-transparent',
          'bg-[rgba(22,199,132,0.12)] text-[var(--success)]',
        ].join(' '),
        warning: [
          'border-transparent',
          'bg-[rgba(245,185,66,0.12)] text-[var(--warning)]',
        ].join(' '),
      },
    },
    defaultVariants: {
      variant: 'default',
    },
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
