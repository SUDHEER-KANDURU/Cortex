'use client';

/**
 * PasswordInput — Input with show/hide toggle, matching Cortex design system.
 */

import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { FloatingInput } from '@/components/ui/input';

interface PasswordInputProps {
  label?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  placeholder?: string;
  id?: string;
  name?: string;
  autoComplete?: string;
}

export function PasswordInput({
  label = 'Password',
  value,
  onChange,
  error,
  id,
  name,
  autoComplete = 'current-password',
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <FloatingInput
        id={id}
        name={name}
        type={visible ? 'text' : 'password'}
        label={label}
        value={value}
        onChange={onChange}
        error={error}
        autoComplete={autoComplete}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisible(!visible)}
        className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-1 rounded-[var(--radius-sm)] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors duration-150"
        aria-label={visible ? 'Hide password' : 'Show password'}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}
