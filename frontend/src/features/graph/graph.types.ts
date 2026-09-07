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

/** Color mapping from node type to hex color.
 *  Tuned to stay legible against the dark ambient background: each hue is
 *  lightened relative to its Tailwind base so node borders and labels keep
 *  enough contrast, while remaining distinct from one another. */
export const NODE_TYPE_COLORS: Record<string, string> = {
  Repository: '#a78bfa', // violet-400
  Module:     '#60a5fa', // blue-400
  File:       '#4ade80', // green-400
  Function:   '#e8b84a', // amber
  Class:      '#fb923c', // orange-400
  Pattern:    '#f87171', // red-400
};
