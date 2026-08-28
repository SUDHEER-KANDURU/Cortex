// =============================================================================
// NavigateButton — Reusable "Navigate" action button
// Placed on graph nodes, insights, artifacts, modules, endpoints, search results.
// Triggers the Navigate panel to open on the specified entity.
// =============================================================================

'use client';

import React from 'react';
import { Compass } from 'lucide-react';

export interface NavigateButtonProps {
  /** Handler called when the user clicks Navigate */
  onClick: () => void;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Whether to show as icon-only or with label */
  variant?: 'full' | 'icon';
  /** Optional custom label */
  label?: string;
  /** Disabled state */
  disabled?: boolean;
}

export default function NavigateButton({
  onClick,
  size = 'sm',
  variant = 'full',
  label = 'Navigate',
  disabled = false,
}: NavigateButtonProps) {
  const isSm = size === 'sm';
  const iconSize = isSm ? 11 : 13;
  const fontSize = isSm ? 10 : 11;
  const padding = variant === 'icon'
    ? (isSm ? '3px' : '5px')
    : (isSm ? '3px 8px' : '5px 10px');

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title="Navigate — explore how this fits into the system"
      aria-label={`Navigate to ${label}`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding,
        borderRadius: isSm ? 5 : 6,
        border: '0.5px solid rgba(99,102,241,0.3)',
        background: 'rgba(99,102,241,0.08)',
        color: disabled ? 'var(--text-muted)' : '#6366f1',
        cursor: disabled ? 'default' : 'pointer',
        fontSize, fontWeight: 600,
        transition: 'all 0.15s',
        opacity: disabled ? 0.5 : 1,
      }}
      onMouseEnter={e => {
        if (!disabled) {
          e.currentTarget.style.background = 'rgba(99,102,241,0.15)';
          e.currentTarget.style.borderColor = 'rgba(99,102,241,0.5)';
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'rgba(99,102,241,0.08)';
        e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)';
      }}
    >
      <Compass style={{ width: iconSize, height: iconSize }} />
      {variant === 'full' && <span>{label}</span>}
    </button>
  );
}
