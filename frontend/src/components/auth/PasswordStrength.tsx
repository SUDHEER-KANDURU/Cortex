'use client';

/**
 * PasswordStrength — visual password strength indicator.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface PasswordStrengthProps {
  password: string;
}

function calculateStrength(password: string): { score: number; label: string; color: string } {
  if (!password) return { score: 0, label: '', color: 'transparent' };

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  if (score <= 1) return { score: 1, label: 'Weak', color: 'var(--danger)' };
  if (score <= 2) return { score: 2, label: 'Fair', color: 'var(--warning)' };
  if (score <= 3) return { score: 3, label: 'Good', color: 'var(--success)' };
  return { score: 4, label: 'Strong', color: 'var(--primary)' };
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const { score, label, color } = useMemo(() => calculateStrength(password), [password]);

  if (!password) return null;

  return (
    <div className="mt-2">
      <div className="flex gap-1.5">
        {[1, 2, 3, 4].map((level) => (
          <motion.div
            key={level}
            className="h-1 flex-1 rounded-full"
            style={{
              background: level <= score ? color : 'var(--border)',
            }}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.2, delay: level * 0.05 }}
          />
        ))}
      </div>
      <p className="mt-1 text-[11px] font-medium" style={{ color }}>
        {label}
      </p>
    </div>
  );
}
