// =============================================================================
// Navigate API — Full-depth code exploration
// Endpoints: GET /navigate/:jobId/:nodeId
//            GET /navigate/:jobId/:nodeId/impact
//            POST /navigate/:jobId/:nodeId/explain
// =============================================================================

import { apiClient } from './client';
import type { CortexAnswer } from '@/types';

// ─── Types ───────────────────────────────────────────────────────────────────

export type RelationshipStatus = 'detected' | 'inferred' | 'unavailable';

export type NavigationMode =
  | 'overview'
  | 'upstream'
  | 'downstream'
  | 'call_path'
  | 'dependencies'
  | 'impact'
  | 'source'
  | 'chat';

export interface SourceLocation {
  repository: string;
  file_path: string;
  line_start: number;
  line_end: number;
  symbol_name: string;
}

export interface ConnectedNode {
  id: string;
  label: string;
  node_type: string;
  relationship: string;
  relationship_status: RelationshipStatus;
  file_path: string;
  line_start: number;
}

export interface NavigateIssue {
  title: string;
  severity: string;
  category: string;
  description: string;
  recommendation: string;
  file_path: string;
  line_start: number;
  line_end: number;
  confidence: number;
}

export interface NavigateInsights {
  complexity: number;
  lines: number;
  methods: number;
  parameters: number;
  is_async: boolean;
  has_docstring: boolean;
  coupling_in: number;
  coupling_out: number;
  issues: NavigateIssue[];
  risk_factors: string[];
}

export interface CallPathNode {
  id: string;
  label: string;
  node_type: string;
  file_path: string;
  depth: number;
}

export interface CallPath {
  nodes: CallPathNode[];
  direction: string;
}

export interface NavigateResponse {
  id: string;
  label: string;
  node_type: string;
  source: SourceLocation;
  callers: ConnectedNode[];
  callees: ConnectedNode[];
  dependencies: ConnectedNode[];
  dependents: ConnectedNode[];
  related_modules: ConnectedNode[];
  tests: ConnectedNode[];
  insights: NavigateInsights;
  source_snippet: string;
  contained_by: ConnectedNode | null;
  contains: ConnectedNode[];
  breadcrumb: ConnectedNode[];
  call_paths_upstream: CallPath[];
  call_paths_downstream: CallPath[];
}

export interface NavigateExplainResponse {
  explanation: string;
  evidence_used: string[];
  confidence: number;
}

/**
 * Request body for a scoped explanation (Req 7.3). A file + line range plus an
 * optional free-text question. The job id travels as a path parameter, so it is
 * not part of the body. Mirrors the backend `ScopedExplainRequest`.
 */
export interface ScopedExplainRequest {
  file_path: string;
  line_start: number;
  line_end: number;
  question?: string;
}

// ─── API Functions ───────────────────────────────────────────────────────────

/** Get full navigation context for a graph entity */
export async function getNavigateContext(
  jobId: string,
  nodeId: string
): Promise<NavigateResponse> {
  const { data } = await apiClient.get<NavigateResponse>(
    `/navigate/${jobId}/${nodeId}`
  );
  return data;
}

/** Get impact analysis — what breaks if this entity changes */
export async function getNavigateImpact(
  jobId: string,
  nodeId: string
): Promise<ConnectedNode[]> {
  const { data } = await apiClient.get<ConnectedNode[]>(
    `/navigate/${jobId}/${nodeId}/impact`
  );
  return data;
}

/** Get AI explanation grounded in navigation evidence */
export async function getNavigateExplain(
  jobId: string,
  nodeId: string,
  question?: string
): Promise<NavigateExplainResponse> {
  const { data } = await apiClient.post<NavigateExplainResponse>(
    `/navigate/${jobId}/${nodeId}/explain`,
    { node_id: nodeId, question: question ?? '' }
  );
  return data;
}

/**
 * Scoped explanation for a file + line range (Req 7.3, Req 7.6).
 *
 * Resolves the range to the graph node(s) at those lines and returns a
 * `CortexAnswer`. When nothing is selected, callers pass the file's whole line
 * span so the backend scopes the answer to the open file (Req 7.6).
 *
 * POST /api/v1/navigate/{job_id}/explain
 */
export async function explainScope(
  jobId: string,
  request: ScopedExplainRequest
): Promise<CortexAnswer> {
  const { data } = await apiClient.post<CortexAnswer>(
    `/navigate/${jobId}/explain`,
    {
      file_path: request.file_path,
      line_start: request.line_start,
      line_end: request.line_end,
      question: request.question ?? '',
    }
  );
  return data;
}
