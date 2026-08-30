// =============================================================================
// CoverageConfidence tests — Req 6.4
// The one shared Coverage + Confidence indicator must clearly surface BOTH a
// confidence value and coverage information, in two modes:
//   - per answer: a confidence value + a free-text coverage caveat
//   - per analysis: a confidence value + structured coverage stats
//     (analyzed/total files, resolved/unresolved references)
// =============================================================================

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CoverageConfidence from './CoverageConfidence';

describe('CoverageConfidence', () => {
  it('renders the confidence value and a free-text coverage caveat (per answer)', () => {
    render(
      <CoverageConfidence
        confidence={0.82}
        coverageNote="Analyzed 48 of 50 files; 2 files skipped."
      />
    );

    expect(screen.getByTestId('confidence-value')).toHaveTextContent('82%');
    expect(screen.getByTestId('coverage-note')).toHaveTextContent(
      'Analyzed 48 of 50 files; 2 files skipped.'
    );
    // No structured stats in the free-text mode.
    expect(screen.queryByTestId('coverage-stats')).toBeNull();
  });

  it('renders structured coverage stats with a confidence indicator (per analysis)', () => {
    render(
      <CoverageConfidence
        confidence={0.9}
        coverage={{
          totalFiles: 120,
          analyzedFiles: 114,
          resolvedReferences: 480,
          unresolvedReferences: 20,
        }}
      />
    );

    // Confidence is always shown.
    expect(screen.getByTestId('confidence-value')).toHaveTextContent('90%');

    // Coverage is labelled and shows analyzed/total files.
    const stats = screen.getByTestId('coverage-stats');
    expect(stats).toHaveTextContent('Coverage');
    expect(screen.getByTestId('coverage-files')).toHaveTextContent('114 of 120 files analyzed');
    expect(screen.getByTestId('coverage-files')).toHaveTextContent('95%');

    // Reference resolution is shown when available.
    expect(screen.getByTestId('coverage-references')).toHaveTextContent(
      '480 resolved / 20 unresolved references'
    );
  });

  it('omits reference stats when resolution counts are not provided', () => {
    render(
      <CoverageConfidence
        confidence={0.7}
        coverage={{ totalFiles: 10, analyzedFiles: 8 }}
      />
    );

    expect(screen.getByTestId('coverage-files')).toHaveTextContent('8 of 10 files analyzed');
    expect(screen.queryByTestId('coverage-references')).toBeNull();
  });

  it('supports overriding the root testId (for the per-answer banner)', () => {
    render(<CoverageConfidence testId="confidence-banner" confidence={0.5} />);
    expect(screen.getByTestId('confidence-banner')).toBeInTheDocument();
  });
});
