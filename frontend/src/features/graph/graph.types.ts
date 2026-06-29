// =============================================================================
// Graph Feature — Local Types
// Types specific to the graph visualization feature.
// Extends the shared GraphNode/GraphEdge types with React Flow specifics.
// =============================================================================

import type { Node as RFNode, Edge as RFEdge } from 'reactflow';
import type { GraphNode, GraphEdge } from '@/types';

/** React Flow node with Cortex graph node data attached */
export type CortexFlowNode = RFNode<GraphNode>;

/** React Flow edge with Cortex graph edge data attached */
export type CortexFlowEdge = RFEdge<GraphEdge>;

/** State managed by the useGraphData hook */
export interface GraphDataState {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isLoading: boolean;
  error: string | null;
}

/** Color mapping from node type to Tailwind/hex color */
export const NODE_TYPE_COLORS: Record<string, string> = {
  Repository: '#7c3aed', // purple-700
  Module: '#2563eb',     // blue-600
  File: '#16a34a',       // green-600
  Function: '#ca8a04',   // yellow-600
  Class: '#ea580c',      // orange-600
  Pattern: '#dc2626',    // red-600
};
