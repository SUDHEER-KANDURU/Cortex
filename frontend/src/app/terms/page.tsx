'use client';

/**
 * Terms of Service Page — Standalone page for direct access.
 */

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import { TermsContent } from '@/components/auth/TermsContent';

export default function TermsPage() {
  return (
    <div className="min-h-screen px-4 py-12 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        className="mx-auto max-w-3xl"
      >
        {/* Back link */}
        <Link
          href="/signup"
          className="inline-flex items-center gap-1.5 text-sm font-medium mb-8 transition-colors duration-150"
          style={{ color: 'var(--text-secondary)' }}
        >
          <ArrowLeft size={16} />
          Back to Sign up
        </Link>

        {/* Content Card */}
        <div
          className="rounded-[var(--radius-xl)] p-8 sm:p-12"
          style={{
            background: 'var(--glass-modal)',
            backdropFilter: 'var(--glass-blur-md)',
            WebkitBackdropFilter: 'var(--glass-blur-md)',
            border: '0.5px solid var(--border)',
            boxShadow: 'var(--glass-shadow), var(--glass-inset)',
          }}
        >
          <h1
            className="text-2xl font-bold tracking-[-0.03em] mb-6"
            style={{ color: 'var(--text)', fontFamily: 'var(--font-display)' }}
          >
            Terms of Service
          </h1>
          <TermsContent />
        </div>
      </motion.div>
    </div>
  );
}
