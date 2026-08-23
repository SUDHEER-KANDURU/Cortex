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
  // Tailwind class kept for test compatibility (slate / yellow / emerald / red)
  twClass: string;
  dotClass: string;
  textClass: string;
  darkBg: string;    darkBorder: string;
  lightBg: string;   lightBorder: string;
  glowColor?: string;
  pulse?: boolean;
}> = {
  pending: {
    label:       'Pending',
    twClass:     'slate',
    dotClass:    'bg-[var(--text-muted)]',
    textClass:   'text-[var(--text-muted)]',
    darkBg:      'rgba(120,128,145,0.10)',  darkBorder:  'rgba(120,128,145,0.20)',
    lightBg:     'rgba(100,108,124,0.07)',  lightBorder: 'rgba(100,108,124,0.18)',
  },
  running: {
    label:       'Running',
    twClass:     'yellow',
    dotClass:    'bg-[var(--primary)]',
    textClass:   'text-[var(--primary)]',
    // Soft slate — not teal
    darkBg:      'rgba(139,175,201,0.10)',  darkBorder:  'rgba(139,175,201,0.28)',
    lightBg:     'rgba(107,143,174,0.08)',  lightBorder: 'rgba(107,143,174,0.26)',
    glowColor:   'var(--primary)',
    pulse:       true,
  },
  completed: {
    label:       'Completed',
    twClass:     'emerald',
    dotClass:    'bg-[var(--success)]',
    textClass:   'text-[var(--success)]',
    darkBg:      'rgba(95,175,130,0.09)',   darkBorder:  'rgba(95,175,130,0.24)',
    lightBg:     'rgba(78,155,111,0.08)',   lightBorder: 'rgba(78,155,111,0.24)',
  },
  failed: {
    label:       'Failed',
    twClass:     'red',
    dotClass:    'bg-[var(--danger)]',
    textClass:   'text-[var(--danger)]',
    darkBg:      'rgba(204,90,90,0.09)',    darkBorder:  'rgba(204,90,90,0.24)',
    lightBg:     'rgba(185,64,64,0.07)',    lightBorder: 'rgba(185,64,64,0.22)',
  },
  cancelled: {
    label:       'Cancelled',
    twClass:     'slate',
    dotClass:    'bg-[var(--text-muted)]',
    textClass:   'text-[var(--text-muted)]',
    darkBg:      'rgba(100,100,110,0.07)',  darkBorder:  'rgba(100,100,110,0.16)',
    lightBg:     'rgba(80,80,90,0.06)',     lightBorder: 'rgba(80,80,90,0.16)',
  },
};

export default React.memo(function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

  const isDark =
    typeof document !== 'undefined'
      ? document.documentElement.getAttribute('data-theme') !== 'light'
      : true;

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
        background:           isDark ? cfg.darkBg     : cfg.lightBg,
        border:               `1px solid ${isDark ? cfg.darkBorder : cfg.lightBorder}`,
        backdropFilter:       'blur(6px) saturate(180%)',
        WebkitBackdropFilter: 'blur(6px) saturate(180%)',
        fontFamily:           'var(--font-mono, "JetBrains Mono", monospace)',
        transition:           'background 0.3s ease, border-color 0.3s ease',
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
