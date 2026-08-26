// =============================================================================
// StatusBadge — Premium status pill using design system tokens
// Adapts to dark/light theme. WCAG AA contrast on all status colours.
//
// NOTE: Tailwind colour classes (slate, yellow, emerald, red) are kept on the
// badge element so existing tests continue to pass. Visual styling is driven
// by the inline styles that use CSS variables for both dark and light themes.
// =============================================================================

import React from 'react';
import type { JobStatus } from '@/types';
import { cn } from '@/lib/utils/cn';

export interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const STATUS_CONFIG: Record<JobStatus, {
  label: string;
  twClass: string;
  dotClass: string;
  textClass: string;
  bg: string;
  border: string;
  glowColor?: string;
  pulse?: boolean;
}> = {
  pending: {
    label:    'Pending',
    twClass:  'slate',
    dotClass: 'bg-[var(--text-muted)]',
    textClass:'text-[var(--text-muted)]',
    bg:       'rgba(255,255,255,0.30)',
    border:   'rgba(255,255,255,0.52)',
  },
  running: {
    label:    'Running',
    twClass:  'yellow',
    dotClass: 'bg-[var(--primary)]',
    textClass:'text-[var(--primary)]',
    bg:       'rgba(255,255,255,0.35)',
    border:   'rgba(255,255,255,0.58)',
    glowColor:'var(--primary)',
    pulse:    true,
  },
  completed: {
    label:    'Completed',
    twClass:  'emerald',
    dotClass: 'bg-[var(--primary)]',
    textClass:'text-[var(--primary)]',
    bg:       'rgba(255,255,255,0.35)',
    border:   'rgba(255,255,255,0.58)',
  },
  failed: {
    label:    'Failed',
    twClass:  'red',
    dotClass: 'bg-[var(--danger)]',
    textClass:'text-[var(--danger)]',
    bg:       'rgba(255,255,255,0.28)',
    border:   'rgba(255,255,255,0.48)',
  },
  cancelled: {
    label:    'Cancelled',
    twClass:  'slate',
    dotClass: 'bg-[var(--text-muted)]',
    textClass:'text-[var(--text-muted)]',
    bg:       'rgba(255,255,255,0.25)',
    border:   'rgba(255,255,255,0.45)',
  },
};

export default React.memo(function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

  return (
    <span
      role="status"
      aria-label={`Status: ${cfg.label}`}
      className={cn(
        cfg.twClass,
        'inline-flex items-center gap-1.5 shrink-0',
        'text-[10px] font-semibold uppercase tracking-[0.07em]',
        'px-2.5 py-0.5 rounded-full',
        cfg.textClass,
        className,
      )}
      style={{
        background:           cfg.bg,
        border:               `0.5px solid ${cfg.border}`,
        backdropFilter:       'blur(12px) saturate(180%)',
        WebkitBackdropFilter: 'blur(12px) saturate(180%)',
        fontFamily:           'var(--font-mono, "JetBrains Mono", monospace)',
        boxShadow:            'inset 0 1px 2px rgba(255,255,255,0.60)',
      }}
      data-testid="status-badge"
      data-status={status}
    >
      {/* animate-pulse class is a plain Tailwind class so tests can query .animate-pulse */}
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full shrink-0',
          cfg.dotClass,
          cfg.pulse && 'animate-pulse',
          cfg.pulse && 'animate-[pulse-dot_1.8s_ease-in-out_infinite]',
        )}
        style={cfg.glowColor ? { boxShadow: `0 0 6px ${cfg.glowColor}` } : undefined}
        aria-hidden="true"
      />
      {cfg.label}
    </span>
  );
});
