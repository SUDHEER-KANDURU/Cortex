'use client';

/**
 * Email Verification Page — Shows verification state after signup.
 * Handles: pending, resend with countdown, success, failure/expired states.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, CheckCircle2, XCircle, RefreshCw, ArrowRight } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { Button } from '@/components/ui/button';
import * as authApi from '@/lib/api/auth';

type VerifyState = 'pending' | 'verifying' | 'success' | 'expired' | 'error';

export default function VerifyEmailPage() {
  const router = useRouter();
  const [state, setState] = useState<VerifyState>('pending');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [isResending, setIsResending] = useState(false);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load email and token from sessionStorage (set during signup)
  useEffect(() => {
    const storedEmail = sessionStorage.getItem('cortex_verify_email');
    const storedToken = sessionStorage.getItem('cortex_verify_token');
    if (storedEmail) setEmail(storedEmail);
    if (storedToken) setToken(storedToken);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (countdown > 0) {
      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            if (countdownRef.current) clearInterval(countdownRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [countdown]);

  // Mask email for display
  const maskedEmail = email
    ? email.replace(/(.{2})(.*)(@.*)/, (_, start, middle, domain) =>
        `${start}${'•'.repeat(Math.min(middle.length, 5))}${domain}`
      )
    : '';

  // Verify the token
  const handleVerify = useCallback(async () => {
    if (!token) {
      setState('error');
      setErrorMessage('No verification token found. Please sign up again.');
      return;
    }

    setState('verifying');
    try {
      await authApi.verifyEmail(token);
      setState('success');
      // Clean up sessionStorage
      sessionStorage.removeItem('cortex_verify_email');
      sessionStorage.removeItem('cortex_verify_token');
    } catch (err: any) {
      const msg = err?.message || 'Verification failed.';
      if (msg.toLowerCase().includes('expired')) {
        setState('expired');
      } else {
        setState('error');
      }
      setErrorMessage(msg);
    }
  }, [token]);

  // Resend verification email
  const handleResend = useCallback(async () => {
    if (!email || countdown > 0) return;

    setIsResending(true);
    try {
      const response = await authApi.resendVerification(email);
      if (response.token) {
        setToken(response.token);
        sessionStorage.setItem('cortex_verify_token', response.token);
      }
      setCountdown(60);
      setState('pending');
      setErrorMessage('');
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to resend verification email.');
    } finally {
      setIsResending(false);
    }
  }, [email, countdown]);

  return (
    <AuthLayout
      title={state === 'success' ? 'Email verified' : 'Verify your email'}
      subtitle={state === 'success' ? undefined : 'We need to confirm your email address'}
    >
      <AnimatePresence mode="wait">
        {/* ── Pending State ── */}
        {(state === 'pending' || state === 'verifying') && (
          <motion.div
            key="pending"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="text-center space-y-5"
          >
            {/* Icon */}
            <div className="flex justify-center">
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{
                  background: 'var(--primary-dim)',
                  border: '0.5px solid var(--border)',
                }}
              >
                <Mail size={28} style={{ color: 'var(--primary)' }} />
              </div>
            </div>

            {/* Message */}
            <div className="space-y-2">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                We sent a verification link to
              </p>
              <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                {maskedEmail || 'your email address'}
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Click the button below to verify your email, or check your inbox for the link.
              </p>
            </div>

            {/* Verify Button */}
            <Button
              onClick={handleVerify}
              loading={state === 'verifying'}
              disabled={state === 'verifying' || !token}
              className="w-full h-12"
              size="lg"
            >
              Verify my email
            </Button>

            {/* Resend */}
            <div className="pt-2">
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Didn&apos;t receive the email?
              </p>
              <button
                type="button"
                onClick={handleResend}
                disabled={countdown > 0 || isResending}
                className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium transition-colors duration-150 disabled:opacity-40"
                style={{ color: 'var(--text-secondary)' }}
              >
                <RefreshCw size={12} className={isResending ? 'animate-spin' : ''} />
                {countdown > 0
                  ? `Resend in ${countdown}s`
                  : 'Resend verification email'}
              </button>
            </div>

            {/* Change email */}
            <div className="pt-1">
              <Link
                href="/signup"
                className="text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--text-muted)' }}
              >
                Use a different email address
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
                Your email has been verified!
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Your account is now active. Sign in to start using Cortex.
              </p>
            </div>

            <Button
              onClick={() => router.push('/login')}
              className="w-full h-12"
              size="lg"
            >
              <span>Continue to Cortex</span>
              <ArrowRight size={16} />
            </Button>
          </motion.div>
        )}

        {/* ── Error / Expired State ── */}
        {(state === 'error' || state === 'expired') && (
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
                <XCircle size={28} style={{ color: 'var(--danger)' }} />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {state === 'expired' ? 'Verification link expired' : 'Verification failed'}
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {errorMessage || 'Something went wrong. Please try again.'}
              </p>
            </div>

            {/* Resend option */}
            {email && (
              <Button
                onClick={handleResend}
                loading={isResending}
                disabled={countdown > 0 || isResending}
                variant="ghost"
                className="w-full h-12"
                size="lg"
              >
                <RefreshCw size={16} />
                {countdown > 0 ? `Resend in ${countdown}s` : 'Request new verification'}
              </Button>
            )}

            <div className="flex items-center justify-center gap-4 pt-2">
              <Link
                href="/signup"
                className="text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--text-muted)' }}
              >
                Sign up again
              </Link>
              <span className="text-xs" style={{ color: 'var(--border-dark)' }}>•</span>
              <Link
                href="/login"
                className="text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--text-muted)' }}
              >
                Back to login
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}
