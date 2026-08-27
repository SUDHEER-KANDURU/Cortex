'use client';

/**
 * Forgot Password Page — Request a password reset link.
 * States: form, sending, success.
 */

import React, { useState, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { FloatingInput } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import * as authApi from '@/lib/api/auth';

type PageState = 'form' | 'success';

export default function ForgotPasswordPage() {
  const [state, setState] = useState<PageState>('form');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resetToken, setResetToken] = useState('');

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await authApi.forgotPassword(email.trim());
      // Store token for demo purposes (in production this would be emailed)
      if (response.token) {
        setResetToken(response.token);
        sessionStorage.setItem('cortex_reset_token', response.token);
      }
      setState('success');
    } catch (err: any) {
      setError(err?.message || 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [email]);

  return (
    <AuthLayout
      title={state === 'success' ? 'Check your email' : 'Reset your password'}
      subtitle={state === 'success' ? undefined : 'Enter your email and we\'ll send you a reset link'}
    >
      <AnimatePresence mode="wait">
        {/* ── Form State ── */}
        {state === 'form' && (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
          >
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Error */}
              <AnimatePresence mode="wait">
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: -8, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-start gap-2 p-3 rounded-[var(--radius-md)] text-sm"
                    style={{
                      background: 'var(--danger-dim)',
                      color: 'var(--danger)',
                      border: '0.5px solid var(--danger)',
                    }}
                    role="alert"
                  >
                    <AlertCircle size={16} className="mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Email */}
              <FloatingInput
                id="forgot-email"
                name="email"
                type="email"
                label="Email"
                icon={<Mail size={16} />}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />

              {/* Submit */}
              <Button
                type="submit"
                loading={isSubmitting}
                disabled={isSubmitting}
                className="w-full h-12"
                size="lg"
              >
                Send reset link
              </Button>
            </form>

            {/* Back to login */}
            <div className="mt-6 text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--text-muted)' }}
              >
                <ArrowLeft size={12} />
                Back to login
              </Link>
            </div>
          </motion.div>
        )}

        {/* ── Success State ── */}
        {state === 'success' && (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="text-center space-y-5"
          >
            <div className="flex justify-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.1 }}
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{
                  background: 'var(--success-dim)',
                  border: '0.5px solid var(--success)',
                }}
              >
                <CheckCircle2 size={28} style={{ color: 'var(--success)' }} />
              </motion.div>
            </div>

            <div className="space-y-2">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                If an account exists for <span className="font-medium" style={{ color: 'var(--text)' }}>{email}</span>,
                you&apos;ll receive a password reset link shortly.
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Check your spam folder if you don&apos;t see it within a few minutes.
              </p>
            </div>

            {/* Demo: direct link to reset page */}
            {resetToken && (
              <Button
                onClick={() => {
                  window.location.href = `/reset-password?token=${resetToken}`;
                }}
                className="w-full h-12"
                size="lg"
              >
                Reset password now
              </Button>
            )}

            <div className="pt-2">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--text-muted)' }}
              >
                <ArrowLeft size={12} />
                Back to login
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}
