import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '@/lib/utils/cn';
import { ButtonSpinner } from '@/components/shared/BrandedLoader';

// =============================================================================
// IconButton — Square/round icon-only button with all interactive states
// =============================================================================

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'ghost' | 'outline' | 'glass' | 'primary';
  size?: 'sm' | 'md' | 'lg';
  shape?: 'square' | 'circle';
  asChild?: boolean;
  loading?: boolean;
  'aria-label': string; // Required for accessibility
}

const SIZE_MAP = {
  sm: 'w-7 h-7',
  md: 'w-9 h-9',
  lg: 'w-11 h-11',
} as const;

const ICON_SIZE_MAP = {
  sm: 'w-3.5 h-3.5',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
} as const;

const VARIANT_MAP = {
  ghost: [
    'bg-transparent text-[var(--text-muted)]',
    'hover:bg-[var(--surface)] hover:text-[var(--text)]',
    'border border-transparent',
  ].join(' '),
  outline: [
    'bg-transparent text-[var(--text-secondary)]',
    'border border-[var(--border)]',
    'hover:bg-[var(--surface)] hover:text-[var(--text)] hover:border-[var(--border-hover)]',
  ].join(' '),
  glass: [
    'bg-[var(--glass-card)] text-[var(--text)]',
    'border border-[var(--border)]',
    'backdrop-blur-[12px]',
    'hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-sm)]',
  ].join(' '),
  primary: [
    'bg-[var(--primary)]',
    'text-white',
    'border border-transparent',
    'hover:brightness-105',
  ].join(' '),
} as const;

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      className,
      variant = 'ghost',
      size = 'md',
      shape = 'square',
      asChild = false,
      loading = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center shrink-0',
          'transition-all duration-200 ease-out',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1',
          'disabled:pointer-events-none disabled:opacity-45',
          'select-none',
          SIZE_MAP[size],
          VARIANT_MAP[variant],
          shape === 'circle' ? 'rounded-full' : 'rounded-[var(--radius-sm)]',
          // Apply icon sizing to direct SVG children
          `[&_svg]:${ICON_SIZE_MAP[size]}`,
          className
        )}
        disabled={disabled ?? loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <ButtonSpinner size={14} />
        ) : (
          children
        )}
      </Comp>
    );
  }
);
IconButton.displayName = 'IconButton';

