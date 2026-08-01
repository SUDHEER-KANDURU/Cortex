import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils/cn';

const buttonVariants = cva(
  [
    // Base
    'inline-flex items-center justify-center gap-2 whitespace-nowrap',
    'text-sm font-semibold tracking-[-0.01em]',
    'ring-offset-background transition-all duration-200 ease-out',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-45',
    'select-none',
  ].join(' '),
  {
    variants: {
      variant: {
        // Primary — gradient
        default: [
          'rounded-[var(--radius-md)]',
          'bg-gradient-to-r from-[var(--primary)] to-[#00c9a7]',
          'text-[#07090d]',
          'hover:brightness-110',
        ].join(' '),
        // Accent
        accent: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--accent)] text-white',
          'hover:brightness-110',
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
          'hover:bg-[rgba(255,255,255,0.06)] hover:text-[var(--text)] hover:border-[var(--border-hover)]',
          '[data-theme="light"]_&:hover:bg-[rgba(0,0,0,0.04)]',
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
        // Glass
        glass: [
          'rounded-[var(--radius-md)]',
          'bg-[rgba(255,255,255,0.07)] text-[var(--text)]',
          'border border-[rgba(255,255,255,0.10)]',
          'backdrop-blur-[12px]',
          'hover:bg-[rgba(255,255,255,0.10)]',
        ].join(' '),
        // Link
        link: [
          'text-[var(--primary)] underline-offset-4',
          'hover:underline hover:text-[var(--primary)]',
        ].join(' '),
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm:      'h-8 rounded-[var(--radius-sm)] px-3 text-xs',
        lg:      'h-12 rounded-[var(--radius-md)] px-7 text-base',
        xl:      'h-14 rounded-[var(--radius-lg)] px-9 text-base',
        icon:    'h-10 w-10 rounded-[var(--radius-md)]',
        'icon-sm': 'h-8 w-8 rounded-[var(--radius-sm)]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size:    'default',
    },
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
