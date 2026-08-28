// =============================================================================
// GraphCanvas — Interactive knowledge graph using React Flow
// Light-only. No dark mode.
// =============================================================================

'use client';

import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
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
import NavigateButton from '@/components/shared/NavigateButton';
import { emitNavigate } from '@/lib/navigate-events';

export interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── Static light-only tokens ──────────────────────────────────────────────────
const T = {
  canvasBg:        'transparent',
  dotColor:        'rgba(80,60,20,0.08)',
  edgeStroke:      'rgba(80,60,20,0.18)',
  edgeLabelFill:   '#4A4640',
  containerBorder: 'rgba(255,255,255,0.45)',
  nodeText:        '#1A1814',
  panelBg:         'rgba(255,255,255,0.50)',
  panelBorder:     'rgba(255,255,255,0.55)',
  panelText:       '#1A1814',
  panelMuted:      '#4A4640',
  panelPropBg:     'rgba(255,255,255,0.35)',
  panelPropBorder: 'rgba(255,255,255,0.50)',
  closeBtnHover:   'rgba(255,255,255,0.40)',
  minimapBg:       'rgba(255,255,255,0.30)',
  minimapBorder:   'rgba(255,255,255,0.45)',
  minimapMask:     'rgba(240,238,235,0.55)',
  controlBtn:      'rgba(255,255,255,0.50)',
  controlBtnBorder:'rgba(255,255,255,0.55)',
  controlBtnText:  '#4A4640',
};

// ── Node factory ──────────────────────────────────────────────────────────────
function toFlowNode(node: GraphNode, index: number): Node<GraphNode> {
  const color = NODE_TYPE_COLORS[node.node_type] ?? '#1E2A38';
  const delayMs = Math.min(index * 18, 600);
  return {
    id: node.id,
    position: { x: (index % 5) * 220, y: Math.floor(index / 5) * 120 },
    data: node,
    style: {
      background: `${color}22`,
      border: `0.5px solid ${color}`,
      borderRadius: '10px',
      padding: '8px 12px',
      color: '#1A1814',
      fontSize: '12px',
      fontFamily: 'ui-monospace, monospace',
      minWidth: '120px',
      opacity: 0,
      animation: 'cortex-node-in 0.35s ease forwards',
      animationDelay: `${delayMs}ms`,
      backdropFilter: 'blur(12px)',
      boxShadow:
        '0 2px 8px rgba(80,60,20,0.08),' +
        'inset 0 1px 3px rgba(255,255,255,0.55)',
    },
  };
}

// ── Edge factory ──────────────────────────────────────────────────────────────
function toFlowEdge(edge: GraphEdge): Edge {
  return {
    id: edge.id,
    source: edge.source_id,
    target: edge.target_id,
    label: edge.relationship,
    labelStyle: { fill: T.edgeLabelFill, fontSize: 10 },
    style: { stroke: T.edgeStroke, strokeWidth: 1 },
    data: edge,
  };
}

// ── Node detail panel ─────────────────────────────────────────────────────────
function NodeDetailPanel({ node, onClose }: {
  node: GraphNode;
  onClose: () => void;
}) {
  const color = NODE_TYPE_COLORS[node.node_type] ?? '#1E2A38';
  return (
    <aside
      aria-label={`Node details: ${node.label}`}
      style={{
        position: 'absolute', right: 0, top: 0, height: '100%',
        width: 'min(288px, 85%)', maxWidth: 288,
        overflowY: 'auto', zIndex: 10,
        background: T.panelBg,
        backdropFilter: 'blur(30px) saturate(180%)',
        WebkitBackdropFilter: 'blur(30px) saturate(180%)',
        borderLeft: `0.5px solid ${T.panelBorder}`,
        padding: '16px',
        boxShadow:
          '-4px 0 20px rgba(80,60,20,0.08),' +
          'inset 0 1px 3px rgba(255,255,255,0.55)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <span style={{
            display: 'inline-block', borderRadius: 9999,
            padding: '2px 10px', fontSize: 11, fontWeight: 600, marginBottom: 6,
            background: `${color}22`, color, border: `0.5px solid ${color}44`,
          }}>{node.node_type}</span>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: T.panelText, wordBreak: 'break-all', margin: 0 }}>
            {node.label}
          </h3>
        </div>
        <button
          onClick={onClose}
          aria-label="Close node details"
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            padding: 6, borderRadius: 6, color: T.panelMuted, flexShrink: 0,
            transition: 'background 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = T.closeBtnHover; (e.currentTarget as HTMLElement).style.color = T.panelText; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = T.panelMuted; }}
        >
          <X style={{ width: 14, height: 14 }} />
        </button>
      </div>

      <p style={{ fontSize: 11, color: T.panelMuted, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all', marginBottom: 12 }}>
        {node.id}
      </p>

      {/* Navigate action */}
      <div style={{ marginBottom: 12 }}>
        <NavigateButton
          onClick={() => emitNavigate({ nodeId: node.id, label: node.label, nodeType: node.node_type })}
          size="md"
          label="Navigate"
        />
      </div>

      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: T.panelMuted, marginBottom: 8 }}>
        Properties
      </p>
      {Object.keys(node.properties).length === 0 ? (
        <p style={{ fontSize: 12, color: T.panelMuted }}>No properties.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {Object.entries(node.properties).map(([key, value]) => (
            <div key={key} style={{
              borderRadius: 8, padding: '8px 12px',
              background: T.panelPropBg, border: `0.5px solid ${T.panelPropBorder}`,
            }}>
              <p style={{ fontSize: 11, fontWeight: 500, color: T.panelMuted, margin: '0 0 2px' }}>{key}</p>
              <p style={{ fontSize: 11, color: T.panelText, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all', margin: 0 }}>
                {JSON.stringify(value)}
              </p>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}

// ── Main canvas ───────────────────────────────────────────────────────────────
export default function GraphCanvas({ nodes: rawNodes, edges: rawEdges }: GraphCanvasProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const initialNodes = useMemo(() => rawNodes.map((n, i) => toFlowNode(n, i)), [rawNodes]);
  const initialEdges = useMemo(() => rawEdges.map(e => toFlowEdge(e)), [rawEdges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNode((node as Node<GraphNode>).data);
  }, []);

  if (rawNodes.length === 0) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 256, borderRadius: 16,
        border: `0.5px solid ${T.containerBorder}`,
        background: 'rgba(255,255,255,0.20)',
        backdropFilter: 'blur(20px) saturate(160%)',
        WebkitBackdropFilter: 'blur(20px) saturate(160%)',
        boxShadow: 'inset 0 2px 6px rgba(255,255,255,0.60)',
      }}>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No graph data available for this job.</p>
      </div>
    );
  }

  return (
    <div style={{
      position: 'relative', height: 'clamp(400px, 65vh, 600px)', width: '100%',
      overflow: 'hidden', borderRadius: 16,
      border: `0.5px solid ${T.containerBorder}`,
      background: 'rgba(255,255,255,0.15)',
      backdropFilter: 'blur(20px) saturate(160%)',
      WebkitBackdropFilter: 'blur(20px) saturate(160%)',
      boxShadow:
        '0 4px 24px rgba(80,60,20,0.08),' +
        'inset 0 2px 6px rgba(255,255,255,0.55),' +
        'inset 0 -4px 14px rgba(255,255,255,0.60)',
    }}>
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
        style={{ background: 'transparent' }}
        zoomOnScroll={false}
        zoomActivationKeyCode="Control"
        panOnScroll={true}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color={T.dotColor}
        />
        <Controls style={{
          '--xy-controls-button-background-color': T.controlBtn,
          '--xy-controls-button-border-color': T.controlBtnBorder,
          '--xy-controls-button-color': T.controlBtnText,
        } as React.CSSProperties} />
        <MiniMap
          nodeColor={node => NODE_TYPE_COLORS[(node as Node<GraphNode>).data?.node_type] ?? '#1E2A38'}
          style={{
            background: T.minimapBg,
            border: `0.5px solid ${T.minimapBorder}`,
            borderRadius: 8,
          }}
          maskColor={T.minimapMask}
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

