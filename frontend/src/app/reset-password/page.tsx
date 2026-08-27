'use client';

/**
 * Reset Password Page — Set a new password using a valid reset token.
 * Reads token from URL query param or sessionStorage.
 */

import React, { useState, useCallback, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, CheckCircle2, ArrowLeft, ArrowRight } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { PasswordStrength } from '@/components/auth/PasswordStrength';
import { Button } from '@/components/ui/button';
import * as authApi from '@/lib/api/auth';

type PageState = 'form' | 'success' | 'error';

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [state, setState] = useState<PageState>('form');
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Get token from URL or sessionStorage
  useEffect(() => {
    const urlToken = searchParams.get('token');
    const storedToken = sessionStorage.getItem('cortex_reset_token');
    const resolvedToken = urlToken || storedToken || '';
    setToken(resolvedToken);

    if (!resolvedToken) {
      setState('error');
      setError('No reset token found. Please request a new password reset link.');
    }
  }, [searchParams]);

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!password) errors.password = 'Password is required.';
    else if (password.length < 8) errors.password = 'At least 8 characters.';
    if (!confirmPassword) errors.confirmPassword = 'Please confirm your password.';
    else if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [password, confirmPassword]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await authApi.resetPassword(token, password);
      setState('success');
      // Cleanup
      sessionStorage.removeItem('cortex_reset_token');
    } catch (err: any) {
      setError(err?.message || 'Failed to reset password. The link may have expired.');
    } finally {
      setIsSubmitting(false);
    }
  }, [token, password, validate]);

  return (
    <AuthLayout
      title={state === 'success' ? 'Password updated' : 'Set new password'}
      subtitle={state === 'success' ? undefined : 'Choose a strong, unique password'}
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
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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

              {/* New Password */}
              <div>
                <PasswordInput
                  id="reset-password"
                  name="password"
                  label="New password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setFieldErrors(p => ({...p, password: ''})); }}
                  error={fieldErrors.password}
                  autoComplete="new-password"
                />
                <PasswordStrength password={password} />
              </div>

              {/* Confirm Password */}
              <PasswordInput
                id="reset-confirm-password"
                name="confirmPassword"
                label="Confirm new password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setFieldErrors(p => ({...p, confirmPassword: ''})); }}
                error={fieldErrors.confirmPassword}
                autoComplete="new-password"
              />

              {/* Submit */}
              <Button
                type="submit"
                loading={isSubmitting}
                disabled={isSubmitting}
                className="w-full h-12"
                size="lg"
              >
                Reset password
              </Button>
            </form>

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
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                Your password has been updated!
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                You can now sign in with your new password.
              </p>
            </div>

            <Button
              onClick={() => router.push('/login')}
              className="w-full h-12"
              size="lg"
            >
              <span>Sign in</span>
              <ArrowRight size={16} />
            </Button>
          </motion.div>
        )}

        {/* ── Error State (no token) ── */}
        {state === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="text-center space-y-5"
          >
            <div className="flex justify-center">
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{
                  background: 'var(--danger-dim)',
                  border: '0.5px solid var(--danger)',
                }}
              >
                <AlertCircle size={28} style={{ color: 'var(--danger)' }} />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                Invalid reset link
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {error || 'This password reset link is invalid or has expired.'}
              </p>
            </div>

            <Button
              onClick={() => router.push('/forgot-password')}
              variant="ghost"
              className="w-full h-12"
              size="lg"
            >
              Request a new reset link
            </Button>

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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
