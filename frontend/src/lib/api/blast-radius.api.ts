// =============================================================================
// Blast Radius API — "What happens if I change this?"
// =============================================================================

import { apiClient } from './client';

export interface BlastRadiusNode {
  id: string;
  label: string;
  node_type: string;
  file_path: string;
  distance: number;
  relationship: string;
}

export interface BlastRadiusData {
  target_id: string;
  target_label: string;
  target_type: string;
  target_file: string;
  direct_dependents: BlastRadiusNode[];
  transitive_dependents: BlastRadiusNode[];
  affected_modules: string[];
  affected_tests: BlastRadiusNode[];
  risk_level: string;
  risk_score: number;
  risk_factors: string[];
  impact_paths: string[][];
}

/** Get blast radius for a node */
export async function getBlastRadius(jobId: string, nodeId: string): Promise<BlastRadiusData> {
  const { data } = await apiClient.get<BlastRadiusData>(
    `/overview/${jobId}/blast-radius/${nodeId}`
  );
  return data;
}
