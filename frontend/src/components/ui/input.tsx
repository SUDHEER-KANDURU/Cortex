'use client';

/**
 * Input — Focus glow animation via Framer Motion spring ring.
 *
 * Motion behaviour:
 *  - On focus: box-shadow ring springs in using motionValue
 *  - On blur: ring springs out
 *  - The ring is rendered as a sibling motion.div behind the input
 *    (avoids repainting the input itself — stays on compositor thread)
 *  - prefers-reduced-motion: plain CSS transitions only
 */

import * as React from 'react';
import { motion, useReducedMotion, useSpring, useTransform } from 'framer-motion';
import { cn } from '@/lib/utils/cn';

// ── Base Input ──────────────────────────────────────────────────────────────

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, onFocus, onBlur, ...props }, ref) => {
    const prefersReduced = useReducedMotion();

    // Spring-animated focus ring opacity (0 → 1)
    const focusProgress = useSpring(0, { stiffness: 400, damping: 28, mass: 0.6 });
    const ringOpacity   = useTransform(focusProgress, [0, 1], [0, 1]);
    const ringScale     = useTransform(focusProgress, [0, 1], [0.97, 1]);

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      if (!prefersReduced) focusProgress.set(1);
      onFocus?.(e);
    };
    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      if (!prefersReduced) focusProgress.set(0);
      onBlur?.(e);
    };

    return (
      <span className="relative block w-full">
        {/* Spring ring — sits behind the input, no layout cost */}
        {!prefersReduced && (
          <motion.span
            aria-hidden
            style={{
              position:     'absolute',
              inset:        -1,
              borderRadius: 'var(--radius-md)',
              boxShadow:    '0 0 0 3px var(--primary-dim)',
              opacity:      ringOpacity,
              scale:        ringScale,
              pointerEvents:'none',
              zIndex:       1,
            }}
          />
        )}
        <input
          type={type}
          className={cn(
            // Layout
            'flex h-10 w-full px-3 py-2',
            // Shape
            'rounded-[var(--radius-md)]',
            // Colors — token-driven so light/dark both work
            'bg-[var(--surface)] text-[var(--text)]',
            'border border-[var(--border)]',
            // Placeholder
            'placeholder:text-[var(--text-muted)]',
            // Focus — CSS ring suppressed when Framer Motion ring is active
            'focus:outline-none',
            prefersReduced
              ? [
                  'focus:border-[var(--primary)]',
                  'focus:shadow-[0_0_0_3px_var(--primary-dim)]',
                  'focus:bg-[var(--card)]',
                ].join(' ')
              : 'focus:border-[var(--primary)] focus:bg-[var(--card)]',
            // Hover
            'hover:border-[var(--border-hover)]',
            // Transition — only non-transform props
            'transition-[border-color,background-color] duration-150 ease-out',
            // Text
            'text-sm font-normal',
            // Disabled
            'disabled:cursor-not-allowed disabled:opacity-45',
            // File input reset
            'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[var(--text)]',
            // Relative z-index so it sits above the spring ring
            'relative z-[2]',
            className
          )}
          ref={ref}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...props}
        />
      </span>
    );
  }
);
Input.displayName = 'Input';

// ── FloatingInput ───────────────────────────────────────────────────────────

interface FloatingInputProps extends InputProps {
  label: string;
  icon?: React.ReactNode;
  error?: string;
}

const FloatingInput = React.forwardRef<HTMLInputElement, FloatingInputProps>(
  ({ label, icon, error, className, id, onFocus, onBlur, ...props }, ref) => {
    const prefersReduced = useReducedMotion();
    const inputId = id ?? `input-${label.toLowerCase().replace(/\s+/g, '-')}`;

    // Spring ring — same pattern as Input
    const focusProgress = useSpring(0, { stiffness: 400, damping: 28, mass: 0.6 });
    const ringOpacity   = useTransform(focusProgress, [0, 1], [0, 1]);
    const ringScale     = useTransform(focusProgress, [0, 1], [0.97, 1]);

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      if (!prefersReduced) focusProgress.set(1);
      onFocus?.(e);
    };
    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      if (!prefersReduced) focusProgress.set(0);
      onBlur?.(e);
    };

    return (
      <div className="relative w-full">
        {/* Icon */}
        {icon && (
          <span
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none z-10"
            aria-hidden="true"
          >
            {icon}
          </span>
        )}

        {/* Spring ring */}
        {!prefersReduced && (
          <motion.span
            aria-hidden
            style={{
              position:     'absolute',
              inset:        -1,
              borderRadius: 'var(--radius-md)',
              boxShadow:    error
                ? '0 0 0 3px var(--danger-dim)'
                : '0 0 0 3px var(--primary-dim)',
              opacity:      ringOpacity,
              scale:        ringScale,
              pointerEvents:'none',
              zIndex:       1,
            }}
          />
        )}

        <input
          ref={ref}
          id={inputId}
          placeholder=" "
          className={cn(
            'peer w-full h-14 rounded-[var(--radius-md)]',
            'bg-[var(--surface)] text-[var(--text)]',
            'border border-[var(--border)]',
            'text-sm font-normal',
            icon ? 'pl-10 pr-4 pt-5 pb-1' : 'px-4 pt-5 pb-1',
            'focus:outline-none focus:border-[var(--primary)]',
            'focus:bg-[var(--card)]',
            'hover:border-[var(--border-hover)]',
            'transition-[border-color,background-color] duration-150 ease-out',
            'disabled:cursor-not-allowed disabled:opacity-45',
            'relative z-[2]',
            error && 'border-[var(--danger)]',
            className
          )}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...props}
        />

        {/* Floating label */}
        <label
          htmlFor={inputId}
          className={cn(
            'absolute pointer-events-none',
            'text-[var(--text-muted)] text-sm',
            'transition-all duration-150 ease-out',
            icon ? 'left-10' : 'left-4',
            'top-1/2 -translate-y-1/2',
            'peer-focus:top-3 peer-focus:translate-y-0 peer-focus:text-[10px]',
            'peer-focus:text-[var(--primary)] peer-focus:font-medium',
            'peer-[:not(:placeholder-shown)]:top-3 peer-[:not(:placeholder-shown)]:translate-y-0',
            'peer-[:not(:placeholder-shown)]:text-[10px] peer-[:not(:placeholder-shown)]:font-medium',
          )}
        >
          {label}
        </label>

        {error && (
          <p
            className="mt-1 text-xs text-[var(--danger)] flex items-center gap-1"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);
FloatingInput.displayName = 'FloatingInput';

export { Input, FloatingInput };
