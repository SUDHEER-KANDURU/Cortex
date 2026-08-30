// =============================================================================
// CoverageConfidence — the single shared Coverage + Confidence indicator.
//
// Req 6.4 requires the frontend to display *both* Coverage and Confidence to
// the user for each analysis and each answer. This component is the one place
// that visual language lives, so the per-answer surface (inside the
// AnswerRenderer) and the per-analysis surface (the repository Overview) stay
// consistent.
//
// It renders two clearly-labelled parts:
//   - Confidence: a 0..1 score shown as a labelled bar + percentage. Low
//     confidence (< 0.5) or the presence of a caveat swaps the icon to a
//     warning so a weak answer never looks authoritative.
//   - Coverage:   either free-text (a coverage/confidence caveat carried on a
//     CortexAnswer.coverage_note) or structured stats for an analysis
//     (analyzed vs. total files, resolved vs. unresolved references).
//
// Styling follows the existing frontend convention: inline styles driven by
// CSS variables so both themes work with no hardcoded palette.
// =============================================================================

'use client';

import React from 'react';
import { CheckCircle2, AlertTriangle, Layers } from 'lucide-react';

/** Structured coverage stats for an analysis (Req 6.4, backed by Task 5). */
export interface CoverageStats {
  /** Total files Cortex saw in the repository. */
  totalFiles: number;
  /** Files that parsed successfully and were analyzed. */
  analyzedFiles: number;
  /** References Cortex resolved to a concrete target. Optional — not every
   *  reachable coverage source exposes reference resolution yet. */
  resolvedReferences?: number | null;
  /** References Cortex could not resolve. */
  unresolvedReferences?: number | null;
}

export interface CoverageConfidenceProps {
  /** Confidence in 0..1. */
  confidence: number;
  /** Free-text coverage/confidence caveat (e.g. CortexAnswer.coverage_note). */
  coverageNote?: string | null;
  /** Structured coverage stats for an analysis. */
  coverage?: CoverageStats | null;
  className?: string;
  /** Overrides the root data-testid (defaults to "coverage-confidence"). */
  testId?: string;
}

function confidenceColor(confidence: number): string {
  return confidence >= 0.75 ? '#22c55e' : confidence >= 0.5 ? '#eab308' : '#f97316';
}

function pct(ratio: number): number {
  return Math.round(Math.max(0, Math.min(1, ratio)) * 100);
}

export default function CoverageConfidence({
  confidence,
  coverageNote,
  coverage,
  className,
  testId = 'coverage-confidence',
}: CoverageConfidenceProps) {
  const confidencePct = pct(confidence);
  const color = confidenceColor(confidence);
  const low = confidence < 0.5 || Boolean(coverageNote);
  const ConfidenceIcon = low ? AlertTriangle : CheckCircle2;

  const hasStats = Boolean(coverage && coverage.totalFiles > 0);
  const fileRatio = hasStats ? coverage!.analyzedFiles / coverage!.totalFiles : 1;
  const hasReferences =
    coverage != null &&
    coverage.resolvedReferences != null &&
    coverage.unresolvedReferences != null &&
    coverage.resolvedReferences + coverage.unresolvedReferences > 0;

  return (
    <div
      data-testid={testId}
      data-confidence={confidence}
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        padding: '12px 14px',
        borderRadius: 12,
        background: 'rgba(255,255,255,0.30)',
        border: '0.5px solid rgba(255,255,255,0.50)',
      }}
    >
      {/* ── Confidence ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ConfidenceIcon style={{ width: 14, height: 14, color }} aria-hidden="true" />
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>Confidence</span>
        </div>
        <div
          style={{
            flex: 1,
            minWidth: 120,
            height: 6,
            borderRadius: 3,
            background: 'rgba(255,255,255,0.25)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${confidencePct}%`,
              height: '100%',
              borderRadius: 3,
              background: color,
              transition: 'width 0.6s ease',
            }}
          />
        </div>
        <span
          data-testid="confidence-value"
          style={{ fontSize: 12, fontWeight: 700, color, minWidth: 34, textAlign: 'right' }}
        >
          {confidencePct}%
        </span>
      </div>

      {/* ── Coverage (structured stats) ────────────────────────────────────── */}
      {hasStats && (
        <div
          data-testid="coverage-stats"
          style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers style={{ width: 14, height: 14, color: 'var(--text-muted)' }} aria-hidden="true" />
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)' }}>Coverage</span>
          </div>
          <span
            data-testid="coverage-files"
            style={{ fontSize: 12, color: 'var(--text-secondary)' }}
          >
            {coverage!.analyzedFiles.toLocaleString()} of {coverage!.totalFiles.toLocaleString()} files
            analyzed ({pct(fileRatio)}%)
          </span>
          {hasReferences && (
            <span
              data-testid="coverage-references"
              style={{ fontSize: 11, color: 'var(--text-muted)' }}
            >
              · {coverage!.resolvedReferences!.toLocaleString()} resolved /{' '}
              {coverage!.unresolvedReferences!.toLocaleString()} unresolved references
            </span>
          )}
        </div>
      )}

      {/* ── Coverage (free-text caveat) ────────────────────────────────────── */}
      {coverageNote && (
        <p
          data-testid="coverage-note"
          style={{
            fontSize: 11,
            color: 'var(--text-muted)',
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          {coverageNote}
        </p>
      )}
    </div>
  );
}
