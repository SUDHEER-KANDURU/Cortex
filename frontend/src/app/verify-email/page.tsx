'use client';

/**
 * Email Verification Page — 6-digit OTP code entry.
 * User receives the code via email and enters it here.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, CheckCircle2, RefreshCw, ArrowRight } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { Button } from '@/components/ui/button';
import * as authApi from '@/lib/api/auth';

type VerifyState = 'pending' | 'verifying' | 'success' | 'expired' | 'error';

export default function VerifyEmailPage() {
  const router = useRouter();
  const [state, setState] = useState<VerifyState>('pending');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [errorMessage, setErrorMessage] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [isResending, setIsResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load email from sessionStorage
  useEffect(() => {
    const storedEmail = sessionStorage.getItem('cortex_verify_email');
    if (storedEmail) setEmail(storedEmail);
  }, []);

  // Countdown timer for resend
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

  // Handle OTP digit input
  const handleOtpChange = useCallback((index: number, value: string) => {
    // Only allow digits
    const digit = value.replace(/\D/g, '').slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setErrorMessage('');

    // Auto-focus next input
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits entered
    if (digit && index === 5) {
      const code = newOtp.join('');
      if (code.length === 6) {
        handleVerify(code);
      }
    }
  }, [otp]);

  // Handle paste (paste full OTP)
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      const digits = pasted.split('');
      setOtp(digits);
      inputRefs.current[5]?.focus();
      handleVerify(pasted);
    }
  }, []);

  // Handle backspace
  const handleKeyDown = useCallback((index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }, [otp]);

  // Verify the OTP code
  const handleVerify = useCallback(async (code?: string) => {
    const otpCode = code || otp.join('');
    if (otpCode.length !== 6) {
      setErrorMessage('Please enter all 6 digits.');
      return;
    }

    setState('verifying');
    try {
      await authApi.verifyEmail(otpCode);
      setState('success');
      sessionStorage.removeItem('cortex_verify_email');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Verification failed.';
      if (msg.toLowerCase().includes('expired')) {
        setState('expired');
      } else {
        setState('error');
      }
      setErrorMessage(msg);
    }
  }, [otp]);

  // Resend verification email
  const handleResend = useCallback(async () => {
    if (!email || countdown > 0) return;

    setIsResending(true);
    try {
      await authApi.resendVerification(email);
      setCountdown(60);
      setState('pending');
      setOtp(['', '', '', '', '', '']);
      setErrorMessage('');
      inputRefs.current[0]?.focus();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to resend code.';
      setErrorMessage(message);
    } finally {
      setIsResending(false);
    }
  }, [email, countdown]);

  return (
    <AuthLayout
      title={state === 'success' ? 'Email verified' : 'Verify your email'}
      subtitle={state === 'success' ? undefined : 'Enter the 6-digit code sent to your email'}
    >
      <AnimatePresence mode="wait">
        {/* ── Pending / Error State — OTP Input ── */}
        {(state === 'pending' || state === 'verifying' || state === 'error' || state === 'expired') && (
          <motion.div
            key="otp-input"
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
                We sent a verification code to
              </p>
              <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                {maskedEmail || 'your email address'}
              </p>
            </div>

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
                  disabled={state === 'verifying'}
                  className="w-11 h-13 text-center text-lg font-bold rounded-[var(--radius-md)] border focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-dim)] transition-all duration-150"
                  style={{
                    background: 'var(--surface)',
                    color: 'var(--text)',
                    borderColor: errorMessage ? 'var(--danger)' : 'var(--border)',
                    fontFamily: 'var(--font-mono)',
                  }}
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>

            {/* Error message */}
            {errorMessage && (
              <p className="text-xs" style={{ color: 'var(--danger)' }} role="alert">
                {errorMessage}
              </p>
            )}

            {/* Verify Button */}
            <Button
              onClick={() => handleVerify()}
              loading={state === 'verifying'}
              disabled={state === 'verifying' || otp.join('').length !== 6}
              className="w-full h-12"
              size="lg"
            >
              Verify
            </Button>

            {/* Resend */}
            <div className="pt-2">
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Didn&apos;t receive the code?
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
                  : 'Resend code'}
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
              <span>Continue to Sign in</span>
              <ArrowRight size={16} />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}
