// =============================================================================
// Types barrel export
// Re-exports all shared types so consumers can import from '@/types'
// =============================================================================

export type {
  JobStatus,
  ArtifactType,
  Job,
  JobCreateRequest,
  Artifact,
  GraphNode,
  GraphEdge,
  ApiError,
  IssueSeverity,
  IssueCategory,
  MetricScore,
  HealthDimension,
  CodeIssue,
  EngineeringConcern,
  AnalysisCoverage,
  InsightsReport,
} from './api.types';

export type {
  EpistemicTag,
  NextActionKind,
  Evidence,
  Claim,
  AnswerSection,
  NextAction,
  CortexAnswer,
} from './answer.types';
