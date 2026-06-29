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
  | 'interview_questions';

// Job — maps to the backend jobs table
export interface Job {
  id: string;                   // UUID
  status: JobStatus;
  artifact_type: ArtifactType;
  repo_url: string;
  options?: Record<string, unknown>;
  created_at: string;           // ISO 8601
  updated_at: string;           // ISO 8601
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
  content_type: string;
  content_inline: string | null;
  storage_path: string | null;
  created_at: string;
}

// Graph node — from GET /api/v1/graph/nodes
export interface GraphNode {
  id: string;
  label: string;
  type: 'Repository' | 'Module' | 'File' | 'Function' | 'Class' | 'Pattern';
  properties: Record<string, unknown>;
}

// Graph edge — from GET /api/v1/graph/relationships
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: 'CONTAINS' | 'IMPORTS' | 'DEPENDS_ON' | 'EXHIBITS' | 'CALLS';
}

// API error shape returned by the FastAPI backend
export interface ApiError {
  detail: string;
  correlation_id?: string;
}
