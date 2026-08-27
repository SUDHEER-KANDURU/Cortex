'use client';
// =============================================================================
// ArchitectureDiagram — Interactive layered architecture explorer
//
// Uses React Flow + dagre for hierarchical layout.
// Three zoom levels: System > Module > Class.
// Health-colored nodes, cycle highlighting, legend, breadcrumb navigation.
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

// ── Types ────────────────────────────────────────────────────────────────────

interface ArchitectureDiagramProps {
  data: DiagramData;
  onDrillModule: (moduleName: string) => void;
  onDrillClass: (className: string) => void;
  onGoSystem: () => void;
  onGoModule: (moduleName: string) => void;
}

// ── Health Colors ────────────────────────────────────────────────────────────

const HEALTH_COLORS = {
  healthy: { bg: '#F0FDF4', border: '#22C55E', text: '#15803D' },
  warning: { bg: '#FFFBEB', border: '#F59E0B', text: '#92400E' },
  critical: { bg: '#FEF2F2', border: '#EF4444', text: '#991B1B' },
} as const;

const TYPE_COLORS = {
  module: { bg: '#EFF6FF', border: '#3B82F6', text: '#1E40AF' },
  file: { bg: '#F5F3FF', border: '#8B5CF6', text: '#5B21B6' },
  class: { bg: '#ECFDF5', border: '#10B981', text: '#065F46' },
  function: { bg: '#FDF4FF', border: '#D946EF', text: '#86198F' },
  external: { bg: '#F9FAFB', border: '#9CA3AF', text: '#4B5563' },
} as const;

const CYCLE_BORDER = '#EF4444';

// ── Dagre Layout ─────────────────────────────────────────────────────────────

const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: direction,
    nodesep: 60,
    ranksep: 100,
    edgesep: 30,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
    };
  });

  return { nodes: layoutedNodes, edges };
}

// ── Custom Node Component ────────────────────────────────────────────────────

function ModuleNode({ data }: { data: Record<string, unknown> }) {
  const nodeData = data as {
    label: string;
    nodeType: string;
    health: string;
    healthReason: string;
    inCycle: boolean;
    fileCount: number;
    classCount: number;
    functionCount: number;
    onClick?: () => void;
  };

  const colors = nodeData.health !== 'healthy'
    ? HEALTH_COLORS[nodeData.health as keyof typeof HEALTH_COLORS]
    : TYPE_COLORS[nodeData.nodeType as keyof typeof TYPE_COLORS] || TYPE_COLORS.module;

  const borderColor = nodeData.inCycle ? CYCLE_BORDER : colors.border;
  const borderWidth = nodeData.inCycle ? 3 : 2;

  // Size based on file count (min 180, max 240)
  const width = Math.min(240, Math.max(180, 180 + (nodeData.fileCount || 0) * 4));

  return (
    <div
      onClick={nodeData.onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' && nodeData.onClick) nodeData.onClick(); }}
      aria-label={`${nodeData.label} - ${nodeData.nodeType}${nodeData.healthReason ? ` - ${nodeData.healthReason}` : ''}`}
      style={{
        width,
        padding: '12px 16px',
        borderRadius: 12,
        border: `${borderWidth}px solid ${borderColor}`,
        background: colors.bg,
        cursor: nodeData.onClick ? 'pointer' : 'default',
        boxShadow: nodeData.inCycle
          ? `0 0 12px ${CYCLE_BORDER}40`
          : '0 2px 8px rgba(0,0,0,0.06)',
        transition: 'box-shadow 0.2s, transform 0.15s',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div style={{
        fontWeight: 600,
        fontSize: 13,
        color: colors.text,
        marginBottom: 4,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}>
        {nodeData.label}
      </div>
      <div style={{ fontSize: 11, color: '#6B7280', lineHeight: 1.4 }}>
        {nodeData.nodeType === 'module' && (
          <>
            {nodeData.fileCount > 0 && <span>{nodeData.fileCount} files</span>}
            {nodeData.classCount > 0 && <span> &middot; {nodeData.classCount} classes</span>}
          </>
        )}
        {nodeData.nodeType === 'class' && (
          <span>{nodeData.functionCount} methods</span>
        )}
        {nodeData.nodeType === 'function' && (
          <span>method</span>
        )}
        {nodeData.nodeType === 'external' && (
          <span style={{ fontStyle: 'italic' }}>external dep</span>
        )}
      </div>
      {nodeData.healthReason && (
        <div style={{
          fontSize: 10,
          marginTop: 4,
          padding: '2px 6px',
          borderRadius: 4,
          background: nodeData.health === 'critical' ? '#FEE2E2' : '#FEF3C7',
          color: nodeData.health === 'critical' ? '#991B1B' : '#92400E',
        }}>
          {nodeData.healthReason}
        </div>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = {
  architectureNode: ModuleNode,
};

// ── Breadcrumb ───────────────────────────────────────────────────────────────

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
    <nav aria-label="Diagram breadcrumb" style={{
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: '8px 16px',
      fontSize: 13,
      fontFamily: 'Inter, system-ui, sans-serif',
      color: '#4B5563',
      borderBottom: '1px solid #E5E7EB',
      background: '#FAFAFA',
    }}>
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        const handleClick = () => {
          if (item.level === 'system') onGoSystem();
          else if (item.level === 'module' && item.module) onGoModule(item.module);
        };
        return (
          <React.Fragment key={i}>
            {i > 0 && <span style={{ color: '#9CA3AF' }}>/</span>}
            {isLast ? (
              <span style={{ fontWeight: 600, color: '#111827' }}>{item.label}</span>
            ) : (
              <button
                onClick={handleClick}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#3B82F6',
                  cursor: 'pointer',
                  padding: 0,
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

function Legend() {
  return (
    <div
      aria-label="Diagram legend"
      style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        background: '#FFFFFF',
        border: '1px solid #E5E7EB',
        borderRadius: 10,
        padding: '12px 16px',
        fontSize: 11,
        fontFamily: 'Inter, system-ui, sans-serif',
        zIndex: 10,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        maxWidth: 220,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8, color: '#111827', fontSize: 12 }}>
        Legend
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <LegendItem color="#22C55E" label="Healthy" />
        <LegendItem color="#F59E0B" label="Warning (god class / large module)" />
        <LegendItem color="#EF4444" label="Critical (circular dependency)" />
        <LegendItem color="#EF4444" dashed label="Cycle edge" />
        <div style={{ borderTop: '1px solid #E5E7EB', margin: '4px 0' }} />
        <div style={{ color: '#6B7280', lineHeight: 1.4 }}>
          Node size reflects file count. Click a node to drill down.
        </div>
      </div>
    </div>
  );
}

function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 16,
        height: 10,
        borderRadius: 3,
        border: `2px ${dashed ? 'dashed' : 'solid'} ${color}`,
        background: dashed ? 'transparent' : `${color}20`,
      }} />
      <span style={{ color: '#4B5563' }}>{label}</span>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function ArchitectureDiagram({
  data,
  onDrillModule,
  onDrillClass,
  onGoSystem,
  onGoModule,
}: ArchitectureDiagramProps) {
  // Convert API data to React Flow nodes and edges
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    const rfNodes: Node[] = data.nodes.map((n: DiagramNode) => ({
      id: n.id,
      type: 'architectureNode',
      position: { x: 0, y: 0 }, // Will be set by dagre
      data: {
        label: n.label,
        nodeType: n.type,
        health: n.health,
        healthReason: n.healthReason,
        inCycle: n.inCycle,
        fileCount: n.fileCount,
        classCount: n.classCount,
        functionCount: n.functionCount,
        // Click handler based on level and type
        onClick:
          data.level === 'system' && n.type === 'module'
            ? () => onDrillModule(n.label)
            : data.level === 'module' && n.type === 'class'
              ? () => onDrillClass(n.label)
              : undefined,
      },
    }));

    const rfEdges: Edge[] = data.edges.map((e: DiagramEdge) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label || undefined,
      type: 'smoothstep',
      animated: e.isCycle,
      style: {
        stroke: e.isCycle ? CYCLE_BORDER : '#94A3B8',
        strokeWidth: e.isCycle ? 2.5 : Math.min(3, 1 + e.weight * 0.15),
        strokeDasharray: e.type === 'inherits' ? '6 3' : undefined,
      },
      labelStyle: {
        fontSize: 10,
        fill: '#6B7280',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      labelBgStyle: {
        fill: '#FFFFFF',
        fillOpacity: 0.9,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.isCycle ? CYCLE_BORDER : '#94A3B8',
        width: 16,
        height: 16,
      },
    }));

    // Apply dagre layout
    return getLayoutedElements(rfNodes, rfEdges, 'TB');
  }, [data, onDrillModule, onDrillClass]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const handler = node.data?.onClick;
      if (typeof handler === 'function') handler();
    },
    []
  );

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Breadcrumb */}
      <Breadcrumb
        items={data.breadcrumb}
        onGoSystem={onGoSystem}
        onGoModule={onGoModule}
      />

      {/* React Flow Canvas */}
      <div style={{ flex: 1, position: 'relative', minHeight: 500 }}>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Background color="#E5E7EB" gap={20} size={1} />
          <Controls
            showInteractive={false}
            style={{ bottom: 16, right: 16 }}
          />
        </ReactFlow>
        <Legend />
      </div>
    </div>
  );
}
