// =============================================================================
// Cortex API Types
// All shared TypeScript types for the Cortex frontend.
// These map 1:1 to the backend's PostgreSQL enums and table schemas.
// =============================================================================

// Job status enum — matches backend job_status PostgreSQL enum exactly
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

// Artifact types Cortex can generate
export type ArtifactType =
  | 'folder_structure'
  | 'module_breakdown'
  | 'architecture_diagram'
  | 'database_schema'
  | 'api_spec'
  | 'learning_path'
  | 'interview_questions'
  | 'vibe_code_detection';  // added to match backend ArtifactType enum

// Job — maps to the backend jobs table
export interface Job {
  id: string;                   // UUID
  status: JobStatus;
  artifact_type: ArtifactType;
  repo_url: string;
  error_message?: string | null;
  options?: Record<string, unknown>;
  created_at: string;           // ISO 8601
  updated_at: string;           // ISO 8601
  is_terminal: boolean;
}

// JobCreateRequest — POST /api/v1/jobs body
export interface JobCreateRequest {
  repo_url: string;
  artifact_type: ArtifactType;
  options?: Record<string, unknown>;
}

// Artifact — maps to the backend artifacts table
export interface Artifact {
  id: string;                   // UUID
  job_id: string;               // UUID FK
  artifact_type: string;        // added — present in backend response
  content_type: string;
  content_inline: string | null;
  storage_path: string | null;
  created_at: string;
}

// Graph node — from GET /api/v1/graph/nodes
export interface GraphNode {
  id: string;
  label: string;
  node_type: 'Repository' | 'Module' | 'File' | 'Function' | 'Class' | 'Pattern';
  job_id: string;
  properties: Record<string, unknown>;
  created_at: string;
}

// Graph edge — backend returns source_id/target_id (fixed mismatch)
export interface GraphEdge {
  id: string;
  source_id: string;
  target_id: string;
  relationship: 'CONTAINS' | 'IMPORTS' | 'DEPENDS_ON' | 'EXHIBITS' | 'CALLS' | 'INHERITS';
  job_id: string;
  properties: Record<string, unknown>;
  created_at: string;
}

// API error shape returned by the FastAPI backend
export interface ApiError {
  detail: string;
  correlation_id?: string;
}

// ── Insights types ────────────────────────────────────────────────────────────

export type IssueSeverity = 'high' | 'medium' | 'low' | 'info';
export type IssueCategory =
  | 'complexity'
  | 'coupling'
  | 'duplication'
  | 'naming'
  | 'documentation'
  | 'error_handling'
  | 'architecture'
  | 'size';

export interface MetricScore {
  label: string;
  score: number;        // 0–100
  raw_value: number;
  unit: string;
  description: string;
}

export interface HealthDimension {
  name: string;
  score: number;        // 0–100
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  summary: string;
  metrics: MetricScore[];
}

export interface CodeIssue {
  category: IssueCategory;
  severity: IssueSeverity;
  title: string;
  description: string;
  suggestion: string;
  file_path: string;
  line: number;
  affected_symbol: string;
}

export interface InsightsReport {
  job_id: string;
  repo_url: string;
  repo_name: string;
  overall_score: number;
  overall_grade: 'A' | 'B' | 'C' | 'D' | 'F';
  dimensions: HealthDimension[];
  issues: CodeIssue[];
  stats: {
    total_nodes: number;
    total_edges: number;
    repositories: number;
    modules: number;
    files: number;
    classes: number;
    functions: number;
    total_issues: number;
    high_issues: number;
    medium_issues: number;
    low_issues: number;
  };
}
