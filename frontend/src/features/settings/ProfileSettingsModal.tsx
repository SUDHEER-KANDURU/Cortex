'use client';

/**
 * ProfileSettingsModal — Edit user profile details and change password (OTP-secured).
 * Two tabs: "Profile" and "Security".
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User, Mail, Building2, Briefcase, Phone, Calendar, Users, Check, KeyRound, RefreshCw } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useAuth } from '@/lib/auth';
import * as authApi from '@/lib/api/auth';

interface ProfileSettingsModalProps {
  open: boolean;
  onClose: () => void;
}

type Tab = 'profile' | 'security';

export function ProfileSettingsModal({ open, onClose }: ProfileSettingsModalProps) {
  const { user, updateUser } = useAuth();
  const [tab, setTab] = useState<Tab>('profile');

  // Profile form state
  const [name, setName] = useState('');
  const [organization, setOrganization] = useState('');
  const [role, setRole] = useState('');
  const [phone, setPhone] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState('');
  const [profileErr, setProfileErr] = useState('');

  // Password change state
  const [pwStep, setPwStep] = useState<'idle' | 'otp'>('idle');
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [pwMsg, setPwMsg] = useState('');
  const [pwErr, setPwErr] = useState('');
  const [countdown, setCountdown] = useState(0);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load user data into form when modal opens
  useEffect(() => {
    if (open && user) {
      setName(user.name || '');
      setOrganization(user.organization || '');
      setRole(user.role || '');
      setPhone(user.phone || '');
      setDateOfBirth(user.date_of_birth || '');
      setGender(user.gender || '');
      setProfileMsg('');
      setProfileErr('');
      setPwStep('idle');
      setPwMsg('');
      setPwErr('');
      setOtp(['', '', '', '', '', '']);
      setNewPassword('');
      setConfirmPassword('');
    }
  }, [open, user]);

  // Lock body scroll
  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Countdown timer
  useEffect(() => {
    if (countdown > 0) {
      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) { if (countdownRef.current) clearInterval(countdownRef.current); return 0; }
          return prev - 1;
        });
      }, 1000);
    }
    return () => { if (countdownRef.current) clearInterval(countdownRef.current); };
  }, [countdown]);

  // ── Save profile ──
  const handleSaveProfile = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileErr('');
    setProfileMsg('');
    if (!name.trim()) { setProfileErr('Name is required.'); return; }

    setSavingProfile(true);
    try {
      const updated = await authApi.updateProfile({
        name: name.trim(),
        organization: organization.trim(),
        role: role.trim(),
        phone: phone.trim(),
        date_of_birth: dateOfBirth,
        gender,
      });
      updateUser(updated);
      setProfileMsg('Profile updated successfully.');
    } catch (err: unknown) {
      setProfileErr(err instanceof Error ? err.message : 'Failed to update profile.');
    } finally {
      setSavingProfile(false);
    }
  }, [name, organization, role, phone, dateOfBirth, gender, updateUser]);

  // ── Request OTP for password change ──
  const handleRequestOtp = useCallback(async () => {
    setPwErr('');
    setPwMsg('');
    setPwSubmitting(true);
    try {
      await authApi.requestPasswordChange();
      setPwStep('otp');
      setCountdown(60);
      setPwMsg('Verification code sent to your email.');
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch (err: unknown) {
      setPwErr(err instanceof Error ? err.message : 'Failed to send code.');
    } finally {
      setPwSubmitting(false);
    }
  }, []);

  // ── OTP input handlers ──
  const handleOtpChange = useCallback((index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setPwErr('');
    if (digit && index < 5) otpRefs.current[index + 1]?.focus();
  }, [otp]);

  const handleOtpKeyDown = useCallback((index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) otpRefs.current[index - 1]?.focus();
  }, [otp]);

  const handleOtpPaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) { setOtp(pasted.split('')); otpRefs.current[5]?.focus(); }
  }, []);

  // ── Confirm password change ──
  const handleConfirmPasswordChange = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setPwErr('');
    const code = otp.join('');
    if (code.length !== 6) { setPwErr('Please enter the 6-digit code.'); return; }
    if (newPassword.length < 8) { setPwErr('Password must be at least 8 characters.'); return; }
    if (newPassword !== confirmPassword) { setPwErr('Passwords do not match.'); return; }

    setPwSubmitting(true);
    try {
      await authApi.confirmPasswordChange(code, newPassword);
      setPwMsg('Password changed successfully!');
      setPwStep('idle');
      setOtp(['', '', '', '', '', '']);
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      setPwErr(err instanceof Error ? err.message : 'Failed to change password.');
    } finally {
      setPwSubmitting(false);
    }
  }, [otp, newPassword, confirmPassword]);

  const inputStyle: React.CSSProperties = {
    width: '100%', height: 44, borderRadius: 10, padding: '0 12px 0 38px',
    background: 'var(--surface)', color: 'var(--text)',
    border: '1px solid var(--border)', fontSize: 14, outline: 'none',
  };
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
    marginBottom: 6, letterSpacing: '0.02em',
  };
  const iconStyle: React.CSSProperties = {
    position: 'absolute', left: 12, top: 34, color: 'var(--text-muted)', pointerEvents: 'none',
  };

  if (typeof window === 'undefined') return null;

  const content = (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0"
            style={{ background: 'rgba(26,24,20,0.6)', backdropFilter: 'blur(8px)' }}
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 24 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
            style={{
              background: '#FEFEFE', border: '1px solid rgba(0,0,0,0.08)',
              boxShadow: '0 24px 48px -12px rgba(0,0,0,0.2)',
            }}
            role="dialog" aria-modal="true"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 shrink-0" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
              <h2 className="text-lg font-bold" style={{ color: '#1A1814', fontFamily: 'var(--font-display)' }}>Account Settings</h2>
              <button type="button" onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full transition-colors hover:bg-black/5" style={{ color: '#6B6560' }} aria-label="Close">
                <X size={18} />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 px-6 pt-3 shrink-0" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
              {(['profile', 'security'] as const).map(t => (
                <button
                  key={t} type="button" onClick={() => setTab(t)}
                  className="px-4 py-2 text-sm font-medium transition-colors relative"
                  style={{ color: tab === t ? 'var(--primary)' : 'var(--text-muted)' }}
                >
                  {t === 'profile' ? 'Profile' : 'Security'}
                  {tab === t && <span className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: 'var(--primary)' }} />}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {/* ── Profile Tab ── */}
              {tab === 'profile' && (
                <form onSubmit={handleSaveProfile} className="space-y-4">
                  {profileMsg && (
                    <div className="flex items-center gap-2 text-xs p-2.5 rounded-lg" style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
                      <Check size={14} /> {profileMsg}
                    </div>
                  )}
                  {profileErr && (
                    <div className="text-xs p-2.5 rounded-lg" style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
                      {profileErr}
                    </div>
                  )}

                  {/* Email (read-only) */}
                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Email (cannot be changed)</label>
                    <Mail size={15} style={iconStyle} />
                    <input type="email" value={user?.email || ''} disabled style={{ ...inputStyle, opacity: 0.6, cursor: 'not-allowed' }} />
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Full name</label>
                    <User size={15} style={iconStyle} />
                    <input type="text" value={name} onChange={e => setName(e.target.value)} style={inputStyle} placeholder="Your name" />
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Phone number</label>
                    <Phone size={15} style={iconStyle} />
                    <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} style={inputStyle} placeholder="+1 234 567 8900" />
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Date of birth</label>
                    <Calendar size={15} style={iconStyle} />
                    <input type="date" value={dateOfBirth} onChange={e => setDateOfBirth(e.target.value)} style={inputStyle} />
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Gender</label>
                    <Users size={15} style={iconStyle} />
                    <select value={gender} onChange={e => setGender(e.target.value)} style={{ ...inputStyle, appearance: 'none', cursor: 'pointer' }}>
                      <option value="">Select gender</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="non-binary">Non-binary</option>
                      <option value="prefer-not-to-say">Prefer not to say</option>
                    </select>
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Organization</label>
                    <Building2 size={15} style={iconStyle} />
                    <input type="text" value={organization} onChange={e => setOrganization(e.target.value)} style={inputStyle} placeholder="Company / school" />
                  </div>

                  <div style={{ position: 'relative' }}>
                    <label style={labelStyle}>Job title / Role</label>
                    <Briefcase size={15} style={iconStyle} />
                    <input type="text" value={role} onChange={e => setRole(e.target.value)} style={inputStyle} placeholder="e.g. Engineer" />
                  </div>

                  <button
                    type="submit" disabled={savingProfile}
                    className="w-full h-11 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-50"
                    style={{ background: '#1A1814', color: '#fff' }}
                  >
                    {savingProfile ? 'Saving...' : 'Save changes'}
                  </button>
                </form>
              )}

              {/* ── Security Tab ── */}
              {tab === 'security' && (
                <div className="space-y-4">
                  {pwMsg && (
                    <div className="flex items-center gap-2 text-xs p-2.5 rounded-lg" style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
                      <Check size={14} /> {pwMsg}
                    </div>
                  )}
                  {pwErr && (
                    <div className="text-xs p-2.5 rounded-lg" style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
                      {pwErr}
                    </div>
                  )}

                  {pwStep === 'idle' && (
                    <div className="space-y-4">
                      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        To change your password, we&apos;ll send a 6-digit verification code to your email
                        <strong style={{ color: 'var(--text)' }}> {user?.email}</strong>.
                      </p>
                      <button
                        type="button" onClick={handleRequestOtp} disabled={pwSubmitting}
                        className="w-full h-11 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-opacity hover:opacity-90 disabled:opacity-50"
                        style={{ background: '#1A1814', color: '#fff' }}
                      >
                        <KeyRound size={15} />
                        {pwSubmitting ? 'Sending...' : 'Send verification code'}
                      </button>
                    </div>
                  )}

                  {pwStep === 'otp' && (
                    <form onSubmit={handleConfirmPasswordChange} className="space-y-4">
                      <div>
                        <label style={labelStyle}>Enter the 6-digit code</label>
                        <div className="flex gap-2" onPaste={handleOtpPaste}>
                          {otp.map((digit, i) => (
                            <input
                              key={i}
                              ref={el => { otpRefs.current[i] = el; }}
                              type="text" inputMode="numeric" maxLength={1} value={digit}
                              onChange={e => handleOtpChange(i, e.target.value)}
                              onKeyDown={e => handleOtpKeyDown(i, e)}
                              className="w-10 h-12 text-center text-lg font-bold rounded-lg border focus:outline-none focus:border-[var(--primary)]"
                              style={{ background: 'var(--surface)', color: 'var(--text)', borderColor: 'var(--border)', fontFamily: 'var(--font-mono)' }}
                            />
                          ))}
                        </div>
                      </div>

                      <div style={{ position: 'relative' }}>
                        <label style={labelStyle}>New password</label>
                        <KeyRound size={15} style={iconStyle} />
                        <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} style={inputStyle} placeholder="At least 8 characters" autoComplete="new-password" />
                      </div>

                      <div style={{ position: 'relative' }}>
                        <label style={labelStyle}>Confirm new password</label>
                        <KeyRound size={15} style={iconStyle} />
                        <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} style={inputStyle} placeholder="Re-enter password" autoComplete="new-password" />
                      </div>

                      <button
                        type="submit" disabled={pwSubmitting}
                        className="w-full h-11 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-50"
                        style={{ background: '#1A1814', color: '#fff' }}
                      >
                        {pwSubmitting ? 'Changing...' : 'Change password'}
                      </button>

                      <div className="text-center">
                        <button
                          type="button" onClick={handleRequestOtp} disabled={countdown > 0}
                          className="inline-flex items-center gap-1.5 text-xs font-medium disabled:opacity-40"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          <RefreshCw size={12} />
                          {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );

  return createPortal(content, document.body);
}
