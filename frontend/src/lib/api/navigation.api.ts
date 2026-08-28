// =============================================================================
// Navigation API — Code navigation / node detail
// =============================================================================

import { apiClient } from './client';

export interface NodeConnection {
  id: string;
  label: string;
  type: string;
  relationship: string;
}

export interface NodeChild {
  id: string;
  label: string;
  type: string;
}

export interface NodeDetailData {
  id: string;
  label: string;
  node_type: string;
  properties: Record<string, unknown>;
  callers: NodeConnection[];
  callees: NodeConnection[];
  contained_by: string | null;
  contains: NodeChild[];
}

/** Get full detail for a graph node including connections */
export async function getNodeDetail(jobId: string, nodeId: string): Promise<NodeDetailData> {
  const { data } = await apiClient.get<NodeDetailData>(
    `/overview/${jobId}/node/${nodeId}`
  );
  return data;
}
