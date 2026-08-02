import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Card — Premium layered glass card with specular edge highlights
// =============================================================================

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[var(--radius)] border border-[var(--border)]',
        'bg-[var(--glass-card)] text-[var(--text)]',
        'shadow-[var(--shadow-md),var(--edge-top)]',
        'transition-all duration-200 ease-out',
        'hover:border-[var(--border-hover)]',
        'hover:shadow-[var(--shadow-lg),var(--edge-top)]',
        'hover:-translate-y-px',
        className
      )}
      {...props}
    />
  )
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-1.5 p-6', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        'text-xl font-semibold leading-tight tracking-[-0.022em]',
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

// Glass variant — maximum depth with backdrop blur
const GlassCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[var(--radius)]',
        'bg-[var(--glass-card)] border border-[var(--border)]',
        'backdrop-blur-[20px] saturate-150',
        'shadow-[var(--shadow-lg),var(--edge-top),var(--edge-inner)]',
        'transition-all duration-200 ease-out',
        'hover:border-[var(--border-hover)]',
        'hover:shadow-[var(--shadow-xl),var(--edge-top)]',
        'hover:-translate-y-px',
        className
      )}
      {...props}
    />
  )
);
GlassCard.displayName = 'GlassCard';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, GlassCard };
