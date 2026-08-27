'use client';

/**
 * Signup Page — Account registration with password strength, confirmation,
 * and terms acknowledgement.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, User, AlertCircle, Check } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { PasswordStrength } from '@/components/auth/PasswordStrength';
import { FloatingInput } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';

export default function SignupPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [isAuthenticated, authLoading, router]);

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!name.trim()) errors.name = 'Name is required.';
    if (!email.trim()) errors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email.';
    if (!password) errors.password = 'Password is required.';
    else if (password.length < 8) errors.password = 'At least 8 characters.';
    if (!confirmPassword) errors.confirmPassword = 'Please confirm your password.';
    else if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';
    if (!agreedToTerms) errors.terms = 'You must agree to the terms.';

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [name, email, password, confirmPassword, agreedToTerms]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const result = await register(name.trim(), email.trim(), password);
      // Store email and token for verification page
      sessionStorage.setItem('cortex_verify_email', result.email);
      sessionStorage.setItem('cortex_verify_token', result.verification_token);
      router.push('/verify-email');
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [name, email, password, validate, register, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) return null;

  return (
    <AuthLayout title="Create your account" subtitle="Start understanding code with Cortex">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Error message */}
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

        {/* Name */}
        <FloatingInput
          id="signup-name"
          name="name"
          type="text"
          label="Full name"
          icon={<User size={16} />}
          value={name}
          onChange={(e) => { setName(e.target.value); setFieldErrors(p => ({...p, name: ''})); }}
          error={fieldErrors.name}
          autoComplete="name"
        />

        {/* Email */}
        <FloatingInput
          id="signup-email"
          name="email"
          type="email"
          label="Email"
          icon={<Mail size={16} />}
          value={email}
          onChange={(e) => { setEmail(e.target.value); setFieldErrors(p => ({...p, email: ''})); }}
          error={fieldErrors.email}
          autoComplete="email"
        />

        {/* Password */}
        <div>
          <PasswordInput
            id="signup-password"
            name="password"
            label="Password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setFieldErrors(p => ({...p, password: ''})); }}
            error={fieldErrors.password}
            autoComplete="new-password"
          />
          <PasswordStrength password={password} />
        </div>

        {/* Confirm Password */}
        <PasswordInput
          id="signup-confirm-password"
          name="confirmPassword"
          label="Confirm password"
          value={confirmPassword}
          onChange={(e) => { setConfirmPassword(e.target.value); setFieldErrors(p => ({...p, confirmPassword: ''})); }}
          error={fieldErrors.confirmPassword}
          autoComplete="new-password"
        />

        {/* Terms */}
        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={agreedToTerms}
            onChange={(e) => { setAgreedToTerms(e.target.checked); setFieldErrors(p => ({...p, terms: ''})); }}
            className="mt-0.5 w-4 h-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)] focus:ring-offset-0 cursor-pointer"
          />
          <span className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            I agree to the{' '}
            <span className="font-medium" style={{ color: 'var(--text)' }}>Terms of Service</span>
            {' '}and{' '}
            <span className="font-medium" style={{ color: 'var(--text)' }}>Privacy Policy</span>
          </span>
        </label>
        {fieldErrors.terms && (
          <p className="text-xs" style={{ color: 'var(--danger)' }} role="alert">
            {fieldErrors.terms}
          </p>
        )}

        {/* Submit */}
        <Button
          type="submit"
          loading={isSubmitting}
          disabled={isSubmitting}
          className="w-full h-12"
          size="lg"
        >
          Create account
        </Button>
      </form>

      {/* Login link */}
      <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
        Already have an account?{' '}
        <Link
          href="/login"
          className="font-medium transition-colors duration-150"
          style={{ color: 'var(--text)' }}
        >
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
