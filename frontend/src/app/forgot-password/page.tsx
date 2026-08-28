'use client';

/**
 * Forgot Password Page — 3-step flow:
 * 1. Enter email → sends OTP code
 * 2. Enter 6-digit OTP code
 * 3. Set new password
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, CheckCircle2, RefreshCw, ArrowLeft } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { PasswordStrength } from '@/components/auth/PasswordStrength';
import { FloatingInput } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import * as authApi from '@/lib/api/auth';

type Step = 'email' | 'otp' | 'new-password' | 'success';

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [isResending, setIsResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // Step 1: Send reset code
  const handleSendCode = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.forgotPassword(email.trim());
      setStep('otp');
      setCountdown(60);
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send reset code.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }, [email]);

  // OTP digit input handlers
  const handleOtpChange = useCallback((index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setError('');

    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // When all 6 digits entered, move to password step
    if (digit && index === 5) {
      const code = newOtp.join('');
      if (code.length === 6) {
        setStep('new-password');
      }
    }
  }, [otp]);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setOtp(pasted.split(''));
      setStep('new-password');
    }
  }, []);

  const handleKeyDown = useCallback((index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }, [otp]);

  // Step 3: Reset password
  const handleResetPassword = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!password) {
      setError('Please enter a new password.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    const code = otp.join('');
    setIsSubmitting(true);
    try {
      await authApi.resetPassword(code, password);
      setStep('success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reset password.';
      setError(msg);
      // If code is invalid/expired, go back to OTP step
      if (msg.toLowerCase().includes('token') || msg.toLowerCase().includes('expired') || msg.toLowerCase().includes('not found')) {
        setStep('otp');
        setOtp(['', '', '', '', '', '']);
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [otp, password, confirmPassword]);

  // Resend code
  const handleResend = useCallback(async () => {
    if (!email || countdown > 0) return;
    setIsResending(true);
    try {
      await authApi.forgotPassword(email.trim());
      setCountdown(60);
      setOtp(['', '', '', '', '', '']);
      setError('');
      inputRefs.current[0]?.focus();
    } catch {
      setError('Failed to resend code.');
    } finally {
      setIsResending(false);
    }
  }, [email, countdown]);

  const maskedEmail = email
    ? email.replace(/(.{2})(.*)(@.*)/, (_, start, middle, domain) =>
        `${start}${'•'.repeat(Math.min(middle.length, 5))}${domain}`
      )
    : '';

  const titles: Record<Step, string> = {
    email: 'Reset your password',
    otp: 'Enter reset code',
    'new-password': 'Choose new password',
    success: 'Password reset!',
  };

  const subtitles: Record<Step, string | undefined> = {
    email: "Enter your email and we'll send you a code",
    otp: `Enter the 6-digit code sent to ${maskedEmail}`,
    'new-password': 'Create a strong new password',
    success: undefined,
  };

  return (
    <AuthLayout title={titles[step]} subtitle={subtitles[step]}>
      <AnimatePresence mode="wait">
        {/* ── Step 1: Email ── */}
        {step === 'email' && (
          <motion.div
            key="email-step"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <form onSubmit={handleSendCode} className="space-y-4" noValidate>
              {error && (
                <p className="text-xs p-2 rounded-[var(--radius-sm)]" style={{ color: 'var(--danger)', background: 'var(--danger-dim)' }} role="alert">
                  {error}
                </p>
              )}

              <FloatingInput
                id="reset-email"
                name="email"
                type="email"
                label="Email"
                icon={<Mail size={16} />}
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(''); }}
                autoComplete="email"
              />

              <Button
                type="submit"
                loading={isSubmitting}
                disabled={isSubmitting}
                className="w-full h-12"
                size="lg"
              >
                Send reset code
              </Button>
            </form>

            <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
              <Link
                href="/login"
                className="inline-flex items-center gap-1 font-medium transition-colors duration-150"
                style={{ color: 'var(--text)' }}
              >
                <ArrowLeft size={14} /> Back to Sign in
              </Link>
            </p>
          </motion.div>
        )}

        {/* ── Step 2: OTP Code ── */}
        {step === 'otp' && (
          <motion.div
            key="otp-step"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="space-y-5"
          >
            {error && (
              <p className="text-xs p-2 rounded-[var(--radius-sm)]" style={{ color: 'var(--danger)', background: 'var(--danger-dim)' }} role="alert">
                {error}
              </p>
            )}

            {/* OTP Input */}
            <div className="flex justify-center gap-2" onPaste={handlePaste}>
              {otp.map((digit, i) => (
                <input
                  key={i}
                  ref={el => { inputRefs.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  className="w-11 h-13 text-center text-lg font-bold rounded-[var(--radius-md)] border focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-dim)] transition-all duration-150"
                  style={{
                    background: 'var(--surface)',
                    color: 'var(--text)',
                    borderColor: error ? 'var(--danger)' : 'var(--border)',
                    fontFamily: 'var(--font-mono)',
                  }}
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>

            <Button
              onClick={() => {
                const code = otp.join('');
                if (code.length === 6) setStep('new-password');
                else setError('Please enter all 6 digits.');
              }}
              disabled={otp.join('').length !== 6}
              className="w-full h-12"
              size="lg"
            >
              Continue
            </Button>

            {/* Resend */}
            <div className="text-center pt-1">
              <button
                type="button"
                onClick={handleResend}
                disabled={countdown > 0 || isResending}
                className="inline-flex items-center gap-1.5 text-xs font-medium transition-colors duration-150 disabled:opacity-40"
                style={{ color: 'var(--text-secondary)' }}
              >
                <RefreshCw size={12} className={isResending ? 'animate-spin' : ''} />
                {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
              </button>
            </div>
          </motion.div>
        )}

        {/* ── Step 3: New Password ── */}
        {step === 'new-password' && (
          <motion.div
            key="password-step"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <form onSubmit={handleResetPassword} className="space-y-4" noValidate>
              {error && (
                <p className="text-xs p-2 rounded-[var(--radius-sm)]" style={{ color: 'var(--danger)', background: 'var(--danger-dim)' }} role="alert">
                  {error}
                </p>
              )}

              <div>
                <PasswordInput
                  id="new-password"
                  name="password"
                  label="New password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  autoComplete="new-password"
                />
                <PasswordStrength password={password} />
              </div>

              <PasswordInput
                id="confirm-new-password"
                name="confirmPassword"
                label="Confirm new password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setError(''); }}
                autoComplete="new-password"
              />

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
          </motion.div>
        )}

        {/* ── Step 4: Success ── */}
        {step === 'success' && (
          <motion.div
            key="success-step"
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
                Password reset successful!
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
              Continue to Sign in
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}
