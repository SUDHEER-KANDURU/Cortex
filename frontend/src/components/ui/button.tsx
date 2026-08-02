import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Button — Premium Liquid Glass button system
// =============================================================================

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap',
    'text-sm font-semibold tracking-[-0.01em]',
    'ring-offset-background transition-all duration-200 ease-out',
    'focus-visible:outline-none focus-visible:ring-2',
    'focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-40',
    'select-none',
  ].join(' '),
  {
    variants: {
      variant: {
        // Primary — gradient capsule
        default: [
          'rounded-[var(--radius-full)]',
          'bg-gradient-to-r from-[var(--primary)] to-[#00c9a7]',
          'text-[#060810] font-semibold',
          'shadow-[0_4px_20px_var(--primary-glow),inset_0_1px_0_rgba(255,255,255,0.28)]',
          'hover:brightness-110 hover:-translate-y-px',
          'active:brightness-95 active:translate-y-0',
        ].join(' '),
        // Accent
        accent: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--accent)] text-white',
          'shadow-[0_4px_16px_var(--accent-glow)]',
          'hover:brightness-110 hover:-translate-y-px',
        ].join(' '),
        // Destructive
        destructive: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--danger)] text-white',
          'hover:brightness-110',
        ].join(' '),
        // Ghost
        ghost: [
          'rounded-[var(--radius-md)]',
          'bg-transparent text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[rgba(255,255,255,0.07)] hover:text-[var(--text)]',
          'hover:border-[var(--border-hover)]',
        ].join(' '),
        // Outline
        outline: [
          'rounded-[var(--radius-md)]',
          'bg-transparent text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[rgba(255,255,255,0.05)] hover:text-[var(--text)]',
        ].join(' '),
        // Secondary
        secondary: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--surface)] text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[var(--card)] hover:text-[var(--text)]',
        ].join(' '),
        // Glass — floating glass capsule
        glass: [
          'rounded-[var(--radius-md)]',
          'bg-[rgba(255,255,255,0.07)] text-[var(--text)]',
          'border border-[rgba(255,255,255,0.10)]',
          'backdrop-blur-[12px]',
          'shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]',
          'hover:bg-[rgba(255,255,255,0.11)] hover:border-[rgba(255,255,255,0.16)]',
        ].join(' '),
        // Link
        link: [
          'text-[var(--primary)] underline-offset-4',
          'hover:underline hover:text-[var(--primary)]',
        ].join(' '),
      },
      size: {
        default:   'h-10 px-5 py-2',
        sm:        'h-8 rounded-[var(--radius-sm)] px-3 text-xs',
        lg:        'h-12 rounded-[var(--radius-md)] px-7 text-base',
        xl:        'h-14 rounded-[var(--radius-lg)] px-9 text-base',
        icon:      'h-10 w-10 rounded-[var(--radius-md)]',
        'icon-sm': 'h-8 w-8 rounded-[var(--radius-sm)]',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        disabled={disabled ?? loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <>
            <span
              className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin"
              aria-hidden="true"
            />
            <span>{children}</span>
          </>
        ) : children}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
