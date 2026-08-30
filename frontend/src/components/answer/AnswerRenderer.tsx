// =============================================================================
// AnswerRenderer — the single shared component that renders any CortexAnswer.
//
// Every Cortex output type (Overview, Module Breakdown, API Spec, Learning
// Path, Interview Prep, Scoped Explanation) is produced as a CortexAnswer on
// the backend and rendered here, so presentation is uniform across answer
// types (Req 4.4, Req 8.2).
//
// It renders:
//   - title + summary
//   - each section (heading + claims)
//   - a per-claim epistemic badge (FACT / INFERENCE / PREDICTION), visually
//     distinct — this sets up the trust layer in Task 17
//   - clickable evidence chips (file_path + line range) that invoke the
//     optional onEvidenceClick callback (Task 14 wires navigation)
//   - a confidence + coverage banner
//   - next-action buttons that invoke the optional onNextAction callback
//
// Styling follows the existing frontend convention: inline styles driven by
// CSS variables so both themes work with no hardcoded palette.
// =============================================================================

'use client';

import React from 'react';
import { FileText, ArrowRight } from 'lucide-react';
import CoverageConfidence from './CoverageConfidence';
import EpistemicBadge from './EpistemicBadge';
import type {
  CortexAnswer,
  AnswerSection,
  Claim,
  Evidence,
  NextAction,
} from '@/types';

export interface AnswerRendererProps {
  answer: CortexAnswer;
  /** Invoked when a user clicks an evidence chip. Wired to navigation in Task 14. */
  onEvidenceClick?: (evidence: Evidence) => void;
  /** Invoked when a user clicks a next-action button. */
  onNextAction?: (action: NextAction) => void;
  className?: string;
}

// ── Epistemic badge ───────────────────────────────────────────────────────────
// The per-claim FACT / INFERENCE / PREDICTION badge (Req 5.6) now lives in its
// own reusable, independently-testable component (./EpistemicBadge). The
// three-way distinction there uses colour + a distinct icon + the text label,
// so it does not rely on colour alone.

// ── Evidence chip ─────────────────────────────────────────────────────────────
function formatLineRange(ev: Evidence): string {
  if (ev.line_start == null) return '';
  if (ev.line_end != null && ev.line_end !== ev.line_start) {
    return `:${ev.line_start}-${ev.line_end}`;
  }
  return `:${ev.line_start}`;
}

function EvidenceChip({
  evidence,
  onClick,
}: {
  evidence: Evidence;
  onClick?: (evidence: Evidence) => void;
}) {
  const label = `${evidence.file_path}${formatLineRange(evidence)}`;
  const interactive = Boolean(onClick);
  return (
    <button
      type="button"
      data-testid="evidence-chip"
      data-file-path={evidence.file_path}
      onClick={() => onClick?.(evidence)}
      disabled={!interactive}
      title={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        maxWidth: '100%',
        fontSize: 10,
        fontWeight: 600,
        padding: '3px 8px',
        borderRadius: 6,
        background: 'rgba(255,255,255,0.30)',
        border: '0.5px solid rgba(255,255,255,0.55)',
        color: 'var(--text-secondary)',
        cursor: interactive ? 'pointer' : 'default',
        fontFamily: 'var(--font-mono)',
        transition: 'background 0.15s ease, color 0.15s ease',
      }}
      onMouseEnter={(e) => {
        if (interactive) {
          e.currentTarget.style.background = 'var(--primary-dim)';
          e.currentTarget.style.color = 'var(--primary)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(255,255,255,0.30)';
        e.currentTarget.style.color = 'var(--text-secondary)';
      }}
    >
      <FileText style={{ width: 11, height: 11, flexShrink: 0 }} aria-hidden="true" />
      <span
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
    </button>
  );
}

// ── Claim ─────────────────────────────────────────────────────────────────────
function ClaimRow({
  claim,
  onEvidenceClick,
}: {
  claim: Claim;
  onEvidenceClick?: (evidence: Evidence) => void;
}) {
  return (
    <li
      data-testid="claim"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        padding: '10px 12px',
        borderRadius: 10,
        background: 'rgba(255,255,255,0.30)',
        border: '0.5px solid rgba(255,255,255,0.50)',
        listStyle: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <EpistemicBadge tag={claim.epistemic} />
        <span
          style={{
            fontSize: 13,
            color: 'var(--text)',
            lineHeight: 1.55,
            margin: 0,
          }}
        >
          {claim.text}
        </span>
      </div>
      {claim.evidence.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', paddingLeft: 2 }}>
          {claim.evidence.map((ev, i) => (
            <EvidenceChip
              key={`${ev.file_path}-${ev.line_start ?? 'x'}-${i}`}
              evidence={ev}
              onClick={onEvidenceClick}
            />
          ))}
        </div>
      )}
    </li>
  );
}

// ── Section ───────────────────────────────────────────────────────────────────
function Section({
  section,
  onEvidenceClick,
}: {
  section: AnswerSection;
  onEvidenceClick?: (evidence: Evidence) => void;
}) {
  return (
    <section data-testid="answer-section">
      <h3
        style={{
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
          margin: '0 0 10px',
          fontFamily: 'var(--font-mono)',
        }}
      >
        {section.heading}
      </h3>
      <ul style={{ display: 'flex', flexDirection: 'column', gap: 8, margin: 0, padding: 0 }}>
        {section.claims.map((claim, i) => (
          <ClaimRow key={i} claim={claim} onEvidenceClick={onEvidenceClick} />
        ))}
      </ul>
    </section>
  );
}

// ── Confidence + coverage banner ────────────────────────────────────────────
// Rendered through the shared CoverageConfidence component so the per-answer
// and per-analysis surfaces stay visually consistent (Req 6.4). For an answer,
// Coverage is carried as the free-text coverage_note caveat.

// ── Next-action button ────────────────────────────────────────────────────────
function NextActionButton({
  action,
  onNextAction,
}: {
  action: NextAction;
  onNextAction?: (action: NextAction) => void;
}) {
  return (
    <button
      type="button"
      data-testid="next-action"
      data-kind={action.kind}
      onClick={() => onNextAction?.(action)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 12,
        fontWeight: 600,
        padding: '8px 14px',
        borderRadius: 10,
        background: 'var(--primary-dim)',
        border: '0.5px solid rgba(255,255,255,0.45)',
        color: 'var(--primary)',
        cursor: 'pointer',
        transition: 'filter 0.15s ease',
        fontFamily: 'var(--font-sans)',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.filter = 'brightness(0.97)')}
      onMouseLeave={(e) => (e.currentTarget.style.filter = '')}
    >
      {action.label}
      <ArrowRight style={{ width: 12, height: 12 }} aria-hidden="true" />
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AnswerRenderer({
  answer,
  onEvidenceClick,
  onNextAction,
  className,
}: AnswerRendererProps) {
  return (
    <article
      data-testid="answer-renderer"
      data-intent={answer.intent}
      className={className}
      aria-label={answer.title}
      style={{ display: 'flex', flexDirection: 'column', gap: 20 }}
    >
      {/* Title + summary */}
      <header style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <h2
          data-testid="answer-title"
          style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', margin: 0, lineHeight: 1.3 }}
        >
          {answer.title}
        </h2>
        {answer.summary && (
          <p
            data-testid="answer-summary"
            style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}
          >
            {answer.summary}
          </p>
        )}
      </header>

      {/* Confidence + coverage banner */}
      <CoverageConfidence
        testId="confidence-banner"
        confidence={answer.confidence}
        coverageNote={answer.coverage_note}
      />

      {/* Sections */}
      {answer.sections.map((section, i) => (
        <Section key={i} section={section} onEvidenceClick={onEvidenceClick} />
      ))}

      {/* Next actions */}
      {answer.next_actions.length > 0 && (
        <div
          data-testid="next-actions"
          style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}
        >
          {answer.next_actions.map((action, i) => (
            <NextActionButton key={i} action={action} onNextAction={onNextAction} />
          ))}
        </div>
      )}
    </article>
  );
}
