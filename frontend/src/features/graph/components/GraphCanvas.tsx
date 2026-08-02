// =============================================================================
// GraphCanvas — Interactive knowledge graph using React Flow
// Fully theme-aware: reads data-theme from <html>, no hardcoded dark values.
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

export interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── Theme helpers (read at render time) ───────────────────────────────────────
function isDarkTheme(): boolean {
  if (typeof document === 'undefined') return true;
  return document.documentElement.getAttribute('data-theme') !== 'light';
}

function themeTokens() {
  const dark = isDarkTheme();
  return {
    dark,
    // Canvas background
    canvasBg:       dark ? '#060810' : '#f6f8fc',
    // Dot / grid color
    dotColor:       dark ? '#1e2533' : '#d1d5db',
    // Edge line color
    edgeStroke:     dark ? '#334155' : '#94a3b8',
    edgeLabelFill:  dark ? '#94a3b8' : '#64748b',
    // Container border
    containerBorder:dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.09)',
    // Node text color — ensure contrast on both themes
    nodeText:       dark ? '#e2e8f0' : '#1e293b',
    // Detail panel
    panelBg:        dark ? '#0f1117' : '#ffffff',
    panelBorder:    dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.10)',
    panelText:      dark ? '#f1f5f9' : '#1e293b',
    panelMuted:     dark ? '#94a3b8' : '#64748b',
    panelPropBg:    dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)',
    panelPropBorder:dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
    closeBtnHover:  dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
    // MiniMap
    minimapBg:      dark ? '#0f1117' : '#f8fafc',
    minimapBorder:  dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.09)',
    minimapMask:    dark ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.5)',
    // Controls
    controlBtn:     dark ? '#1e2533' : '#ffffff',
    controlBtnBorder:dark? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.12)',
    controlBtnText: dark ? '#94a3b8' : '#475569',
  };
}

// ── Node factory ──────────────────────────────────────────────────────────────
function toFlowNode(node: GraphNode, index: number, dark: boolean): Node<GraphNode> {
  const color = NODE_TYPE_COLORS[node.type] ?? '#64748b';
  return {
    id: node.id,
    position: { x: (index % 5) * 220, y: Math.floor(index / 5) * 120 },
    data: node,
    style: {
      background: dark ? `${color}22` : `${color}18`,
      border: `1px solid ${color}`,
      borderRadius: '8px',
      padding: '8px 12px',
      // Node text: always readable against the node bg
      color: dark ? '#e2e8f0' : '#1e293b',
      fontSize: '12px',
      fontFamily: 'ui-monospace, monospace',
      minWidth: '120px',
    },
  };
}

// ── Edge factory ──────────────────────────────────────────────────────────────
function toFlowEdge(edge: GraphEdge, t: ReturnType<typeof themeTokens>): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relationship,
    labelStyle: { fill: t.edgeLabelFill, fontSize: 10 },
    style: { stroke: t.edgeStroke, strokeWidth: 1 },
    data: edge,
  };
}

// ── Node detail panel ─────────────────────────────────────────────────────────
function NodeDetailPanel({ node, onClose, t }: {
  node: GraphNode;
  onClose: () => void;
  t: ReturnType<typeof themeTokens>;
}) {
  const color = NODE_TYPE_COLORS[node.type] ?? '#64748b';
  return (
    <aside
      aria-label={`Node details: ${node.label}`}
      style={{
        position: 'absolute', right: 0, top: 0, height: '100%', width: 288,
        overflowY: 'auto', zIndex: 10,
        background: t.panelBg,
        borderLeft: `1px solid ${t.panelBorder}`,
        padding: '16px',
        boxShadow: t.dark ? '-8px 0 32px rgba(0,0,0,0.4)' : '-4px 0 16px rgba(0,0,0,0.08)',
        transition: 'background 0.3s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <span style={{
            display: 'inline-block', borderRadius: 9999,
            padding: '2px 10px', fontSize: 11, fontWeight: 600, marginBottom: 6,
            background: `${color}22`, color, border: `1px solid ${color}44`,
          }}>{node.type}</span>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: t.panelText, wordBreak: 'break-all', margin: 0 }}>
            {node.label}
          </h3>
        </div>
        <button
          onClick={onClose}
          aria-label="Close node details"
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            padding: 6, borderRadius: 6, color: t.panelMuted, flexShrink: 0,
            transition: 'background 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = t.closeBtnHover; (e.currentTarget as HTMLElement).style.color = t.panelText; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = t.panelMuted; }}
        >
          <X style={{ width: 14, height: 14 }} />
        </button>
      </div>

      <p style={{ fontSize: 11, color: t.panelMuted, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all', marginBottom: 12 }}>
        {node.id}
      </p>

      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: t.panelMuted, marginBottom: 8 }}>
        Properties
      </p>
      {Object.keys(node.properties).length === 0 ? (
        <p style={{ fontSize: 12, color: t.panelMuted }}>No properties.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {Object.entries(node.properties).map(([key, value]) => (
            <div key={key} style={{
              borderRadius: 8, padding: '8px 12px',
              background: t.panelPropBg, border: `1px solid ${t.panelPropBorder}`,
            }}>
              <p style={{ fontSize: 11, fontWeight: 500, color: t.panelMuted, margin: '0 0 2px' }}>{key}</p>
              <p style={{ fontSize: 11, color: t.panelText, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all', margin: 0 }}>
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
  const t = themeTokens();

  const initialNodes = useMemo(() => rawNodes.map((n, i) => toFlowNode(n, i, t.dark)), [rawNodes, t.dark]);
  const initialEdges = useMemo(() => rawEdges.map(e => toFlowEdge(e, t)), [rawEdges, t]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNode((node as Node<GraphNode>).data);
  }, []);

  if (rawNodes.length === 0) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 256, borderRadius: 12,
        border: `1px solid ${t.containerBorder}`,
        background: t.canvasBg,
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No graph data available for this job.</p>
      </div>
    );
  }

  return (
    <div style={{
      position: 'relative', height: 600, width: '100%',
      overflow: 'hidden', borderRadius: 12,
      border: `1px solid ${t.containerBorder}`,
      background: t.canvasBg,
      transition: 'background 0.3s ease, border-color 0.3s ease',
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
        style={{ background: t.canvasBg }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color={t.dotColor}
        />
        <Controls style={{
          '--xy-controls-button-background-color': t.controlBtn,
          '--xy-controls-button-border-color': t.controlBtnBorder,
          '--xy-controls-button-color': t.controlBtnText,
        } as React.CSSProperties} />
        <MiniMap
          nodeColor={node => NODE_TYPE_COLORS[(node as Node<GraphNode>).data?.type] ?? '#64748b'}
          style={{
            background: t.minimapBg,
            border: `1px solid ${t.minimapBorder}`,
            borderRadius: 8,
          }}
          maskColor={t.minimapMask}
        />
      </ReactFlow>

      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          t={t}
        />
      )}
    </div>
  );
}

