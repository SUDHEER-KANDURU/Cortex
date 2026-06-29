// =============================================================================
// GraphCanvas — Interactive code knowledge graph using React Flow
// Color-codes nodes by type, supports zoom/pan/fit-view, side panel on click.
// =============================================================================

'use client';

import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type NodeTypes,
  type Node,
  type Edge,
  type NodeMouseHandler,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { X } from 'lucide-react';
import type { GraphNode, GraphEdge } from '@/types';
import { NODE_TYPE_COLORS } from '@/features/graph/graph.types';

export interface GraphCanvasProps {
  /** Graph nodes from the Cortex API */
  nodes: GraphNode[];
  /** Graph edges from the Cortex API */
  edges: GraphEdge[];
}

/** Convert Cortex GraphNode → React Flow Node */
function toFlowNode(node: GraphNode, index: number): Node<GraphNode> {
  const color = NODE_TYPE_COLORS[node.type] ?? '#64748b';
  return {
    id: node.id,
    position: {
      // Simple grid layout — a layout algorithm can be added later
      x: (index % 5) * 220,
      y: Math.floor(index / 5) * 120,
    },
    data: node,
    style: {
      background: `${color}22`,
      border: `1px solid ${color}`,
      borderRadius: '8px',
      padding: '8px 12px',
      color: '#e2e8f0',
      fontSize: '12px',
      fontFamily: 'ui-monospace, monospace',
      minWidth: '120px',
    },
  };
}

/** Convert Cortex GraphEdge → React Flow Edge */
function toFlowEdge(edge: GraphEdge): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relationship,
    labelStyle: { fill: '#94a3b8', fontSize: 10 },
    style: { stroke: '#475569', strokeWidth: 1 },
    data: edge,
  };
}

/** Side panel showing node properties */
function NodeDetailPanel({
  node,
  onClose,
}: {
  node: GraphNode;
  onClose: () => void;
}) {
  const color = NODE_TYPE_COLORS[node.type] ?? '#64748b';

  return (
    <aside
      className="absolute right-0 top-0 h-full w-72 overflow-y-auto border-l border-gray-700 bg-gray-900 p-4 shadow-xl z-10"
      aria-label={`Node details: ${node.label}`}
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <span
            className="inline-block rounded-full px-2 py-0.5 text-xs font-medium mb-1"
            style={{ background: `${color}33`, color }}
          >
            {node.type}
          </span>
          <h3 className="text-sm font-semibold text-white break-all">{node.label}</h3>
        </div>
        <button
          onClick={onClose}
          aria-label="Close node details"
          className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className="mb-2 text-xs text-gray-500 font-mono break-all">{node.id}</p>

      <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
        Properties
      </h4>
      {Object.keys(node.properties).length === 0 ? (
        <p className="text-xs text-gray-600">No properties.</p>
      ) : (
        <dl className="flex flex-col gap-2">
          {Object.entries(node.properties).map(([key, value]) => (
            <div key={key} className="rounded bg-gray-800 px-3 py-2">
              <dt className="text-xs font-medium text-gray-400">{key}</dt>
              <dd className="mt-0.5 break-all text-xs text-gray-300 font-mono">
                {JSON.stringify(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </aside>
  );
}

export default function GraphCanvas({ nodes: rawNodes, edges: rawEdges }: GraphCanvasProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const initialNodes = useMemo(
    () => rawNodes.map((n, i) => toFlowNode(n, i)),
    [rawNodes]
  );
  const initialEdges = useMemo(
    () => rawEdges.map(toFlowEdge),
    [rawEdges]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    const cortexNode = (node as Node<GraphNode>).data;
    setSelectedNode(cortexNode);
  }, []);

  if (rawNodes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-700 bg-gray-900">
        <p className="text-sm text-gray-500">No graph data available for this job.</p>
      </div>
    );
  }

  return (
    <div className="relative h-[600px] w-full overflow-hidden rounded-lg border border-gray-700 bg-gray-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        attributionPosition="bottom-left"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="#334155"
        />
        <Controls
          className="[&>button]:bg-gray-800 [&>button]:border-gray-700 [&>button]:text-gray-300"
        />
        <MiniMap
          nodeColor={(node) => {
            const data = (node as Node<GraphNode>).data;
            return NODE_TYPE_COLORS[data?.type] ?? '#64748b';
          }}
          className="bg-gray-900 border border-gray-700 rounded"
          maskColor="rgba(0,0,0,0.6)"
        />
      </ReactFlow>

      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
