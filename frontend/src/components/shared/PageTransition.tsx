'use client'

/**
 * PageTransition
 * ──────────────────────────────────────────────────────────────
 * Animates a page section in on mount.
 *
 * Hydration safety:
 *  - motion.div renders on both server and client
 *  - `initial="hidden"` on server produces opacity:0 in HTML
 *  - After hydration, Framer Motion animates to "visible"
 *  - No AnimatePresence (exit animations require layout-level wiring
 *    which Next.js App Router does not support without extra setup)
 *  - `useReducedMotion` is called client-only via Framer Motion's own
 *    SSR guard, so no mismatch
 */

import { motion, useReducedMotion } from 'framer-motion'
import { pageEnter } from '@/lib/utils/motion'
import type { ReactNode } from 'react'

interface PageTransitionProps {
  children: ReactNode
  routeKey?: string
  className?: string
}

export function PageTransition({
  children,
  routeKey,
  className,
}: PageTransitionProps) {
  const prefersReduced = useReducedMotion()

  if (prefersReduced) {
    return <div className={className} style={{ width: '100%' }}>{children}</div>
  }

  return (
    <motion.div
      key={routeKey}
      variants={pageEnter}
      initial="hidden"
      animate="visible"
      className={className}
      style={{ width: '100%' }}
    >
      {children}
    </motion.div>
  )
}

/**
 * SectionReveal
 * ──────────────────────────────────────────────────────────────
 * whileInView entrance wrapper for landing sections.
 * Safe for SSR — Framer Motion handles whileInView correctly
 * without hydration issues.
 */

interface SectionRevealProps {
  children: ReactNode
  delay?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
  className?: string
  once?: boolean
}

const directionVariants = {
  up:    { hidden: { opacity: 0, y: 40,  filter: 'blur(3px)' }, visible: { opacity: 1, y: 0,  filter: 'blur(0px)' } },
  down:  { hidden: { opacity: 0, y: -28, filter: 'blur(3px)' }, visible: { opacity: 1, y: 0,  filter: 'blur(0px)' } },
  left:  { hidden: { opacity: 0, x: -44, filter: 'blur(3px)' }, visible: { opacity: 1, x: 0,  filter: 'blur(0px)' } },
  right: { hidden: { opacity: 0, x:  44, filter: 'blur(3px)' }, visible: { opacity: 1, x: 0,  filter: 'blur(0px)' } },
  none:  { hidden: { opacity: 0 },                               visible: { opacity: 1 } },
}

export function SectionReveal({
  children,
  delay = 0,
  direction = 'up',
  className,
  once = true,
}: SectionRevealProps) {
  const prefersReduced = useReducedMotion()
  const base = directionVariants[direction]

  const variants = {
    hidden:  base.hidden,
    visible: {
      ...base.visible,
      transition: {
        duration: 0.65,
        delay,
        ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
      },
    },
  }

  if (prefersReduced) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      variants={variants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount: 0.1, margin: '0px 0px -48px 0px' }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
