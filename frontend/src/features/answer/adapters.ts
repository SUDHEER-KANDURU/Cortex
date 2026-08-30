// =============================================================================
// CortexAnswer adapters
// ---------------------------------------------------------------------------
// The backend (spec Tasks 6-9) produces a CortexAnswer for every intent. Those
// producers are not yet exposed through dedicated frontend endpoints, so these
// adapters build a CortexAnswer from the data each view already has. This lets
// the Overview / Modules / API / Learning Path views render through the single
// shared AnswerRenderer today (Req 4.4, Req 8.2) and gives a clear integration
// point: when a `/api/v1/answers/{intent}` endpoint lands, swap the adapter for
// the real CortexAnswer and delete the adapter — the renderer is unchanged.
//
// Epistemic tagging here follows the same fixed rule set the backend producers
// use: directly-extracted structure = fact, heuristic conclusion = inference,
// forward-looking statement = prediction (Req 5.2-5.4).
// =============================================================================

import type { CortexAnswer, AnswerSection, Claim, NextAction } from '@/types';
import type { OverviewData, HealthData } from '@/lib/api/overview.api';
import type { Artifact } from '@/types';

// ── Overview ────────────────────────────────────────────────────────────────

/** Build a CortexAnswer for the repository overview from overview + health. */
export function overviewToAnswer(
  overview: OverviewData,
  health: HealthData | null
): CortexAnswer {
  const repoEvidence = [{ file_path: overview.repo_url, line_start: null, line_end: null, node_id: null }];

  const structure: Claim[] = [
    {
      text: `${overview.total_modules} modules across ${overview.total_files.toLocaleString()} files (${overview.total_lines.toLocaleString()} lines).`,
      epistemic: 'fact',
      evidence: repoEvidence,
    },
    {
      text: `${overview.total_classes} classes, ${overview.total_functions} functions, ${overview.total_endpoints} API endpoints, ${overview.total_tests} tests.`,
      epistemic: 'fact',
      evidence: repoEvidence,
    },
    {
      text: `Languages detected: ${overview.languages.join(', ') || 'unknown'}.`,
      epistemic: 'fact',
      evidence: repoEvidence,
    },
  ];

  const quality: Claim[] = [
    {
      text: `Average complexity is ${overview.avg_complexity.toFixed(1)} (max ${overview.max_complexity}).`,
      epistemic: 'fact',
      evidence: repoEvidence,
    },
    {
      text: `Documentation ratio ${Math.round(overview.documentation_ratio * 100)}%, test ratio ${Math.round(
        overview.test_ratio * 100
      )}%.`,
      epistemic: 'fact',
      evidence: repoEvidence,
    },
  ];

  const sections: AnswerSection[] = [
    { heading: 'Repository Structure', claims: structure },
    { heading: 'Quality Indicators', claims: quality },
  ];

  if (health && health.dimensions.length > 0) {
    sections.push({
      heading: 'Engineering Health',
      claims: health.dimensions.map((dim) => ({
        text: `${dim.name}: grade ${dim.grade} (${dim.score}/100)${
          dim.summary ? ` — ${dim.summary}` : ''
        }`,
        // Health grades are heuristic conclusions over metrics.
        epistemic: 'inference' as const,
        evidence: repoEvidence,
      })),
    });
  }

  if (health && health.top_issues.length > 0) {
    sections.push({
      heading: 'Top Risks',
      claims: health.top_issues.slice(0, 5).map((issue) => ({
        text: `[${issue.severity}] ${issue.title}${issue.symbol ? ` (${issue.symbol})` : ''}`,
        // Risks are forward-looking statements about what may need attention.
        epistemic: 'prediction' as const,
        evidence: issue.file_path
          ? [{ file_path: issue.file_path, line_start: null, line_end: null, node_id: null }]
          : repoEvidence,
      })),
    });
  }

  const score = health?.overall_score ?? overview.overall_score;

  const nextActions: NextAction[] = [
    { label: 'View module breakdown', kind: 'run_producer', target: 'module_breakdown', line_start: null, line_end: null },
    { label: 'View API spec', kind: 'run_producer', target: 'api_spec', line_start: null, line_end: null },
  ];

  return {
    intent: 'architecture_overview',
    title: overview.repo_name,
    summary: `A ${overview.languages[0] || 'multi-language'} project with ${overview.total_modules} modules and ${
      overview.total_endpoints
    } API endpoints. Overall grade ${health?.overall_grade ?? overview.overall_grade}.`,
    sections,
    confidence: Math.max(0, Math.min(1, score / 100)),
    coverage_note: null,
    next_actions: nextActions,
  };
}

// ── Artifact-backed intents (Modules / API / Learning Path) ──────────────────

const INTENT_META: Record<string, { intent: string; title: string; summary: string }> = {
  module_breakdown: {
    intent: 'module_breakdown',
    title: 'Module Breakdown',
    summary: 'How this repository is organized into modules.',
  },
  api_spec: {
    intent: 'api_spec',
    title: 'API Specification',
    summary: 'The public interface this repository exposes.',
  },
  learning_path: {
    intent: 'learning_path',
    title: 'Learning Path',
    summary: 'A guided order for learning this codebase.',
  },
};

/**
 * Build a CortexAnswer from an artifact whose content is currently plain
 * text / markdown / YAML. Until the backend serves a structured CortexAnswer
 * for these intents, we surface the artifact content as a single FACT claim
 * (it is directly-extracted output) so the view is uniform. When the real
 * endpoint exists, replace this call with the fetched CortexAnswer.
 */
export function artifactToAnswer(artifact: Artifact): CortexAnswer {
  const meta = INTENT_META[artifact.artifact_type] ?? {
    intent: artifact.artifact_type,
    title: artifact.artifact_type,
    summary: '',
  };

  const content = artifact.content_inline ?? '';
  const evidence = [{ file_path: artifact.storage_path ?? artifact.artifact_type, line_start: null, line_end: null, node_id: null }];

  const sections: AnswerSection[] = content
    ? [
        {
          heading: 'Details',
          claims: [{ text: content, epistemic: 'fact', evidence }],
        },
      ]
    : [];

  return {
    intent: meta.intent,
    title: meta.title,
    summary: meta.summary,
    sections,
    confidence: content ? 0.9 : 0,
    coverage_note: content ? null : 'No content was generated for this answer yet.',
    next_actions: [],
  };
}
