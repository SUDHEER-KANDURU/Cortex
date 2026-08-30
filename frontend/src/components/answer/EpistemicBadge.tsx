// =============================================================================
// EpistemicBadge — the single, reusable badge that visually distinguishes the
// three epistemic tags on a claim (Req 5.6):
//
//   FACT       → green   + check-circle icon
//   INFERENCE  → amber   + lightbulb icon
//   PREDICTION → violet  + trending-up icon
//
// The distinction deliberately does NOT rely on colour alone: each tag also
// carries a distinct icon AND its text label, and the whole badge exposes a
// title + aria-label so it is understandable to assistive technology and to
// users with colour-vision differences (WCAG-friendly).
//
// NOTE: full accessibility validation requires manual testing with assistive
// technologies and expert review; this component aims for the not-colour-alone,
// labelled, and titled baseline rather than a certified WCAG conformance claim.
//
// The `data-testid="epistemic-badge"` + `data-epistemic={tag}` contract is
// preserved so existing consumers (AnswerRenderer and its tests) keep working.
//
// Styling follows the frontend convention: inline styles driven by CSS
// variables + lucide-react icons.
// =============================================================================

import React from 'react';
import { CheckCircle2, Lightbulb, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { EpistemicTag } from '@/types';

interface EpistemicStyle {
  label: string;
  bg: string;
  border: string;
  text: string;
  Icon: LucideIcon;
  /** Short human-readable meaning, surfaced via title/aria for accessibility. */
  meaning: string;
}

// Three visually distinct tags. The distinction (colour + icon + label) is
// enforced in this one place so it stays consistent everywhere the badge is
// used.
const EPISTEMIC_STYLE: Record<EpistemicTag, EpistemicStyle> = {
  fact: {
    label: 'FACT',
    bg: 'rgba(34,197,94,0.10)',
    border: 'rgba(34,197,94,0.35)',
    text: '#16a34a',
    Icon: CheckCircle2,
    meaning: 'Directly grounded in the code',
  },
  inference: {
    label: 'INFERENCE',
    bg: 'rgba(234,179,8,0.10)',
    border: 'rgba(234,179,8,0.35)',
    text: '#ca8a04',
    Icon: Lightbulb,
    meaning: 'Reasoned from the evidence',
  },
  prediction: {
    label: 'PREDICTION',
    bg: 'rgba(139,92,246,0.10)',
    border: 'rgba(139,92,246,0.35)',
    text: '#7c3aed',
    Icon: TrendingUp,
    meaning: 'A projected outcome',
  },
};

export interface EpistemicBadgeProps {
  tag: EpistemicTag;
}

export default function EpistemicBadge({ tag }: EpistemicBadgeProps) {
  // Fall back gracefully for any unexpected value from the backend, still
  // never relying on colour alone (label + neutral icon remain present).
  const style: EpistemicStyle =
    EPISTEMIC_STYLE[tag] ??
    ({
      label: String(tag).toUpperCase(),
      bg: 'rgba(148,163,184,0.12)',
      border: 'rgba(148,163,184,0.35)',
      text: 'var(--text-muted)',
      Icon: Lightbulb,
      meaning: 'Unclassified claim',
    } satisfies EpistemicStyle);

  const { Icon } = style;
  const description = `Epistemic tag: ${style.label} — ${style.meaning}`;

  return (
    <span
      data-testid="epistemic-badge"
      data-epistemic={tag}
      data-icon={style.Icon.displayName ?? style.label}
      role="img"
      aria-label={description}
      title={description}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '0.08em',
        padding: '2px 6px',
        borderRadius: 5,
        background: style.bg,
        border: `0.5px solid ${style.border}`,
        color: style.text,
        flexShrink: 0,
        fontFamily: 'var(--font-mono)',
        lineHeight: 1.4,
        whiteSpace: 'nowrap',
      }}
    >
      <Icon
        data-testid="epistemic-badge-icon"
        style={{ width: 10, height: 10, flexShrink: 0 }}
        aria-hidden="true"
      />
      {style.label}
    </span>
  );
}
