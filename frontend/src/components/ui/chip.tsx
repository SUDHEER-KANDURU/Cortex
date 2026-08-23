import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

// =============================================================================
// Chip — Compact selectable/removable token (tags, filters, selections)
// =============================================================================

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  selected?: boolean;
  onRemove?: () => void;
  size?: 'sm' | 'md';
  color?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
}

const COLOR_MAP = {
  default: {
    bg:             'var(--surface)',
    border:         'var(--border)',
    text:           'var(--text-secondary)',
    selectedBg:     'var(--card)',
    selectedBorder: 'var(--border-hover)',
    selectedText:   'var(--text)',
  },
  primary: {
    bg:             'var(--primary-dim)',
    border:         'var(--border-hover)',
    text:           'var(--primary)',
    selectedBg:     'var(--primary-dim)',
    selectedBorder: 'var(--primary)',
    selectedText:   'var(--primary)',
  },
  success: {
    bg:             'var(--success-dim)',
    border:         'var(--success-dim)',
    text:           'var(--success)',
    selectedBg:     'var(--success-dim)',
    selectedBorder: 'var(--success)',
    selectedText:   'var(--success)',
  },
  warning: {
    bg:             'var(--warning-dim)',
    border:         'var(--warning-dim)',
    text:           'var(--warning)',
    selectedBg:     'var(--warning-dim)',
    selectedBorder: 'var(--warning)',
    selectedText:   'var(--warning)',
  },
  danger: {
    bg:             'var(--danger-dim)',
    border:         'var(--danger-dim)',
    text:           'var(--danger)',
    selectedBg:     'var(--danger-dim)',
    selectedBorder: 'var(--danger)',
    selectedText:   'var(--danger)',
  },
} as const;

export function Chip({
  className,
  selected = false,
  onRemove,
  size = 'md',
  color = 'default',
  children,
  ...props
}: ChipProps) {
  const c = COLOR_MAP[color];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium transition-all duration-150',
        size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-3 py-1',
        className
      )}
      style={{
        background: selected ? c.selectedBg : c.bg,
        border: `1px solid ${selected ? c.selectedBorder : c.border}`,
        color: selected ? c.selectedText : c.text,
        fontFamily: 'var(--font-sans)',
      }}
      {...props}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          aria-label="Remove"
          className="flex items-center justify-center rounded-full w-3.5 h-3.5 hover:bg-[var(--surface)] transition-colors"
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}
    </span>
  );
}
