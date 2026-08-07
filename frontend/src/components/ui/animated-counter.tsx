'use client';

/**
 * AnimatedCounter
 * ────────────────────────────────────────────────────────────────
 * Rolls a number from its previous value to the new value using
 * Framer Motion's useSpring + useTransform.
 * Each digit slot uses AnimatePresence for a vertical roll effect.
 *
 * Usage:
 *   <AnimatedCounter value={241} suffix="+" />
 *   <AnimatedCounter value={pct} format={(n) => `${n}%`} />
 *
 * Motion behaviour:
 *  - Number springs from prev → next value (SPRING.stiff — near-instant, no bounce)
 *  - Digit slots slide up/down (counterTick variant)
 *  - prefers-reduced-motion: instant jump, no spring, no slide
 */

import * as React from 'react';
import {
  motion,
  useSpring,
  useTransform,
  AnimatePresence,
  useReducedMotion,
} from 'framer-motion';
import { SPRING, DURATION, EASE } from '@/lib/utils/motion';

// ── Types ──────────────────────────────────────────────────────────────────

interface AnimatedCounterProps {
  value: number;
  /** Text appended after the number (e.g. "+" or "%") */
  suffix?: string;
  /** Text prepended before the number (e.g. "$") */
  prefix?: string;
  /** Custom format function — overrides prefix/suffix if provided */
  format?: (value: number) => string;
  /** Round to nearest integer (default: true) */
  round?: boolean;
  /** Decimal places when round=false */
  decimals?: number;
  className?: string;
}

// ── Digit roll variant ──────────────────────────────────────────────────────

const digitVariants = {
  enter: (dir: number) => ({
    y:       dir > 0 ? -12 : 12,
    opacity: 0,
  }),
  center: {
    y:          0,
    opacity:    1,
    transition: { ...SPRING.snappy },
  },
  exit: (dir: number) => ({
    y:          dir > 0 ? 12 : -12,
    opacity:    0,
    transition: { duration: DURATION.fast, ease: EASE.snap },
  }),
};

// ── Spring counter — the numeric motion value ──────────────────────────────

function useCounterSpring(target: number, prefersReduced: boolean | null) {
  const spring = useSpring(target, prefersReduced ? { duration: 0 } : SPRING.stiff as object);
  const rounded = useTransform(spring, (v: number) => Math.round(v));

  React.useEffect(() => {
    spring.set(target);
  }, [target, spring]);

  return rounded;
}

// ── Component ──────────────────────────────────────────────────────────────

export function AnimatedCounter({
  value,
  suffix = '',
  prefix = '',
  format,
  round = true,
  decimals = 0,
  className,
}: AnimatedCounterProps) {
  const prefersReduced = useReducedMotion();
  const springValue    = useCounterSpring(value, prefersReduced);

  // Track previous display value to determine roll direction
  const [displayValue, setDisplayValue] = React.useState(value);
  const prevValue = React.useRef(value);

  React.useEffect(() => {
    if (prefersReduced) {
      setDisplayValue(value);
      return;
    }
    const unsubscribe = springValue.on('change', (v) => {
      setDisplayValue(round ? Math.round(v) : parseFloat(v.toFixed(decimals)));
    });
    return unsubscribe;
  }, [springValue, prefersReduced, value, round, decimals]);

  const direction = value >= prevValue.current ? 1 : -1;
  React.useEffect(() => { prevValue.current = value; }, [value]);

  const formatted = format
    ? format(displayValue)
    : `${prefix}${displayValue}${suffix}`;

  if (prefersReduced) {
    return <span className={className}>{formatted}</span>;
  }

  return (
    <span
      className={className}
      style={{ display: 'inline-flex', alignItems: 'center', overflow: 'hidden' }}
      aria-live="polite"
      aria-atomic="true"
      aria-label={formatted}
    >
      <AnimatePresence mode="popLayout" custom={direction} initial={false}>
        <motion.span
          key={formatted}
          custom={direction}
          variants={digitVariants}
          initial="enter"
          animate="center"
          exit="exit"
          style={{ display: 'inline-block' }}
        >
          {formatted}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

// ── Simpler variant — pure rAF count-up (no spring, activates on mount) ───
// Use this for one-shot "count from 0 on page load" stats.

interface CountUpProps {
  target: number;
  suffix?: string;
  prefix?: string;
  duration?: number;  // ms, default 1200
  className?: string;
  /** Whether to start the animation (e.g. tie to whileInView) */
  active?: boolean;
}

export function CountUp({
  target,
  suffix = '',
  prefix = '',
  duration = 1200,
  className,
  active = true,
}: CountUpProps) {
  const prefersReduced = useReducedMotion();
  const [display, setDisplay] = React.useState(prefersReduced ? target : 0);
  const startedRef = React.useRef(false);
  const rafRef     = React.useRef<number | null>(null);

  React.useEffect(() => {
    if (!active || startedRef.current) return;
    if (prefersReduced) { setDisplay(target); return; }

    startedRef.current = true;
    const start = performance.now();

    const tick = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      // Cubic ease-out
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(eased * target));
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [active, target, duration, prefersReduced]);

  return (
    <span className={className}>
      {prefix}{display}{suffix}
    </span>
  );
}
