/**
 * Card — Premium layered glass card with Framer Motion spring hover.
 *
 * Motion behaviour:
 *  whileHover → spring lift (-6 px) + shadow deepen
 *  whileTap   → micro compress (scale 0.99)
 *  Tilt       → data-spotlight attribute handled by GSAP in page.tsx
 *  prefers-reduced-motion → plain CSS hover only
 */
'use client'

import * as React from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { SPRING, DURATION, EASE } from '@/lib/utils/motion'

// ── Motion presets ──────────────────────────────────────────────────────────

const CARD_HOVER = {
  y:          -6,
  boxShadow:  'var(--shadow-xl), var(--edge-top)',
  transition: SPRING.snappy,
}

const CARD_TAP = {
  scale:      0.99,
  transition: { duration: DURATION.micro },
}

const CARD_REST = {
  y:          0,
  boxShadow:  'var(--shadow-md), var(--edge-top)',
  transition: { duration: DURATION.fast, ease: EASE.easeOut },
}

// ── Card ───────────────────────────────────────────────────────────────────

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Disable hover spring animation (e.g. inside carousels) */
  noMotion?: boolean
  /** Whether to add data-spotlight for GSAP tilt */
  spotlight?: boolean
  asChild?: boolean
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, noMotion = false, spotlight = false, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion()
    const applyMotion = !noMotion && !prefersReducedMotion

    return (
      <motion.div
        ref={ref}
        data-spotlight={spotlight ? '' : undefined}
        className={cn(
          'rounded-[var(--radius)] border border-[var(--border)]',
          'bg-[var(--glass-card)] text-[var(--text)]',
          'shadow-[var(--shadow-md),var(--edge-top)]',
          // Keep CSS fallback for non-JS / reduced-motion
          !applyMotion && [
            'transition-all duration-200 ease-out',
            'hover:border-[var(--border-hover)]',
            'hover:shadow-[var(--shadow-lg),var(--edge-top)]',
            'hover:-translate-y-px',
          ].join(' '),
          className
        )}
        whileHover={applyMotion ? CARD_HOVER : undefined}
        whileTap={applyMotion ? CARD_TAP : undefined}
        animate={applyMotion ? CARD_REST : undefined}
        {...props}
      />
    )
  }
)
Card.displayName = 'Card'

// ── Sub-components ─────────────────────────────────────────────────────────

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col gap-1.5 p-6', className)}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      'text-xl font-semibold leading-tight tracking-[-0.022em]',
      'text-[var(--text)]',
      className
    )}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn(
      'text-sm leading-relaxed text-[var(--text-secondary)]',
      className
    )}
    {...props}
  />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'flex items-center p-6 pt-0',
      'border-t border-[var(--border)] mt-auto',
      className
    )}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

// ── Glass variant ──────────────────────────────────────────────────────────

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  noMotion?: boolean
  spotlight?: boolean
}

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, noMotion = false, spotlight = false, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion()
    const applyMotion = !noMotion && !prefersReducedMotion

    return (
      <motion.div
        ref={ref}
        data-spotlight={spotlight ? '' : undefined}
        className={cn(
          'rounded-[var(--radius)]',
          'bg-[var(--glass-card)] border border-[var(--border)]',
          'backdrop-blur-[20px] saturate-150',
          'shadow-[var(--shadow-lg),var(--edge-top),var(--edge-inner)]',
          !applyMotion && [
            'transition-all duration-200 ease-out',
            'hover:border-[var(--border-hover)]',
            'hover:shadow-[var(--shadow-xl),var(--edge-top)]',
            'hover:-translate-y-px',
          ].join(' '),
          className
        )}
        whileHover={
          applyMotion
            ? {
                y:          -6,
                boxShadow:  'var(--shadow-xl), var(--edge-top)',
                transition: SPRING.snappy,
              }
            : undefined
        }
        whileTap={applyMotion ? CARD_TAP : undefined}
        {...props}
      />
    )
  }
)
GlassCard.displayName = 'GlassCard'

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  GlassCard,
}
