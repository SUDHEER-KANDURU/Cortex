import * as React from 'react';
import { cn } from '@/lib/utils/cn';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

// =============================================================================
// Input — Premium input with design system tokens
// Uses CSS variables — adapts to dark/light theme automatically
// =============================================================================

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Layout
          'flex h-10 w-full px-3 py-2',
          // Shape
          'rounded-[var(--radius-md)]',
          // Colors — use design tokens
          'bg-[rgba(255,255,255,0.05)] text-[var(--text)]',
          'border border-[var(--border)]',
          // Placeholder
          'placeholder:text-[var(--text-muted)]',
          // Focus
          'focus:outline-none focus:border-[var(--primary)]',
          'focus:shadow-[0_0_0_3px_var(--primary-dim)]',
          'focus:bg-[rgba(255,255,255,0.07)]',
          // Hover
          'hover:border-[var(--border-hover)]',
          // Transition
          'transition-all duration-200 ease-out',
          // Text
          'text-sm font-normal',
          // Disabled
          'disabled:cursor-not-allowed disabled:opacity-45',
          // File input
          'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[var(--text)]',
          // Light mode overrides via data-theme
          '[data-theme="light"]_&:bg-white [data-theme="light"]_&:border-[rgba(0,0,0,0.10)]',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

// Premium input with floating label
interface FloatingInputProps extends InputProps {
  label: string;
  icon?: React.ReactNode;
  error?: string;
}

const FloatingInput = React.forwardRef<HTMLInputElement, FloatingInputProps>(
  ({ label, icon, error, className, id, ...props }, ref) => {
    const inputId = id ?? `input-${label.toLowerCase().replace(/\s+/g, '-')}`;
    return (
      <div className="relative w-full">
        {icon && (
          <span
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none z-10"
            aria-hidden="true"
          >
            {icon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          placeholder=" "
          className={cn(
            'peer w-full h-14 rounded-[var(--radius-md)]',
            'bg-[rgba(255,255,255,0.05)] text-[var(--text)]',
            'border border-[var(--border)]',
            'text-sm font-normal',
            icon ? 'pl-10 pr-4 pt-5 pb-1' : 'px-4 pt-5 pb-1',
            'focus:outline-none focus:border-[var(--primary)]',
            'focus:shadow-[0_0_0_3px_var(--primary-dim)]',
            'hover:border-[var(--border-hover)]',
            'transition-all duration-200 ease-out',
            'disabled:cursor-not-allowed disabled:opacity-45',
            error && 'border-[var(--danger)] focus:shadow-[0_0_0_3px_var(--danger-dim)]',
            className
          )}
          {...props}
        />
        <label
          htmlFor={inputId}
          className={cn(
            'absolute pointer-events-none',
            'text-[var(--text-muted)] text-sm',
            'transition-all duration-200 ease-out',
            icon ? 'left-10' : 'left-4',
            // Float up when focused or has value
            'top-1/2 -translate-y-1/2',
            'peer-focus:top-3 peer-focus:translate-y-0 peer-focus:text-[10px] peer-focus:text-[var(--primary)] peer-focus:font-medium',
            'peer-[:not(:placeholder-shown)]:top-3 peer-[:not(:placeholder-shown)]:translate-y-0',
            'peer-[:not(:placeholder-shown)]:text-[10px] peer-[:not(:placeholder-shown)]:font-medium',
          )}
        >
          {label}
        </label>
        {error && (
          <p className="mt-1 text-xs text-[var(--danger)] flex items-center gap-1" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);
FloatingInput.displayName = 'FloatingInput';

export { Input, FloatingInput };
