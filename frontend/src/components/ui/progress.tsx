'use client';

/**
 * Progress — Framer Motion animated fill bar.
 *
 * Motion behaviour:
 *  - Fill bar animates width from 0 → pct using motion.div + spring
 *  - On value change, width re-animates from current → new (not from 0)
 *  - prefers-reduced-motion: instant width, no spring
 */

import * as React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils/cn';
import { SPRING, DURATION, EASE } from '@/lib/utils/motion';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProgressProps {
  value: number;       // 0–100
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'danger';
  className?: string;
  /** Add a shimmer sweep to the fill (e.g. active uploads) */
  animated?: boolean;
  /** Delay before the fill animates in — useful for staggered lists */
  delay?: number;
}

// ── Token maps ─────────────────────────────────────────────────────────────

const COLOR_MAP: Record<NonNullable<ProgressProps['color']>, string> = {
  primary: 'var(--primary)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  danger:  'var(--danger)',
};

const HEIGHT_MAP: Record<NonNullable<ProgressProps['size']>, string> = {
  sm: '2px',
  md: '4px',
  lg: '6px',
};

// ── Component ──────────────────────────────────────────────────────────────

export function Progress({
  value,
  max = 100,
  label,
  showValue = false,
  size = 'md',
  color = 'primary',
  className,
  animated = false,
  delay = 0,
}: ProgressProps) {
  const prefersReduced = useReducedMotion();
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  // Spring transition for the fill — stiff feels purposeful, not bouncy
  const fillTransition = prefersReduced
    ? { duration: 0 }
    : {
        ...SPRING.stiff,
        delay,
      };

  return (
    <div className={cn('w-full', className)}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && (
            <span className="text-[11px] font-medium text-[var(--text-muted)]">
              {label}
            </span>
          )}
          {showValue && (
            <motion.span
              key={Math.round(pct)}
              initial={prefersReduced ? false : { opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: DURATION.fast, ease: EASE.out }}
              className="text-[11px] font-semibold text-[var(--text)] tabular-nums"
            >
              {Math.round(pct)}%
            </motion.span>
          )}
        </div>
      )}

      {/* Track */}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
        style={{
          height:       HEIGHT_MAP[size],
          background:   'var(--border)',
          borderRadius: '9999px',
          overflow:     'hidden',
          position:     'relative',
        }}
      >
        {/* Fill — motion.div animates width as a percentage */}
        <motion.div
          initial={{ width: '0%' }}
          animate={{ width: `${pct}%` }}
          transition={fillTransition}
          style={{
            height:       '100%',
            background:   animated
              // Animated shimmer gradient
              ? `linear-gradient(90deg, ${COLOR_MAP[color]} 0%, ${COLOR_MAP[color]}cc 50%, ${COLOR_MAP[color]} 100%)`
              : COLOR_MAP[color],
            borderRadius: '9999px',
            backgroundSize: animated ? '200% 100%' : 'auto',
            // Shimmer sweep handled via CSS animation on the fill only
            animation: animated ? 'shimmer 1.5s ease-in-out infinite' : 'none',
          }}
        />
      </div>
    </div>
  );
}
