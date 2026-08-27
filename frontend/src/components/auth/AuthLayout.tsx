'use client';

/**
 * AuthLayout — shared wrapper for all authentication pages.
 * Centers content with the Cortex liquid glass card, matches the
 * existing design system perfectly.
 */

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import Link from 'next/link';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  const prefersReduced = useReducedMotion();

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <motion.div
        initial={prefersReduced ? {} : { opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-[420px]"
      >
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <h1
              className="text-2xl font-bold tracking-[-0.03em]"
              style={{ color: 'var(--text)', fontFamily: 'var(--font-display)' }}
            >
              Cortex
            </h1>
          </Link>
          <h2
            className="mt-3 text-lg font-semibold tracking-[-0.02em]"
            style={{ color: 'var(--text)' }}
          >
            {title}
          </h2>
          {subtitle && (
            <p
              className="mt-1.5 text-sm"
              style={{ color: 'var(--text-muted)' }}
            >
              {subtitle}
            </p>
          )}
        </div>

        {/* Glass Card */}
        <div
          className="rounded-[var(--radius-xl)] p-8 sm:p-10"
          style={{
            background: 'var(--glass-modal)',
            backdropFilter: 'var(--glass-blur-md)',
            WebkitBackdropFilter: 'var(--glass-blur-md)',
            border: '0.5px solid var(--border)',
            boxShadow: 'var(--glass-shadow), var(--glass-inset)',
          }}
        >
          {children}
        </div>
      </motion.div>
    </div>
  );
}
