import { cn } from '@/lib/utils/cn';

// =============================================================================
// Skeleton — shimmer loading placeholder using design system tokens
// =============================================================================

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-sm)]',
        'skeleton-shimmer',
        className
      )}
      aria-hidden="true"
      {...props}
    />
  );
}

export { Skeleton };
