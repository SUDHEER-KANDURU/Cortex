// =============================================================================
// Source annotations (Req 7.2)
// Derives per-line annotations for the open file directly from graph evidence:
//   • complexity — from a symbol node's `cyclomatic` property (warn when >= 10)
//   • fan-in     — count of incoming CALLS / DEPENDS_ON / EXPOSES edges (who
//                  calls or depends on the symbol). Falls back to a node
//                  property (`fan_in` / `callers`) when edges are unavailable.
//   • endpoint   — the symbol is an API endpoint (node_type === 'Endpoint',
//                  or an `is_endpoint` / `route_info` property).
//
// Everything here is deterministic and read-only: given the same nodes/edges
// it always produces the same annotations. No IO, no mutation of inputs.
// =============================================================================

import type { GraphNode, GraphEdge } from '@/types';

/** Node types that carry a source line span worth annotating. */
const SYMBOL_TYPES: ReadonlySet<GraphNode['node_type']> = new Set([
  'Function',
  'Method',
  'Class',
  'Endpoint',
]);

/** Edge relationships that count as "someone points at this symbol" (fan-in). */
const FAN_IN_RELATIONSHIPS: ReadonlySet<GraphEdge['relationship']> = new Set([
  'CALLS',
  'DEPENDS_ON',
  'EXPOSES',
]);

/** A single line's annotation derived from a symbol node. */
export interface LineAnnotation {
  /** 1-based source line the badges attach to. */
  line: number;
  symbolLabel: string;
  /** Cyclomatic complexity, when known (> 0). */
  complexity: number | null;
  /** True when complexity is at/over the high-complexity threshold. */
  complexityWarn: boolean;
  /** Incoming reference count (callers / dependents). */
  fanIn: number;
  /** True when the symbol is an API endpoint. */
  isEndpoint: boolean;
  /** Route descriptor for endpoints, when present. */
  route: string | null;
}

/** Complexity at or above this is flagged as high (matches CodeNavigator). */
export const COMPLEXITY_WARN_THRESHOLD = 10;

/** Read the owning file path off a symbol node. */
function nodeFile(node: GraphNode): string {
  const p = (node.properties.file as string) || (node.properties.path as string) || '';
  return p.replace(/\\/g, '/').replace(/^\/+/, '');
}

/** Normalize a file path for comparison (forward slashes, no leading slash). */
export function normalizePath(path: string): string {
  return (path || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

function intProp(node: GraphNode, key: string): number {
  const v = node.properties[key];
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

function isEndpointNode(node: GraphNode): boolean {
  if (node.node_type === 'Endpoint') return true;
  if (node.properties.is_endpoint) return true;
  return Boolean(node.properties.route_info);
}

/**
 * Count incoming references (fan-in) to a symbol from graph edges. When no
 * edges are supplied, fall back to a node-level count property if the backend
 * recorded one (`fan_in` or `callers`).
 */
function computeFanIn(node: GraphNode, edgesByTarget: Map<string, number>): number {
  const fromEdges = edgesByTarget.get(node.id);
  if (fromEdges != null) return fromEdges;
  const prop = intProp(node, 'fan_in') || intProp(node, 'callers');
  return prop;
}

/**
 * Build a line → annotation map for the symbols defined in `filePath`.
 *
 * Symbol nodes carry a 1-based `line` property. Each symbol in the open file
 * contributes one annotation keyed by that line. When several symbols share a
 * line (rare), the last one wins deterministically after a stable id sort.
 */
export function buildAnnotations(
  filePath: string,
  nodes: GraphNode[],
  edges: GraphEdge[] = []
): Map<number, LineAnnotation> {
  const target = normalizePath(filePath);
  const result = new Map<number, LineAnnotation>();
  if (!target) return result;

  // Precompute fan-in counts per target node from the relevant edges.
  const edgesByTarget = new Map<string, number>();
  for (const edge of edges) {
    if (!FAN_IN_RELATIONSHIPS.has(edge.relationship)) continue;
    edgesByTarget.set(edge.target_id, (edgesByTarget.get(edge.target_id) ?? 0) + 1);
  }

  // Deterministic order: sort by id so repeated builds are identical.
  const symbols = nodes
    .filter((n) => SYMBOL_TYPES.has(n.node_type) && normalizePath(nodeFile(n)) === target)
    .slice()
    .sort((a, b) => a.id.localeCompare(b.id));

  for (const node of symbols) {
    const line = intProp(node, 'line');
    if (line <= 0) continue;

    const complexity = intProp(node, 'cyclomatic');
    const fanIn = computeFanIn(node, edgesByTarget);
    const endpoint = isEndpointNode(node);
    const route = (node.properties.route_info as string) || null;

    result.set(line, {
      line,
      symbolLabel: node.label,
      complexity: complexity > 0 ? complexity : null,
      complexityWarn: complexity >= COMPLEXITY_WARN_THRESHOLD,
      fanIn,
      isEndpoint: endpoint,
      route: endpoint ? route : null,
    });
  }

  return result;
}
