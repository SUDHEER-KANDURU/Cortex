import * as React from 'react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Progress — Linear progress bar using design tokens
// =============================================================================

export interface ProgressProps {
  value: number;       // 0–100
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'danger';
  className?: string;
  animated?: boolean;
}

const COLOR_MAP = {
  primary: 'var(--primary)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  danger:  'var(--danger)',
} as const;

const HEIGHT_MAP = {
  sm: '2px',
  md: '4px',
  lg: '6px',
} as const;

export function Progress({
  value,
  max = 100,
  label,
  showValue = false,
  size = 'md',
  color = 'primary',
  className,
  animated = false,
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && (
            <span className="text-[11px] font-medium text-[var(--text-muted)]">{label}</span>
          )}
          {showValue && (
            <span className="text-[11px] font-semibold text-[var(--text)] tabular-nums">
              {Math.round(pct)}%
            </span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
        style={{
          height: HEIGHT_MAP[size],
          background: 'var(--border)',
          borderRadius: '9999px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: COLOR_MAP[color],
            borderRadius: '9999px',
            transition: 'width 0.5s cubic-bezier(0.16,1,0.3,1)',
            animation: animated ? 'shimmer 1.5s ease-in-out infinite' : 'none',
            backgroundSize: animated ? '200% 100%' : 'auto',
          }}
        />
      </div>
    </div>
  );
}
