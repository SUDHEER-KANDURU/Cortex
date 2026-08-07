/**
 * useMotion — prefers-reduced-motion aware hook
 *
 * Returns:
 *  prefersReduced  boolean — true when user prefers reduced motion
 *  rv(variants)    collapses any Framer Motion variant to instant transitions
 *  spring(type)    returns the right spring preset
 *
 * Usage:
 *   const { prefersReduced, rv } = useMotion()
 *   <motion.div variants={rv(fadeUp)} initial="hidden" whileInView="visible" />
 */
'use client'

import { useEffect, useState } from 'react'
import type { Variants } from 'framer-motion'
import { reduceMotion, SPRING, getSpring } from './motion'
import type { Transition } from 'framer-motion'

export function useMotion() {
  const [prefersReduced, setPrefersReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReduced(mq.matches)
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  /** Reduce variants if user prefers reduced motion */
  const rv = (variants: Variants): Variants =>
    reduceMotion(prefersReduced, variants)

  /** Return appropriate spring or instant transition */
  const sp = (
    type: keyof typeof SPRING = 'default',
    overrides?: Partial<Transition>
  ): Transition =>
    prefersReduced ? { duration: 0 } : getSpring(type, overrides)

  /** whileHover props — empty when reduced-motion */
  const hover = (props: Record<string, unknown>) =>
    prefersReduced ? {} : props

  /** whileTap props — empty when reduced-motion */
  const tap = (props: Record<string, unknown>) =>
    prefersReduced ? {} : props

  return { prefersReduced, rv, sp, hover, tap }
}
