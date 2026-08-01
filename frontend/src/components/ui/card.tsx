import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Card — Premium glass-morphic card using design system tokens
// =============================================================================

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[var(--radius)] border border-[var(--border)]',
        'bg-[var(--card)] text-[var(--text)]',
        'shadow-[var(--shadow-md)]',
        'transition-all duration-200 ease-out',
        'hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-lg)]',
        className
      )}
      {...props}
    />
  )
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col gap-1.5 p-6', className)}
      {...props}
    />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        'text-xl font-semibold leading-tight tracking-[-0.02em]',
        'text-[var(--text)]',
        className
      )}
      {...props}
    />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm leading-relaxed text-[var(--text-secondary)]', className)}
    {...props}
  />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex items-center p-6 pt-0',
        'border-t border-[var(--border)] mt-auto',
        className
      )}
      {...props}
    />
  )
);
CardFooter.displayName = 'CardFooter';

// Glass variant card
const GlassCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[var(--radius)]',
        'bg-[var(--glass)] border border-[var(--border)]',
        'backdrop-blur-[18px] saturate-150',
        'shadow-[var(--shadow-lg),inset_0_1px_0_rgba(255,255,255,0.06)]',
        'transition-all duration-200 ease-out',
        'hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-xl)]',
        className
      )}
      {...props}
    />
  )
);
GlassCard.displayName = 'GlassCard';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, GlassCard };
