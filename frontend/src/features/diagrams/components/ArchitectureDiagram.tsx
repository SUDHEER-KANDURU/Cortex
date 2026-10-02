'use client';
// =============================================================================
// ArchitectureDiagram — Interactive layered architecture explorer
//
// Uses React Flow + dagre for hierarchical layout.
// Three zoom levels: System > Module > Class.
// Health-coloured nodes, cycle highlighting, layer badges, legend.
// =============================================================================

import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeTypes,
  MarkerType,
  Position,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

import type { DiagramData, DiagramNode, DiagramEdge } from '@/lib/api/diagrams.api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ArchitectureDiagramProps {
  data: DiagramData;
  onDrillModule: (moduleName: string) => void;
  onDrillClass:  (className:  string) => void;
  onGoSystem:    () => void;
  onGoModule:    (moduleName: string) => void;
}

// ── Colour palette ────────────────────────────────────────────────────────────

const HEALTH_COLORS = {
  healthy:  { bg: 'rgba(74,222,128,0.11)',  border: '#4ADE80', text: '#BBF7D0' },
  warning:  { bg: 'rgba(232,184,74,0.13)',  border: '#E8B84A', text: '#FDE9B8' },
  critical: { bg: 'rgba(248,113,113,0.13)', border: '#F87171', text: '#FECACA' },
} as const;

const TYPE_COLORS = {
  module:   { bg: 'rgba(96,165,250,0.12)',  border: '#60A5FA', text: '#BFDBFE' },
  file:     { bg: 'rgba(167,139,250,0.12)', border: '#A78BFA', text: '#DDD6FE' },
  class:    { bg: 'rgba(74,222,128,0.11)',  border: '#4ADE80', text: '#BBF7D0' },
  function: { bg: 'rgba(232,121,249,0.12)', border: '#E879F9', text: '#F5D0FE' },
  external: { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.28)', text: 'rgba(245,239,231,0.72)' },
} as const;

const CYCLE_BORDER = '#F87171';

// Layer badge colours — subtle, informational only
const LAYER_COLORS: Record<string, string> = {
  Presentation:   '#60A5FA',
  Frontend:       '#A78BFA',
  Application:    '#34D399',
  Domain:         '#FBBF24',
  Infrastructure: '#F97316',
  Shared:         '#94A3B8',
  Testing:        '#6B7280',
};

// ── Dagre Layout ──────────────────────────────────────────────────────────────

// Node height is fixed; width is computed per-node from label length.
const NODE_HEIGHT = 76;
const NODE_WIDTH_MIN = 160;
const NODE_WIDTH_MAX = 280;
const CHAR_WIDTH_PX  = 8; // approx px per character at 13px font

function _nodeWidth(label: string): number {
  return Math.min(NODE_WIDTH_MAX, Math.max(NODE_WIDTH_MIN, label.length * CHAR_WIDTH_PX + 48));
}

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB',
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir:  direction,
    nodesep:  72,
    ranksep:  120,
    edgesep:  24,
    marginx:  40,
    marginy:  40,
    acyclicer: 'greedy',  // handles cycles gracefully
    ranker:   'network-simplex',
  });

  nodes.forEach((node) => {
    const w = _nodeWidth(String(node.data?.label ?? ''));
    g.setNode(node.id, { width: w, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id);
    const w   = _nodeWidth(String(node.data?.label ?? ''));
    return {
      ...node,
      position: {
        x: pos.x - w / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
      targetPosition: direction === 'TB' ? Position.Top    : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
    };
  });

  return { nodes: layoutedNodes, edges };
}

// ── Custom Node ───────────────────────────────────────────────────────────────

interface NodeData {
  label:        string;
  nodeType:     string;
  health:       string;
  healthReason: string;
  inCycle:      boolean;
  fileCount:    number;
  classCount:   number;
  functionCount:number;
  layer:        string;
  onClick?:     () => void;
}

function ModuleNode({ data }: { data: Record<string, unknown> }) {
  const d = data as unknown as NodeData;
  const w = _nodeWidth(d.label);

  const colors =
    d.health !== 'healthy'
      ? HEALTH_COLORS[d.health as keyof typeof HEALTH_COLORS]
      : TYPE_COLORS[d.nodeType as keyof typeof TYPE_COLORS] ?? TYPE_COLORS.module;

  const borderColor = d.inCycle ? CYCLE_BORDER : colors.border;
  const borderWidth = d.inCycle ? 3 : 2;
  const layerColor  = LAYER_COLORS[d.layer] ?? null;

  return (
    <div
      onClick={d.onClick}
      role={d.onClick ? 'button' : undefined}
      tabIndex={d.onClick ? 0 : undefined}
      onKeyDown={(e) => { if (e.key === 'Enter' && d.onClick) d.onClick(); }}
      aria-label={`${d.label} — ${d.nodeType}${d.healthReason ? ` — ${d.healthReason}` : ''}`}
      style={{
        width: w,
        minHeight: NODE_HEIGHT,
        padding: '10px 14px',
        borderRadius: 10,
        border: `${borderWidth}px solid ${borderColor}`,
        background: colors.bg,
        cursor: d.onClick ? 'pointer' : 'default',
        boxShadow: d.inCycle
          ? `0 0 14px ${CYCLE_BORDER}44`
          : '0 4px 14px rgba(0,0,0,0.32)',
        fontFamily: 'Inter, system-ui, sans-serif',
        transition: 'box-shadow 0.18s, transform 0.14s',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Layer badge */}
      {layerColor && d.nodeType === 'module' && (
        <div style={{
          position: 'absolute',
          top: 0, right: 0,
          background: `${layerColor}28`,
          borderLeft: `2px solid ${layerColor}55`,
          borderBottom: `2px solid ${layerColor}55`,
          borderRadius: '0 8px 0 6px',
          padding: '1px 6px',
          fontSize: 9,
          color: layerColor,
          fontWeight: 600,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          {d.layer}
        </div>
      )}

      {/* Label */}
      <div style={{
        fontWeight: 600,
        fontSize: 13,
        color: colors.text,
        marginBottom: 3,
        marginRight: layerColor ? 52 : 0,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}>
        {d.label}
      </div>

      {/* Subtitle */}
      <div style={{ fontSize: 11, color: 'rgba(245,239,231,0.55)', lineHeight: 1.4 }}>
        {d.nodeType === 'module' && (
          <>
            {d.fileCount > 0 && <span>{d.fileCount} file{d.fileCount !== 1 ? 's' : ''}</span>}
            {d.classCount > 0 && <span> · {d.classCount} class{d.classCount !== 1 ? 'es' : ''}</span>}
          </>
        )}
        {d.nodeType === 'class' && (
          <span>{d.functionCount} method{d.functionCount !== 1 ? 's' : ''}</span>
        )}
        {d.nodeType === 'function' && <span>method</span>}
        {d.nodeType === 'external' && (
          <span style={{ fontStyle: 'italic' }}>external</span>
        )}
      </div>

      {/* Health pill */}
      {d.healthReason && (
        <div style={{
          marginTop: 5,
          padding: '2px 6px',
          borderRadius: 4,
          fontSize: 10,
          background: d.health === 'critical'
            ? 'rgba(248,113,113,0.16)'
            : 'rgba(232,184,74,0.16)',
          color: d.health === 'critical' ? '#FECACA' : '#FDE9B8',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {d.healthReason}
        </div>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = { architectureNode: ModuleNode };

// ── Breadcrumb ────────────────────────────────────────────────────────────────

function Breadcrumb({
  items,
  onGoSystem,
  onGoModule,
}: {
  items: DiagramData['breadcrumb'];
  onGoSystem: () => void;
  onGoModule: (mod: string) => void;
}) {
  return (
    <nav
      aria-label="Diagram breadcrumb"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '8px 16px',
        fontSize: 13,
        fontFamily: 'Inter, system-ui, sans-serif',
        color: 'rgba(245,239,231,0.70)',
        borderBottom: '1px solid rgba(255,255,255,0.10)',
        background: 'rgba(255,255,255,0.04)',
        flexShrink: 0,
      }}
    >
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        const onClick = () => {
          if (item.level === 'system') onGoSystem();
          else if (item.level === 'module' && item.module) onGoModule(item.module);
        };
        return (
          <React.Fragment key={i}>
            {i > 0 && <span style={{ color: 'rgba(245,239,231,0.35)' }}>/</span>}
            {isLast ? (
              <span style={{ fontWeight: 600, color: '#F5EFE7' }}>{item.label}</span>
            ) : (
              <button
                onClick={onClick}
                style={{
                  background: 'none', border: 'none',
                  color: 'var(--primary)',
                  cursor: 'pointer', padding: 0,
                  fontSize: 13,
                  textDecoration: 'underline',
                  textUnderlineOffset: 2,
                }}
              >
                {item.label}
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

// ── Legend ────────────────────────────────────────────────────────────────────

function LegendItem({
  color, label, dashed,
}: { color: string; label: string; dashed?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 16, height: 10, borderRadius: 3,
        border: `2px ${dashed ? 'dashed' : 'solid'} ${color}`,
        background: dashed ? 'transparent' : `${color}22`,
        flexShrink: 0,
      }} />
      <span style={{ color: 'rgba(245,239,231,0.62)', fontSize: 11 }}>{label}</span>
    </div>
  );
}

function Legend() {
  return (
    <div
      aria-label="Diagram legend"
      style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        background: 'rgba(20,14,6,0.88)',
        backdropFilter: 'blur(20px) saturate(150%)',
        WebkitBackdropFilter: 'blur(20px) saturate(150%)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 10,
        padding: '12px 14px',
        zIndex: 10,
        boxShadow: '0 12px 30px rgba(0,0,0,0.44)',
        maxWidth: 'min(210px, 58%)',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8, color: '#F5EFE7', fontSize: 12 }}>
        Legend
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <LegendItem color="#22C55E" label="Healthy module" />
        <LegendItem color="#F59E0B" label="Warning (large / god class)" />
        <LegendItem color="#EF4444" label="Critical (circular dep.)" />
        <LegendItem color="#EF4444" dashed label="Cycle edge" />
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.10)', margin: '4px 0' }} />
        <div style={{ color: 'rgba(245,239,231,0.50)', lineHeight: 1.5, fontSize: 10 }}>
          Click a module to drill in.
          Edge weight = number of imports.
        </div>
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100%',
      color: 'rgba(245,239,231,0.45)',
      fontSize: 13,
      fontFamily: 'Inter, system-ui, sans-serif',
      flexDirection: 'column',
      gap: 8,
    }}>
      <div style={{ fontSize: 32, opacity: 0.4 }}>⬡</div>
      <div>No modules detected at this level.</div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function ArchitectureDiagram({
  data,
  onDrillModule,
  onDrillClass,
  onGoSystem,
  onGoModule,
}: ArchitectureDiagramProps) {
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    const rfNodes: Node[] = data.nodes.map((n: DiagramNode) => ({
      id:   n.id,
      type: 'architectureNode',
      position: { x: 0, y: 0 },
      data: {
        label:         n.label,
        nodeType:      n.type,
        health:        n.health,
        healthReason:  n.healthReason,
        inCycle:       n.inCycle,
        fileCount:     n.fileCount,
        classCount:    n.classCount,
        functionCount: n.functionCount,
        layer:         (n as DiagramNode & { layer?: string }).layer ?? '',
        onClick:
          data.level === 'system' && n.type === 'module'
            ? () => onDrillModule(n.label)
            : data.level === 'module' && n.type === 'class'
              ? () => onDrillClass(n.label)
              : undefined,
      },
    }));

    const rfEdges: Edge[] = data.edges.map((e: DiagramEdge) => ({
      id:     e.id,
      source: e.source,
      target: e.target,
      label:  e.label || undefined,
      type:   'smoothstep',
      animated: e.isCycle,
      style: {
        stroke:          e.isCycle ? CYCLE_BORDER : 'rgba(148,163,184,0.75)',
        strokeWidth:     e.isCycle ? 2.5 : Math.min(3.5, 1 + e.weight * 0.18),
        strokeDasharray: e.type === 'inherits' ? '6 3' : undefined,
      },
      labelStyle: {
        fontSize: 10,
        fill: 'rgba(245,239,231,0.65)',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      labelBgStyle: { fill: '#1A1208', fillOpacity: 0.90 },
      markerEnd: {
        type:   MarkerType.ArrowClosed,
        color:  e.isCycle ? CYCLE_BORDER : 'rgba(148,163,184,0.75)',
        width:  15,
        height: 15,
      },
    }));

    return getLayoutedElements(rfNodes, rfEdges, 'TB');
  }, [data, onDrillModule, onDrillClass]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (typeof node.data?.onClick === 'function') node.data.onClick();
    },
    [],
  );

  const isEmpty = data.nodes.length === 0;

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Breadcrumb
        items={data.breadcrumb}
        onGoSystem={onGoSystem}
        onGoModule={onGoModule}
      />

      <div style={{ flex: 1, position: 'relative', minHeight: 320 }}>
        {isEmpty ? (
          <EmptyState />
        ) : (
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            fitView
            fitViewOptions={{ padding: 0.18 }}
            minZoom={0.25}
            maxZoom={2.5}
            proOptions={{ hideAttribution: true }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            zoomOnScroll={false}
            zoomActivationKeyCode="Control"
            panOnScroll={true}
          >
            <Background color="rgba(255,255,255,0.10)" gap={22} size={1} />
            <Controls
              showInteractive={false}
              style={{ bottom: 16, right: 16 }}
            />
          </ReactFlow>
        )}
        <Legend />
      </div>
    </div>
  );
}
