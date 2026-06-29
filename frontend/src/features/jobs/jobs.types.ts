// =============================================================================
// Jobs Feature — Local Types
// Types specific to the jobs feature that extend or complement the shared
// API types in @/types/api.types.ts.
// =============================================================================

import type { Job } from '@/types';

/** Human-readable labels for each ArtifactType value */
export const ARTIFACT_TYPE_LABELS: Record<string, string> = {
  folder_structure: 'Folder Structure',
  module_breakdown: 'Module Breakdown',
  architecture_diagram: 'Architecture Diagram',
  database_schema: 'Database Schema',
  api_spec: 'API Spec',
  learning_path: 'Learning Path',
  interview_questions: 'Interview Questions',
};

/** State shape managed by the jobs feature */
export interface JobsFeatureState {
  jobs: Job[];
  selectedJobId: string | null;
  isLoading: boolean;
  error: string | null;
}

/** Props for any component that needs to notify when a job is selected */
export interface JobSelectHandler {
  onJobSelected: (job: Job) => void;
}

/** Props for any component that needs to notify when a job is submitted */
export interface JobSubmitHandler {
  onJobSubmitted: (job: Job) => void;
}
