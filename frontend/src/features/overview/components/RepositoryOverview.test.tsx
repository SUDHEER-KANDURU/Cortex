// =============================================================================
// RepositoryOverview tests — Req 6.4 (Coverage + Confidence per analysis)
// Asserts the Overview surface renders a Coverage/Confidence indicator showing
// analyzed/total files and a confidence indicator, driven by the real analysis
// coverage when available and degrading to a caveat when it is not.
// The heavy child features (Delta, AnswerView) are stubbed so the test
// isolates the coverage display; the real CoverageConfidence renders.
// =============================================================================

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { OverviewData, HealthData } from '@/lib/api/overview.api';
import type { AnalysisCoverage } from '@/types';

// ── Stub the data hook so we control overview/health/coverage ────────────────
const mockUseOverview = vi.fn();
vi.mock('../hooks/useOverview', () => ({
  useOverview: (jobId: string | null) => mockUseOverview(jobId),
}));

// ── Stub heavy child features (irrelevant to this test) ──────────────────────
vi.mock('@/features/delta', () => ({
  DeltaIntelligence: () => <div data-testid="delta-stub" />,
}));
vi.mock('@/features/answer', () => ({
  AnswerView: () => <div data-testid="answer-view-stub" />,
  overviewToAnswer: () => ({}),
}));

import RepositoryOverview from './RepositoryOverview';

const OVERVIEW: OverviewData = {
  repo_name: 'acme-service',
  repo_url: 'https://github.com/acme/service',
  total_files: 120,
  total_lines: 10000,
  total_modules: 8,
  total_classes: 40,
  total_functions: 300,
  total_endpoints: 24,
  total_tests: 60,
  languages: ['TypeScript'],
  overall_score: 78,
  overall_grade: 'B',
  avg_complexity: 3.2,
  max_complexity: 18,
  documentation_ratio: 0.6,
  test_ratio: 0.5,
};

const HEALTH: HealthData = {
  overall_score: 84,
  overall_grade: 'B',
  dimensions: [],
  top_issues: [],
};

const COVERAGE: AnalysisCoverage = {
  total_files_in_repo: 130,
  source_files: 120,
  test_files: 60,
  generated_files: 0,
  vendor_files: 0,
  config_files: 4,
  unsupported_files: 2,
  analyzed_files: 114,
  skipped_files: 6,
  coverage_pct: 95,
  languages_detected: ['TypeScript'],
};

beforeEach(() => {
  mockUseOverview.mockReset();
});

describe('RepositoryOverview coverage/confidence (Req 6.4)', () => {
  it('renders analyzed/total files and a confidence indicator from real coverage', () => {
    mockUseOverview.mockReturnValue({
      overview: OVERVIEW,
      health: HEALTH,
      coverage: COVERAGE,
      isLoading: false,
      error: null,
    });

    render(<RepositoryOverview jobId="job-1" />);

    const cc = screen.getByTestId('coverage-confidence');
    expect(cc).toBeInTheDocument();

    // Confidence comes from the overall health score (84 → 84%).
    expect(screen.getByTestId('confidence-value')).toHaveTextContent('84%');

    // Coverage shows analyzed vs. total files from the real analysis coverage.
    expect(screen.getByTestId('coverage-files')).toHaveTextContent('114 of 120 files analyzed');
  });

  it('falls back to a caveat when analysis coverage is unavailable', () => {
    mockUseOverview.mockReturnValue({
      overview: OVERVIEW,
      health: HEALTH,
      coverage: null,
      isLoading: false,
      error: null,
    });

    render(<RepositoryOverview jobId="job-1" />);

    expect(screen.getByTestId('coverage-confidence')).toBeInTheDocument();
    expect(screen.getByTestId('confidence-value')).toHaveTextContent('84%');
    expect(screen.queryByTestId('coverage-stats')).toBeNull();
    expect(screen.getByTestId('coverage-note')).toHaveTextContent(
      'Detailed file coverage is not available'
    );
  });
});
