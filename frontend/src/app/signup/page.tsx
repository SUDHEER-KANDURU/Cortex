'use client';

/**
 * Signup Page — Account registration with password strength, confirmation,
 * and terms acknowledgement.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, User, AlertCircle, Building2, Briefcase, Phone, Calendar, Users } from 'lucide-react';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { PasswordStrength } from '@/components/auth/PasswordStrength';
import { LegalModal } from '@/components/auth/LegalModal';
import { TermsContent } from '@/components/auth/TermsContent';
import { PrivacyContent } from '@/components/auth/PrivacyContent';
import { FloatingInput } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';

export default function SignupPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [role, setRole] = useState('');
  const [phone, setPhone] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [showTerms, setShowTerms] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

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
      const result = await register({
        name: name.trim(),
        email: email.trim(),
        password,
        organization: organization.trim() || undefined,
        role: role.trim() || undefined,
        phone: phone.trim() || undefined,
        date_of_birth: dateOfBirth || undefined,
        gender: gender || undefined,
      });
      // Store email for verification page
      sessionStorage.setItem('cortex_verify_email', result.email);
      router.push('/verify-email');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [name, email, password, organization, role, phone, dateOfBirth, gender, validate, register, router]);

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

        {/* Organization */}
        <FloatingInput
          id="signup-organization"
          name="organization"
          type="text"
          label="Organization (optional)"
          icon={<Building2 size={16} />}
          value={organization}
          onChange={(e) => setOrganization(e.target.value)}
          autoComplete="organization"
        />

        {/* Role / Title */}
        <FloatingInput
          id="signup-role"
          name="role"
          type="text"
          label="Job title / Role (optional)"
          icon={<Briefcase size={16} />}
          value={role}
          onChange={(e) => setRole(e.target.value)}
          autoComplete="organization-title"
        />

        {/* Phone */}
        <FloatingInput
          id="signup-phone"
          name="phone"
          type="tel"
          label="Phone number (optional)"
          icon={<Phone size={16} />}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          autoComplete="tel"
        />

        {/* Date of Birth */}
        <div className="relative w-full">
          <label
            htmlFor="signup-dob"
            className="absolute left-10 top-2 text-[10px] font-medium pointer-events-none z-10"
            style={{ color: 'var(--text-muted)' }}
          >
            Date of birth (optional)
          </label>
          <span
            className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-10"
            style={{ color: 'var(--text-muted)' }}
          >
            <Calendar size={16} />
          </span>
          <input
            id="signup-dob"
            name="date_of_birth"
            type="date"
            value={dateOfBirth}
            onChange={(e) => setDateOfBirth(e.target.value)}
            className="w-full h-14 rounded-[var(--radius-md)] border pl-10 pr-4 pt-5 pb-1 text-sm focus:outline-none focus:border-[var(--primary)] transition-colors duration-150"
            style={{
              background: 'var(--surface)',
              color: 'var(--text)',
              borderColor: 'var(--border)',
            }}
          />
        </div>

        {/* Gender */}
        <div className="relative w-full">
          <label
            htmlFor="signup-gender"
            className="absolute left-10 top-2 text-[10px] font-medium pointer-events-none z-10"
            style={{ color: 'var(--text-muted)' }}
          >
            Gender (optional)
          </label>
          <span
            className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-10"
            style={{ color: 'var(--text-muted)' }}
          >
            <Users size={16} />
          </span>
          <select
            id="signup-gender"
            name="gender"
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full h-14 rounded-[var(--radius-md)] border pl-10 pr-4 pt-5 pb-1 text-sm focus:outline-none focus:border-[var(--primary)] transition-colors duration-150 appearance-none cursor-pointer"
            style={{
              background: 'var(--surface)',
              color: gender ? 'var(--text)' : 'var(--text-muted)',
              borderColor: 'var(--border)',
            }}
          >
            <option value="">Select gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="non-binary">Non-binary</option>
            <option value="prefer-not-to-say">Prefer not to say</option>
          </select>
        </div>

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
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); setShowTerms(true); }}
              className="font-medium underline transition-colors duration-150 hover:opacity-80 cursor-pointer"
              style={{ color: 'var(--text)' }}
            >
              Terms of Service
            </button>
            {' '}and{' '}
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); setShowPrivacy(true); }}
              className="font-medium underline transition-colors duration-150 hover:opacity-80 cursor-pointer"
              style={{ color: 'var(--text)' }}
            >
              Privacy Policy
            </button>
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

      {/* Legal Modals */}
      <LegalModal open={showTerms} onClose={() => setShowTerms(false)} title="Terms of Service">
        <TermsContent />
      </LegalModal>
      <LegalModal open={showPrivacy} onClose={() => setShowPrivacy(false)} title="Privacy Policy">
        <PrivacyContent />
      </LegalModal>
    </AuthLayout>
  );
}
