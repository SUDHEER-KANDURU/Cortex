/**
 * Button — Premium Liquid Glass button system with Framer Motion
 * micro-interactions.
 *
 * Motion behaviour:
 *  whileHover  → spring lift (-3 px) with subtle scale
 *  whileTap    → compress (scale 0.96, +1 px) — feels physical
 *  loading     → spinner entrance with scale spring
 *  prefers-reduced-motion → all motion props stripped
 */
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils/cn';
import { ButtonSpinner } from '@/components/shared/BrandedLoader';
import { SPRING, DURATION } from '@/lib/utils/motion';

// ── Variant styles ─────────────────────────────────────────────────────────

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap',
    'text-sm font-semibold tracking-[-0.01em]',
    'ring-offset-background',
    'focus-visible:outline-none focus-visible:ring-2',
    'focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-40',
    'select-none',
    // Duration handled by Framer Motion — keep CSS transitions only for
    // color / filter properties that FM doesn't manage
    'transition-[color,filter,background-color,border-color] duration-150 ease-out',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          'rounded-[var(--radius-full)]',
          'bg-gradient-to-r from-[var(--primary)] to-[#00c9a7]',
          'text-[#060810] font-semibold',
          'shadow-[0_4px_20px_var(--primary-glow),inset_0_1px_0_rgba(255,255,255,0.28)]',
          'hover:brightness-110',
        ].join(' '),
        accent: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--accent)] text-white',
          'shadow-[0_4px_16px_var(--accent-glow)]',
          'hover:brightness-110',
        ].join(' '),
        destructive: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--danger)] text-white',
          'hover:brightness-110',
        ].join(' '),
        ghost: [
          'rounded-[var(--radius-md)]',
          'bg-transparent text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[rgba(255,255,255,0.07)] hover:text-[var(--text)]',
          'hover:border-[var(--border-hover)]',
        ].join(' '),
        outline: [
          'rounded-[var(--radius-md)]',
          'bg-transparent text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[rgba(255,255,255,0.05)] hover:text-[var(--text)]',
        ].join(' '),
        secondary: [
          'rounded-[var(--radius-md)]',
          'bg-[var(--surface)] text-[var(--text-secondary)]',
          'border border-[var(--border)]',
          'hover:bg-[var(--card)] hover:text-[var(--text)]',
        ].join(' '),
        glass: [
          'rounded-[var(--radius-md)]',
          'bg-[rgba(255,255,255,0.07)] text-[var(--text)]',
          'border border-[rgba(255,255,255,0.10)]',
          'backdrop-blur-[12px]',
          'shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]',
          'hover:bg-[rgba(255,255,255,0.11)] hover:border-[rgba(255,255,255,0.16)]',
        ].join(' '),
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
)

// ── Props ───────────────────────────────────────────────────────────────────

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?:  boolean
  loading?:  boolean
  /** Disable hover/tap animation (e.g. inside already-animated containers) */
  noMotion?: boolean
}

// ── Motion presets ─────────────────────────────────────────────────────────

const HOVER_LIFT = {
  y:          -3,
  transition: SPRING.snappy,
}

const TAP_PRESS = {
  scale:      0.96,
  y:          1,
  transition: { duration: DURATION.micro, ease: [0.25, 0.46, 0.45, 0.94] as [number, number, number, number] },
}

// ── Component ──────────────────────────────────────────────────────────────

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild    = false,
      loading    = false,
      noMotion   = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const prefersReducedMotion = useReducedMotion()
    const isDisabled = disabled ?? loading
    const applyMotion = !noMotion && !prefersReducedMotion && !isDisabled

    const inner = (
      <>
        {loading ? (
          <>
            <motion.span
              key="spinner"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={SPRING.bouncy}
              style={{ display: 'flex', alignItems: 'center' }}
            >
              <ButtonSpinner size={14} />
            </motion.span>
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </>
    )

    if (asChild) {
      const Comp = Slot as unknown as React.ForwardRefExoticComponent<
        React.ButtonHTMLAttributes<HTMLButtonElement> & { ref?: React.Ref<HTMLButtonElement> }
      >
      return (
        <Comp
          className={cn(buttonVariants({ variant, size }), className)}
          ref={ref}
          disabled={isDisabled}
          aria-busy={loading || undefined}
          {...props}
        >
          {inner}
        </Comp>
      )
    }

    return (
      <motion.button
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        whileHover={applyMotion ? HOVER_LIFT : undefined}
        whileTap={applyMotion ? TAP_PRESS : undefined}
        {...(props as React.ComponentProps<typeof motion.button>)}
      >
        {inner}
      </motion.button>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
